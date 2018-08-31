import pathlib
from collections import defaultdict
import datetime
from rule.rule import Rule
from task import Task
from config import *
from network.urlloader import Url
from config import set_app_config, get_app_config
from multiprocessing import Process, Queue, Lock
import time
from queue import Empty
from app import BaseApp
from common.log import logger
from common.util import writelines
from threading import Thread

'''
主应用：使用多进程处理并发
'''


class QueueWithLock(object):
    def __init__(self, name):
        self.q = Queue()
        self.name = name

    @classmethod
    def now(cls):
        return datetime.datetime.now()

    def put(self, item, block=True, timeout=None):
        try:
            t = self.now()
            ret = self.q.put(item, block, timeout)
            dt = (self.now() - t).microseconds // 1000
            if dt > 500:
                logger.info('Put object takes {} ms, qsize: {}'.format(dt, self.qsize()))
        except Empty:
            pass
        return ret

    def put_many(self, items, block=True, timeout=None):
        try:
            t = self.now()
            for item in items:
                self.q.put(item, block, timeout)
            dt = (self.now() - t).microseconds // 1000
            logger.info('Put {} object takes {} ms, qsize: {}'.format(len(items), dt, self.qsize()))
        except Empty:
            pass

    def get(self, block=False, timeout=None):
        try:
            t = self.now()
            ret = self.q.get(block, timeout)
            dt = (self.now() - t).microseconds // 1000
            if dt > 500:
                logger.info('[{}] - Get object takes {} ms, qsize: {}'.format(self.name, dt, self.qsize()))
        except Empty:
            pass

        return ret

    def get_many(self, n=2, block=False, timeout=None):
        result = []
        try:
            t = self.now()
            while n > 0:
                if self.q.empty():
                    break
                result.append(self.q.get(block, timeout))
                n -= 1
        except Empty:
            pass
        finally:
            dt = (self.now() - t).microseconds // 1000
            logger.info('[{}] - Get {} objects takes {} ms, qsize: {}'.format(self.name, len(result), dt, self.qsize()))
        return result

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
        self.app_config = app_config

    @classmethod
    def is_proxy_url(cls, url):
        pm = app_config.proxy_mapping
        return pm.get_url_proxy(url) is not None

    @classmethod
    def run_worker_thread(cls, job):
        while job.is_running:
            tasks = job.task_queue.get_many()
            if not tasks:
                time.sleep(5)
                continue

            task_results = []
            for task in tasks:
                tr = task.execute()
                if tr.sub_tasks:
                    job.task_queue.put_many(tr.sub_tasks)
                    logger.info('Add {} new tasks, total task count:{}'.format(len(tr.sub_tasks), job.task_queue.qsize()))

                if tr.data:
                    # job.data_queue.put((task, tr.data))
                    task_results.append((task, tr.data))
            job.data_queue.put_many(task_results)

    @classmethod
    def run_worker(cls, job):
        logger.info("Start process")
        set_app_config(job.app_config)
        logger.info('app config:%s', get_app_config)
        for i in range(3):
            sub_thread = Thread(target=cls.run_worker_thread, args=(job,))
            sub_thread.start()
            logger.info("Start sub-thread: {}".format(sub_thread.ident))

        while 1:
            time.sleep(60)

    @classmethod
    def run_store(cls, job):
        index, count = 0, 0
        base_path = pathlib.Path(OUTPUT_DIR) / job.name / cls.now()
        while job.is_running:
            # 每2s存储一次数据
            # time.sleep(1)
            grouped_data = defaultdict(lambda: [])
            for task, data in job.data_queue.get_many(1024, block=True):
                grouped_data[task.rule.name].append(data)

            if not grouped_data:
                time.sleep(3)
                continue

            for rule_name, data_list in grouped_data.items():
                path = base_path / '{}.txt'.format(rule_name)
                writelines(data_list, path)
            index, count = index + 1, count + len(grouped_data)
            logger.info('Store index: {}, count:{}, data queue size: {}'.format(index, count, job.data_queue.qsize()))

        logger.info('Storing thread done !')

    @classmethod
    def now(cls):
        return datetime.datetime.now().date().isoformat()

    def start_processes(self):
        self.is_running = True

        for url in self.urls:
            self.task_queue.put(Task(url=url, rule=Rule.find_by_name(self.rule_name)))
        self.worker_processes = [Process(target=self.run_worker, args=(self,)) for i in
                                 range(self.process_count)]

        self.data_process = Process(target=self.run_store, args=(self,))

        for t in self.worker_processes:
            t.daemon = True
            t.start()
            logger.info('Start worker process: %d', t.pid)

            time.sleep(0.5)

        self.data_process.daemon = True
        self.data_process.start()
        logger.info('Start data process: %d', self.data_process.pid)

        while 1:
            logger.info('main sleep')
            time.sleep(10)

    def shutdown_processes(self):
        logger.info('Start shut down all threads')
        for t in self.worker_processes:
            t.terminate()

    def start(self):
        return self.start_processes()

    def stop(self):
        return self.shutdown_processes()


class App(BaseApp):
    """
    (多线程)爬虫应用框架，用于创建一个定时抓取任务，只需要指定抓取入口链接和对应的解析规则即可，
    后续提取和链接会自动添加到抓取队列，例如：
    my_app = App('myApp', url='http://www.sina.com', rule_name='sina')
    my_app.schedule()
    """

    def __init__(self, name: str, urls: list, rule_name: str):
        """
        初始化一个抓取应用
        :param name: 应用名
        :param urls: 入口链接
        :param rule_name: 入口链接内容对应的解析规则
        """
        self._name = name
        app_config.app_name = name
        self._urls = [Url(url) for url in urls]
        self._rule_name = rule_name
        self._current_job = None
        self._process_count = 1
        self._task_queue = QueueWithLock('TaskQueue')
        self._data_queue = QueueWithLock('DataQueue')
        super(App, self).__init__(name, urls, rule_name)

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
    app = App('sync_app', rule_name='jd_page', urls=['https://list.jd.hk/list.html?cat=1316,1381,1389&page=1'])
    app.schedule()
