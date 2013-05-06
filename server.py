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
from json import loads
from datetime import datetime


class PocketSocketServer(SimpleWebSocketServer):
    
    def __init__(self, host, port, websocketclass, verbose=False):
        self.verbose = verbose
        super(PocketSocketServer, self).__init__(host, port, websocketclass)

    def constructWebSocket(self, sock, address):
        return self.websocketclass(self, sock, address, verbose=self.verbose)


class SimpleMultiSocket(WebSocket):
    
    def __init__(self, server, sock, address, verbose=False, client_safe=True):
        self.verbose = verbose
        self.client_safe = client_safe
        print 'SimpleMultiSocket', self.verbose
        super(SimpleMultiSocket, self).__init__(server, sock, address)

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
        '''Iter through all connected clients, __send_to called multiple times'''
        for client in self.server.connections.itervalues():
            if kwargs.get('client_safe', True):
                if client != self:
                    self.__send_to(client, o)
            else:
                # import pdb; pdb.set_trace()
                self.__send_to(client, o)

    def __send_to(self, client, msg):
        '''Receive an object to send as a string via JSON serializer'''
        if type(msg).__name__ != 'str':
            j = str(json_serialize(msg))
        else:
            j = msg

        try:
            if self.verbose:
                print 'Send:', type(j), j
            client.sendMessage(j)
        except Exception as n:
            print n

    def handleConnected(self):

        self.send_to_all('client','connected',  str(self.address[0]))

    def handleClose(self):
        self.send_to_all('client', 'disconnected', str(self.address[0]))


class PocketSocket(SimpleMultiSocket):

    def receive(self, msg):
        '''Recieve a JSON String and call methods'''
        try:
            json = True
            s = loads(msg)
            sid = s.get('id', None)
        except Exception, n:
            json = False
            print 'JSON conversion error:', s
            sid = len(msg)
            s = msg

        # Not sending information.
        # ? Perhaps send size and other message info..
        # self.send_to_all('socket', 'receive', { 'messageId': sid }, client_safe=True)

        # Send receipt 
        j = str(json_serialize({
            'socket': 'sent', 
            'attr': 'json' if json else 'string',
            'messageId': sid,
            'time': str(datetime.now()), 
        }))
        if self.verbose:
            print "Receive:", type(s), s

        # Pipe a receipt back to the client.
        self.sendMessage(j)


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