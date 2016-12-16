import socket
from select import select
from client import SocketClient, OPTION_CODE
import errno


def main():
    server = Server()
    server.setup('127.0.0.1', 8009)
    server.loop()


class Listener(socket.socket):
    '''
    A Listener is a socket, defined as a parental socket managing the
    main open port for clients.

    It's mainly written so it's easier to identify on the command line.
    '''
    def __repr__(self):
        try:
            name = 'peer'
            pn = self.getpeername()
        except socket.error as e:
            # https://msdn.microsoft.com/en-us/library/windows/desktop/
            # ms740668(v=vs.85).aspx
            if e.errno in [errno.WSAENOTCONN]:
                name = 'sock'
                try:
                    pn = self.getsockname()
                except socket.error as e:
                    pn = 'unknown'
            else:
                raise e
        # import pdb; pdb.set_trace()  # breakpoint 5f2f3c04 //
        return r'<Listener(socket.socket): %s %s>' % (name, pn, )


class SocketCreateMixin(object):

    ''' Class used to maintain a socket.
    Wrapper to socket.socket
    '''
    socket_class = Listener

    def setup_listeners(self, host=None, port=None):
        '''Setup the internal listeners of the server.'''
        hosts = (host,) if host is not None else self.hosts
        ports = (port,) if port is not None else self.ports

        listeners = self.bind_pairs(hosts, ports)
        return listeners

    def bind_pairs(self, hosts, ports):
        ''' Given a list of hosts and ports of equal length, return a list of
        readysocketseach with a uniqe host and port. Will call
        `self.create_socket`'''
        r = []
        for host, port in zip(hosts, ports):
            sock, h, p = self.create_socket(host, port)
            r.append(sock)
        return r

    def create_socket(self, host=None, port=None):
        '''
        Create and return a ready bound socket using the given host and port.
        '''
        return self.socket_bind(host, port, socket_class=self.socket_class)

    def socket_bind(self, host='127.0.0.1', port=None, socket_class=None):
        '''A server socket readied with a host and port.
        provide a socket class or socket.socket is used.'''
        SocketClass = socket_class or socket.socket
        s = SocketClass(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(5)
        return s, host, port


class ConnectionIteratorMixin(object):

    client_class = SocketClient

    def served(self):
        '''Return boolean if the the socket should be served.
        Is used by the  service loop for each iteration.'''
        return True

    def select(self, listeners, writers, timeout=None):
        '''Using select system call return the waiting objects of the listeners.
        https://docs.python.org/2/library/select.html#select.select'''
        return select(listeners, writers, listeners, timeout)

    def loop_forever(self, listeners):
        '''
        Start the server loop, forever receiving clients and serving
        information
        '''
        # Clients in service
        connections = {}

        methods = ('write_list', 'read_list', 'fail_list', )
        while self.served():
            writers = self.writers(listeners, connections)
            # read, write, exception list
            rl, wl, xl = self.select(listeners, writers)
            for name, sl in zip(methods, (wl, rl, xl)):
                getattr(self, name)(sl, listeners, connections)

    def writers(self, listeners, connections):
        '''
        Return a list of writers for the UNIX system select()
            wlist: wait until ready for writing
            If the socket is in the listeners, and does not exist in the
            connections, the client is added to the write list.'''
        r = tuple()
        for sock in listeners:

            if (sock in connections) is False:
                continue

            client = connections[sock]
            client.set_id(sock)
            # client._connection_id = sock
            if self.is_writable(client):
                r += (sock, )
        return r

    def is_writable(self, sock):
        ''' Determine if the socket is writable Return boolean'''
        return hasattr(sock, 'writable') and sock.writable is True

    def write_list(self, wlist, listeners, connections):
        # Iterate write to client, Pushing client.sendq
        # data to the Websocket._sendBuffer
        for fileno in wlist:
            client = connections[fileno]
            opcode, remaining = client.loop_buffer()
            if opcode == OPTION_CODE.CLOSE:
                self.client_close(client, listeners, connections)

    def read_list(self, rlist, listeners, connections):
        # list of clients to read from.
        for sock in rlist:
            if self.raw_socket_match(sock, listeners, connections):
                client = self.accept_socket(sock, listeners, connections)
            else:
                client = connections[sock]
                client._handleData()

    def fail_list(self, xlist, listeners, connections):
        for failed in xlist:
            if self.raw_socket_match(failed, listeners, connections):
                self.exception_close(failed, listeners, connections)
            else:
                self.client_close(failed, listeners, connections)

    def exception_close(self, sock, listeners, connections):
        self.close(sock)
        raise Exception('Socket close %s' % sock)

    def client_close(self, client, listeners, connections):
        print 'close a client', client
        if hasattr(client, 'socket'):
            self.close(client.socket)

        _id = client._connection_id

        if _id in listeners:
            listeners.remove(_id)

        if _id in connections:
            del connections[_id]

        del_con = (_id in connections) is False
        del_lis = (_id in listeners) is False
        return del_con and del_lis

    def close(self, sock):
        sock.close()

    def raw_socket_match(self, client, listeners, connections):
        '''
        Determine if the given client is a server socket for clients.
        '''

        # TODO: Get this removed by ensuring the client is resolved
        # before hand.
        if isinstance(client, long):
            client = connections[client]

        ip, port = client.getsockname()

        # Check against any open IPS and ports for a true
        # parent match. Given at listen() time.
        if (ip in self.hosts) and (port in self.ports):
                return True
        return False

    def accept_socket(self, sock, listeners, connections):
        '''
        Accet the given sock and append to the connections and listeners
        for iteration.
        Returned is the client from `self.create_client`
        '''

        # TODO: remove this from the internal logic; resolve
        # before this method.
        if isinstance(sock, long):
            sock = connections[sock]

        # TODO: fix this, it's terrible
        if isinstance(sock, self.get_client_class()):
            connected = sock.start(self, listeners, connections)
            print 'connected %s: %s' % (sock, connected)
            return sock
        else:
            return self.add_socket(sock, listeners, connections)

    def add_socket(self, sock, listeners, connections):
        ''' Add a socket to the connections and listeners sets.
        Returned is a new client using self.create_client '''
        fileno, client = self.create_client(sock)
        listeners.append(fileno)
        connections[fileno] = client
        return client

    def create_client(self, socket):
        '''
        Create and return a new Websocket class and client.
        The client is appended to a list of receivers, handling in/out data.
        '''
        Client = self.get_client_class()
        client = Client()
        fileno = client.accept(socket)
        return fileno, client

    def get_client_class(self):
        return self.client_class


class Server(SocketCreateMixin, ConnectionIteratorMixin):
    '''
    Open a server socket, bind and listen for connection
    The server handles the Service, Client and Config
    '''

    def setup(self, host, port):
        self.hosts = (host,)
        self.ports = (port,)
        self.listeners = self.setup_listeners()
        print 'Created listeners', self.listeners

    def loop(self):
        self.loop_forever(self.listeners)

    def start(self, *args, **kw):
        '''
        Perform setup and start
        '''
        self.setup(*args)
        self.loop()

if __name__ == '__main__':
    main()
