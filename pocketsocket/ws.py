'''
    https://developer.mozilla.org
    /en-US/docs/Web/API/WebSockets_API/Writing_WebSocket_servers
    #Decoding_Payload_Length

'''
import struct

from pocketsocket.client import SocketClient
from pocketsocket.server import Server
from pocketsocket.states import States, StateHandler, StateManager, OPTION_CODE, STATE, _VALID_STATUS_CODES
from pocketsocket.utils import _check_unicode
from pocketsocket.settings import auto_discover
from pocketsocket.logger import log

MAXPAYLOAD = 33554432


def main():
    settings = None
    server = WebsocketServer(settings=settings)
    server.start()


def main_2():
    server = Server(client_class=Client, settings={'settings': './settings.json'})
    server.start()


class WebsocketBinaryPayloadMixin(object):

    def handle_payload(self):

        opcode = self._opcode_manager.get_state()
        # Fin state is set by HEADERB1 state change.
        if self.fin == 0:
            if opcode != OPTION_CODE.STREAM:
                # Not currently receiving a constant stream
                if opcode in [OPTION_CODE.PING, OPTION_CODE.PONG]:
                    self.handleError('control messages can not be fragmented')

                # Data type TEXT, BINARY
                self.frag_type = opcode
                self.frag_start = True
                self.frag_decoder.reset()

                if self.frag_type == OPTION_CODE.TEXT:
                    self.frag_buffer = []
                    self.append_decode_text(self.data)
                else:
                    self.frag_buffer = bytearray()
                    self.frag_buffer.extend(self.data)

            else:
                self.frag_error_if(False)

                if self.frag_type == OPTION_CODE.TEXT:
                    self.append_decode_text(self.data)
                else:
                    self.frag_buffer.extend(self.data)

        else:
            if opcode == OPTION_CODE.STREAM:
                self.frag_error_if(False)

                if self.frag_type == OPTION_CODE.TEXT:
                    self.append_decode_text(self.data)
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
                self.frag_error_if(True)

                if opcode == OPTION_CODE.TEXT:
                    try:
                        self.data = self.data.decode('utf8', errors='strict')
                    except Exception as exp:
                        self.handleError('invalid utf-8 payload', exp)

    def encode_payload_data(self, data, opcode=None, fin=False):
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


