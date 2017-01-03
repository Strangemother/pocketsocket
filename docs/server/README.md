
# Server

The `server` module applies a generic layer for serving your client sockets. Unlike other frameworks with a defined focus, `pocketsocket` allows a fluid adaption of your client.

## Serving

The basic server simply routes incoming connections to server your client. The base server provides everything for hosting websockets:

```bash
$> python -m pocketsocket.server --port 8009
Created listeners [<Listener(socket.socket): sock ('127.0.0.1', 8009)>]
```

Are you're ready! Configurations are done through a config file or CLI arguments.

A new client connection is handled by the `SocketClient` or your chose Client class. This offsets all the protocol management to your Client class.

### Writing your own

You can write your own class and serve it on a custom script.

```py
from pocketsocket.client import SocketClient
from pocketsocket.server import Server


class Client(SocketClient):

    def accept(self, socket):
        r = super(SocketClient, self).accept(socket)
        print 'New client', self.address
        return r


if __name__ == '__main__':
    server = Server(client_class=Client)
    server.start('127.0.0.1', 8009)
```

Extending the `SocketClient` provides all the required methods.

---

You'll notice no actual `Server` extension. It's unlikely you'll need to extend the Server, unless you're doing something really cool.

```py
from pocketsocket.client import SocketClient
from pocketsocket.server import Server


class Client(SocketClient):

    def accept(self, socket):
        r = super(SocketClient, self).accept(socket)
        print 'New client', self.address
        return r


class CustomServer(Server):
    client_class = Client

    def create_client(self, socket):
        _id, client = super(CustomServer, self).create_client(socket)
        return _id, client

if __name__ == '__main__':
    server = CustomServer()
    server.start('127.0.0.1', 8009)
```
