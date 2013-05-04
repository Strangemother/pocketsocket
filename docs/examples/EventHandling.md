# Event Handling

Events are obviously very important - so there are a few methods
to make sending and receiving events super simple.

Lets look at how we can hook to channel events.


## The Theory.

Passing messages to the server is done via funky websocket blobly stuff.
This ensures transport of your information stays true to it's original by sending it as byte data.

The server collects byteArray information and converts it to a string.
The data string is the information passed from pocket.socket js as JSON.


### What's that got to do with the price of fish?

It's this fancy JSON conversion allows us to use channels to communicate
to the server and other clients.


#### Muh?

Time for for demo stuff. Let send some information to the server and see how we can make life hard.

To demo this, we use a subset feature of `pocket.socket`, the object method
`pocket.websocket`.

The `pocket.websocket` is a wrapper for the WebSocket, providing an API to perform reconnections and event hooks. Using `pocket.websocket.send()` method rather than `pocket.socket.send()`, we circumvent the JSONification of
our outbound message.

    pocket.websocket.send("woopx")








# Channel Listener

    pocket.socket.on('socket', 'receive', function(e){
        console.log("Socket has received")
    });

    pocket.socket.signal('channelName', 'event')