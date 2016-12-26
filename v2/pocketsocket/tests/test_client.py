import unittest
from mock import MagicMock
import socket
from client import Listener, SocketClient, PayloadMixin
from collections import deque
from states import States, StateHandler, StateManager, OPTION_CODE, STATE, _VALID_STATUS_CODES


class TestListener(unittest.TestCase):

    def setUp(self):
        self.socket = None

    def tearDown(self):

        if self.socket is not None:
            self.socket.close()

    def test___repr__(self):
        host = '127.0.0.1'
        port = 9100

        SocketClass = Listener
        s = SocketClass(socket.AF_INET, socket.SOCK_STREAM)
        self.socket = s
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        expected = "<Listener(socket.socket): sock unknown>"
        self.assertEqual(expected, s.__repr__())
        s.bind((host, port))
        expected = "<Listener(socket.socket): sock ('127.0.0.1', 9100)>"
        self.assertEqual(expected, s.__repr__())

class TestPayloadMixin(unittest.TestCase):

    def test_encode_payload_data(self):
        payload_mixin = PayloadMixin()
        expected = 'test string'
        data = 'test string'
        opcode = None
        fin = None
        self.assertEqual(expected, payload_mixin.encode_payload_data(data, opcode, fin))


    def test_handle_payload(self):
        # payload_mixin = PayloadMixin()
        # self.assertEqual(expected, payload_mixin.handle_payload())
        pass

class TestSocketClient(unittest.TestCase):
    def test___init__(self):
        socket_client = SocketClient()
        self.assertIsNone(socket_client.address)
        self.assertIsInstance(socket_client.buffer_queue, deque)
        self.assertIsInstance(socket_client._state_manager, StateManager)
        self.assertIsInstance(socket_client._opcode_manager, StateManager)

    def test___repr__(self):
        socket_client = SocketClient()
        socket_client.address = 'Apples'
        expected = '<SocketClient "Apples">'
        self.assertEqual(expected, socket_client.__repr__())


    def test___unicode__(self):
        socket_client = SocketClient()
        socket_client.address = 'Apples'
        self.assertEqual('Client: Apples', socket_client.__unicode__())

    def test_append_decode_text(self):
        socket_client = SocketClient()
        expected = 'Test'
        self.assertEqual(expected, socket_client.append_decode_text('Test'))
        socket_client.append_decode_text('three')
        socket_client.append_decode_text('blind')
        socket_client.append_decode_text('mice')
        expected = ['Test', 'three', 'blind', 'mice']
        self.assertListEqual(expected, socket_client.frag_buffer)


    def test_decode_text_fragment(self):
        socket_client = SocketClient()
        expected = u'apple"ham#spamDUfUw'
        data = 'apple\x22ham\x23spam\x44\x55\x66\x55\x77'
        self.assertEqual(expected, socket_client.decode_text_fragment(data))

    def test_default_manager_caller(self):
        sc = SocketClient()
        sc.cake_state = MagicMock(return_value='cherry')
        manager = sc._state_manager
        manager._state = 'CAKE'
        v = sc.default_manager_caller(manager, 1, 2, foo='bar')
        sc.cake_state.assert_called_with(1,2, foo='bar')
        self.assertEqual('cherry', v)

    def test_frag_error_if(self):
        sc = SocketClient()
        sc.frag_start
        sc.handleError = MagicMock()
        sc.frag_error_if('foo')
        self.assertFalse(sc.handleError.called)

        sc.frag_error_if(False)
        self.assertEqual(sc.handleError.call_count, 1)

    def test_handleError(self):
        # socket_client = SocketClient()
        # self.assertEqual(expected, socket_client.handleError(msg, exc, client))
        pass

    def test_handle_byte_chunk(self):
        socket_client = SocketClient()
        socket_client._handle_byte = MagicMock()
        data = 'Test String'
        socket_client.handle_byte_chunk(data)
        l = socket_client._handle_byte.call_count
        self.assertEqual(l, len(data))

    def test_sendMessage(self):
        socket_client = SocketClient()
        socket_client._sendMessage = MagicMock()
        data = 'Example string'
        socket_client.sendMessage(data, 'opcode')
        socket_client._sendMessage.assert_called_with(False, 'opcode', data)

class MockSocket(object):

    def getsockname(self):
        return 'HOST', 'PORT'

'''
class TestClientListMixin(unittest.TestCase):
    def test_accept_socket(self):
        client_list_mixin = ClientListMixin()
        a = client_list_mixin.accept_socket(MockSocket(), None, None)
        self.assertEqual(expected, a)
    def test_client_close(self):
        # client_list_mixin = ClientListMixin()
        # self.assertEqual(expected, client_list_mixin.client_close(client, listeners, connections))
        assert False # TODO: implement your test here

    def test_send_all(self):
        # client_list_mixin = ClientListMixin()
        # self.assertEqual(expected, client_list_mixin.send_all(data, opcode, ignore))
        assert False # TODO: implement your test here

    def test_setup(self):
        # client_list_mixin = ClientListMixin()
        # self.assertEqual(expected, client_list_mixin.setup(*args, **kw))
        assert False # TODO: implement your test here

    def test_socket_bind(self):
        # client_list_mixin = ClientListMixin()
        # self.assertEqual(expected, client_list_mixin.socket_bind(host, port, socket_class, **kw))
        assert False # TODO: implement your test here
'''
if __name__ == '__main__':
    unittest.main()
