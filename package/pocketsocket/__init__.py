"""
pocketsocket - a lean WebSocket server backed by Nim (mummy) with a Python
callback hook.

    import pocketsocket

    def ingress(uuid, etype, event):
        if etype != pocketsocket.MESSAGE:
            return
        pocketsocket.send(uuid, event['kind'], event['data'])

    pocketsocket.hook(ingress)
    pocketsocket.run_blocking_server('127.0.0.1', 8090)
"""

import pocketsocket_server 

# Event types passed to the hook as `etype`.
CONNECT = 0
MESSAGE = 1
ERROR = 2
CLOSE = 3

# Message kinds, matching mummy's MessageKind ordinals.
TEXT = 0
BINARY = 1
PING = 2
PONG = 3


def _load_globals():
    _globals = globals()
    for _k in dir(pocketsocket_server):
        if not _k.startswith("_"):
            _globals[_k] = getattr(pocketsocket_server, _k)

_load_globals()
