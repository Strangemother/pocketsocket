import os
import json
from optparse import OptionParser

DEFAULT_HOSTS = ("127.0.0.1",)
DEFAULT_PORTS = (8009, )

parser = OptionParser()
parser.add_option("-q", "--quiet",
                  action="store_false",
                  dest="verbose",
                  default=True,
                  help="don't print status messages to stdout")
parser.add_option("-s", "--settings",
                  dest="settings",
                  help="Provide a settings path")
parser.add_option("-p", "--port",
                  type='int',
                  dest="port",
                  help="Provide a port")
parser.add_option("-a", "--host",
                  dest="host",
                  help="Provide a host")

parsed = parser.parse_args()


def verbosity():
    return parsed[0].verbose


def auto_discover(**kw):
    '''Use all options to provide a dictionary of settings
    Provide any additional keyword arguments for force override.'''

    # DICT
    settings = dict(
            hosts=tuple(),
            ports=tuple(),
        )

    # JSON
    json_path = kw.get('settings', None)
    if json_path is None:
        json_path = parsed[0].settings

    if json_path is not None:
        settings.update(json_data(json_path))

    # CLI
    keys = ['port', 'host']
    for k in keys:
        settings[k] = getattr(parsed[0], k, None) or settings.get(k, None)

    # Apply kw last, to force over all confing
    kwh = kw.get('host', None)
    kwp = kw.get('port', None)

    if kwh is None:
        kwh = settings['host']

    if kwp is None:
        kwp = settings['port']

    if kwh is not None:
        settings['hosts'] += (kwh, )
    if kwp is not None:
        settings['ports'] += (kwp, )

    if getattr(settings, 'host', None) is None and \
       len(settings.get('hosts', tuple())) == 0:
        settings['hosts'] = DEFAULT_HOSTS

    if getattr(settings, 'port', None) is None and \
       len(settings.get('ports', tuple())) == 0:
        settings['ports'] = DEFAULT_PORTS

    return settings


def json_data(json_path):
    d = {}
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            d = json.load(f)
    return d


class SettingsMixin(object):
    ''' Provide settings from config points.'''

    def configure(self, *args, **kw):
        ''' Configure the server. Inline ip and port are most important.
            configure('127.0.0.1', port=8001, host='', port=-1) '''

        host = kw.get('host', None)
        port = kw.get('port', None)

        if len(args) == 2:
            host, port = args
        elif len(args) == 1:
            port = args[0]

        v = auto_discover(host=host, port=port, **kw)
        return v

    def inherit_attributes(self, keys):
        hp = {x: self.settings.get(x, None) for x in keys}
        for x in hp:
            setattr(self, x, hp[x])
