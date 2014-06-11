
var ips = ['127.0.0.1', '192.168.0.40'];
var ports = [8001];
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
// JS signal to alert all available connections are ready.
pocket.socket.on('socket', 'broadcast-all-connected', function(e, socket){
    debugger;
    console.log("All sockets in broadcase connected", socket);
})
 
pocket.socket.on('socket', 'connected', function(e, socket){
    console.log("Socket has connected", socket)
});

pocket.socket.setup(ips, ports, 'mix', 'broadcast').connect();
