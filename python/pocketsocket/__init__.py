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

from pocketsocket import pocketsocket_server

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

hook = pocketsocket_server.hook
send = pocketsocket_server.send
send_all = pocketsocket_server.send_all
close_client = pocketsocket_server.close_client
set_broadcast_mode = pocketsocket_server.set_broadcast_mode
set_echo_mode = pocketsocket_server.set_echo_mode
set_print_mode = pocketsocket_server.set_print_mode
run_blocking_server = pocketsocket_server.run_blocking_server
shutdown_server = pocketsocket_server.shutdown_server

__all__ = [
    "pocketsocket_server",
    "hook", "send", "send_all", "close_client",
    "set_broadcast_mode", "set_echo_mode", "set_print_mode",
    "run_blocking_server", "shutdown_server",
    "CONNECT", "MESSAGE", "ERROR", "CLOSE",
    "TEXT", "BINARY", "PING", "PONG",
]
