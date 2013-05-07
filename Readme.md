# Pocketsocket

A fast all round solution to websockets using python and javascript.

*python*
    
    $ virtualenv env
    $ pip install docopts
    $ python server.py -ev


*javascript*

    pocket.socket.setup('127.0.0.1:8001').on('socket', function (name){
            console.log("socket", name);
        }).connect();


**web sockets are done!**


In this library, you'll find a nice basic javascript API for handling and creating channels and extendable server based on http://opiate.github.io/SimpleWebSocketServer.

You could role out your own websocket solution, but consider using a pocketsocket to get you started on your realtime massive project.

## Features

* Connect to many websockets at once and send to all simultaneously (broadcast)
* Auto reconnect feature for lost websocket connection.
* Light channel based client communication
* Auto json
* use sockets with a familiar and simple API:
    
    *  `setup(*addressConfig*)`            - setup your websocket connection
    *  `connect()`                         - start socketing...
    *  `on('channel', 'event', function)`  - listen to your signals
    *  `signal('channel', 'event', data)`  - send a signal

### Extending features.

* Communicate without channels easily.
* Clever url parsing at setup (makes it easier to integrate)
* automatic socket communication for core message

----

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


----

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

It'll return something like `Ready 127.0.0.1 8001`. All information proceeding will be communications sent and received.

----

## Running pocket.socket javascript

Now your server is running, we can take a look at how to send information to it. 

First we need to give pocket.socket connection information. This can range from a single string to a large array of possible connections.


### Setting up connections

Lets have a look at the `.setup()` method


#### Basic Setup

pass a single string to the setup method. You can combine your ip and port into a single connection address.

    pocket.socket.setup('127.0.0.1:8001');


#### Pair Setup

Alternatively, you can supply the IP and port individually. 

    pocket.socket.setup('127.0.0.1', 8001);


#### Duplex Setup

You can now do something very advanced - connect to many concurrent websocket connections and broadcast a message across all.

This will allow you to host lots of server's on many different IP addresses. 
In the example below, we have a local IP and a dev machine; both listening to the same event. Both will send and receive the same information.

    var addresses = ['192.168.0.55', '127.0.0.1'];
    var ports     = [8001, 8009];

    pocket.socket.setup(addresses, ports, 'broadcast');


*Something interesting*

Duplicating addresses can do more and enumerate a flat pair. You can specify a `mix` or `flat` enumeration.

The following methods will provide a list of socket address enumerated based upon `mix` of `flat`.

    pocket.socket.connection.list('mix');
    pocket.socket.connection.list('flat');


To make it easier to ead these back, You have some helper functions:
    
    // Provides an array of socket string uri's
    socket.socket.connection.list('flat').toArray();

    // Provides a comma delimited string of socket connection uri's
    socket.socket.connection.list('flat').toString();


#### Dictionary (object) Setup

You can also supply an object to setup, with array's of IP, port pairs. The key names are ignored within `pocket.socket`.

    var addressPair = {
        'local': ['120.0.0.1', 8001],
        'dev': ['192.168.0.55', 8009]
    };
    pocket.socket.setup(addressPair)


### Mix Enumeration

Receive a list of all possible cominations for all ports and IP's passed to the setup method. In the above example you would receive a list of 12 possible connection to use.

    var addresses = ['192.168.0.55', '127.0.0.1', '44.343.134.135'];
    var ports     = [8001, 8002, 8009, 8010];

    pocket.socket.setup(addresses, ports, 'broadcast');
    
    pocket.socket.connection.list('mix');

    [
     "192.168.0.55:8001", 
     "192.168.0.55:8002", 
     "192.168.0.55:8009", 
     "192.168.0.55:8010", 
     // ... snip ...
     "44.343.134.135:8009", 
     "44.343.134.135:8010"
    ]


### Flat Enumeration

Recieve a list of possible combinations based upon a flat enumeration of IP's ans ports. *You must supply a IP array and a port array of the same length*. 

