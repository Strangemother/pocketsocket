pocket.socket.on('socket', 'receive', function(e){
    console.log("Socket has received")
});

// Send a signal, evoking the auto connect.
pocket.socket.signal('client', 'connect');


