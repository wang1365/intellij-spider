import pathlib
from collections import defaultdict

import schedule
import json
import time
import datetime
from rule.rule import Rule
from task import Task
from threading import Thread
import queue
from config import *


class Queue(queue.Queue):
    @classmethod
    def now(cls):
        return datetime.datetime.now()

    def put(self, item, block=True, timeout=None):
        t = self.now()
        ret = super().put(item, block, timeout)
        dt = (self.now() - t).microseconds // 1000
        if dt > 500:
            print('Put object takes {} ms, qsize: {}'.format(dt, self.qsize()))
        return ret

    def get(self, block=True, timeout=None):
        t = self.now()
        ret = super().get(block, timeout)
        dt = (self.now() - t).microseconds // 1000
        if dt > 500:
            print('Get object takes {} ms, qsize: {}'.format(dt, self.qsize()))
        return ret


class App(object):
    """
    (多线程)爬虫应用框架，用于创建一个定时抓取任务，只需要指定抓取入口链接和对应的解析规则即可，
    后续提取和链接会自动添加到抓取队列，例如：
    my_app = App('myApp', url='http://www.sina.com', rule_name='sina')
    my_app.schedule()
    """

    def __init__(self, name: str, url: str, rule_name: str):
        """
        初始化一个抓取应用
        :param name: 应用名
        :param url: 入口链接
        :param rule_name: 入口链接内容对应的解析规则
        """
        self._name = name
        self._url = url
        self._rule_name = rule_name

        # 不使用代理的下载queue1/worker_normal_threads
        self._task_normal_queue = None
        self._worker_normal_threads = []
        self._normal_thread_count = 1

        # 使用代理的下载queue2/worker_proxy_threads
        self._task_proxy_queue = None
        self._worker_proxy_threads = []
        self._proxy_thread_count = 1

        # 解析结果存储 data_queue / store_thread
        self._data_queue = None
        self._store_thread = None

        self._is_running = False

    @property
    def task_normal_queue(self):
        return self._task_normal_queue

    @property
    def task_proxy_queue(self):
        return self._task_proxy_queue

    @property
    def data_queue(self):
        return self._data_queue

    @property
    def name(self):
        return self._name

    @property
    def worker_normal_threads(self):
        return self._worker_normal_threads

    @property
    def worker_proxy_threads(self):
        return self._worker_proxy_threads

    @property
    def store_thread(self):
        return self._store_thread

    @classmethod
    def is_proxy_url(cls, url):
        pm = app_config.proxy_mapping
        return pm.get_url_proxy(url) is not None

    @property
    def is_running(self):
        return self._is_running

    @classmethod
    def run_worker1(cls, app):
        while app.is_running:
            try:
                task = app.task_normal_queue.get()
            except queue.Empty as e:
                time.sleep(0.1)
                continue
            tr = task.execute()
            if tr.sub_tasks:
                for t in tr.sub_tasks:
                    if cls.is_proxy_url(t.url):
                        app.task_proxy_queue.put(t)
                        print('Add to task queue(proxy):', t.url, app.task_proxy_queue.qsize())
                    else:
                        app.task_normal_queue.put(t)
                        print('Add to task queue(normal):', t.url, app.task_normal_queue.qsize())

            if tr.data:
                app.data_queue.put((task, tr.data))
        print('Task 1 thread done !')

    @classmethod
    def run_worker2(cls, app):
        while app.is_running:
            try:
                task = app.task_proxy_queue.get(block=False)
            except queue.Empty as e:
                time.sleep(0.1)
                continue
            tr = task.execute()
            if tr.sub_tasks:
                for t in tr.sub_tasks:
                    if cls.is_proxy_url(t.url):
                        app.task_proxy_queue.put(t)
                        print('Add to task queue(proxy):', t.url, app.task_proxy_queue.qsize())
                    else:
                        app.task_normal_queue.put(t)
                        print('Add to task queue(normal):', t.url, app.task_normal_queue.qsize())

            if tr.data:
                app.data_queue.put((task, tr.data))
        print('Task 2 thread done !')

    @classmethod
    def run_store(cls, app):
        while app.is_running:
            grouped_data = defaultdict(lambda: [])
            while 1:
                try:
                    task, data = app.data_queue.get(block=False)
                    grouped_data[task.rule.name].append(data)
                except queue.Empty:
                    break

            if not grouped_data:
                time.sleep(0.1)
                continue

            for rule_name, data_list in grouped_data.items():
                path = pathlib.Path(OUTPUT_DIR) / '{}/{}/{}.txt'.format(app.name, cls.now(), rule_name)
                if not path.parent.exists():
                    path.parent.mkdir(parents=True)

                with path.open('a', encoding='utf8') as f:
                    for data in data_list:
                        f.writelines(json.dumps(data, ensure_ascii=False) + '\n')

        print('Storing thread done !')

    @classmethod
    def now(cls):
        return datetime.datetime.now().date().isoformat()

    def start_all_threads(self):
        self.shutdown_all_threads()

        self._is_running = True

        self._task_normal_queue = Queue()
        self._task_normal_queue.put(Task(url=self._url, rule=Rule.find_by_name(self._rule_name)))
        self._worker_normal_threads = [Thread(target=self.run_worker1, args=(self,)) for i in
                                       range(self._normal_thread_count)]

        self._task_proxy_queue = Queue()
        self._worker_proxy_threads = [Thread(target=self.run_worker2, args=(self,)) for i in
                                      range(self._proxy_thread_count)]

        self._data_queue = Queue()
        self._store_thread = Thread(target=self.run_store, args=(self,))

        for t in self._worker_normal_threads:
            t.start()
        for t in self._worker_proxy_threads:
            t.start()
        self._store_thread.start()

    def shutdown_all_threads(self):
        print('Start shut down all threads')
        self._is_running = False
        for thread in self._worker_normal_threads:
            print('Wait work1 thread end:', thread.name)
            if thread.isAlive():
                thread.join()
        for thread in self._worker_proxy_threads:
            print('Wait work2 thread end:', thread.name)
            if thread.isAlive():
                thread.join()
        print('Wait store thread end')
        if self._store_thread and self._store_thread.isAlive():
            self._store_thread.join()
        print('End shut down all threads')

    def schedule(self, normal_thread_count=2, proxy_thread_count=10, start_time=None, interval_days=1):
        self._normal_thread_count, self._proxy_thread_count = normal_thread_count, proxy_thread_count

        # 如果没有设置开始时间，则立即执行，否则定时执行
        if not start_time:
            self.start_all_threads()
        else:
            print('Start at {} everyday'.format(start_time))
            schedule.every(interval_days).day.at(start_time).do(self.start_all_threads)
            while True:
                schedule.run_pending()
                time.sleep(1)


if __name__ == '__main__':
    app_config.proxy_mapping = ProxyMapping.of_asdl_high()
    app = App('sync_app', rule_name='jd_page', url='https://list.jd.hk/list.html?cat=1316,1381,1389&page=1')
    app.schedule()