class SocketStates(StateHandler):

    def reset_data_pointers(self, state=None):
        ''' re-initialize all the init variables, dropping data
        packets and fragements'''
        self.index = 0
        self.length = 0
        self.lengtharray = bytearray()
        self.reset_data_state(state)

    def reset_data_state(self, state=None):
        self.data = bytearray()
        self._state_manager.set_state(state or STATE.HEADERB1)

    def set_mask_state(self):
        '''Reset the maskarray and set as MASK'''
        self.maskarray = bytearray()
        self._state_manager.set_state(STATE.MASK)

    def headerb1_state(self, byte):
        self.reset_data_pointers(STATE.HEADERB2)
        self.fin = byte & 0x80
        # self.opcode = byte & 0x0F
        self._opcode_manager.set_state(byte & 0x0F)

        rsv = byte & 0x70
        if rsv != 0:
            self.handleError('RSV bit must be 0')

    def process_or_step(self):
        ''' Process the data if the packet is complete, else
        change the header state to PAYLOAD and containue (wait for the
        next incoming packet '''
        # if there is no mask and no payload we are done
        if self.length <= 0:
            r = self.process_payload_packet()
        # we have no mask and some payload
        else:
            r = self.reset_data_state(STATE.PAYLOAD)
        return r

    def headerb2_state(self, byte):
        mask = byte & 0x80
        length = byte & 0x7F
        opcode = self._opcode_manager.get_state()

        if length > 125 and opcode == OPTION_CODE.PING:
            self.handleError('ping packet is too large')

        self.hasmask = True if mask == 128 else False

        if length <= 125:
            self.length = length
            self.mask_process_step()
        else:
            hm = {
                126: STATE.LENGTHSHORT,
                127: STATE.LENGTHLONG,
                }
            self.lengtharray = bytearray()
            self._state_manager.set_state(hm[length])

    def lengthshort_state(self, byte):
        self.lengtharray.append(byte)

        if len(self.lengtharray) > 2:
            self.handleError('short length exceeded allowable size')

        if len(self.lengtharray) == 2:
            self.length = struct.unpack_from('!H', self.lengtharray)[0]
            self.mask_process_step()

    def mask_process_step(self):
        '''Perform set_mask_state if a mask exists, exist call process_or_step
        '''
        if self.hasmask is True:
            r = self.set_mask_state()
        else:
            r = self.process_or_step()
        return r

    def lengthlong_state(self, byte):
        self.lengtharray.append(byte)

        if len(self.lengtharray) > 8:
            self.handleError('long length exceeded allowable size')

        if len(self.lengtharray) == 8:
            self.length = struct.unpack_from('!Q', self.lengtharray)[0]
            self.mask_process_step()

    def mask_state(self, byte):
        self.maskarray.append(byte)

        if len(self.maskarray) > 4:
            self.handleError('mask exceeded allowable size')

        if len(self.maskarray) == 4:
            self.process_or_step()

    def processed_length(self):
        # check if we have processed length bytes; if so we are done
        return (self.index+1) == self.length

    def payload_state(self, byte):
        '''
            https://developer.mozilla.org
            /en-US/docs/Web/API/WebSockets_API/Writing_WebSocket_servers
            #Reading_and_Unmasking_the_Data
        '''
        d = byte
        if self.hasmask is True:
            d = byte ^ self.maskarray[self.index % 4]
        self.data.append(d)

        if len(self.data) >= MAXPAYLOAD:
            self.handleError('payload exceeded allowable size')

        if self.processed_length():
            self.process_payload_packet()
        else:
            self.index += 1


class OpcodeStates(StateHandler):

    def text_opcode(self, data):
        pass

    def close_opcode(self, data):
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

    def pong_opcode(self, data):
        '''
        Pong send nothing, but does check data size
        '''
        if len(data) > 125:
            self.handleError('control frame length can not be > 125')

    def ping_opcode(self, data):
        ''' Ping send pong '''
        self.pong_opcode(data)
        self._sendMessage(False, OPTION_CODE.PONG, data)

    def binary_opcode(self, data):
        pass


class Client(WebsocketBinaryPayloadMixin,
             SocketStates,
             OpcodeStates,
             SocketClient
             ):

    def __init__(self, *a, **kw):
        self.init(*a, **kw)
        super(Client, self).__init__(*a, **kw)
        self.ready(*a, **kw)

    def init(self, *args, **kw):
        pass

    def ready(self, *args, **kw):
        print( 'Ready Client')

    def accept(self, socket, server):
        self.server = server
        return super(Client, self).accept(socket, server)

    def send_all(self, *args, **kw):
        return self.server.send_all(*args, **kw)

    def binary_opcode(self, data):
        self.recv_binary(data)
        self.recv(data, type=OPTION_CODE.BINARY)

    def text_opcode(self, data):
        self.recv_text(data)
        self.recv(data, opcode=OPTION_CODE.TEXT)

    def send(self, data, opcode=None):
        log('<', data)
        return self.sendMessage(data, opcode)

    def recv(self, data, opcode):
        log('>', data)
        self.send('Thank you.', opcode)

    def recv_text(self, data):
        pass

    def recv_binary(self, data):
        pass

    def __repr__(self):
        if self.connected:
            v = self.address
        else:
            if hasattr(self, 'socket') and self.socket is not None:
                v = self.getsockname()
            else:
                if self.closed:
                    v = 'CLOSED'
                else:
                    v = 'UNCONNECTED'
        n = self.__class__.__name__
        return "<ws.{}: {}>".format(n, v)


class WebsocketServer(Server):
    ''' Basic instance of a server, instansiating ws.Client for
    socket clients '''

    # hosts = (9002,)
    port = 9002
    client_class = Client


if __name__ == '__main__':
    main()
