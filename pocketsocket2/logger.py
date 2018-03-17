import logging
from functools import partial


class Log(logging.getLoggerClass()):

    def _fm(self,  *args, **kw):
        msg = ' '.join([str(x) for x in args])
        return msg

    def info(self, *args, **kw):
        super(Log, self).info(self._fm(*args, **kw), **kw)

    def debug(self, *args, **kw):
        super(Log, self).debug(self._fm(*args, **kw), **kw)

    def warning(self, *args, **kw):
        super(Log, self).warning(self._fm(*args, **kw), **kw)

    def error(self, *args, **kw):
        super(Log, self).error(self._fm(*args, **kw), **kw)

    def critical(self, *args, **kw):
        super(Log, self).critical(self._fm(*args, **kw), **kw)

logging.setLoggerClass(Log)
logging.basicConfig(format='%(funcName)s :: %(message)s')

logger = logging.getLogger('app_logger')
logger.setLevel(logging.DEBUG)


def log_type(l_type, *args):
    return getattr(logger, l_type)(' '.join([str(x) for x in args]))

log = logger.info
logd = logger.debug
logw = logger.warning
loge = logger.error
logc = logger.critical
