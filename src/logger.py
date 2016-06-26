import logging
from functools import partial

logging.basicConfig(format='%(module)s.%(funcName)s:%(lineno)d %(message)s')
logger = logging.getLogger('app_logger')
logger.setLevel(logging.DEBUG)

def log_type(l_type, *args):
    return getattr(logger, l_type)(' '.join([str(x) for x in args]))

log = partial(log_type, 'info')
logd = partial(log_type, 'debug')
logw = partial(log_type, 'warning')
loge = partial(log_type, 'error')
logc = partial(log_type, 'critical')

log('-- logger created --')
