from collections import deque
import codecs

import socket
from functools import partial
import errno

from pocketsocket.states import States, StateHandler, StateManager, OPTION_CODE, STATE, _VALID_STATUS_CODES
from pocketsocket.mixins import ServerIntegrationMixin, BufferMixin
from pocketsocket.utils import _check_unicode, VER, _is_text
from pocketsocket.logger import log, loge


def client(address=None, **kw):
    '''
    Simple client generation using websocket-client
    '''
    import websocket

    ws = websocket.WebSocket()
    if address is not None:
        ws.connect(address, **kw)
    return ws


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


class PayloadMixin(object):
    '''Data manager handling tools
    '''
    def handle_payload(self):
        if len(self.data) > 0:
            log('Data', self.data)

    def create_payload(self, data, opcode=None, fin=False):
        '''https://tools.ietf.org/html/rfc6455#page-28'''
        # log('PayloadMixin.createPayload')

        if opcode is None:
            opcode = OPTION_CODE.BINARY
            if _is_text(data):
                opcode = OPTION_CODE.TEXT

        payload = self.encode_payload_data(data, opcode, fin)
        return opcode, payload

    def encode_payload_data(self, data, opcode, fin):
        log('encode_payload_data')
        return data


class SocketClient(BufferMixin, PayloadMixin, ServerIntegrationMixin):
    '''
    A client for the Connections
    '''
    def __init__(self):#, sock, address):
        self.address = None
        self.headerbuffer = bytearray()
        self.buffer_queue = deque()
        self.closed = False
        self.state = STATE.HEADERB1
        self.frag_start = False
        self.frag_type = OPTION_CODE.BINARY
        self.frag_buffer = []
        self.frag_decoder = codecs.getincrementaldecoder('utf-8')(errors='strict')

        self._state_manager = StateManager(STATE.HEADERB1,
                                           state_class=STATE,
                                           caller=self.default_manager_caller,
                                           caller_format='{0}_state'
                                           )

        self._opcode_manager = StateManager(state_class=OPTION_CODE,
                                           caller=self.default_manager_caller,
                                           caller_format='{0}_opcode'
                                           )

    def default_manager_caller(self, manager, *args, **kw):
        '''Call the manager current state function on `self` if the method exists
        If the state method does not exist on `self` None is returned, else the
        value from the function call is returned.
        '''
        # Format the manager string to produce a method for self
        name = manager.caller_format.format(manager._state.lower())
        f = getattr(self, name, None)
        v = None
        if f is not None:
            v = f(*args, **kw)
        return v

    def handle_byte_chunk(self, data, size=None, socket=None):
        '''
        Handle a data chunk from the socket.recv(CHUNK).
        Returns nothing

        The function is called by the server during client loop iteration
        The `handle_byte_chunk` is given the received packet from
        the client using BufferMixin.read(CHUNK) and iterates each byte into
        _handle_byte.
        '''
        for d in data:
            self._handle_byte(d if VER >= 3 else ord(d))

    def _handle_byte(self, byte):
        '''Call the internal _state_manager with the given byte'''
        return self._state_manager.call(byte)

    def _handlePacket(self):
        '''
        Called during server iteration BufferMixin.process_payload_packet()
        if a packet has been received
        Returns nothing.
        '''
        called = self._opcode_manager.call(self.data)
        if called is False:
            self.handleError('unknown opcode')

        self.handle_payload()

    def frag_error_if(self, b):
        if self.frag_start is b:
            self.handleError('fragmentation protocol error')

    def handleError(self, msg, exc=None, client=None):
        loge('Error:', msg, exc, client)

    def append_decode_text(self, data, final=True):
        # utf_str = self.frag_decoder.decode(data, final=final)
        utf_str = self.decode_text_fragment(data, final=final)
        if utf_str:
            self.frag_buffer.append(utf_str)
        return utf_str

    def decode_text_fragment(self, data, final=True):
        return self.frag_decoder.decode(data, final=final)

    def sendMessage(self, data, opcode=None):
        """Send websocket data frame to the client.

            If data is a unicode object then the frame is sent as Text.
            If the data is a bytearray object then the frame is sent as Binary.
        """
        op, data = self.create_payload(data, opcode)
        self._sendMessage(False, op, data)

    def _sendMessage(self, fin, opcode, data):
        op_payload = (opcode, data, )
        # log('Adding to buffer queue', opcode)
        self.buffer_queue.append(op_payload)

    def __unicode__(self):
        return 'Client: %s' % self.address

    def __repr__(self):
        s = u'<SocketClient "%s">' % (self.address, )
        return s


class ClientListMixin(object):
    '''Maintain a dictionary of connected clients for cross communication.
    applies the `send_all` method.
    '''
    def setup(self, *args, **kw):
        self.clients = {'hosts': {}, 'ports': {}}
        super(ClientListMixin, self).setup(*args, **kw)

    def client_close(self, client, listeners, connections):

        if isinstance(client, long):
            v = connections.get(client, None)
            if v is None:
                log('DETECT FAIL', client)
                # Ignore and return at this point,
                # the closing client is not in the connections
                return True
            else:
                client = v

        if hasattr(client, 'socket'):
            self.close(client.socket)

        h_h = None
        h_p = None

        try:
            h_h, h_p = client.socket.getsockname()
        except socket.error as e:
            if e.errno in [errno.EBADF]:
                if hasattr(client, 'closed'):
                    if client.closed is True:
                        h_h, _ = client.address
                    else:
                        client.close(OPTION_CODE.CLOSE, str(e.errno))
                        h_h, _ = client.address
                else:
                    import pdb; pdb.set_trace()  # breakpoint 878bd391 //
                    raise e
            else:
                raise e
        v = super(ClientListMixin, self).client_close(client, listeners, connections)

        if v is True:
            if h_h is not None:
                self.clients['hosts'][h_h].remove(client)
            else:
                for name, clients in self.clients['hosts'].items():
                    if client in clients:
                        self.clients['hosts'][name].remove(client)

            if h_p is not None:
                self.clients['ports'][h_p].remove(client)
            else:
                # backup routine as we've lost reference
                # to the original port
                for name, clients in self.clients['ports'].items():
                    if client in clients:
                        self.clients['ports'][name].remove(client)

        return v

    def accept_socket(self, sock, listeners, connections):
        v = super(ClientListMixin, self).accept_socket(sock, listeners, connections)
        host, port = sock.getsockname()

        self.clients['ports'][port].append(v)
        self.clients['hosts'][host].append(v)
        return v

    def socket_bind(self, host='127.0.0.1', port=None, socket_class=None, **kw):
        if self.clients['ports'].get(port, None) is None:
            self.clients['ports'][port] = []

        if self.clients['hosts'].get(host, None) is None:
            self.clients['hosts'][host] = []

        return super(ClientListMixin, self).socket_bind(host, port, socket_class, **kw)

    def send_all(self, data, opcode=None, ignore=None):
        if ignore is None:
            ignore = []

        for client in self.clients_iter(ignore):
                client.send(data, opcode)

    def get_clients(self, ignore=None):
        return list(self.clients_iter(ignore))

    def clients_iter(self, ignore=None):
        ignore = ignore or []
        for host in self.clients['hosts']:
            for client in self.clients['hosts'][host]:
                if client in ignore:
                    continue
                yield client
