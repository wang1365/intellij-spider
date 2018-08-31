import os
import re
from common.util import today_str
from common.log import logger

IS_WINDOWS = (os.name == 'nt')

# request interval (unit/seconds)
REQUEST_INTERVAL = 0

# Cache
CACHE_DIR = 'c:/cache/' if IS_WINDOWS else '/home/wxc/cache/'

# Output directory
OUTPUT_DIR = 'c:/data/' if IS_WINDOWS else '/home/wxc/data/'


class Proxies(object):
    ADSL_HIGH = {
        'http': 'http://proxy',
        'https': 'http://proxy''
    }

    ADSL_LOW = {
        'http': 'http://proxy',
        'https': 'http://proxy''
    }

    FOREIGN = {
        'http': 'http://proxy',
        'https': 'http://proxy''
    }

    NONE = {}


class ProxyMapping(object):
    def __init__(self):
        self._url_proxies = []

    def get_url_proxy(self, url: str) -> dict:
        proxy = None
        for item in self._url_proxies:
            result = re.search(item[0], url)
            if result:
                proxy = item[1]
                break
        return proxy

    def add_url_proxy(self, url_pattern: str, proxy: dict):
        self._url_proxies.append((url_pattern, proxy))
        return self

    @classmethod
    def of_asdl_high(cls):
        return ProxyMapping().add_url_proxy('.*', Proxies.ADSL_HIGH)

    @classmethod
    def of_asdl_low(cls):
        return ProxyMapping().add_url_proxy('.*', Proxies.ADSL_LOW)

    def clear(self):
        self._url_proxies = []


class RefererConfig(object):
    def __init__(self):
        self._url_referer = {}

    def get_url_referer(self, url: str) -> str:
        referer_rule = None
        for url_pattern, value in self._url_referer.items():
            result = re.search(url_pattern, url)
            if result:
                referer_rule = value
                break
        return referer_rule

    def add_url_referer(self, url_pattern: str, host=None, use_parent_link=False):
        self._url_referer[url_pattern] = {'host': host, 'use_parent_link': use_parent_link}
        return self

    def clear(self):
        self._url_referer = {}


class FailureCondition(object):
    def __init__(self, failure_map: dict = None):
        """
        初始化下载失败场景
        :param failure_map: 失败场景映射表，
        例如：{
            'tamall.com': ['下载失败', '请求过于频繁'],
            'www.jd.com': '"error_code":-1'
        }
        """
        self._failure_map = failure_map if failure_map is not None else {}

    def get_failure_str_list(self, url):
        ret = []
        for k, v in self._failure_map.items():
            if k in url:
                ret.append(v) if isinstance(v, str) else ret.extend(v)
        return ret

    def test(self, url, content):
        """
        根据配置（反扒响应条件）检查是否是期望的内容（如果URL被反扒，响应内容返回错误的信息）
        检查通过，则URL内容正确；检查失败，说明该请求被反扒.
        :param url:
        :param content:
        :return:
        """
        ret = True
        failure_list = self.get_failure_str_list(url)
        if failure_list:
            for failure_item in failure_list:
                if failure_item in content:
                    logger.warn('Wrong response content, fail condition: %s', failure_item)
                    ret = False
                    break
        return ret

    def __str__(self) -> str:
        return str(self._failure_map)


class AppMode(object):
    MULTI_THREAD = 'multi-thread'
    THREAD_POOL = 'thread-pool'
    MULTI_PROCESS = 'multi-process'
    PROCESS_POOL = 'process-pool'
    ASYNC = 'async'


class CacheMode(object):
    LOCAL_FILE = 'local-file'
    ELASTICSEARCH = 'elasticsearch'


class Configuration(object):
    def __init__(self, proxy_config: ProxyMapping=None, use_session=False):
        self.proxy_mapping = ProxyMapping() if not proxy_config else proxy_config
        self.use_session = use_session
        self.fail_conditions = FailureCondition()
        self.referer_config = RefererConfig()

        self.no_save = False
        self.app_name = 'default'
        self.app_start_date = today_str()
        self.cache_mode = CacheMode.LOCAL_FILE
        self.app_mode = AppMode.MULTI_THREAD

    def __str__(self) -> str:
        return {
            'proxy_mapping': str(self.proxy_mapping),
            'use_session': self.use_session,
            'fail_conditions': str(self.fail_conditions),
            'referer_config': self.referer_config,
            'cache_mode': self.cache_mode,
            'app_mode': self.app_mode
        }.__str__()


app_config = Configuration()


def get_app_config():
    return app_config


def set_app_config(config):
    global app_config
    app_config = config
