# 是否使用同步模型（多线程）（异步模型为gevent）
EXECUTE_SYNC = True


def start_app(appname, url, rule_name, now=False):
    """
    启动application
    :param appname: 应用名称
    :param url: 入口链接
    :param rule_name: 入口链接对应的解析规则
    :param now: 是否立即执行，True：立即执行，False：定时执行
    :return:
    """
    def run(now=False, time='1:01'):
        if EXECUTE_SYNC:
            from app import App
            app = App(appname, url, rule_name)
            if now:
                app.schedule(normal_thread_count=3, proxy_thread_count=15)
            else:
                app.schedule(normal_thread_count=3, proxy_thread_count=15, start_time=time)
        else:
            from asyncapp import AsyncApp
            app = AsyncApp(appname, url, rule_name)
            if now:
                app.schedule(parallelism=10)
            else:
                app.schedule(parallelism=10, start_time=time)

    if now:
        run(True)
    else:
        import fire
        fire.Fire(run)


if __name__ == '__main__':
    APP_NAME = 'jd'
    URL = 'https://list.jd.hk/list.html?cat=1316,16831'
    RULE_NAME = 'jd_cat2'
    start_app('test', URL, RULE_NAME, True)
