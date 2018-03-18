from select import select


class ConnectionIteratorMixin(object):

    client_class = None
    methods = ('write_list', 'read_list', 'fail_list', )

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

        self._loop_with_interrupt(listeners, connections)

    def _loop_with_interrupt(self, listeners, connections):

        try:
            while self.served():
                self._loop_methods(self.methods, listeners, connections)
        except KeyboardInterrupt:
            log('--- Keyboard shutdown')

    def _loop_methods(self, methods, listeners, connections):
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
                self.accept_socket(sock, listeners, connections)
            else:
                c = self.resolve_client(sock, listeners, connections)
                if c is None:
                    continue

                try:
                    c.read()
                except socket.error as e:
                    print( 'ERROR', e.errno)
                    self.client_close(c, listeners, connections)
                    #if e.errno in [errno.EAGAIN, errno.EWOULDBLOCK]:
                    #    return slice
                    #else:
                    #    raise e

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

        _id = None

        if hasattr(client, 'socket'):
            self.close(client.socket)
        elif isinstance(client, long):
            v = connections.get(client, None)
            if v is None:
                _id = client
            else:
                client = v

        if _id is None:
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

    def resolve_client(self, client, listeners, connections):
        '''
        Given an object or long return a client.
        '''

        # TODO: Get this removed by ensuring the client is resolved
        # before hand.

        if isinstance(client, long):
            try:
                client = connections[client]
            except KeyError:
                # Client is missing
                logw('resolve_client: Client death')
                deleted = self.client_close(client, listeners, connections)
                if deleted:
                    return None
        return client

    def raw_socket_match(self, client, listeners, connections):
        '''
        Determine if the given client is a server socket for clients.
        '''
        client = self.resolve_client(client, listeners, connections)

        if client is None:
            return False
        ip, port = client.getsockname()

        # Check against any open IPS and ports for a true
        # parent match. Given at listen() time.
        if (ip in self.hosts) and (port in self.ports):
                return True
        return False

    def accept_socket(self, sock, listeners, connections):
        '''
        Accept the given sock and append to the connections and listeners
        for iteration.
        Returned is the client from `self.create_client`
        '''
        sock = self.resolve_client(sock, listeners, connections)


        # TODO: fix this, it's terrible
        if isinstance(sock, self.get_client_class()):
            sock.start(self, listeners, connections)
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
        client.connected = False
        fileno = client.accept(socket, self)
        log('Create Client', client)
        return fileno, client

    def get_client_class(self):
        return self.client_class
