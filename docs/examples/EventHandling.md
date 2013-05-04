# Event Handling

Events are obviously very important - so there are a few methods
to make sending and receiving events super simple.

This is done via a common method, 'channels'.

Lets look at how we can hook to channel events.


This is a simple example of hooking to the channel `fooChannel` and waiting
for an event called `receive`. Obvious really.

    pocket.socket.on('fooChannel', 'delorean', function(e){
        console.log("MARTY! Is that you?!");
    });


The function is called when the event occurs. You can dispatch any event 
to any channel 

    pocket.socket.signal('fooChannel', 'delorean')


And What? That's it?! Yup! hooks all done. Run your server and see it work.


## The Theory.

Passing messages to the server is done via funky websocket blobly stuff.
This ensures transport of your information stays true to it's original by sending it as byte data.

The server collects byteArray information and converts it to a string.
The data string is the information passed from pocket.socket js as JSON.


### What's that got to do with the price of fish?

It's this fancy JSON conversion allows us to use channels to communicate
to the server and other clients.


#### Muh?

Time for for demo stuff. Let send some information to the server and see how we can make life hard. Instead of using channels, events and JSON, why not role out your own code.

To demo this, we use a subset feature of `pocket.socket`, the object method
`pocket.websocket`.

The `pocket.websocket` is a wrapper for the WebSocket, providing an API to perform reconnections and event hooks. Using `pocket.websocket.send()` method rather than `pocket.socket.send()`, we circumvent the JSONification of
our outbound message.

    pocket.websocket.send("What are you looking at butt head?")
    
