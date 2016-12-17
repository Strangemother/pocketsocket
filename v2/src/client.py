from collections import deque
import codecs
import struct
import sys
import hashlib
import base64
import socket


CHUNK = 8192
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

class States:

    @classmethod
    def keys(cls):
        c = cls
        v =[a for a in dir(c) if not a.startswith('__') and not callable(getattr(c,a))]
        return v

    @classmethod
    def values(cls):
        c = cls
        v =[getattr(c, a) for a in dir(c) if not a.startswith('__') and not callable(getattr(c,a))]
        return v

    @classmethod
    def key_value(cls, value=None, default_value=None):
        '''
        Given a value return its key
        If key is None, a tuple of tuples for every key; (KEY, Value,)
        '''
        c = cls
        v =[(getattr(c, a), a) for a in dir(c) if not a.startswith('__') and not callable(getattr(c,a))]
        dset = dict(v).get(value, default_value)

        return dset


class OPTION_CODE(States):
    '''
    An option code from the client stream

    https://tools.ietf.org/html/rfc6455#page-29
    '''
    STREAM = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA


class STATE(States):
    HEADERB1 = 1
    HEADERB2 = 3
    LENGTHSHORT = 4
    LENGTHLONG = 5
    MASK = 6
    PAYLOAD = 7


class HTTPRequest(BaseHTTPRequestHandler):

    def __init__(self, request_text):
        if VER >= 3:
            self.rfile = BytesIO(request_text)
        else:
            self.rfile = StringIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()


def _check_unicode(val):
    if VER >= 3:
        return isinstance(val, str)
    else:
        return isinstance(val, unicode)


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
                print 'BufferMixin.loop_buffer.CLOSE'
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


class ServerIntegrationMixin(object):

    def set_id(self, value):
        self._connection_id = value

    def accept(self, socket):
        ''' Server has given a socket parent to accept this client on.
        Return an identifier; the socket fileno. '''
        sock, addr = socket.accept()
        self.socket = sock
        self.address = addr
        print 'create_client', addr
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
            if self.closed is False:
                print 'client close', status, reason
                close_msg = bytearray()
                close_msg.extend(struct.pack("!H", status))
                if _check_unicode(reason):
                    close_msg.extend(reason.encode('utf-8'))
                else:
                    close_msg.extend(reason)
                self._sendMessage(False, OPTION_CODE.CLOSE, close_msg)
        finally:
            self.closed = True

    def start(self, server=None, listeners=None, connections=None):

        print '\nSocketClient.handshake', self
        return self.handshake()

    def handshake(self):
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
        response = self.handshake_response(request.headers)
        v = (OPTION_CODE.BINARY, response)
        self.buffer_queue.append(v)
        self.connected = True
        return self.connected

    def handshake_response(self, headers):
        # handshake rfc 6455
        # print '  Headers: ', headers.keys()
        key = headers['Sec-WebSocket-Key']
        ascii_guid = GUID_STR.encode('ascii')
        ascii_key = key.encode('ascii')
        k = ascii_key + ascii_guid
        sha_key = hashlib.sha1(k).digest()
        k_s = base64.b64encode(sha_key).decode('ascii')
        hStr = HANDSHAKE_STR % {'acceptstr': k_s}
        return hStr.encode('ascii')


class WebsocketBinaryPayloadMixin(object):

    def create_websocket_payload(self, data, opcode=None, fin=False):
        '''
        https://tools.ietf.org/html/rfc6455#page-28
        '''
        payload = bytearray()

        b1 = 0
        b2 = 0
        if fin is False:
            b1 |= 0x80
        b1 |= opcode

        if _check_unicode(data):
            data = data.encode('utf-8')

        length = len(data)
        payload.append(b1)

        if length <= 125:
            b2 |= length
            payload.append(b2)

        elif length >= 126 and length <= 65535:
            b2 |= 126
            payload.append(b2)
            # unasigned short
            payload.extend(struct.pack("!H", length))

        else:
            b2 |= 127
            payload.append(b2)
            # unassigned long long
            payload.extend(struct.pack("!Q", length))

        if length > 0:
            payload.extend(data)

        return payload


