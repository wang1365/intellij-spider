import logging

logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s-%(process)5d-%(threadName)10s][%(filename)20s-%(lineno)3d] %(levelname)7s: %(message)s')
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    logger.info("Start print log")
    logger.debug("Do something")
    logger.warning("Something maybe fail.")
    logger.info("Finish")
