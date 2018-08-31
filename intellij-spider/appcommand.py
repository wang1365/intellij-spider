from config import get_app_config, AppMode
from common.log import logger


def start_app(app_name: str, urls: list, rule_name: str, process_count=3):
    mode = get_app_config().app_mode
    logger.info('Start app [{}] with mode [{}]'.format(app_name, mode))
    if mode == AppMode.MULTI_THREAD:
        from app_threaded import App
        app = App(app_name, urls, rule_name)
        app.schedule(process_count)
    elif mode == AppMode.THREAD_POOL:
        from app_pooled import App
        app = App(app_name, urls, rule_name)
        app.schedule(process_count)
    elif mode == AppMode.MULTI_PROCESS:
        from app_processed import App
        app = App(app_name, urls, rule_name)
        app.schedule(process_count)
    else:
        logger.error('Not support mode: %s', mode)
