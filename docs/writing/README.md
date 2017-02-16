# Writing

Pocket Socket is written for clarity. In many cases the client is everything you need.

A quick recap on an echo server:

```bash
$>python -m pocketsocket.echo --port 9001
```

An echo server repeats a message to all connected clients except for the original sender.

## Client
Rolling your own app requires a new `Client`. Let's change the echo to a "Thank you." reply server:

```py
from pocketsocket.ws import Client
from pocketsocket.server import Server


def main():
    server = Server(client_class=ReplyClient)
    server.start()


class ReplyClient(Client):

    def recv(self, data, opcode):
        self.send('Thank you.')

if __name__ == '__main__':
    main()
```

As the `Client` handles nearly all of the data wrangling, extending the `Server` doesn't need editing. You can see an example of this by running the following:

```bash
$>python -m pocketsocket.reply --port 9001
```

A client has its own socket and everything required to manage its connection. As a `Client` is built for clarity, it's ready for a prototyping a simple app, to building an entire protocol.

### Full example

For those of whom prefer copy/paste, this example provides all the server interactive methods.

```python
from pocketsocket.ws import Client
from pocketsocket.server import Server
from pocketsocket.client import ClientListMixin
from pocketsocket.logger import log


def main():
    server = EchoServer(client_class=LogClient)
    server.start()


class LogClient(Client):

    def setup(self, *args, **kw):
        s = 'Setup of new client: {}'.format(self)
        log(s)
        super(LogClient, self).setup(*args, **kw)

    def accept(self, socket, server):
        v = super(Client, self).accept(socket, server)
        s = 'New Client: {} for {}'.format(self, server)
        log(s)
        self.send_all(s, ignore=[self])
        return v

    def recv(self, data, opcode):
        s = 'Got message from: {}'.format(self)
        self.send('Thanks.')
        self.send_all(s, ignore=[self])

    def recv_text(self, data):
        log('Recevied text:', data)

    def recv_binary(self, data):
        log('Recevied binary: Len:', len(data))

    def send(self, data, opcode=None):
        log('Send:', data)
        return self.sendMessage(data, opcode)

    def close(self, status, reason):
        s = 'Client close: {}'.format(self)
        log(s)
        self.send_all(s, ignore=[self])
        super(LogClient, self).close(status, reason)


class EchoServer(ClientListMixin, Server):
    pass


if __name__ == '__main__':
    main()
```

Drop this in a file such as _"server.py"_. The example can be run as a module:

```bash
$>python -m server --settings=./settings.json
```

or as your standard script:


```
$>python server.py --port=9001
```


This code is ready as an example:


```
$>python -m pocketsocket.example
```

Settings and configurations are collected in the same manner, regardless of the start method.

## Server

A custom server enhances the accessibility of settings and the connection routines. We can write reply server with the `client_class` built-in:

```py
class ReplyClient(Client):

    def recv(self, data, opcode):
        self.send_all('Got a message')


class WebsocketServer(Server):
    port = 9002
    client_class = ReplyClient

ws = WebsocketServer()
ws.start()
```


