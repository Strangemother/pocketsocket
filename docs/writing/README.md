# Writing

Pocket Socket is written for clarity. In many cases the client is everything you need.

A quick recap on an echo server:

```bash
$>python -m pocketsocket.echo --port 9001
```

An echo server repeats a message to all connected clients except for the original sender.

## Client
Rolling your own requires a new `Client`. Let's change the echo to a "Thank you." reply server:

```py
from ws import Client
from server import Server


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
