from config import app_config, AppMode
from common.log import logger


def start_app(app_name, url, rule_name, process_count=3, proxy_process_count=15):
    mode = app_config.app_mode
    logger.info('Start app [{}] with mode [{}]'.format(app_name, mode))
    if mode == AppMode.MULTI_THREAD:
        from app_threaded import App
        app = App(app_name, url, rule_name)
        app.schedule(process_count, proxy_process_count)
    elif mode == AppMode.THREAD_POOL:
        from app_pooled import App
        app = App(app_name, url, rule_name)
        app.schedule(process_count, proxy_process_count)
    elif mode == AppMode.MULTI_PROCESS:
        from app_processed import App
        app = App(app_name, url, rule_name)
        app.schedule(process_count)
    else:
        logger.error('Not support mode: %s', mode)
