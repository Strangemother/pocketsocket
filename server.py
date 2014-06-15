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
  -v --verbose   Print the recieved data [default: False].
  -i --host=<host>  Provide a IP address to host the server [default: 127.0.0.1]
  -p --port=<port>  Provide a port to host the server [default: 8001]
'''

try:
    from docopt import docopt
    docopt_module = True
except ImportError, e:
    print 'no docopts'
    docopt_module = False

from vendor.ISocketServer.SimpleWebSocketServer import WebSocket, \
    SimpleWebSocketServer

from vendor.poo.overloader import overload
from json import loads, dumps
from datetime import datetime
import multiprocessing
import Queue
from time import sleep


class SimpleMultiSocket(WebSocket):

    def __init__(self, server, sock, address, verbose=False, client_safe=True, queue=None):
        self.verbose = verbose
        self.client_safe = client_safe
        print 'SimpleMultiSocket', self.verbose
        self.queue = queue
        super(SimpleMultiSocket, self).__init__(server, sock, address)

    def put(self, *args, **kwargs):
        if self.queue:
            self.queue.put(*args, **kwargs)

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
            j = str(dumps(msg))
        else:
            j = msg

        try:
            if self.verbose:
                print 'Send:', type(j), j
            client.sendMessage(j)
        except Exception as n:
            print n

    def handleConnected(self):
        if self.verbose:
            print 'connected', self.address
        self.send_to_all('socket','connected',  str(self.address[0]))

    def handleClose(self):
        if self.verbose:
            print 'disconnected', self.address
        self.send_to_all('socket', 'disconnected', str(self.address[0]))


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

    def receive(self, msg):
        '''Recieve a JSON String and call methods'''
        try:
            json = True
            print msg
            s = loads(msg)

            sid = s.get('id', None)
        except Exception, n:
            json = False
            print 'JSON conversion error:', n
            sid = len(msg)
            s = msg

        # Not sending information.
        # ? Perhaps send size and other message info..
        # self.send_to_all('socket', 'receive', { 'messageId': sid },
        #   client_safe=True)

        # Send receipt
        j = str(dumps({
            'socket': 'sent',
            'attr': 'json' if json else 'string',
            'messageId': sid,
            'time': str(datetime.now()),
        }))
        if self.verbose:
            print "Receive:", type(s), s
        self.put(s)

        # Pipe a receipt back to the client.
        self.sendMessage(j)


class ThreadedSocketServer(SimpleWebSocketServer):
    # A threaded server creates a socketed client and
    # cares for a threaded process running the socket.

    def __init__(self, host, port, websocketclass, verbose=False, queue=None):
        self.host = host
        self.port = port
        self.client = JsonMultiSocket if websocketclass is None else websocketclass
        self.verbose = verbose
        self.queue = queue

        super(ThreadedSocketServer, self).__init__(host, port, websocketclass)

    def constructWebSocket(self, sock=None, address=None):
        '''
        Create a new websocket based upon the socket address and cliet.
        returned is a ready
        '''
        _sock = sock or self.sock
        _add = address or self.address
        if self.websocketclass:
            return self.websocketclass(self, _sock, _add, verbose=self.verbose, queue=self.queue)
        else:
            print 'no websocketclass'
            if self.queue: self.queue.put('Error: No WebSocket class provided')

    def start(self, host=None, port=None, client=None, verbose=False, queue=None):
        '''
        Begin the multi thread process of the WebSockets.
        '''
        print 'Begin multiprocess'
        host = host or self.host
        port = port or self.port
        client = client or self.client
        # Multiprocessing queue o communicate to each thread
        queue = queue or self.queue
        if queue is None:
            queue = multiprocessing.Queue()
        self.queue = queue
        server_proc = multiprocessing.Process(target=self.start_serveforever, args=(host, port, client, verbose, queue))
        self.multiprocess = server_proc
        server_proc.start()
        self.wait_serve()

    def start_serveforever(self, host, port, socket=None, verbose=False, queue=None):
        print 'Serving', host, port, socket
        self.serveforever()
        return self.multiprocess

    def wait_serve(self):
        try:
            self.served(self.multiprocess)
        except KeyboardInterrupt, e:
            self.terminate(e)

    def served(self, process, queue=None):
        queue = queue or self.queue
        print 'Socket Served:', process.name, process.pid
        while True:
            try:
                msg = queue.get_nowait()
                print process.name, process.is_alive(), ':"%s"' % msg
            except Queue.Empty as e:
                pass
            sleep(.1)
            # com = raw_input('Input')
            # print com

    def terminate(self, error=None):
        print 'Kill'
        self.multiprocess.terminate()
        print 'Dead'

    def put(self, *args, **kwargs):
        if self.queue:
            self.queue.put(*args, **kwargs)



def start(host, port, verbose, socket=None):
    server = ThreadedSocketServer(host, port, socket, verbose=verbose)
    server.start()


def main(queue=None, client=None):
    if docopt_module:
        arguments = docopt(__doc__, version='0.1')
        host = arguments.get('<host>', None) or arguments['--host']
        port = int(arguments.get('<port>', None) or arguments['--port'])
        verbose = arguments['--verbose']
    else:
        import sys
        args = sys.argv[1:]
        l = len(args)
        host = '127.0.0.1'
        port = 8001
        verbose = True

        if l >= 1:
            host = args[0]
        elif l >= 2:
            port = int(args[1])
        elif l >= 3:
            verbose = bool(args[2])
    start(host, port, verbose)

if __name__ == '__main__':
    main()
