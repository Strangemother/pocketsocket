from ws4py import format_addresses, configure_logger


logger = configure_logger()
def log(*a):
    logger.info(' '.join(map(str, a)))
