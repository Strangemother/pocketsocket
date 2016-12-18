import struct


from client import SocketClient
from server import Server
from states import States, StateHandler, StateManager, OPTION_CODE, STATE, _VALID_STATUS_CODES
from utils import _check_unicode


MAXPAYLOAD = 33554432


def main():
    server = WebsocketServer()
    server.start('127.0.0.1', 8009)


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

        elif length == 126:
            self.lengtharray = bytearray()
            self.state = STATE.LENGTHSHORT
            self._state_manager.set_state(STATE.LENGTHSHORT)

        elif length == 127:
            self.lengtharray = bytearray()
            self.state = STATE.LENGTHLONG
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
        '''
        Ping send pong
        '''
        self.pong_opcode(data)
        self._sendMessage(False, OPTION_CODE.PONG, data)

    def binary_opcode(self, data):
        print 'binary_opcode'


class WebsocketClient(SocketClient,
    SocketStates,
    OpcodeStates,
    WebsocketBinaryPayloadMixin):
    pass


class WebsocketServer(Server):
    client_class = WebsocketClient

if __name__ == '__main__':
    main()
