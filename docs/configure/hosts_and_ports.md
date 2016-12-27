# Host and Port

Websockets are hosted on any preferred port. You can provide the `host` and `port` of a listener through the command line, settings file or via your class.

## Command Line

Any built-in example will accept the `--port` and `--host` from the command line. If you utilize the `settings.auto_discover()` function, your script will accept the same parameters.

```
$>python -m pocketsocket.echo --host 127.0.0.1 --port 9008
```

## JSON

Provide the same properties using a JSON settings file

_settings.json_

```json
{
    "port": 9001,
    "host": "127.0.0.1"
}
```

Provide the JSON filepath to the `--settings` command line parameter.
```
$>python -m pocketsocket.echo --settings ./settings.json
```

Provide the settings file within your code:

```py
server = Server(client_class=Client, settings={'settings': './settings.json'})
server.start()
```

## Dictionary

A `Server` class accepts the `host`, `port` and many other attributes for configuration.


```py
class ReplyClient(Client):

    def recv(self, data, opcode):
        self.send('Thank you.')

server = Server(client_class=ReplyClient, port=9003)
server.start()
```

## Class

Provide those same options within the `Client` class

```py
class EchoClient(Client):
    def recv(self, data, opcode):
        self.send_all(data, opcode, ignore=[self])


class EchoServer(ClientListMixin, Server):
    port = 9004
    client_class = EchoClient


server = EchoServer()
server.start()

```
