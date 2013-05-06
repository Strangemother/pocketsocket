
var ips = ['127.0.0.1', '43.137.157.170'];
var ports = [8001];
pocket.socket.setup(ips, ports, 'mix', 'broadcast').connect();

// JS signal to alert all available connections are ready.
pocket.socket.on('socket', 'broadcast-all-connected', function(e, socket){
    debugger;
    console.log("All sockets in broadcase connected", socket);
})

pocket.socket.on('socket', 'connected', function(e, socket){
    console.log("Socket has connected", socket)
});