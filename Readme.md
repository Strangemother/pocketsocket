# Pocketsocket

A fast all round solution to websockets using python and javascript.

In this library, you'll find a nice basic javascript API for handling and creating channels and extendable server based on http://opiate.github.io/SimpleWebSocketServer.

You could role out your own websocket solution, but consider using a pocketsocket to get you started on your realtime massive project.

## Features

* Connect to many websockets at once and send to all simultaneously (broadcast)
* Auto reconnect feature for lost websocket connection.
* Light channel based client communication
* Auto json

### Extending features.

* Communicate without channels easily.
* Clever url parsing at setup (makes it easier to integrate)
* automatic socket communication for core message

# Getting Started.

First get the server running on your server. To get it going, not to much is needed.

### Requirements

    docopts
    * opaite/SimpleWebSocketServer      supplied
    * strangemother/poo                 supplied
    * strangemother/django-djansoner    supplied


#### Installing requirements
    
    $ virtualenv env
    $ pip install docopts


## Running server.py


Your websocket server has a few options

    --verbose    prints data when supplied from a socket
    --echo       return message to sender as echo response


We'll use these options because it's easier to see whats happening to our messages!

You can also specify an IP address and port. By default they are `127.0.0.1` and `8001` respectively. You can pass these into the command line.

    // example map to external listening IP
    $ python server.py 0.0.0.0 8001


*Run this one* In our example, it's best to run simple like this. The server will tell you it's ready.

    $ python server.py -ev

It'll return something like:

    $ Ready 127.0.0.1 8001


