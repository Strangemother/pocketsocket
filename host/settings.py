import importlib.util
import os

def import_module(path, name='module.name'):
    spec = importlib.util.spec_from_file_location(name, path)
    imported = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported)
    return imported


class Settings(object):
    WS_PORT = 8001
    WS_HOST = '127.0.0.1'

    def __init__(self, config=None):
        self.config = config

    def get_address(self):
        return (self.WS_HOST, self.WS_PORT,)

    def update(self, d):
        for k in d:
            setattr(self, k, d[k])


def load_settings(path, options):
    conf = import_module(path)
    res = Settings(conf)
    keys = [x for x in dir(conf) if x.startswith('__') is False]
    for name in keys:
        setattr(res, name, getattr(conf,name))

    for name in options:
        setattr(res, name, options[name])

    return res


def create_settings(args=None, settings=None):
    conf = settings or {}

    if isinstance(settings, (str,)):
        conf = {
            'settings':settings
        }

    if args is not None and args.settings is not None:
        conf['settings'] = args.settings

    if conf.get('settings', None) is not None:
        conf['settings'] = os.path.abspath(conf['settings'])
        settings = load_settings(conf['settings'], conf)
    else:
        settings = Settings(conf)

    settings.update({
        'WS_PORT': args.WS_PORT or settings.WS_PORT,
        'WS_HOST': args.WS_HOST or settings.WS_HOST,
    })


    return settings
