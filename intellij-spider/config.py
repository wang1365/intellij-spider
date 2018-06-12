import os
import re

IS_WINDOWS = (os.name == 'nt')

# Proxy settings
USE_PROXY = True

# request interval (unit/seconds)
REQUEST_INTERVAL = 0

# Cache
CACHE_DIR = 'c:/cache/' if IS_WINDOWS else '/home/wangxiaochuan/cache/'

# Output directory
OUTPUT_DIR = 'c:/data/' if IS_WINDOWS else '/home/wangxiaochuan/data/'


class Proxies(object):
    PROXY_INTERNAL = {
        'http': 'http://127.0.0.1:8080',
        'https': 'http://127.0.0.1:8080'
    }

    PROXY_EXTERNAL = {
        'http': 'http://127.0.0.1:8080',
        'https': 'http://127.0.0.1:8080'
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

    def clear(self):
        self._url_proxies = []


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
        ret = True
        failure_list = self.get_failure_str_list(url)
        if failure_list:
            for failure_item in failure_list:
                if failure_item in content:
                    print('Wrong response content, fail condition: ', failure_item)
                    ret = False
                    break
        return ret


class Configuration(object):
    def __init__(self, proxy_config: ProxyMapping = None, use_session=False):
        self._proxy = ProxyMapping() if not proxy_config else proxy_config
        self._use_session = use_session
        self._fail_conditions = FailureCondition()

    @property
    def proxy_mapping(self):
        return self._proxy

    @proxy_mapping.setter
    def proxy_mapping(self, v):
        self._proxy = v

    @property
    def use_session(self):
        return self._use_session

    @property
    def fail_conditions(self):
        return self._fail_conditions

    @fail_conditions.setter
    def fail_conditions(self, v):
        self._fail_conditions = v

app_config = Configuration()
