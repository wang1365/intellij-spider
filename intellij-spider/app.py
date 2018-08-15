from network.urlloader import Url
from config import app_config


class BaseApp(object):
    """
    爬虫应用框架，只需要指定抓取入口链接和对应的解析规则即可，
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
        self.name = name
        app_config.app_name = name
        self.urls = [Url(i) for i in url] if isinstance(url, list) else [Url(url)]
        self.rule_name = rule_name
        self.current_job = None
        self.normal_thread_count = 1
        self.proxy_thread_count = 1
