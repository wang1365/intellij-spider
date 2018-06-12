import hashlib
import pathlib
import functools
import datetime
from config import *


def daily_cache_for_str(func):
    """
    装饰器，用于本地文件缓存json数据，缓存的key为被装饰函数第一个参数的MD5值。
    暂不支持缓存失效，可以手动删除使缓存失效
    :param func:
    :return:
    """

    @functools.wraps(func)
    def wrapper(*args, **kwarg):
        cache_dir = pathlib.Path(CACHE_DIR)
        url = kwarg.get('url')
        date = datetime.datetime.now().date().isoformat()
        if url:
            items = kwarg['url'].split('/')
            domain = items[2]
            cache_dir = cache_dir / date / domain

        if not cache_dir.exists():
            cache_dir.mkdir(parents=True)

        h = hashlib.md5()
        h.update(url.encode())
        cache_file = cache_dir / h.hexdigest()
        if not cache_file.exists():
            ok, result = func(*args, **kwarg)
            if ok:
                with open(cache_file, 'w', encoding='utf8') as fp:
                    fp.write(result)
                    print('Save to cache, url: {}, file: {}, size: {}'.format(url, cache_file, len(result)))
        else:
            print('Read from cache:{},{}'.format(str(cache_file), url))
            with open(cache_file, encoding='utf8') as fp:
                result = '\n'.join(fp.readlines())
        return result

    return wrapper
