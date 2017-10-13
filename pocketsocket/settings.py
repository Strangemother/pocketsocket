import os
import json
from pocketsocket.options import parsed


DEFAULT_HOSTS = ("127.0.0.1",)
DEFAULT_PORTS = (8009, )


def verbosity():
    return parsed[0].verbose


def auto_discover(**kw):
    '''Use all options to provide a dictionary of settings
    Provide any additional keyword arguments for force override.'''

    # DICT
    settings = dict(
            hosts=[],
            ports=[],
        )

    settings.update(kw)

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

    s_ports = parsed[0].ports
    if s_ports is not None:
        settings['ports'].extend([int(x.strip()) for x in s_ports.split(',')])

    s_hosts = parsed[0].hosts
    if s_hosts is not None:
        settings['hosts'].extend([int(x.strip()) for x in s_hosts.split(',')])

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

        host = kw.get('host', getattr(self, 'host', None))
        port = kw.get('port', getattr(self, 'port', None))

        if len(args) == 2:
            host, port = args
        elif len(args) == 1:
            port = args[0]

        kw['host'] = kw.get('host', host)
        kw['port'] = kw.get('port', port)

        v = auto_discover(**kw)
        return v

    def inherit_attributes(self, keys):
        hp = {x: self.settings.get(x, None) for x in keys}
        for x in hp:
            if hp[x] is not None:
                setattr(self, x, hp[x])
