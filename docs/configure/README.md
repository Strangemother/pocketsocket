# Configure

Pocket Socket can be configured through the following:

## Dict

If you're running Pocket Socket using in your code, you can configure a Server instance using a dictionary

```py
from pocketsocket import Server

config = dict(port=9002)
server = Server(**config)
```

You can make this neater by providing a `settings` object. It's a great way to load auto-discovered settings:

```py
from pocketsocket.ws import WebsocketServer
from pocketsocket.settings import auto_discover

settings = auto_discover(**{})
server = WebsocketServer(settings=settings)
server.start()
```

The `auto_discover` function aggreates settings from the CLI, JSON, Class, argument settings and puts them all together.

## JSON

Provide your settings with the use of a JSON config.

```bash
$> python -m pocketsocket.ws --settings=./settings.json
```

## CLI

All parameters are available as command line arguments

```bash
$> python -m pocketsocket.ws --port=9002
```

## Class

The same settings can be applied to a class

```py
class WebsocketServer(Server):
    port = 9002
    client_class = Client

```

