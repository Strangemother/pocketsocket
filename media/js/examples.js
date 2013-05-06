// Connecting to a single event on a single channel
pocket.socket.on('channel', 'foo', function(data, ev){
    console.log("Socket has received", data)
});

// Receipt a receipt when the message is complete.
pocket.socket.signal('channel', "foo", function(receipt, ev){ 
    console.log('receipt', receipt.socket, receipt.time); 
});

// Send a signal, evoking the auto connect.
pocket.socket.signal('channel', 'foo');