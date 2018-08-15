from functools import wraps
from common.util import now, take_ms
from common.log import logger


def time_it(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        t = now()
        result = func(*args, **kwargs)
        ms = take_ms(t)
        if ms > 500:
            logger.warn('Execute [{}] takes {}ms'.format(func.__name__, ms))
        return result

    return wrapper
