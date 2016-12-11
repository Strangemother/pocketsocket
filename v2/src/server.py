from SimpleWebSocketServer import SimpleWebSocketServer
import socket
from select import select
from collections import deque
import time
import struct
import sys


GUID_STR = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


VER = sys.version_info[0]
if VER >= 3:
    import socketserver
    from http.server import BaseHTTPRequestHandler
    from io import StringIO, BytesIO
else:
    import SocketServer
    from BaseHTTPServer import BaseHTTPRequestHandler
    from StringIO import StringIO


_VALID_STATUS_CODES = [1000, 1001, 1002, 1003, 1007, 1008,
                       1009, 1010, 1011, 3000, 3999, 4000, 4999]

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

HEADERB1 = 1
HEADERB2 = 3
LENGTHSHORT = 4
LENGTHLONG = 5
MASK = 6
PAYLOAD = 7

MAXHEADER = 65536
MAXPAYLOAD = 33554432


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


class HTTPRequest(BaseHTTPRequestHandler):

    def __init__(self, request_text):
        if VER >= 3:
            self.rfile = BytesIO(request_text)
        else:
            self.rfile = StringIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()


import hashlib
import base64
import codecs

HANDSHAKE_STR = (
    "HTTP/1.1 101 Switching Protocols\r\n"
    "Upgrade: WebSocket\r\n"
    "Connection: Upgrade\r\n"
    "Sec-WebSocket-Accept: %(acceptstr)s\r\n\r\n"
)