class StateHandler(object):

    states = None

    _current_state = None

    def get_current_state(self):
        return self._current_state

    def set_current_state(self, v):
        r = v
        if v != self._current_state:
            r = self.state_changed(v)
        self._current_state = r

    def state_changed(self, value):
        ''''''
        v = OPTION_CODE.key_value(1)
        print 'state changed to', v
        return v

    def call_state(self, *args, **kw):
        '''
        Call the state driven current method with the
        args and kwargs supplied
        '''

        v = kw.get('state', None)
        f = self.resolve_call_state_method(v)
        r = None

        if callable(f):
            r = f(*args, **kw)
        else:
            print 'No call state function'
        return r

    def resolve_call_state_method(self, state=None):
        a = self.get_call_state_method_name(state)
        if a is not None:
            a = getattr(self, a)
        return a

    def get_call_state_method_name(self, state=None):
        '''
        Return the call state method name, if a state method matching
        the state exists wthin OPTION_CODE

        If no state is given, self.current_state is used. If a method
        for the function exists within self.states map, the name of the
        function is returned.
        '''
        c = state or self.current_state
        name = self.state_method_name(c)

        print 'checking state', name

        a = getattr(self, name, None)
        return name if a is not None else None

    def state_method_name(self, state=None):
        '''
        create and return a string for the method name of the
        state. If no state is given, self.current_state is used.
        '''
        c = state or self.current_state
        return '{0}_state'.format(c.lower())

    current_state = property(get_current_state, set_current_state)


class CloseStateMixin(object):

    def close_state(self, data):
        print 'close_state', data

        status = 1000
        reason = u''
        length = len(data)

        if length == 0:
            pass
        elif length >= 2:
            status = struct.unpack_from('!H', data[:2])[0]
            reason = data[2:]

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



class StateManager(object):

    state_class = None
    caller = None
    caller_format = "{0}_state"

    def __init__(self, state=None, caller_format=None, *args, **kwargs):
        self.init_args = args
        self.init_kw = kwargs
        self.caller_format = caller_format or self.caller_format
        self.state_class = kwargs.get('state_class', self.state_class)
        self.caller = kwargs.get('caller', self.caller)
        self._caller = partial(self.caller, self)
        self.set_state(state)
        # super(cls, self).__init__(*args, **kwargs)

    def call(self, *args, **kw):
        # print "Call StateManager", args
        self._caller(*args, **kw)

    def set_state(self, state):
        '''
        Given a state value set the state for the next call to the
        StateManger.call
        '''


        # v = States.key_value(self.state_class, state)
        v = self.state_class.key_value(state)
        print 'set_state', v
        self._state = v


class SocketStates(StateHandler):

    def headerb1_state(self, byte):

        self.fin = byte & 0x80
        self.opcode = byte & 0x0F
        self._opcode_manager.set_state(byte & 0x0F)
        self.state = STATE.HEADERB2
        self._state_manager.set_state(STATE.HEADERB2)
        self.index = 0
        self.length = 0
        self.lengtharray = bytearray()
        self.data = bytearray()

        rsv = byte & 0x70
        if rsv != 0:
            self.handleError('RSV bit must be 0')

    def headerb2_state(self, byte):
        print '!! headerb2_state - Header call state', byte

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
                self._state_manager.set_state(STATE.MASK)
            else:
                # if there is no mask and no payload we are done
                if self.length <= 0:
                    try:
                        self._handlePacket()
                    finally:
                        self.state = STATE.HEADERB1
                        self._state_manager.set_state(STATE.HEADERB1)

                        self.data = bytearray()

                # we have no mask and some payload
                else:
                    #self.index = 0
                    self.data = bytearray()
                    self.state = STATE.PAYLOAD
                    self._state_manager.set_state(STATE.PAYLOAD)
                    self._state_manager.set_state(STATE.PAYLOAD)

        elif length == 126:
            self.lengtharray = bytearray()
            self.state = STATE.LENGTHSHORT
            self._state_manager.set_state(STATE.LENGTHSHORT)
            self._state_manager.set_state(STATE.LENGTHSHORT)

        elif length == 127:
            self.lengtharray = bytearray()
            self.state = STATE.LENGTHLONG
            self._state_manager.set_state(STATE.LENGTHLONG)
            self._state_manager.set_state(STATE.LENGTHLONG)

    def lengthshort_state(self, byte):
        self.lengtharray.append(byte)

        if len(self.lengtharray) > 2:
            self.handleError('short length exceeded allowable size')

        if len(self.lengtharray) == 2:
            self.length = struct.unpack_from('!H', self.lengtharray)[0]

            if self.hasmask is True:
                self.maskarray = bytearray()
                self.state = STATE.MASK
                self._state_manager.set_state(STATE.MASK)
            else:
                # if there is no mask and no payload we are done
                if self.length <= 0:
                    try:
                        self._handlePacket()
                    finally:
                        self.state = STATE.HEADERB1
                        self._state_manager.set_state(STATE.HEADERB1)
                        self.data = bytearray()

                # we have no mask and some payload
                else:
                    #self.index = 0
                    self.data = bytearray()
                    self.state = STATE.PAYLOAD
                    self._state_manager.set_state(STATE.PAYLOAD)

    def lengthlong_state(self, byte):
        self.lengtharray.append(byte)

        if len(self.lengtharray) > 8:
            self.handleError('long length exceeded allowable size')

        if len(self.lengtharray) == 8:
            self.length = struct.unpack_from('!Q', self.lengtharray)[0]

            if self.hasmask is True:
                self.maskarray = bytearray()
                self.state = STATE.MASK
                self._state_manager.set_state(STATE.MASK)
            else:
                # if there is no mask and no payload we are done
                if self.length <= 0:
                    try:
                        self._handlePacket()
                    finally:
                        self.state = STATE.HEADERB1
                        self._state_manager.set_state(STATE.HEADERB1)
                        self.data = bytearray()

                # we have no mask and some payload
                else:
                    #self.index = 0
                    self.data = bytearray()
                    self.state = STATE.PAYLOAD
                    self._state_manager.set_state(STATE.PAYLOAD)

    def mask_state(self, byte):
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
                    self._state_manager.set_state(STATE.HEADERB1)
                    self.data = bytearray()

            # we have no mask and some payload
            else:
                #self.index = 0
                self.data = bytearray()
                self.state = STATE.PAYLOAD
                self._state_manager.set_state(STATE.PAYLOAD)

    def payload_state(self, byte):
        if self.hasmask is True:
            self.data.append(byte ^ self.maskarray[self.index % 4])
        else:
            self.data.append(byte)

        # if length exceeds allowable size then we except and remove the
        # connection
        if len(self.data) >= MAXPAYLOAD:
            self.handleError('payload exceeded allowable size')

        # check if we have processed length bytes; if so we are done
        if (self.index+1) == self.length:
            try:
                self._handlePacket()
            finally:
                #self.index = 0
                self.state = STATE.HEADERB1
                self._state_manager.set_state(STATE.HEADERB1)
                self.data = bytearray()
        else:
            self.index += 1


