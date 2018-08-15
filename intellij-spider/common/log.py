import logging

logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s-%(process)d-%(threadName)s][%(filename)s-%(lineno)d] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("Start print log")
    logger.debug("Do something")
    logger.warning("Something maybe fail.")
    logger.info("Finish")