class SocketClient(object):
    '''
    A client for the Connections
    '''

    def __init__(self, sock, address):
        self.socket = sock
        self.address = address
        self.headerbuffer = bytearray()
        self.sendq = deque()
        self.connected = False

        self.state = HEADERB1
        self.frag_start = False
        self.frag_type = OPTION_CODES.BINARY
        self.frag_buffer = None
        self.frag_decoder = codecs.getincrementaldecoder(
            'utf-8')(errors='strict')

    def handshake(self):

        print '\nSocketClient.handshake', self

        # self.socket.accept()
        # Start handshake
        if self.connected is False:
            data = self.socket.recv(2048)

            if not data:
                print '  Received no data. SocketClosed'
                return False

        # accumulate
        self.headerbuffer.extend(data)

        if len(self.headerbuffer) >= MAXHEADER:
            print '  header exceeded allowable size'
            return False

        # indicates end of HTTP header
        if (b'\r\n\r\n' in self.headerbuffer) is False:
            # Data is not complete. Wait until the buffer is complete
            return

        # Build a HTTP request with the finished data.
        request = HTTPRequest(self.headerbuffer)

        print '  building handshake'
        # handshake rfc 6455
        key = request.headers['Sec-WebSocket-Key']
        k = key.encode('ascii') + GUID_STR.encode('ascii')
        k_s = base64.b64encode(hashlib.sha1(k).digest()).decode('ascii')
        hStr = HANDSHAKE_STR % {'acceptstr': k_s}
        v = (OPTION_CODES.BINARY, hStr.encode('ascii'))
        self.sendq.append(v)
        print '  added to sendq',
        print '  size', len(self.sendq)

        self.connected = True

        return self.socket, self.address

    def _handleData(self):
        # do the HTTP header and handshake
        if self.connected is False:
            self.handshake()
        # else do normal data
        else:
            data = self.socket.recv(8192)
            if not data:
                self.handleError("remote socket closed")

            if VER >= 3:
                for d in data:
                    self._parseMessage(d)
            else:
                for d in data:
                    self._parseMessage(ord(d))

    def _parseMessage(self, byte):
        # read in the header
        if self.state == HEADERB1:

            self.fin = byte & 0x80
            self.opcode = byte & 0x0F
            self.state = HEADERB2

            self.index = 0
            self.length = 0
            self.lengtharray = bytearray()
            self.data = bytearray()

            rsv = byte & 0x70
            if rsv != 0:
                self.handleError('RSV bit must be 0')

        elif self.state == HEADERB2:
            mask = byte & 0x80
            length = byte & 0x7F

            if self.opcode == OPTION_CODES.PING and length > 125:
                self.handleError('ping packet is too large')

            if mask == 128:
                self.hasmask = True
            else:
                self.hasmask = False

            if length <= 125:
                self.length = length

                # if we have a mask we must read it
                if self.hasmask is True:
                    self.maskarray = bytearray()
                    self.state = MASK
                else:
                    # if there is no mask and no payload we are done
                    if self.length <= 0:
                        try:
                            self._handlePacket()
                        finally:
                            self.state = self.HEADERB1
                            self.data = bytearray()

                    # we have no mask and some payload
                    else:
                        #self.index = 0
                        self.data = bytearray()
                        self.state = PAYLOAD

            elif length == 126:
                self.lengtharray = bytearray()
                self.state = LENGTHSHORT

            elif length == 127:
                self.lengtharray = bytearray()
                self.state = LENGTHLONG

        elif self.state == LENGTHSHORT:
            self.lengtharray.append(byte)

            if len(self.lengtharray) > 2:
                self.handleError('short length exceeded allowable size')

            if len(self.lengtharray) == 2:
                self.length = struct.unpack_from('!H', self.lengtharray)[0]

                if self.hasmask is True:
                    self.maskarray = bytearray()
                    self.state = MASK
                else:
                    # if there is no mask and no payload we are done
                    if self.length <= 0:
                        try:
                            self._handlePacket()
                        finally:
                            self.state = HEADERB1
                            self.data = bytearray()

                    # we have no mask and some payload
                    else:
                        #self.index = 0
                        self.data = bytearray()
                        self.state = PAYLOAD

        elif self.state == LENGTHLONG:

            self.lengtharray.append(byte)

            if len(self.lengtharray) > 8:
                self.handleError('long length exceeded allowable size')

            if len(self.lengtharray) == 8:
                self.length = struct.unpack_from('!Q', self.lengtharray)[0]

                if self.hasmask is True:
                    self.maskarray = bytearray()
                    self.state = MASK
                else:
                    # if there is no mask and no payload we are done
                    if self.length <= 0:
                        try:
                            self._handlePacket()
                        finally:
                            self.state = HEADERB1
                            self.data = bytearray()

                    # we have no mask and some payload
                    else:
                        #self.index = 0
                        self.data = bytearray()
                        self.state = PAYLOAD

        # MASK STATE
        elif self.state == MASK:
            self.maskarray.append(byte)

            if len(self.maskarray) > 4:
                self.handleError('mask exceeded allowable size')

            if len(self.maskarray) == 4:
                # if there is no mask and no payload we are done
                if self.length <= 0:
                    try:
                        self._handlePacket()
                    finally:
                        self.state = HEADERB1
                        self.data = bytearray()

                # we have no mask and some payload
                else:
                    #self.index = 0
                    self.data = bytearray()
                    self.state = PAYLOAD

        # PAYLOAD STATE
        elif self.state == PAYLOAD:
            if self.hasmask is True:
                self.data.append(byte ^ self.maskarray[self.index % 4])
            else:
                self.data.append(byte)

            # if length exceeds allowable size then we except and remove the
            # connection
            if len(self.data) >=MAXPAYLOAD:
                self.handleError('payload exceeded allowable size')

            # check if we have processed length bytes; if so we are done
            if (self.index+1) == self.length:
                try:
                    self._handlePacket()
                finally:
                    #self.index = 0
                    self.state = HEADERB1
                    self.data = bytearray()
            else:
                self.index += 1

    def _handlePacket(self):
        if self.opcode == OPTION_CODES.CLOSE:
            pass
        elif self.opcode == OPTION_CODES.STREAM:
            pass
        elif self.opcode == OPTION_CODES.TEXT:
            print 'DATA:', self.data
        elif self.opcode == OPTION_CODES.BINARY:
            pass
        elif self.opcode == OPTION_CODES.PONG or self.opcode == OPTION_CODES.PING:
            if len(self.data) > 125:
                self.handleError('control frame length can not be > 125')
        else:
            # unknown or reserved opcode so just close
            self.handleError('unknown opcode')

        if self.opcode == OPTION_CODES.CLOSE:
            status = 1000
            reason = u''
            length = len(self.data)

            if length == 0:
                pass
            elif length >= 2:
                status = struct.unpack_from('!H', self.data[:2])[0]
                reason = self.data[2:]

                if status not in _VALID_STATUS_CODES:
                    status = 1002

                if len(reason) > 0:
                    try:
                        reason = reason.decode('utf8', errors='strict')
                    except:
                        status = 1002
            else:
                status = 1002

            self.close(status, reason)
            return

        elif self.fin == 0:
            if self.opcode != OPTION_CODES.STREAM:
                if self.opcode == OPTION_CODES.PING or self.opcode == OPTION_CODES.PONG:
                    self.handleError('control messages can not be fragmented')

                self.frag_type = self.opcode
                self.frag_start = True
                self.frag_decoder.reset()

                if self.frag_type == OPTION_CODES.TEXT:
                    self.frag_buffer = []
                    utf_str = self.frag_decoder.decode(self.data, final=False)
                    if utf_str:
                        self.frag_buffer.append(utf_str)
                else:
                    self.frag_buffer = bytearray()
                    self.frag_buffer.extend(self.data)

            else:
                if self.frag_start is False:
                    self.handleError('fragmentation protocol error')

                if self.frag_type == OPTION_CODES.TEXT:
                    utf_str = self.frag_decoder.decode(self.data, final=False)
                    if utf_str:
                        self.frag_buffer.append(utf_str)
                else:
                    self.frag_buffer.extend(self.data)

        else:
            if self.opcode == OPTION_CODES.STREAM:
                if self.frag_start is False:
                    self.handleError('fragmentation protocol error')

                if self.frag_type == OPTION_CODES.TEXT:
                    utf_str = self.frag_decoder.decode(self.data, final=True)
                    self.frag_buffer.append(utf_str)
                    self.data = u''.join(self.frag_buffer)
                else:
                    self.frag_buffer.extend(self.data)
                    self.data = self.frag_buffer

                self.handleMessage()

                self.frag_decoder.reset()
                self.frag_type = OPTION_CODES.BINARY
                self.frag_start = False
                self.frag_buffer = None

            elif self.opcode == OPTION_CODES.PING:
                self._sendMessage(False, OPTION_CODES.PONG, self.data)

            elif self.opcode == OPTION_CODES.PONG:
                pass

            else:
                if self.frag_start is True:
                    self.handleError('fragmentation protocol error')

                if self.opcode == OPTION_CODES.TEXT:
                    try:
                        self.data = self.data.decode('utf8', errors='strict')
                    except Exception as exp:
                        self.handleError('invalid utf-8 payload', exp)

    def _sendBuffer(self, buff):
        size = len(buff)
        tosend = size
        already_sent = 0

        print self, 'send', size
        while tosend > 0:
            try:
                # i should be able to send a bytearray
                sent = self.socket.send(buff[already_sent:])
                if sent == 0:
                    self.handleError("socket connection broken")

                already_sent += sent
                tosend -= sent

            except socket.error as e:
                # if we have full buffers then wait for them to drain and try
                # again
                if e.errno in [errno.EAGAIN, errno.EWOULDBLOCK]:
                    return buff[already_sent:]
                else:
                    raise e

        return None

    def __unicode__(self):
        return 'Client: %s' % self.address

    def __repr__(self):
        s = u'<SocketClient "%s" Queue: %s>' % (self.address, len(self.sendq))
        return s


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
        self.connections = {}

        methods = ('write_list', 'read_list', 'fail_list', )
        while self.served():
            writers = self.writers(listeners, self.connections)
            # read, write, exception list

            rl, wl, xl = self.select(listeners, writers)
            for name, sl in zip(methods, (wl, rl, xl)):
                getattr(self, name)(sl, listeners, self.connections)

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
            #except socket.error as e:
            #    print '  write_list Exception', type(e), str(e), client
            #    self.client_close(client, listeners, connections)

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

        print '\n-- Accepting socket', socket

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
