import logging
from functools import partial


class Log(logging.getLoggerClass()):

    def info(self, *args, **kw):
        msg = ' '.join([str(x) for x in args])
        super(Log, self).info(msg, **kw)

logging.setLoggerClass(Log)
logging.basicConfig(format='%(funcName)s :: %(message)s')

logger = logging.getLogger('app_logger')
logger.setLevel(logging.DEBUG)


def log_type(l_type, *args):
    return getattr(logger, l_type)(' '.join([str(x) for x in args]))


# log = partial(log_type, 'info')
log = logger.info
logd = logger.debug
logw = logger.warning
loge = logger.error
logc = logger.critical

log('-- logger created --')
