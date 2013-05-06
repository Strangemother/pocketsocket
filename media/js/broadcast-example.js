
pocket.socket.setup(['127.0.0.1', '43.137.157.170'], [8001], 'mix', 'broadcast');

// JS signal to alert all available connections are ready.
pocket.socket.on('socket', 'broadcast-all-connected', function(e, socket){
    console.log("All sockets in broadcase connected", socket);
})

pocket.socket.on('socket', 'connected', function(e, socket){
    console.log("Socket has connected", socket)
});