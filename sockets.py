
from vendor.ISocketServer.SimpleWebSocketServer import WebSocket, \
    SimpleWebSocketServer

from vendor.poo.overloader import overload
from json import loads, dumps
from datetime import datetime
from termcolor import cprint

class SimpleMultiSocket(WebSocket):

    def __init__(self, server, websocketclass, address, verbose=False, \
        client_safe=True, queue=None, pipe=None):


        self.pipe = pipe
        self.verbose = verbose
        self.client_safe = client_safe
        self.queue = queue
        super(SimpleMultiSocket, self).__init__(server, websocketclass, address)

    def to_pipe(self, args):
        self.pipe.send(args)

    def from_pipe(self):
        self.pipe.send()

    def put(self, *args, **kwargs):
        '''Writes a message to the multiprocess queue'''
        if self.queue:
            self.queue.put(*args, **kwargs)

    def handleConnected(self):
        self.send_to_all('socket','connected',  str(self.address[0]))
        self.connect(self.address)   

    def handleMessage(self):
        if self.data is None:
            self.data = ''

        self.data = str(self.data)
        self.receive(self.data)
        self._iter_send(self.data)


    def handleClose(self):
        if self.verbose:
            print 'disconnected', self.address
        self.send_to_all('socket', 'disconnected', str(self.address[0]))
        self.disconnect()

    def receive(self, msg):
        '''method to hook data received for user override'''
        print 'message'  

    def connect(self, address):
        '''method to hook connect for user override'''
        print 'connect', self, address
        
    def close(self):
        # tell the client close will hand.
        # self.pipe.close()
        super(SimpleMultiSocket, self).close()

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
            j = str(dumps(msg))
        else:
            j = msg

        try:
            if self.verbose:
                print 'Send:', type(j), j
            client.sendMessage(j)
        except Exception as n:
            print "__send_to", n


class PocketSocketProtocol(SimpleMultiSocket):
    '''Easy implementable of a class to extend.
    Each method in the class has been designed for easy hooks
    to your python class.'''

    def __init__(self):
        '''Doesn't do much. it's override safe'''
        pass

    def output(self, msg, code):
        '''implement to receive class messages from the framework. These
        are independant of the messaging server. This method is
        used to capture errors and debug logs.'''
        self.write("%s output: %s, %s" % (self.name, msg, code))

    def write(self, data):
        '''override to receive a write string'''

    def send(self, s):
        pass


class JsonMultiSocket(SimpleMultiSocket):
    '''
    A Socket client receiver is provided to the SocketServer. This
    class receives messages and handles connections. This is essentially
    the client served socket. It maintains it's own threaded socket server;
    served on a host and unique port provided.

    Usage:

    Pass the Socket (inheriting `WebSocket`) to connect and recieve websocket
    clients.

    '''

    def receive(self, msg):
        '''Recieve a JSON String and call methods'''
        try:
            s = loads(msg)
            n = ''
        except Exception, n:
            s = msg

        # Not sending information.
        # ? Perhaps send size and other message info..
        # self.send_to_all('socket', 'receive', { 'messageId': sid },
        #   client_safe=True)

        # Send receipt
        j = "{'status': 'sent'}"

        if self.verbose:
            print "Receive:", s
        # self.put(s)
        # Pipe a receipt back to the client.
        self.sendMessage(j)


class ThreadSocket(JsonMultiSocket):

    def term(self, text, color=None, **kwargs):
        cprint(text, kwargs.get('color', color), kwargs.get('on', None))
    
    def disconnect(self):
        '''
        Client has closed connection
        '''
        self.term('client close %s' % self.address[0], 'blue')

    def receive(self, data):
        '''
        Client has received a connecrion
        '''
        self.to_pipe(('message', 'len: %s' % len(self.data)) + self.address)

    def connect(self, address):
        ''' 
        A client has connected to the socket
        '''
        self.term('client connect %s' % address[0], 'blue')
        self.to_pipe(('connected', ) + address)
