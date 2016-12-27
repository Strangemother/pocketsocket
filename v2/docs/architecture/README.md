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

## Server

A server maintains a list of client connections through the given port. Implementing a listener the server waits for incoming requests and generates an instance of a server client for each connected user.

The chosen methodology of _thin server fat client_ ensures the server instance is lightweight. The `Server` will call `start`, `accept`, and `handle` for action management.

Basic run example: _(SRC EXAMPLE)_

```bash
/pocketsocket/src/> python -m server
```

### Under the hood.

The main `Server` iterates the UNIX like "select" functionality, polling a client connection list for the usual throughput. As it's bi-directional connections the _read list_ and _write lists_ are the same.

For each connected `socket._socket` type connected, a sibling `SocketClient` serves your code.

As the server assumes no protocol, the client can perform any routine for _handshake_. The goal; to provide a hot-swappable server instance, agnostically serving classes of any type.

This should allow any python code to run _within_ a server<>client connectivity context. With Websockets; it allows us to run a permenant class instance, maintains all aspects of the connected client.

+ Unified logic at the server base, such as authentication of your external sources.
+ Versioning of client services is done at client instance
+ Run any class within the server by _duck punching_ or mixin inheritence
+ Easier to extend client logic to threadsafe and bridge nodes


### Simply put?

Have an extremely lightweight Server using the Client for all communcition - Servicing FTP, WS, HTTP, SSH or _any other bi-directional_ on the same port - With the client performing the transaction management.

A single server address could tandem maintain an FTP and Websocket connection within one thread - sharing the same polling resource.

### Performance

At the moment the skeleton code runs without middleman processing; Gaining access to the low-level socket loop and basic `socket.socket` instance.

+ No dependencies
+ No translation layers
+ Thin Server
+ Pure python

## Client

A _fat client_ handles all routines for a client connection. Basic client handlers are thrown-in as batteries. They're built for the main `WebsocketClient` class.

The initiation of a client is lightweight - to help with testing and init-phase setup.

```py
client = SocketClient()
client_id = client.accept(server_socket)
connected = client.start() # handshake
```

The _accept_ provides the server `Listener` socket - the master open socket. In this routine you handle any initiation protocol required.

In the Websocket world, the master socket is _accepted_, yielding a server socket and address and set the new created socket to non blocking.

Returned from `client.accept` is an _identification_ value. This is actually the _fileno_ or the file register number for the socket.

The value is applied to the existing `connections` and iterated on every poll of the _select_

