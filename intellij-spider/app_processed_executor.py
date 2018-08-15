import pathlib
from collections import defaultdict

import json
import datetime
from rule.rule import Rule
from task import Task
from config import *
from network.urlloader import Url
from config import app_config
from multiprocessing import Process, Queue, Lock, Manager
from queue import Empty
import os, signal, time
from concurrent.futures import ProcessPoolExecutor



class QueueWithLock(object):
    def __init__(self):
        manager = Manager()
        self.lock = manager.Lock()
        self.q = manager.Queue()

    @classmethod
    def now(cls):
        return datetime.datetime.now()

    def put(self, item, block=True, timeout=None):
        try:
            self.lock.acquire()
            t = self.now()
            ret = self.q.put(item, block, timeout)
            dt = (self.now() - t).microseconds // 1000
            if dt > 500:
                print('Put object takes {} ms, qsize: {}'.format(dt, self.qsize()))
        except Exception as e:
            print(e)
            raise e
        finally:
            self.lock.release()
        return ret

    def get(self, block=True, timeout=None):
        try:
            self.lock.acquire()
            t = self.now()
            ret = self.q.get(block, timeout)
            dt = (self.now() - t).microseconds // 1000
            if dt > 500:
                print('Get object takes {} ms, qsize: {}'.format(dt, self.qsize()))
        except Exception as e:
            print(e)
            raise e
        finally:
            self.lock.release()
        return ret

    def qsize(self):
        return self.q.qsize()


class Job(object):
    """
    (多线程)爬虫应用框架，用于创建一个定时抓取任务，只需要指定抓取入口链接和对应的解析规则即可，
    后续提取和链接会自动添加到抓取队列，例如：
    my_app = App('myApp', url='http://www.sina.com', rule_name='sina')
    my_app.schedule()
    """

    def __init__(self, name: str, urls: list, rule_name: str, task_queue: QueueWithLock, data_queue: QueueWithLock,
                 process_count=2):
        """
        初始化一个抓取应用
        :param name: 应用名
        :param url: 入口链接
        :param rule_name: 入口链接内容对应的解析规则
        """
        self.name = name
        self.urls = urls
        self.rule_name = rule_name

        # 不使用代理的下载queue1/worker_normal_threads
        self.task_queue = task_queue
        self.worker_processes = []
        self.process_count = process_count

        # 解析结果存储 data_queue / store_thread
        self.data_queue = data_queue
        self.data_process = None

        self.is_running = False

        self.id = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        self.ppid = os.getppid()

    @classmethod
    def is_proxy_url(cls, url):
        pm = app_config.proxy_mapping
        return pm.get_url_proxy(url) is not None

    @classmethod
    def run_worker1(cls, job):
        print('run_worker1:', os.getpid())
        while job.is_running:
            try:
                task = job.task_queue.get(block=False)
            except Empty as e:
                print('No data in task queue', e)
                time.sleep(0.1)
                continue
            tr = task.execute()
            if tr.sub_tasks:
                for t in tr.sub_tasks:
                    job.task_queue.put(t)
                print('Add {} new tasks, total task count:{}'.format(len(tr.sub_tasks), job.task_queue.qsize()))

            if tr.data:
                job.data_queue.put((task, tr.data))
        print('Task 1 thread done !')

    @classmethod
    def run_store(cls, job):
        index, count = 0, 0
        base_path = pathlib.Path(OUTPUT_DIR) / job.name / cls.now()
        while 1:
            # 每10s存储一次数据
            time.sleep(2)
            print('Start read data and save to file')
            grouped_data = defaultdict(lambda: [])
            while 1:
                try:
                    task, data = job.data_queue.get(block=False, timeout=1)
                    grouped_data[task.rule.name].append(data)
                except Empty as e:
                    print('No data in data queue', e)
                    break
            if not grouped_data:
                continue

            for rule_name, data_list in grouped_data.items():
                path = base_path / '{}.txt'.format(rule_name)
                if not path.parent.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)

                with path.open('a', encoding='utf8') as f:
                    for data in data_list:
                        try:
                            f.writelines(json.dumps(data, ensure_ascii=False) + '\n')
                        except Exception as e:
                            print('!!!!!!!!!!!!!!!!! Write failed', e, data)
            index, count = index + 1, count + len(grouped_data)
            print('Store index: {}, count:{}'.format(index, count))

        print('Storing thread done !')

    @classmethod
    def now(cls):
        return datetime.datetime.now().date().isoformat()

    def start_processes(self):
        self.is_running = True

        for url in self.urls:
            self.task_queue.put(Task(url=url, rule=Rule.find_by_name(self.rule_name)))

        ppe = ProcessPoolExecutor(max_workers=self.process_count)
        future = ppe.submit(self.run_worker1, self)
        future = ppe.submit(self.run_worker1, self)
        future = ppe.submit(self.run_store, self)
        print(future.result())

        while 1:
            print('main sleep')
            time.sleep(10)


    def shutdown_processes(self):
        print('Start shut down all threads')
        for t in self.worker_processes:
            t.terminate()

    def start(self):
        return self.start_processes()

    def stop(self):
        return self.shutdown_processes()


class App(object):
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
        self._name = name
        self._urls = [Url(i) for i in url] if isinstance(url, list) else [Url(url)]
        self._rule_name = rule_name
        self._current_job = None
        self._process_count = 1
        self._task_queue = QueueWithLock()
        self._data_queue = QueueWithLock()
        self.set_sub_process_auto_exit()


    def set_sub_process_auto_exit(self):
        def catch_signal():
            if os.name != 'nt':
                def term(sig_num, addtion):
                    print('current pid is %s, group id is %s' % (os.getpid(), os.getpgrp()))
                    os.killpg(os.getpgid(os.getpid()), signal.SIGKILL)

                print('set_sub_process_auto_exit')
                signal.signal(signal.SIGTERM, term)
                signal.signal(signal.SIGQUIT, term)
                signal.signal(signal.SIGABRT, term)
        from threading import Thread
        t = Thread(target=catch_signal)
        t.start()
        t.join()

    def start_job(self):
        self._current_job = Job(self._name, self._urls, self._rule_name,
                                self._task_queue, self._data_queue,
                                self._process_count)
        self._current_job.start()

    def schedule(self, process_count=2):
        self._process_count = process_count
        self.start_job()


if __name__ == '__main__':
    app_config.proxy_mapping = ProxyMapping.of_asdl_high()
    app = App('sync_app', rule_name='jd_page', url='https://list.jd.hk/list.html?cat=1316,1381,1389&page=1')
    app.schedule()
