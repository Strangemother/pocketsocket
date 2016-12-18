from collections import deque
import codecs

import socket
from functools import partial
import errno

from states import States, StateHandler, StateManager, OPTION_CODE, STATE, _VALID_STATUS_CODES
from mixins import ServerIntegrationMixin, BufferMixin
from utils import _check_unicode, VER


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


class SocketClient(BufferMixin, ServerIntegrationMixin):
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
        self.frag_buffer = None
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
        name = manager.caller_format.format(manager._state.lower())
        # headerb2_state
        f = getattr(self, name, None)

        v = None
        if f is not None:
            v = f(*args, **kw)
        return v

    def handleError(self, msg, exc=None, client=None):
        print 'Error:', msg, exc, client

    def handle_byte_chunk(self, data, size=None, socket=None):
        for d in data:
            self._handle_byte(d if VER >= 3 else ord(d))

    def _handle_byte(self, byte):
        return self._state_manager.call(byte)

    def _handlePacket(self):

        called = self._opcode_manager.call(self.data)
        opcode = self._opcode_manager.get_state()
        if called is False:
            self.handleError('unknown opcode')

        if self.fin == 0:
            if opcode != OPTION_CODE.STREAM:
                if opcode in [OPTION_CODE.PING, OPTION_CODE.PONG]:
                    self.handleError('control messages can not be fragmented')

                self.frag_type = opcode
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
            if opcode == OPTION_CODE.STREAM:
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

            else:
                if self.frag_start is True:
                    self.handleError('fragmentation protocol error')

                if opcode == OPTION_CODE.TEXT:
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
        op_payload = (opcode, data, )
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
