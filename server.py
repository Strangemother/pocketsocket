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
  --host=<host>  Provide a IP address to host the server [default: 127.0.0.1] 
  --port=<port>  Provide a port to host the server [default: 8001]
'''
from docopt import docopt

from vendor.ISocketServer.SimpleWebSocketServer import WebSocket, SimpleWebSocketServer

from vendor.poo.overloader import overload
from vendor.serializers import json_serialize
from json import loads
from datetime import datetime
import multiprocessing
import Queue


'''
Concept implemenation:

    if used and ready, automatically implement.

'''


class PocketSocketServer(SimpleWebSocketServer):

    def __init__(self, host, port, websocketclass, verbose=False, queue=None):
        self.verbose = verbose
        self.queue= queue
        super(PocketSocketServer, self).__init__(host, port, websocketclass)

    def constructWebSocket(self, sock, address):
        if self.websocketclass:
            return self.websocketclass(self, sock, address, verbose=self.verbose,queue= self.queue)
        else:
            print 'no websocketclass'
            if self.queue: self.queue.put('Error: No WebSocket class provided')



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


class PocketSocket(SimpleMultiSocket):

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
        self.put(s)

        # Pipe a receipt back to the client.
        self.sendMessage(j)



def file_filter(name):
    return (not name.startswith(".")) and (not name.endswith(".swp"))


def file_times(path):
    for top_level in filter(file_filter, os.listdir(path)):
        for root, dirs, files in os.walk(top_level):
            for file in filter(file_filter, files):
                yield os.stat(os.path.join(root, file)).st_mtime


def print_stdout(process):
    stdout = process.stdout
    if stdout != None:
        print stdout

def serve_forever(host, port, socket=None, verbose=False, queue=None):
    socket = PocketSocket if socket is None else socket
    server = PocketSocketServer(host, port, socket, verbose=verbose, queue=queue)
    if verbose:
        print 'Ready', host, port
    server.serveforever()
    return server

from time import sleep

def served(process, queue=None):

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

def main(queue=None, client=None):
    if queue is None:
        queue = multiprocessing.Queue()
    arguments = docopt(__doc__, version='0.1')  
    host = arguments.get('<host>', None) or arguments['--host']
    port = int(arguments.get('<port>', None) or arguments['--port'])
    # socket = PocketSocket if client is None else client
    verbose = arguments['--verbose']

    server_proc = multiprocessing.Process(target=serve_forever, args=(host, port, client, verbose, queue))
    server_proc.start()

    try:
        served(server_proc, queue)
    except KeyboardInterrupt, e:
        print 'Kill'
        server_proc.terminate()
        print 'Dead'



if __name__ == '__main__':
    main()
