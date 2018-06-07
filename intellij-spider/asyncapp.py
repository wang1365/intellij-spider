import gevent
from gevent import queue
from gevent import monkey

# 注意姿势，必须在引入IO库(requests)之前patch
monkey.patch_all()

import pathlib
import schedule
import json
import time
import datetime
from rule import Rule
from task import Task
from config import *
from collections import defaultdict


class AsyncApp(object):
    """
    (基于gevent异步)爬虫应用框架，用于创建一个定时抓取任务，只需要指定抓取入口链接和对应的解析规则即可，
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
        self._task_queue = None
        self._data_queue = []
        self._parallelism = 10

    @property
    def data_queue(self):
        return self._data_queue

    @property
    def name(self):
        return self._name

    @property
    def store_thread(self):
        return self._store_thread

    @classmethod
    def is_proxy_url(cls, url):
        pm = app_config.proxy_mapping
        return pm.get_url_proxy(url) is not None

    def save(self):
        # group data by rule name of task
        grouped_data = defaultdict(lambda: [])
        for item in self._data_queue:
            grouped_data[item[0]].append(item[1])

        # 清空队列数据
        self._data_queue = []

        for rule_name, data_list in grouped_data.items():
            path = pathlib.Path(OUTPUT_DIR) / '{}/{}/{}.txt'.format(self.name, self.now(), rule_name)
            if not path.parent.exists():
                path.parent.mkdir(parents=True)

            with path.open('a', encoding='utf8') as f:
                for data in data_list:
                    f.writelines(json.dumps(data, ensure_ascii=False) + '\n')

    @classmethod
    def now(cls):
        return datetime.datetime.now().date().isoformat()

    def load(self):
        tasks = []
        for i in range(0, self._parallelism):
            try:
                tasks.append(self._task_queue.get(block=False))
            except queue.Empty as e:
                pass

        if tasks:
            jobs = [gevent.spawn(task.execute) for task in tasks]
            gevent.joinall(jobs)

            for job in jobs:
                print(job.value)
                for task in job.value.sub_tasks:
                    self._task_queue.put(task)
                self._data_queue.append((job.value.task.rule.name, job.value.data))

            gevent.joinall([gevent.spawn(self.save)])

            print('##################  Generate new task:{}, total size:{}'.format(len(jobs), self._task_queue.qsize()))

        return self._task_queue.qsize()

    def load2(self, id):
        while 1:
            task = self._task_queue.get(timeout=1)
            tr = task.execute()
            if tr.sub_tasks:
                for t in tr.sub_tasks:
                    self._task_queue.put(t)
                    print('[{}] Add to task queue: {} {}'.format(id, t.url, self._task_queue.qsize()))

    def start2(self):
        self._task_queue = queue.Queue()
        self._task_queue.put(Task(url=self._url, rule=Rule.find_by_name(self._rule_name)))

        jobs = [
            gevent.spawn(self.load2, "job1"),
            gevent.spawn(self.load2, "job2"),
            gevent.spawn(self.load2, "job3"),
        ]
        gevent.joinall(jobs)
        print('All tasks are done ~')

    def start(self):
        self._task_queue = queue.Queue()
        self._task_queue.put(Task(url=self._url, rule=Rule.find_by_name(self._rule_name)))

        while 1:
            if self.load() == 0:
                break
        print('All tasks are done ~')

    def schedule(self, parallelism=10, start_time=None):
        """
        Application开始执行调度，缺省为立即且只执行一次，如果start_time不为None，则每天定时执行
        :param parallelism: 并行度，每N个下载任务并行执行
        :param start_time: 任务开始时间
        :return:
        """
        self._parallelism = parallelism

        # 如果没有设置开始时间，则立即执行，否则定时执行
        if not start_time:
            self.start1()
        else:
            print('Start at {} everyday'.format(start_time))
            schedule.every(1).day.at(start_time).do(self.start1)
            while True:
                schedule.run_pending()
                time.sleep(1)


if __name__ == '__main__':
    app_config.proxy_mapping = ProxyMapping.of_asdl_high()
    app = AsyncApp('asyn_app', rule_name='jd_page', url='https://list.jd.hk/list.html?cat=1316,1381,1389&page=1')
    app.schedule(parallelism=10)
