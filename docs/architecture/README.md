# Architecture

## Listeners

The Websocket has a list of bound server ports, checking for data on every cycle.

You can generate a listener using `socket_bind`:

```py
from pocketsocket.server import socket_bind

socket, host, port = socket_bind()
```
This will provide an open socket, ready for websocketing on the host `'127.0.0.1'` and an available port.

The `host` and `port` are optional, but you'll still return from the `socket_bind` function

```py
from pocketsocket.server import socket_bind

socket, host, port = socket_bind('127.0.0.1', 9002)
```
