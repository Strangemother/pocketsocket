# Hosts and Ports

You may wish to serve many host names (IP Addresses) and ports for a single server. With more than one host or port, you can bridge network connections, using the same client class.

Just like the `host` and `port` argument from a single host setup, you can provide `hosts` or `ports` for multiple host setup

## CLI

Provide `--hosts` and `--ports` with comma delim strings:

```bash
python -m pocketsocket.echo --ports 9001,9002
```

## JSON

_settings.json_

```json
{
    "port": [9001, 9002, 9003, 9004],
    "hosts": ["127.0.0.1"]
}
```

```bash
python -m pocketsocket.reply --settings=./settings.json
```

## Class

Provide the `hosts` and `ports` keyword to the `Server` instance:

```py
from pocketsocket.server import Server

Server(ports=(9000, 9001, 9002)).start()
```

Burn the hosts and ports into the class:

```python
class EchoServer(ClientListMixin, Server):
    ports = (9004, 9005, )
    client_class = EchoClient
```
