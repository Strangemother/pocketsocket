import socket
from select import select
import errno
import hashlib
import base64
import struct

from itertools import product
from http import HTTPRequest
from utils import VER,  _check_unicode
from states import OPTION_CODE, STATE
from logger import log, loge, logw

HANDSHAKE_STR = (
    "HTTP/1.1 101 Switching Protocols\r\n"
    "Upgrade: WebSocket\r\n"
    "Connection: Upgrade\r\n"
    "Sec-WebSocket-Accept: %(acceptstr)s\r\n\r\n"
)

MAXHEADER = 65536
CHUNK = 8192
GUID_STR = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


class ServerIntegrationMixin(object):

    connected = None

    def set_id(self, value):
        self._connection_id = value

    def accept(self, socket, server):
        ''' Server has given a socket parent to accept this client on.
        Return an identifier; the socket fileno. '''
        sock, addr = socket.accept()
        self.socket = sock
        self.address = addr
        fileno = sock.fileno()
        sock.setblocking(0)
        return fileno

    def getsockname(self):
        '''
        Shim replacement to return the socketname of the internal socket.
        '''
        return self.socket.getpeername()

    def close(self, status, reason):
        """
           Send Close frame to the client. The underlying socket is only closed
           when the client acknowledges the Close frame.

           status is the closing identifier.
           reason is the reason for the close.
        """
        try:
            if self.closed is True:
                return

            log('Client close', status, reason)
            close_msg = bytearray()
            close_msg.extend(struct.pack("!H", status))
            is_uni = _check_unicode(reason)
            close_msg.extend(reason.encode('utf-8') if is_uni else reason)
            self._sendMessage(False, OPTION_CODE.CLOSE, close_msg)
        finally:
            self.closed = True


class BufferMixin(object):

    writable = True

    def has_data(self):
        ''' Determine if the socket has any content to send, Returns true if
        the socket queue has content, false if the queue length is 0; '''
        return len(self.buffer_queue) > 0

    def next_buffer(self):
        # opcode, payload = client.buffer_queue.popleft()
        return self.buffer_queue.popleft()

    def add_buffer(self, opcode, data, top=False):
        ''' Set the queue entry to the output buffer queue.
        Provide `opcode<OPTION_CODE>` and `data`.
        If `top` is True, the data is applied to the top
        of the bugger queue. '''
        v = (opcode, data)

        if top is True:
            self.buffer_queue.appendleft(v)
        else:
            self.buffer_queue.append(v)

    def loop_buffer(self):
        while self.has_data():
            opcode, remaining = self._loop_send_buffer()
            if opcode == OPTION_CODE.CLOSE:
                log('BufferMixin.loop_buffer.CLOSE')
                self.close(opcode, 'Client closed early')
                return opcode, remaining
        return True, 0

    def _loop_send_buffer(self):
        opcode, payload = self.next_buffer()
        remaining = self._send_payload(payload)
        # Push the unsent content back into the send buffer
        # for the next loop.
        if remaining is not None:
            # self.buffer_queue.appendleft((opcode, remaining))
            self.add_buffer(opcode, remaining)
        return opcode, remaining

    def _send_payload(self, payload):
        '''
        Send the payload using `socket.send`. Iterate any chunk remaining
        from the socket send result until nothing remains.
        Returns the remaining amount <int> of payload. None if no payload content
        remains
        '''
        remaining = len(payload)
        total_sent = 0

        while remaining > 0:
            slice = payload[total_sent:]
            try:
                # i should be able to send a bytearray
                sent = self.socket.send(slice)
                if sent == 0:
                    self.handleError("socket connection broken")
                total_sent += sent
                remaining -= sent
            except socket.error as e:
                if e.errno in [errno.EAGAIN, errno.EWOULDBLOCK]:
                    return slice
                else:
                    raise e
        return None

    def start(self, server=None, listeners=None, connections=None):
        print '\nSocketClient.handshake', self
        return self.handshake()

    def handshake(self):
        # Start handshake
        if self.connected is False:
            data = self.socket.recv(2048)

            if not data:
                loge('Received no data. SocketClosed')
                return False

        # accumulate
        self.headerbuffer.extend(data)

        if len(self.headerbuffer) >= MAXHEADER:
            loge('Header exceeded allowable size')
            return False

        # indicates end of HTTP header
        if (b'\r\n\r\n' in self.headerbuffer) is False:
            # Data is not complete. Wait until the buffer is complete
            return

        # Build a HTTP request with the finished data.
        request = HTTPRequest(self.headerbuffer)
        response = self.handshake_response(request.headers)
        v = (OPTION_CODE.BINARY, response)
        self.buffer_queue.append(v)
        self.connected = True
        return self.connected

    def handshake_response(self, headers):
        # handshake rfc 6455
        key = headers['Sec-WebSocket-Key']
        ascii_guid = GUID_STR.encode('ascii')
        ascii_key = key.encode('ascii')
        k = ascii_key + ascii_guid
        sha_key = hashlib.sha1(k).digest()
        k_s = base64.b64encode(sha_key).decode('ascii')
        hStr = HANDSHAKE_STR % {'acceptstr': k_s}
        return hStr.encode('ascii')

    def read(self):
        if self.connected is False:
            self.handshake()
        else:
            data = self.socket.recv(CHUNK)
            self.handle_byte_chunk(data, size=CHUNK, socket=self.socket)

    def handle_byte_chunk(self, data, size=None, socket=None):
        pass
        # for d in data:
        #     v = (d if VER >= 3 else ord(d))

    def process_payload_packet(self):
        self._handlePacket()
        self.reset_data_state()