class OpcodeStates(StateHandler):

    def text_opcode(self, data):
        print 'TEXT:', data


from functools import partial


class SocketClient(BufferMixin, WebsocketBinaryPayloadMixin, ServerIntegrationMixin, SocketStates, OpcodeStates, CloseStateMixin):
    '''
    A client for the Connections
    '''

    states = {x: '{0}_state'.format(x.lower()) for x in OPTION_CODE.keys()}

    def __init__(self):#, sock, address):
        self.address = None
        self.headerbuffer = bytearray()
        self.buffer_queue = deque()
        self.connected = False
        self.closed = False
        self.state = STATE.HEADERB1
        self.frag_start = False
        self.frag_type = OPTION_CODE.BINARY
        self.frag_buffer = None
        self.frag_decoder = codecs.getincrementaldecoder('utf-8')(errors='strict')

        _state_caller = self.default_caller
        _opcode_caller = self.default_caller

        self._state_manager = StateManager(STATE.HEADERB1,
                                           state_class=STATE,
                                           caller=_state_caller,
                                           caller_format='{0}_state'
                                           )

        self._opcode_manager = StateManager(state_class=OPTION_CODE,
                                           caller=_opcode_caller,
                                           caller_format='{0}_opcode'
                                           )

    def default_caller(self, manager, *args, **kw):
        name = manager.caller_format.format(manager._state.lower())
        # headerb2_state
        print 'caller', manager,name
        f = getattr(self, name, None)

        v = None
        if f is not None:
            v = f(*args, **kw)
        return v

    def _handleData(self):
        if self.connected is False:
            self.handshake()
        else:
            data = self.socket.recv(CHUNK)
            if not data:
                self.handleError("remote socket closed")

            for d in data:
                self._handle_byte(d if VER >= 3 else ord(d))

    def handleError(self, msg, exc=None, client=None):
        print 'Error:', msg, exc, client

    def _handle_byte(self, byte):
        return self._state_manager.call(byte)

    def _handlePacket(self):

        name = OPTION_CODE.key_value(self.opcode)
        print 'opcode state', name
        self._opcode_manager.call(self.data)

        if self.opcode == OPTION_CODE.CLOSE:
            pass
        elif self.opcode == OPTION_CODE.STREAM:
            pass
        elif self.opcode == OPTION_CODE.TEXT:
            print 'OLD:', self.data
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

    def sendMessage(self, data):
        """
            Send websocket data frame to the client.

            If data is a unicode object then the frame is sent as Text.
            If the data is a bytearray object then the frame is sent as Binary.
        """
        self._sendMessage(False, None, data)

    def _sendMessage(self, fin, opcode, data):
        op_payload = self._create_payload(data, opcode, fin)
        self.buffer_queue.append(op_payload)

    def _create_payload(self, data, opcode=None, fin=False):
        '''
        https://tools.ietf.org/html/rfc6455#page-28
        '''
        payload = self.create_websocket_payload(data, opcode, fin)

        if opcode is None:
            opcode = OPTION_CODE.BINARY
            if _check_unicode(data):
                opcode = OPTION_CODE.TEXT

        return opcode, payload

    def __unicode__(self):
        return 'Client: %s' % self.address

    def __repr__(self):
        s = u'<SocketClient "%s">' % (self.address, )
        return s
