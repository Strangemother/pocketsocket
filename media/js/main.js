// optional basic Setup configurations.
var address  = '127.0.0.1';
var port     = 8001;
pocket.socket.setup(address, port);

// String style setup
pocket.socket.setup('127.0.0.1:8001')
pocket.socket.setup('127.0.0.1:8001', 'broadcast')
pocket.socket.setup('127.0.0.1:8001', 'overflow')

// double muliplexing
var addresses = ['192.168.0.55', '127.0.0.1'];
var ports     = [8001, 8009];
pocket.socket.setup(addresses, ports);
pocket.socket.setup(addresses, ports, 'broadcast');
pocket.socket.setup(addresses, ports, 'overflow');
// 192.168.0.55:8001
// 192.168.0.55:8009
// 127.0.0.1:8001
// 127.0.0.1:8009


// pairs
var addressPair = {
    'local': ['120.0.0.1', 8001],
    'dev': ['192.168.0.55', 8009]
};

pocket.socket.setup(addressPair);
pocket.socket.setup(addressPair, 'broadcast');
pocket.socket.setup(addressPair, 'overflow');

// Connect to a single address
pocket.socket.setup(address, port);

// Connect to double multiplex
pocket.socket.setup(addresses, ports);

// Broadcast - Open all connections.
// Message is sent to all live connections.
pocket.socket.setup(addresses, ports, 'broadcast');
//     M --> 192.168.0.55:8001
//     M --> 192.168.0.55:8009
//     M --> 127.0.0.1:8001
//     M --> 127.0.0.1:8009

// Overflow - Open the first available connection.
// Message is sent through an open connection, 
//  on failure - open a new connection and retry.
//  The process will will loop forever.
// E.g - Failure until node three succeeds
pocket.socket.setup(addresses, ports, 'overflow');
//     M --> 192.168.0.55:8001 --> FALSE
//          M --> 192.168.0.55:8009 --> FALSE
//              M --> 127.0.0.1:8001 --> TRUE
//                  X --> 127.0.0.1:8009 -- unused.
//     # Next message
//     M --> 127.0.0.1:8001 --> FALSE
//          M --> 127.0.0.1:8009 --> TRUE


pocket.socket.on('socket', 'receive', function(e){
    console.log("Socket has received")
});

// Send a signal, evoking the auto connect.
pocket.socket.signal('client', 'connect');