class SocketCreateMixin(object):
    ''' Class used to maintain a socket.
    Wrapper to socket.socket '''
    socket_class = None

    def setup_listeners(self, hosts=None, ports=None, **kw):
        '''Setup the internal listeners of the server.'''
        hosts = hosts or tuple()
        ports = ports or tuple()

        listeners = self.bind_pairs(hosts, ports, **kw)
        return listeners

    def bind_pairs(self, hosts, ports, **kw):
        ''' Given a list of hosts and ports of equal length, return a list of
        readysocketseach with a uniqe host and port. Will call
        `self.create_socket`'''
        r = []
        match_len = len(ports) == len(hosts)
        items = zip(ports, hosts) if match_len else product(ports, hosts)

        for port, host in items:
            sock, h, p = self.create_socket(host, port)
            r.append(sock)
        return r

    def create_socket(self, host=None, port=None, **kw):
        '''
        Create and return a ready bound socket using the given host and port.
        '''
        return self.socket_bind(host, port, socket_class=self.socket_class, **kw)

    def socket_bind(self, host='127.0.0.1', port=None, socket_class=None, **kw):
        '''A server socket readied with a host and port.
        provide a socket class or socket.socket is used.'''
        SocketClass = socket_class or socket.socket
        s = SocketClass(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(5)
        from logger import log

        # l = logging.getLogger('SocketLog')
        log('Listen on', host, port)
        return s, host, port


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
                if c is not None:
                    c.read()

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


class Fragment(object):
    '''
    Byte array builder
    '''
    _type = None

    def __init__(self, _type, **kwargs):
        # self.frag_decoder = codecs.getincrementaldecoder('utf-8')(errors='strict')
        self.frag_buffer = []
        self.type = _type

    def add(self, data):
        '''
        Push data to the working fragment
        '''

        if self.type == OPTION_CODE.TEXT:
            self.frag_buffer = []
            utf_str = self.frag_decoder.decode(self.data, final=False)
            if utf_str:
                self.frag_buffer.append(utf_str)
        else:
            self.frag_buffer = bytearray()
            self.frag_buffer.extend(self.data)

    def get_type(self):
        return self._type

    def set_type(self, v):
        self._type = v

    type = property(get_type, set_type)

class FragmentMixin(object):
    pass
