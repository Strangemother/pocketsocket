'''
This is the localwebsocket server to provide
an async service for itunes integration to the interface.
This needs to be booted as a seperate process 

Usage:
  server.py
  server.py [options]
  server.py [<host>] [<port>] [options]
  server.py (-h | --help)
  server.py --version
  server.py debug [options]

Options:
  -h --help      Show this screen.
  -e --echo      reply a client message back to the sender client
  --version      Show version.
  -s --spy       Print the recieved data [default: False].
  --host=<host>  Provide a IP address to host the server [default: 127.0.0.1] 
  --port=<port>  Provide a port to host the server [default: 8001]
'''
from docopt import docopt

from vendor.ISocketServer.SimpleWebSocketServer import WebSocket, SimpleWebSocketServer
from vendor.poo.overloader import overload
from vendor.serializers import json_serialize


class SimpleMultiClient(WebSocket):
    
    def __init__(self, server, sock, address, verbose=False, client_safe=True):
        self.verbose = verbose
        self.client_safe = client_safe
        print 'SimpleMultiClient', self.verbose
        super(SimpleMultiClient, self).__init__(server, sock, address)

    def receive(self, msg):
        '''method to hook data received for user override'''
        pass

    def handleMessage(self):
        if self.data is None:
            self.data = ''
        self.data = str(self.data)
        self.receive(self.data)
        self._iter_send(self.data)

    def send_to_all(self, *args, **kwargs):

        o = {
            'address': self.address[0],
            'port': self.address[1],
        }

        # import pdb; pdb.set_trace()
        if len(args) > 1:
            o = overload(o, args[0], args[1])
        else:
            o['data'] = args[0]

        self._iter_send(o, **kwargs)

    def _iter_send(self, o, **kwargs):

        for client in self.server.connections.itervalues():
            if kwargs.get('client_safe', True):
                if client != self:
                    self.__send_to(client, o)
            else:
                # import pdb; pdb.set_trace()
                self.__send_to(client, o)

    def __send_to(self, client, msg):
        # import pdb; pdb.set_trace()
        j = json_serialize(msg)
        try:
            if self.verbose:
                print 'send', j
            client.sendMessage(str(j))
            # client.sendMessage(str(self.address[0]) + ' - ' + str(self.data))
        except Exception as n:
            print n

    def handleConnected(self):
        self.send_to_all('client.connected',  str(self.address[0]))

    def handleClose(self):
        self.send_to_all('client.disconnected', str(self.address[0]))

from json import loads


class PocketSocketServer(SimpleWebSocketServer):
    
    def __init__(self, host, port, websocketclass, verbose=False):
        self.verbose = verbose
        super(PocketSocketServer, self).__init__(host, port, websocketclass)

    def constructWebSocket(self, sock, address):
        return self.websocketclass(self, sock, address, verbose=self.verbose)


class PocketSocket(SimpleMultiClient):

    def receive(self, msg):
        self.send_to_all('socket', 'receive', client_safe=False)
        if self.verbose:
            print "Receive:", msg

def main(client=None):
    arguments = docopt(__doc__, version='0.1')  
    host = arguments.get('<host>', None) or arguments['--host']
    port = int(arguments.get('<port>', None) or arguments['--port'])
    socket = PocketSocket if client is None else client
    spy = arguments['--spy']
    server = PocketSocketServer(host, port, socket, verbose=spy)
    if spy:
        print 'Ready', host, port
    server.serveforever()

if __name__ == '__main__':
    main()