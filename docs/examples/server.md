# Server

The server is designed to be as simple as possible. To setup a running 
pocketsocket simply:


    $ python server.py


Your socket server is running on `127.0.0.1` port `8001`. Run this in
your javascript console:


    ws = new WebSocket('ws://localhost:8001/');
    ws.onmessage = function(ev) { console.log('message:', ev.data); };
    ws.onopen = function(evt) {
        ws.send('New client connected.')
    };

*Or use pocketsocket javascript code to communicate **(You should!)**:*


## More complexities!

Okay, I'm being slighty facetious. Lets set up a real test server.


    $ python server.py 0.0.0.0 8001 -s


We've set up the server to listen on all incoming through port 8001. `-s` 
is `--spy`, allowing us to view an echo of messages on the server though 
the python CLI.

Next, some javascript. Add this to your console. It's some code to tick the time.


### Using pocket.socket API

pocketsocket has a convenient API to get you started with some simple events.

    // Listen to an event
    pocket.socket.on('clock', 'tick', function(e){
        console.log(e.data);
    });

    // Start ticking
    window.setInterval(function(){
        r = d.getHours() + ':' + d.getMinutes() + ':' + d.getSeconds()
        // send some information
        pocket.socket.signal('clock', 'tick', r);
    }, 1000)

if you're watching on the server, you'll see something like:

    >>> send {"socket": "receive", "port": 58674, "address": "127.0.0.1"}
    >>> Receive: {"id":"0.kifom28","data":"click.tick"}


#### TODO! Fix a wrong example
    
    Notice the server receive example is wrong. I've copy pasted the wrong exmaple here!


### Using raw websockets!


You don'e have to use the pocketsocket JS API. You can roll out your own 
javascript and server will handle it like any normal message.


    ws = new WebSocket('ws://localhost:8001/');
    ws.onopen = function(evt) {
        
        window.setInterval(function(){
            r = d.getHours() + ':' + d.getMinutes() + ':' + d.getSeconds()
            ws.send(r)
        }, 1000)

    };


If you're watch the server you'll see something like the following print every
second.


    >>> send {"socket": "receive", "port": 58528, "address": "127.0.0.1"}
    >>> Receive: 15:24:35
    >>> send "15:24:35"