The mix enumeration example, 3 addresses are supplied and 4 ports. This will fail in flat enueration.

    var addresses = ['192.168.0.55', '127.0.0.1'];
    var ports     = [8001, 8009];

    pocket.socket.setup(addresses, ports, 'broadcast');
    
    pocket.socket.connection.list('flat');
    
    [
     "192.168.0.55:8001", 
     "127.0.0.1:8009"
    ]

----

## Connection

You can use the `pocket.socket.connection` object to alter the connection list. This is recevied back from the `.setup()` method for lovely chaining.

    var connection = pocket.socket.setup()


### isSetup()

Returns a boolean value to define if there are addresses to connect to.
    
    pocket.socket.connection.isSetup()
    true/false


### list(*'mix' || 'flat'*)

Call the list method with `mix` or `flat` as the first argument.
returned is a list of string socket uri's. Read 'Mix Enumeration' and 'Flat Enumeration' for outcome

    pocket.socket.connection.list('mix');
    pocket.socket.connection.list('flat');


### addToList(list, ip, port, name)

Correctly implement a new connection to a provided list. This is mainly an internal method and shouldn't be called externally.

    pocket.socket.connection.addToList()


### empty()

delete all ips, ports and addresses - this does not disconnect any active connections.

    pocket.socket.connection.empty()

----

## Connect to sockets.

Okay, you've supplied your list of sockets, you've started your server. Next is to connect.

    $ pocket.socket.connect()
    $ pocket.socket.setup(addresses, ports).connect()
    $ pocket.socket.connect(pocket.socket.connection.list(), 'broadcast')


### makeSocket(url, *[callback]*)

ready up a websocket for connection. pass an optional callback; used for every returned event from the socket.

Returned is a new socket.


    $ pocket.socket.makeSocket('127..0.0.1:8001', function(name obj){
            // name == open, close, message, error
            // obj == { name, socket, data }
            
        })

----

# Sending Messages

Two very simple methods have been created for use. The `on()` and `signal()` methods used to send and listen for data.

## sendToAll(channel, object) 

send a message to the client on a channel with some data. This is also the `send()` method. This method will continually call the `sendTo()` method

*send() method is the same*


### Simple messaging

The channel is in essence the message and is received on the server as `message` You can send any information on the channel. for example:

    // javascript 
    $ pocket.socket.sendToAll('Art can be very abstract.')

will successfully send a message to the server and received as something like:

    // python
    {"id":"0.lchkqdo","message":"Art can be very abstract.","data":{}}


### Channel Messaging

To utlise the messaging framework and JSONification of your data into a channel, reformat your message to read.

    // javascript
    $ pocket.socket.sendToAll('socket.message', 'milk');

Of which appears on the server as:

    // python
    {"id":"0.12l60m","message":"socket.message","data":"milk"}


### Channel message JSON

You can send a block of data through a channel. by providing an object as the second argument.

    pocket.socket.sendToAll('socket.message', {
            apples:'green',
            pie: 'cherry',
            animal: 'fishy'
        })


## sendTo(AugementedWebSocket, str, val)

Accepts the same parameters as `sendToAll()` method, but the first argument is a WebSocket element.

*This is an AugementedWebSocket, of which is a WebSocket but with a couple of extra methods*


## signal(channel, eventName, *[data, AugementedWebSocket]*)

Signal is pushed into the websocket streams. This should be successful for broadcast and overflow. 

provide a channel name, event name, optionally some data and or a socket.
If the setup is in broadcast mode for connection type, the forth parameter AugementedWebSocket is ignored as it's not required.

    pocket.socket.signal('socket' 'message')

This is the preferred way to send information through the sockets.


## on()

Listening to events is again simple but powerful. There are many ways to setup a listener

#### Channel Listener

Listen to all events on a single channel. Passed to the the callback function is the name of the event along with the data (socket, event)


    pocket.socket.on('socket', function(name, data) {
        switch(name) {
            case 'connecting':
                console.log("connecting", data[1]);
                break;
            case 'open':
                console.log("open", data.socket.uri)
        }
         console.log("data replied: ", name, data)
    })


#### Event Listener

You can listen to a single event on a channel by specifying the event name as the second parameter.

    pocket.socket.on('socket', 'connected', function(e, socket){
        console.log("Socket has connected", socket)
    });
