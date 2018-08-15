import hashlib
import pathlib
import functools
import datetime

from common.annotation import time_it
from config import *
from config import app_config
from common.log import logger
from common.util import now, take_ms

if app_config.cache_mode == CacheMode.ELASTICSEARCH:
    from elasticsearch import Elasticsearch


class EsClient(object):
    HOSTS = ['192.168.0.1', '192.168.0.2', '192.168.0.3']
    INDEX = 'my-index'
    TYPE = 'default'
    KEY = 'my_data'

    INSTANCE = None
    MAX_ID_LENGTH = 256

    def __init__(self):
        self.app_name = app_config.app_name
        self.client = Elasticsearch(hosts=self.HOSTS)

    @staticmethod
    def get_id(url):
        return url if len(url) < EsClient.MAX_ID_LENGTH else url[:EsClient.MAX_ID_LENGTH]

    @classmethod
    def instance(cls):
        if not cls.INSTANCE:
            cls.INSTANCE = EsClient()
        return cls.INSTANCE

    def get_index(self):
        return self.INDEX + self.app_name + '-' + datetime.datetime.now().strftime('%Y-%m-%d')

    @time_it
    def save(self, url, data):
        """
        保存抓取的URL内容
        :param url:
        :param data:
        :return:
        """
        result = False
        try:
            res = self.client.index(self.get_index(), self.TYPE, id=self.get_id(url), body={self.KEY: data})
            result = res['created']
        except Exception as e:
            logger.error(e)
        return result

    @time_it
    def get(self, url):
        """
        从ES获取指定URL的内容
        :param url:
        :return:
        """
        result = None
        try:
            res = self.client.get(self.get_index(), self.TYPE, id=self.get_id(url))
            result = res['_source'][self.KEY]
        except Exception as e:
            logger.error(e)
        return result

    @time_it
    def exists(self, url):
        res = False
        try:
            res = self.client.exists(self.get_index(), self.TYPE, id=url)
        except Exception as e:
            logger.error(e)
        return res


def daily_file_cache_for_str(func):
    """
    装饰器，用于本地文件缓存数据，缓存的key为被装饰函数第一个参数的MD5值。
    暂不支持缓存失效，可以手动删除使缓存失效
    :param func:
    :return:
    """

    @functools.wraps(func)
    def wrapper(*args, **kwarg):
        cache_dir = pathlib.Path(CACHE_DIR)
        url = kwarg.get('url').value
        date = datetime.datetime.now().date().isoformat()
        if url:
            items = url.split('/')
            domain = items[2]
            cache_dir = cache_dir / date / domain

        if not cache_dir.exists():
            cache_dir.mkdir(parents=True, exist_ok=True)

        t = now()
        h = hashlib.md5()
        h.update(url.encode())
        cache_file = cache_dir / h.hexdigest()
        if not cache_file.exists():
            ok, result = func(*args, **kwarg)
            if ok:
                with open(cache_file, 'w', encoding='utf8') as fp:
                    fp.write(result)
                    logger.info(
                        'Save to cache, takes {}ms, url: {}, file: {}, size: {}'.format(take_ms(t), url, cache_file,
                                                                                        len(result)))
        else:
            logger.info('Read from cache: {}ms, {},{}'.format(take_ms(t), str(cache_file), url))
            with open(cache_file, encoding='utf8') as fp:
                result = '\n'.join(fp.readlines())
        return result

    return wrapper


def daily_es_cache_for_str(func):
    """
    装饰器，用于ES缓存数据，缓存的key为被装饰函数第一个参数的MD5值。
    暂不支持缓存失效，可以手动删除使缓存失效
    :param func:
    :return:
    """

    @functools.wraps(func)
    def wrapper(*args, **kwarg):
        url = kwarg.get('url').value

        start = now()
        es = EsClient.instance()
        content = None
        is_cache_exists = es.exists(url)
        if is_cache_exists:
            content = es.get(url)
            logger.info('Read from es [{}] cache takes {}ms, {}'.format(es.get_index(), take_ms(start), url))
        else:
            ok, result = func(*args, **kwarg)
            if ok:
                content = result
                EsClient.instance().save(url, result)
                logger.info('Save to es cache, takes {}ms, size: {}, url: {}'.format(take_ms(start), len(result), url))

        return content

    return wrapper


daily_cache = daily_file_cache_for_str if app_config.cache_mode == CacheMode.LOCAL_FILE else daily_es_cache_for_str

if __name__ == '__main__':
    es = EsClient()
    logger.info(es.exists('aaaaaa'))
    es.save('b', 'b-data')
    logger.info(es.exists('b'))
    logger.info(es.get('b'))
