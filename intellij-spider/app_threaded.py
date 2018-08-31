import pathlib
from collections import defaultdict

import json
import time
import datetime

from app import BaseApp
from rule.rule import Rule
from task import Task
from threading import Thread
import queue
from config import *
from config import get_app_config
from common.log import logger
from common.util import writelines

'''
主应用：使用多线程处理并发
'''


class DataQueue(queue.Queue):
    def put(self, item, block=True, timeout=None):
        if not get_app_config().no_save:
            return super().put(item, block, timeout)
        else:
            return None


class Queue(queue.Queue):
    @classmethod
    def now(cls):
        return datetime.datetime.now()

    def put(self, item, block=True, timeout=None):
        t = self.now()
        ret = super().put(item, block, timeout)
        dt = (self.now() - t).microseconds // 1000
        if dt > 500:
            logger.info('Put object takes {} ms, qsize: {}'.format(dt, self.qsize()))
        return ret

    def get(self, block=True, timeout=None):
        t = self.now()
        ret = super().get(block, timeout)
        dt = (self.now() - t).microseconds // 1000
        if dt > 500:
            logger.info('Get object takes {} ms, qsize: {}'.format(dt, self.qsize()))
        return ret


class Job(object):
    """
    (多线程)爬虫应用框架，用于创建一个定时抓取任务，只需要指定抓取入口链接和对应的解析规则即可，
    后续提取和链接会自动添加到抓取队列，例如：
    my_app = App('myApp', url='http://www.sina.com', rule_name='sina')
    my_app.schedule()
    """

    def __init__(self, name: str, urls: list, rule_name: str, normal_thread_count=2):
        """
        初始化一个抓取应用
        :param name: 应用名
        :param url: 入口链接
        :param rule_name: 入口链接内容对应的解析规则
        """
        self._name = name
        self._urls = urls
        self._rule_name = rule_name

        # 不使用代理的下载queue1/worker_normal_threads
        self.task_normal_queue = None
        self.worker_normal_threads = []
        self.normal_thread_count = 1

        # 解析结果存储 data_queue / store_thread
        self.data_queue = None
        self.store_thread = None

        self.is_running = False
        self.normal_thread_count = normal_thread_count

    @property
    def name(self):
        return self._name

    @classmethod
    def is_proxy_url(cls, url):
        pm = get_app_config().proxy_mapping
        return pm.get_url_proxy(url) is not None

    @classmethod
    def run_worker(cls, app):
        task_queue = app.task_normal_queue
        while app.is_running:
            try:
                task = task_queue.get(block=False)
            except queue.Empty as e:
                time.sleep(0.1)
                continue
            tr = task.execute()
            if tr.sub_tasks:
                for t in tr.sub_tasks:
                    app.task_normal_queue.put(t)
                    logger.info('Add to task queue(normal):{}, {}'.format(t.url, app.task_normal_queue.qsize()))

            if tr.data:
                app.data_queue.put((task, tr.data))
        logger.info('Task 1 thread done !')

    @classmethod
    def run_store(cls, job):
        index, count = 0, 0
        base_path = pathlib.Path(OUTPUT_DIR) / job.name / cls.now()
        while job.is_running:
            # 每10s存储一次数据
            time.sleep(10)
            grouped_data = defaultdict(lambda: [])
            while 1:
                try:
                    task, data = job.data_queue.get(block=False)
                    grouped_data[task.rule.name].append(data)
                except queue.Empty:
                    break

            if not grouped_data:
                continue

            for rule_name, data_list in grouped_data.items():
                path = base_path / '{}.txt'.format(rule_name)
                writelines(data_list, path)
            index, count = index + 1, count + len(grouped_data)
            logger.info('Store index: {}, count:{}'.format(index, count))

        logger.info('Storing thread done !')

    @classmethod
    def now(cls):
        return datetime.datetime.now().date().isoformat()

    def start_all_threads(self):
        self.is_running = True

        self.task_normal_queue = Queue()
        for url in self._urls:
            self.task_normal_queue.put(Task(url=url, rule=Rule.find_by_name(self._rule_name)))
        self.worker_normal_threads = [Thread(target=self.run_worker, args=(self,)) for i in
                                      range(self.normal_thread_count)]

        self.data_queue = DataQueue()
        self.store_thread = Thread(target=self.run_store, args=(self,))

        for t in self.worker_normal_threads:
            t.start()
            time.sleep(0.5)

        self.store_thread.start()

    def shutdown_all_threads(self):
        logger.info('Start shut down all threads')
        self.is_running = False
        for thread in self.worker_normal_threads:
            logger.info('Wait work1 thread end:', thread.name)
            if thread.isAlive():
                thread.join()
        logger.info('Wait store thread end')
        if self.store_thread and self.store_thread.isAlive():
            self.store_thread.join()
        logger.info('End shut down all threads')

    def start(self):
        return self.start_all_threads()

    def stop(self):
        return self.shutdown_all_threads()


class App(BaseApp):
    """
    (多线程)爬虫应用框架，用于创建一个定时抓取任务，只需要指定抓取入口链接和对应的解析规则即可，
    后续提取和链接会自动添加到抓取队列，例如：
    my_app = App('myApp', url='http://www.sina.com', rule_name='sina')
    my_app.schedule()
    """

    def __init__(self, name: str, url: (str, list), rule_name: str):
        """
        初始化一个抓取应用
        :param name: 应用名
        :param url: 入口链接
        :param rule_name: 入口链接内容对应的解析规则
        """
        super(App, self).__init__(name, url, rule_name)

    def start_job(self):
        job = Job(self.name, self.urls, self.rule_name, self.normal_thread_count)
        job.start()

    def schedule(self, normal_thread_count=2):
        self.normal_thread_count = normal_thread_count
        self.start_job()


if __name__ == '__main__':
    get_app_config().proxy_mapping = ProxyMapping.of_asdl_high()
    app = App('sync_app', rule_name='jd_page', url='https://list.jd.hk/list.html?cat=1316,1381,1389&page=1')
    app.schedule()
