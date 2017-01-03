# Pocket Socket

Websockets in python is boring and hard. Using websockets is all the fun. Pocket Socket provides a base for websocket development. Designed for clarity and portability.

## Getting started

Install Pocket Socket using `pip`

```py
pip install pocketsocket
```

Pocket Socket is built for ease with no dependencies and no setup.

The quickest method to boot an echo server doesn't need any code

```bash
$>python -m pocketsocket.echo --port 9001
```

An echo server repeats a message to all connected clients. If you're building a simple chat server, this is a great start.

## Requirements

It's lighweight with no dependencies and should run on any python ready platform. Current implementations are:

+ Rasberry Pi
+ Window
+ Linux (Debian, Ubuntu, BusyBox, AB.IO ...)
