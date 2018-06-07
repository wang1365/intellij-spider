import requests
import datetime
import time
from threading import current_thread
from config import app_config
from common.cache import daily_cache_for_str

UA = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'

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


class UrlLoader(object):
    """
    URL下载器，
    支持缓存，如果本地文件存在缓存，则先从缓存读取，缓存有效期为1个自然日
    支持下载失败重试
    """

    @classmethod
    @daily_cache_for_str
    def load(cls, url, retry=20):
        result = None

        # 代理设置
        proxies = app_config.proxy_mapping.get_url_proxy(url)
        print('Start request url: {}, proxy: {}'.format(url, proxies))

        for i in range(retry):
            from_t = datetime.datetime.now()
            print('[{}] request url: {}, proxy: {}'.format(i, url, proxies))
            try:
                dt = (datetime.datetime.now() - from_t).microseconds // 1000
                # 根据配置选择是否使用会话
                if app_config.use_session:
                    session = get_current_thread_session()
                    session.proxies = proxies
                    # 使用会话抓取，自动处理天猫的302跳转
                    res = session.get(url, timeout=10)
                else:
                    res = requests.get(url, headers=headers, proxies=proxies)

                if res.ok:
                    print('[{}] request url success, takes: {} ms, size:{}, {}'.format(i, dt, len(res.text), url))
                    result = res.text if res.encoding in ('gbk', 'GBK', 'gb2312', None) else res.content.decode('utf8')
                    break
                else:
                    print('[{}] request url failed, code: {}, takes: {} ms, reason:{}'.format(i, res.status_code, dt,
                                                                                          res.reason))
            except Exception as e:
                print('[{}] request url failed, error: {}'.format(i, e))
                # import traceback
                # traceback.print_exc()
                time.sleep(0.2)
        return result


if __name__ == '__main__':
    UrlLoader.load(url='http://www.baidu.com/aaaaa')
