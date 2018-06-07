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


class Configuration(object):
    def __init__(self, proxy_config: ProxyMapping = None, use_session=False):
        self._proxy = ProxyMapping() if not proxy_config else proxy_config
        self._use_session = use_session

    @property
    def proxy_mapping(self):
        return self._proxy

    @proxy_mapping.setter
    def proxy_mapping(self, v):
        self._proxy = v

    @property
    def use_session(self):
        return self._use_session


app_config = Configuration()
