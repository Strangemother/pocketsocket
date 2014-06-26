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

from vendor.ISocketServer.SimpleWebSocketServer import SimpleWebSocketServer

from sockets import ThreadSocket as _WebSocket
import multiprocessing
from multiprocessing import Pipe
import Queue
from time import sleep
from utils import get_local_ip
from termcolor import cprint

class PocketSocketError(Exception):

    def __init__(self, value, msg):
        self.value = value
        self.msg = msg


class ThreadedSocketServer(SimpleWebSocketServer):
    '''
    A SocketServer asyncronously threads a Socket and handled the process
    until death.

    Usage:
    '''
    # A threaded server creates a socketed client and
    # cares for a threaded process running the socket.

    def __init__(self, host, port, client_socket, verbose=False, queue=None):
        self.host = host
        self.port = port
        # Client socket implements the class constructed to handle connections.
        #
        self.client_socket = _WebSocket if client_socket is None \
            else client_socket
        self.verbose = verbose
        self.queue = queue

        self.clock_speed = .1 # Tickers in seconds for every mutliprocess
                              # message queue check.

        # Call the super, creating the simple web socket server and
        # setting up websocket connections.
        super(ThreadedSocketServer, self).__init__(host, port, client_socket)

    def constructWebSocket(self, sock=None, address=None):
        '''
        Create a new websocket based upon the socket address and client class
        provided. Returned is a ready client serving a websocket receiver on
        a host and unique port
        '''
        _sock = sock or self.sock
        _add = address or self.address
        if self.client_socket:
            return self.client_socket(self, _sock, _add, verbose=self.verbose, \
                queue=self.queue, pipe=self.child_pipe)
        else:
            print 'no client_socket'
            if self.queue: self.queue.put('Error: No WebSocket class provided')

    def get_queue(self):
        '''
        create and return or return a multiprocessing Queue for multithread
        communication
        '''
        if self.queue is None:
            self.queue = multiprocessing.Queue()
        return self.queue

    def from_pipe(self):
        pipm = self.pipe.recv()
       
        return pipm

    def term(self, text, color=None, **kwargs):
        cprint(text, kwargs.get('color', color), kwargs.get('on', None))

    def thread_messages(self):
        queue = self.get_queue()
        process = self.multiprocess
        msg = None
        ms = []

        pipm = self.from_pipe()
        ms.append(pipm)

        try:
            msg = queue.get_nowait()
            ms.append(msg)
            print process.name, process.is_alive(), ':"%s"' % msg
        except Queue.Empty as e:
            pass
        return ms

    def start(self, host=None, port=None, client_socket=None, verbose=False, \
        queue=None):
        '''
        Begin the multi thread process of the WebSockets.
        '''
        host = host or self.host
        port = port or self.port
        client_socket = client_socket or self.client_socket
        
        self.spawn_process(host=host, port=port, client_socket=client_socket)
        self.sync_process()

    def sync_process(self, *args, **kwargs):
        # Create a new multiprocess thread.
        server_proc = multiprocessing.Process(target=self.wait_for_message, \
            args=())
        self.term('Create clock %s' % server_proc, 'yellow')
        server_proc.start()
        self.clock = server_proc
  
    def send_to_all(self, *args, **kwargs):
        self.pipe.send( ('send_to_all', args, kwargs,))

    def spawn_process(self, *args, **kwargs):
        '''
        Spawn a threaded process adding it to the cared group of threads.
        '''
        # Multiprocessing queue o communicate to each thread
        queue = kwargs.get('queue', self.get_queue() )
        # Create the pipes to communicate through
        self.pipe, self.child_pipe = Pipe()

        host = kwargs.get('host', self.host)
        port = kwargs.get('port', self.port)
        client_socket = kwargs.get('client_socket', self.client_socket)
        verbose = kwargs.get('verbose', self.verbose)


        # Create a new multiprocess thread.
        server_proc = multiprocessing.Process(target=self.start_serveforever, \
            args=(host, port, client_socket, verbose, queue, self.child_pipe)
            )
        # Store the multiprocess
        self.multiprocess = server_proc
        self.term('Create WebSocket %s' % server_proc, 'yellow')
        # start the multi process
        server_proc.start()

    def start_serveforever(self, host, port, socket=None, verbose=False, \
        queue=None, child_pipe=None):
        '''
        Begin the parental start server. called by the multithreading
        start() method
        '''
        print 'serve on', host, port
        print 'internal ip:', get_local_ip()
        self.socket_bind(host or self.host, port or self.port)
        self.serveforever()

    def start_wait(self, *args, **kwargs):
        self.start(*args, **kwargs)
        # serve the keyboard wait through the served method
        self.wait_serve()

    def wait_serve(self):
        '''
        Wait on the multiprocessing threads for entering messages
        until a KeyboardInterrupt
        '''

        try:
            self.wait_for_message(self.multiprocess)
        except KeyboardInterrupt, e:
            self.terminate(self.multiprocess, e)

    def wait_for_message(self, process=None, queue=None):
        '''
        Pool the multiprocessing queue for messages
        '''
        queue = queue or self.queue
        process = process or self.multiprocess
        while True:
            msg = self.thread_messages()
            if msg: 
                print cprint(msg, 'green')
            sleep(.1)


    def terminate(self, process=None, error=None):
        # Terminate a multiprocess thread; i.e a client.
        print 'Kill'
        self.pipe.send(['close'])
        self.close()
        process = self.multiprocess if process is None else process
        process.terminate()
        print 'Dead'

    def put(self, *args, **kwargs):
        '''
        Write to the multiprocess queue. All clients will receive it.
        '''
        if self.queue:
            self.queue.put(*args, **kwargs)


class PocketServer(ThreadedSocketServer):
    
    def __init__(self, host='127.0.0.1', port=8001, client_socket=None, \
        verbose=True, queue=None):
        super(PocketServer, self).__init__(host, port, client_socket, \
            verbose, queue)

    def start_serveforever(self, *args, **kwargs):
        '''
        Begin the parental start server.
        '''
        super(PocketServer, self).start_serveforever(*args, **kwargs)
        print get_local_ip()


def cli(host, port=8001, verbose=True, socket=None):
    server = PocketServer(host, port, socket, verbose=verbose)
    server.start()
    return server

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
    cli(host, port, verbose)

if __name__ == '__main__':
    main()
