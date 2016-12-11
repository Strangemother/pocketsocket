# Configure

Pocket Socket can be configured through thr following:

## Dict

If you're running Pocket Socket using in your code, you can configure a Server instance using a dictionary

```py
from pocketsocket import Server

config = dict(port='9002')
server = Server(**config)
```

## JSON

Provide your settings with the use of a JSON config.

```bash
$> python -m pocketsocket.server --config=./settings.json
```

## CLI

All parameters are available as command line arguments

```bash
$> python -m pocketsocket.server --port=9002
``` 

This will work with your own script

```py
from pocketsocket import Server, get_config

server = Server(get_config())
```

This will detect and resolve the config using any of the above examples.
