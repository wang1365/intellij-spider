import requests
import datetime
import time
from threading import current_thread
from config import app_config
from common.cache import daily_cache
from common.log import logger

UA = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'
# UA = 'Mozilla/5.0 (compatible; Baiduspider-render/2.0; +http://www.baidu.com/search/spider.html)'

headers = {'user-agent': UA}

threaded_session = {}


def get_current_thread_session():
    """
    获取当前线程使用的http session.
    http session不能多线程并发使用
    :return:
    """
    t = current_thread()
    tid = t.ident
    session = threaded_session.get(tid)
    if not session:
        session = requests.Session()
        session.headers = headers
        threaded_session[tid] = session
    return session


class Url(object):
    def __init__(self, value, referer=None):
        self._value = value
        self._referer = referer

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = v

    @property
    def referer(self):
        return self._referer

    @referer.setter
    def referer(self, v):
        self._referer = v

    def __str__(self) -> str:
        return self._value


class UrlLoader(object):
    """
    URL下载器，
    支持缓存，如果本地文件存在缓存，则先从缓存读取，缓存有效期为1个自然日
    支持下载失败重试
    """

    @classmethod
    # @daily_cache_for_str
    @daily_cache
    def load(cls, url: Url, retry=25):
        """
        下载URL链接，返回下载的内容；
        先从缓存查询该链接（本地文件缓存或者ElasticSearch缓存），如果缓存存在，直接返回缓存内容
        :param url:
        :param retry:
        :return:
        """
        ok, result = False, None
        referer = url.referer
        url = url.value

        if referer:
            headers['referer'] = referer

        # 代理设置
        proxies = app_config.proxy_mapping.get_url_proxy(url)
        logger.info('Start request url: {}, proxy: {}'.format(url, proxies))

        for i in range(retry):
            from_t = datetime.datetime.now()
            logger.info('[{}] request url: {}, proxy: {}'.format(i, url, proxies))
            try:
                dt = (datetime.datetime.now() - from_t).microseconds // 1000
                # 根据配置选择是否使用会话
                if app_config.use_session:
                    session = get_current_thread_session()
                    session.proxies = proxies
                    # 使用会话抓取，自动处理天猫的302跳转, 中间可能有多个302跳转，所以不要设置超时时间
                    res = session.get(url, timeout=120)
                else:
                    res = requests.get(url, headers=headers, proxies=proxies)

                if res.ok:
                    logger.info('[{}] request url success, takes: {} ms, size:{}, {}'.format(i, dt, len(res.text), url))
                    if res.encoding == 'ISO-8859-1':
                        result = res.content.decode('utf8')
                    elif res.encoding is None and res.apparent_encoding == 'ISO-8859-1':
                        result = res.content.decode('gb2312')
                    else:
                        result = res.text if res.encoding in (
                            'gbk', 'GBK', None, 'gb2312', 'ISO-8859-1') else res.content.decode('utf8')

                    # 根据配置检查是否是正常的返回内容，如果不是，重新抓取
                    if app_config.fail_conditions.test(url, result):
                        ok = True
                        break
                else:
                    logger.info('[{}] request url failed, takes {}ms, code:{}-{}'.format(i, dt, res.status_code, res.reason))
                    time.sleep(0.5)
            except Exception as e:
                logger.error('[{}] request url failed, error: {}'.format(i, e))
                # import traceback
                # traceback.print_exc()
            time.sleep(0.1)
        return ok, result


if __name__ == '__main__':
    UrlLoader.load(url='http://www.baidu.com/aaaaa')
