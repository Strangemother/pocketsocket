from collections import deque
import codecs
import struct
import sys
import hashlib
import base64
import socket


class STATE:
    HEADERB1 = 1
    HEADERB2 = 3
    LENGTHSHORT = 4
    LENGTHLONG = 5
    MASK = 6
    PAYLOAD = 7

MAXHEADER = 65536
MAXPAYLOAD = 33554432


_VALID_STATUS_CODES = [1000, 1001, 1002, 1003, 1007, 1008,
                       1009, 1010, 1011, 3000, 3999, 4000, 4999]


HANDSHAKE_STR = (
    "HTTP/1.1 101 Switching Protocols\r\n"
    "Upgrade: WebSocket\r\n"
    "Connection: Upgrade\r\n"
    "Sec-WebSocket-Accept: %(acceptstr)s\r\n\r\n"
)


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


class OPTION_CODE:
    '''
    An option code from the client stream
    '''
    STREAM = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA


class HTTPRequest(BaseHTTPRequestHandler):

    def __init__(self, request_text):
        if VER >= 3:
            self.rfile = BytesIO(request_text)
        else:
            self.rfile = StringIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()


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

        self.state = STATE.HEADERB1
        self.frag_start = False
        self.frag_type = OPTION_CODE.BINARY
        self.frag_buffer = None
        self.frag_decoder = codecs.getincrementaldecoder('utf-8')(errors='strict')

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
        v = (OPTION_CODE.BINARY, hStr.encode('ascii'))
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
        if self.state == STATE.HEADERB1:

            self.fin = byte & 0x80
            self.opcode = byte & 0x0F
            self.state = STATE.HEADERB2

            self.index = 0
            self.length = 0
            self.lengtharray = bytearray()
            self.data = bytearray()

            rsv = byte & 0x70
            if rsv != 0:
                self.handleError('RSV bit must be 0')

        elif self.state == STATE.HEADERB2:
            mask = byte & 0x80
            length = byte & 0x7F

            if self.opcode == OPTION_CODE.PING and length > 125:
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
                    self.state = STATE.MASK
                else:
                    # if there is no mask and no payload we are done
                    if self.length <= 0:
                        try:
                            self._handlePacket()
                        finally:
                            self.state = self.STATE.HEADERB1
                            self.data = bytearray()

                    # we have no mask and some payload
                    else:
                        #self.index = 0
                        self.data = bytearray()
                        self.state = STATE.PAYLOAD

            elif length == 126:
                self.lengtharray = bytearray()
                self.state = STATE.LENGTHSHORT

            elif length == 127:
                self.lengtharray = bytearray()
                self.state = STATE.LENGTHLONG

        elif self.state == STATE.LENGTHSHORT:
            self.lengtharray.append(byte)

            if len(self.lengtharray) > 2:
                self.handleError('short length exceeded allowable size')

            if len(self.lengtharray) == 2:
                self.length = struct.unpack_from('!H', self.lengtharray)[0]

                if self.hasmask is True:
                    self.maskarray = bytearray()
                    self.state = STATE.MASK
                else:
                    # if there is no mask and no payload we are done
                    if self.length <= 0:
                        try:
                            self._handlePacket()
                        finally:
                            self.state = STATE.HEADERB1
                            self.data = bytearray()

                    # we have no mask and some payload
                    else:
                        #self.index = 0
                        self.data = bytearray()
                        self.state = STATE.PAYLOAD

        elif self.state == STATE.LENGTHLONG:

            self.lengtharray.append(byte)

            if len(self.lengtharray) > 8:
                self.handleError('long length exceeded allowable size')

            if len(self.lengtharray) == 8:
                self.length = struct.unpack_from('!Q', self.lengtharray)[0]

                if self.hasmask is True:
                    self.maskarray = bytearray()
                    self.state = STATE.MASK
                else:
                    # if there is no mask and no payload we are done
                    if self.length <= 0:
                        try:
                            self._handlePacket()
                        finally:
                            self.state = STATE.HEADERB1
                            self.data = bytearray()

                    # we have no mask and some payload
                    else:
                        #self.index = 0
                        self.data = bytearray()
                        self.state = STATE.PAYLOAD

        # STATE.MASK STATE
        elif self.state == STATE.MASK:
            self.maskarray.append(byte)

            if len(self.maskarray) > 4:
                self.handleError('mask exceeded allowable size')

            if len(self.maskarray) == 4:
                # if there is no mask and no payload we are done
                if self.length <= 0:
                    try:
                        self._handlePacket()
                    finally:
                        self.state = STATE.HEADERB1
                        self.data = bytearray()

                # we have no mask and some payload
                else:
                    #self.index = 0
                    self.data = bytearray()
                    self.state = STATE.PAYLOAD

        # STATE.PAYLOAD STATE
        elif self.state == STATE.PAYLOAD:
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
                    self.state = STATE.HEADERB1
                    self.data = bytearray()
            else:
                self.index += 1

    def _handlePacket(self):
        if self.opcode == OPTION_CODE.CLOSE:
            pass
        elif self.opcode == OPTION_CODE.STREAM:
            pass
        elif self.opcode == OPTION_CODE.TEXT:
            print 'DATA:', self.data
        elif self.opcode == OPTION_CODE.BINARY:
            pass
        elif self.opcode == OPTION_CODE.PONG or self.opcode == OPTION_CODE.PING:
            if len(self.data) > 125:
                self.handleError('control frame length can not be > 125')
        else:
            # unknown or reserved opcode so just close
            self.handleError('unknown opcode')

        if self.opcode == OPTION_CODE.CLOSE:
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
            if self.opcode != OPTION_CODE.STREAM:
                if self.opcode == OPTION_CODE.PING or self.opcode == OPTION_CODE.PONG:
                    self.handleError('control messages can not be fragmented')

                self.frag_type = self.opcode
                self.frag_start = True
                self.frag_decoder.reset()

                if self.frag_type == OPTION_CODE.TEXT:
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

                if self.frag_type == OPTION_CODE.TEXT:
                    utf_str = self.frag_decoder.decode(self.data, final=False)
                    if utf_str:
                        self.frag_buffer.append(utf_str)
                else:
                    self.frag_buffer.extend(self.data)

        else:
            if self.opcode == OPTION_CODE.STREAM:
                if self.frag_start is False:
                    self.handleError('fragmentation protocol error')

                if self.frag_type == OPTION_CODE.TEXT:
                    utf_str = self.frag_decoder.decode(self.data, final=True)
                    self.frag_buffer.append(utf_str)
                    self.data = u''.join(self.frag_buffer)
                else:
                    self.frag_buffer.extend(self.data)
                    self.data = self.frag_buffer

                self.handleMessage()

                self.frag_decoder.reset()
                self.frag_type = OPTION_CODE.BINARY
                self.frag_start = False
                self.frag_buffer = None

            elif self.opcode == OPTION_CODE.PING:
                self._sendMessage(False, OPTION_CODE.PONG, self.data)

            elif self.opcode == OPTION_CODE.PONG:
                pass

            else:
                if self.frag_start is True:
                    self.handleError('fragmentation protocol error')

                if self.opcode == OPTION_CODE.TEXT:
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

