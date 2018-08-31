import pathlib
from collections import defaultdict

import time
import datetime
from rule.rule import Rule
from task import Task
from threading import Thread
import queue
from config import *
from config import get_app_config
from concurrent.futures import ThreadPoolExecutor
from queue import Empty
from app import BaseApp
from common.log import logger
from common.util import writelines

'''
主应用：使用线程池处理并发
'''


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
    my_app = App('myApp', url='http://www.sina.com', rulename='sina')
    my_app.schedule()
    """

    def __init__(self, name: str, urls: list, rule_name: str, normal_thread_count=2):
        """
        初始化一个抓取应用
        :param name: 应用名
        :param urls: 入口链接列表
        :param rule_name: 入口链接内容对应的解析规则
        """
        self.name = name
        self.urls = urls
        self.rule_name = rule_name

        self.normal_task_queue = None
        self.normal_thread_count = 1

        # 解析结果存储 data_queue / store_thread
        self.data_queue = None
        self.store_thread = None

        self.is_running = False
        self.normal_thread_count = normal_thread_count

        self.id = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

        self.normal_task_pool = ThreadPoolExecutor(max_workers=normal_thread_count, thread_name_prefix='normal_task')


    @classmethod
    def run_worker(cls, task, app):
        tr = task.execute()
        if tr.sub_tasks:
            for t in tr.sub_tasks:
                app.normal_task_queue.put(t)
        if tr.data:
            app.data_queue.put((task, tr.data))

    @classmethod
    def run_store(cls, job):
        index, count = 0, 0
        base_path = pathlib.Path(OUTPUT_DIR) / job.name / cls.now()
        while job.is_running:
            # 每10s存储一次数据
            time.sleep(1)
            grouped_data = defaultdict(lambda: [])
            try:
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
            except Exception as e:
                logger.info(e)
            logger.info('Store index: {}, count:{}'.format(index, count))

        logger.info('Storing thread done !')

    @classmethod
    def now(cls):
        return datetime.datetime.now().date().isoformat()

    def start_all_threads(self):
        self.is_running = True

        # Task queue for url without proxy downloading
        self.normal_task_queue = Queue()
        for url in self.urls:
            self.normal_task_queue.put(Task(url=url, rule=Rule.find_by_name(self.rule_name)))
        # Task queue for url with proxy downloading
        self.proxy_task_queue = Queue()
        # Data queue for result storage
        self.data_queue = Queue()

        self.store_thread = Thread(target=self.run_store, args=(self,))
        self.store_thread.start()

        while 1:
            try:
                task: Task = self.normal_task_queue.get(block=False)
                task_pool = self.normal_task_pool

                task_pool.submit(self.run_worker, task, self)
                logger.info('Submit new task: %s', task.url)
            except Empty:
                pass

    def start(self):
        return self.start_all_threads()


class App(BaseApp):
    """
    (多线程)爬虫应用框架，用于创建一个定时抓取任务，只需要指定抓取入口链接和对应的解析规则即可，
    后续提取和链接会自动添加到抓取队列，例如：
    my_app = App('myApp', url='http://www.sina.com', rulename='sina')
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
