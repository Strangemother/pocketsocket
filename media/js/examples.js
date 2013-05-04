// Connecting to a single event on a single channel
pocket.socket.on('channel', 'foo', function(data, ev){
    console.log("Socket has received", data)
});

// Connect to a channel, receiving all events
pocket.socket.on('channel', function(data, ev){
    console.log("Socket has received", data)
});

// Receipt a receipt when the message is complete.
pocket.socket.signal('client', "foo", function(receipt, ev){ 
    console.log('receipt', receipt.socket, receipt.time); 
});

// Send a signal, evoking the auto connect.
pocket.socket.signal('client', 'foo');