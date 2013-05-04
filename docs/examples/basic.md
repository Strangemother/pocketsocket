# Basic

The very basic setup is easy to work with.

Start the server in your terminal. This should look like:

    $ python server.py


Run the `basic.html` file from the `/media/html/basic.html`

    open the browser to the direcory */media/html/basic.html*


For the curious; you'll notice this is a simple socket shim - allowing you to
post simple websocket messages to the server.


# Basic

The very basic setup is easy to work with.

Start the server in your terminal. This should look like:

    $ python server.py


Run the `basic.html` file from the `/media/html/basic.html`

    open the browser to the direcory */media/html/basic.html*

For the curious; you'll notice this is a simple socket shim - allowing you to
post simple websocket messages to the server.

## Basic JS

Want to role out your own JS hook? Here is something to get the ball rolling

    ws = new WebSocket('ws://localhost:8001/');
    ws.onopen = function(e) {
        console.log('open');
        var r = Math.round(Math.random() * 100) // a bit of random for no reason
        ws.send("Flerburry (" + r + ")!")
    };
    ws.onclose = function(e) { console.log('close'); };
    ws.onmessage = function(e) { console.log('message:', e.data); };
    ws.onerror = function(e) { console.log('error', e); };


# Done!

And that's it! You now have a websocket server ready to pimp your data across all
clients.