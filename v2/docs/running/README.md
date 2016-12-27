# Running

Pocket Socket elements are modular and extendable. A battery of modules are built-in, providing a layer of abstraction for your websocket archtecture.

The basic module provides the socketing layer:

```py
python -m pocketsocket.server
```

You'll see your client connection server boot and wait for input. This is pretty rubbish - The websocket server is just easy:


```py
python -m pocketsocket.ws
```

