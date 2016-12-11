import socket
from select import select
from client import SocketClient


class OPTION_CODES:
    '''
    An option code from the client stream
    '''
    STREAM = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA


def main():
    server = Server()
    server.setup('127.0.0.1', 8009)
    server.loop()


def socket_bind(host='127.0.0.1', port=None):
    '''
    A server socket readied with a host and port.
    '''
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(5)
    return s, host, port


class SocketCreateMixin(object):

    def setup_listeners(self, host=None, port=None):
        '''
        Setup the internal listeners of the server.
        '''
        hosts = (host,) if host is not None else self.hosts
        ports = (port,) if port is not None else self.ports

        listeners = self.bind_pairs(hosts, ports)

        # TODO: Change this...
        self._socket = listeners[0]

        return listeners

    def bind_pairs(self, hosts, ports):
        '''
        Given a list of hosts and ports of equal length, return a list of ready sockets
        each with a uniqe host and port. Will call `self.create_socket`
        '''
        r = []
        for host, port in zip(hosts, ports):
            sock, h, p = self.create_socket(host, port)
            r.append(sock)
        return r

    def create_socket(self, host=None, port=None):
        '''
        Create and return a ready bound socket using the given host and port.
        '''
        return socket_bind(host, port)


class ConnectionIteratorMixin(object):

    def served(self):
        '''Return boolean if the the socket should be served.
        Is used by the  service loop for each iteration.
        '''
        return True

    def select(self, listeners, writers):
        '''
        Using select system call return the waiting objects of the listeners.
        https://docs.python.org/2/library/select.html#select.select
        '''
        timeout = 4

        # time.sleep(.5)

        # print '.',
        return select(listeners, writers, listeners, timeout)

    def writers(self, listeners, connections):
        r = tuple()
        for sock in listeners:

            if (sock in connections) is False:
                continue

            client = connections[sock]

            if hasattr(client, 'sendq'):
                r += (sock, )
        return r

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

    def write_list(self, wlist, listeners, connections):
        # Iterate write to client, Pushing client.sendq
        # data to the Websocket._sendBuffer
        client = None

        for ready in wlist:

            #try:
            client = connections[ready]
            # print 'write_list', ready, len(client.sendq), client

            while client.sendq:
                print 'write_list Sending payload:', client
                opcode, payload = client.sendq.popleft()
                remaining = client._sendBuffer(payload)
                if remaining is not None:
                    client.sendq.appendleft((opcode, remaining))
                    break
                else:
                    if opcode == OPTION_CODES.CLOSE:
                        raise Exception("received client close")

    def read_list(self, rlist, listeners, connections):
        # list of clients to read from.
        for sock in rlist:

            if self.raw_socket_match(sock, listeners):
                if isinstance(sock, long):
                    sock = connections[sock]
                print '  Raw match accept'
                client = self.accept_socket(sock, listeners, connections)
            else:
                print '  Handle',
                client = connections[sock]
                client._handleData()

    def fail_list(self, xlist, listeners, connections):
        for failed in xlist:
            if self.raw_socket_match(failed, listeners):
                self.exception_close(failed, listeners, connections)
            else:
                self.client_close(failed, listeners, connections)

    def exception_close(self, sock, listeners, connections):
        print 'Socket error', sock
        self.close(sock)
        raise Exception('Socket close %s' % sock)

    def client_close(self, client, listeners, connections):
        print 'close a client', client, dir(client)
        if hasattr(client, 'socket'):
            client.socket.close()

        if client in listeners:
            'Removing client from listeners'
            listeners.remove(client)
        if client in connections:
            print 'deleting connection'
            del connections[client]

    def close(self, sock):
        sock.close()

    def raw_socket_match(self, client, listeners):
        '''
        Determine if the given client is a server socket for clients.
        '''
        if client == self._socket:
            # if fileno == client:
                return True
        return False

    def accept_socket(self, socket, listeners, connections):
        '''
        Accet the given socket and append to the connections and listeners
        for iteration.
        Returned is the client from `self.create_client`
        '''

        # TODO: Wtf the eww.
        if isinstance(socket, SocketClient):
            print '  resocket', socket
            sock, addr = socket.handshake()
            return socket
        else:
            sock, addr = socket.accept()
            print 'A socket accept', socket
            fileno, client = self.create_client(sock, addr)
            print '  Socket:', client

            listeners.append(fileno)
            connections[fileno] = client
            return client

    def create_client(self, sock, addr):
        '''
        Create and return a new Websocket class and client.
        The client is appended to a list of receivers, handling in/out data.
        '''
        print 'create_client', sock
        fileno = sock.fileno()
        sock.setblocking(0)
        # TODO: Be websocket client
        client = SocketClient(sock, addr)
        return fileno, client


class SocketServer(SocketCreateMixin, ConnectionIteratorMixin):
    # Open a server socket, bind and listen for connection

    def setup(self, host, port):
        self.hosts = (host,)
        self.ports = (port,)
        self.listeners = self.setup_listeners()
        print 'Created listeners', self.listeners

    def loop(self):
        self.loop_forever(self.listeners)


class Server(SocketServer):
    '''
    The server handles the Service, Client and Config
    '''
    pass


if __name__ == '__main__':
    main()
