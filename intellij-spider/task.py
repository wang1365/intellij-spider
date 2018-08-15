import queue
from rule.rule import Rule
from rule.ruleparser import RuleParser
from network.urlloader import UrlLoader, Url
from config import app_config


class Task(object):
    """
    对一个URL的处理过程，包括下载和解析2个步骤，同步执行
    执行结果返回Tuple，1：解析结果JSON， 2：提取的新的链接任务字典（k：链接， v:解析规则模板名称）
    """

    def __init__(self, url: Url, rule: Rule):
        self._url = url if isinstance(url, Url) else Url(url)
        self._rule = rule

    @property
    def url(self):
        return self._url

    @property
    def rule(self):
        return self._rule

    def execute(self):
        url_content = UrlLoader.load(url=self._url)
        result = TaskResult(task=self, ok=False)
        if url_content:
            pr = RuleParser(self._rule, url_content, self._url.value).parse()
            new_links = {}
            for url, rule in pr.linked_urls.items():
                new_url = self.wrap_new_url(url)
                if new_url:
                    new_links[new_url] = rule
            result = TaskResult(task=self, ok=True, data=pr.data, linked_urls=new_links)
        return result

    def wrap_new_url(self, url):
        if not url:
            return None
        new_url = Url(url)
        referer_config = app_config.referer_config
        url_referer = referer_config.get_url_referer(url)
        if url_referer:
            if url_referer['host']:
                new_url.referer = url_referer['host']
            if url_referer['use_parent_link']:
                new_url.referer = self._url.value
        return new_url


class TaskResult(object):
    """
    单个任务执行结果包装
    """

    def __init__(self, task: Task, ok, data: dict = None, linked_urls: dict = None):
        self._ok = ok
        self._data = data
        self._task = task
        self._sub_tasks = []
        if linked_urls:
            for url, rule_name in linked_urls.items():
                if not url or not rule_name:
                    print('Error: cannot make new task because of invalid url or rule:', url, rule_name)
                    continue
                rule = Rule.find_by_name(rule_name)
                if rule:
                    self._sub_tasks.append(Task(url=url, rule=rule))
                else:
                    print('Error: cannot find rule:', rule_name)

    @property
    def ok(self):
        return self._ok

    @property
    def task(self):
        return self._task

    @property
    def data(self):
        return self._data

    @property
    def sub_tasks(self):
        return self._sub_tasks


class TaskQueue(object):
    def __init__(self):
        self._queue = queue.Queue()

    def put(self, task: (Task, list)):
        if isinstance(task, Task):
            self._queue.put(task)
        elif isinstance(task, list):
            for t in task:
                self._queue.put(t)

    def get(self):
        return self._queue.get()
