import unittest
import socket
from server import Listener, SocketCreateMixin


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


class TestSocketCreateMixin(unittest.TestCase):

    def test_bind_pairs(self):
        # socket_create_mixin = SocketCreateMixin()
        # self.assertEqual(expected, socket_create_mixin.bind_pairs(hosts, ports))
        expects = (
                ('127.0.0.1', 9100),
                ('127.0.0.1', 9101),
            )

        # Pair each listener as tuple(ip, port)
        pairs = tuple( (x, y, ) for x, y in zip(*expects))

        s = SocketCreateMixin()
        p = s.bind_pairs(*pairs)

        self.assertEqual(len(p), 2)
        for l in p:
            # check the socket is one of the tuples
            sock = l._sock.getsockname()
            self.assertIn(sock, expects)
            self.assertIsInstance(l, Listener)

    def test_create_socket(self):

        host, port = '127.0.0.1', 9100
        s = SocketCreateMixin()
        l, h, p = s.create_socket(host, port)
        self.assertEqual(h, host)
        self.assertEqual(p, port)
        s_host, s_port = l._sock.getsockname()
        self.assertEqual(host, s_host)
        self.assertEqual(port, s_port)


'''

    def test_setup_listeners(self):
        # socket_create_mixin = SocketCreateMixin()
        # self.assertEqual(expected, socket_create_mixin.setup_listeners(host, port))
        assert False # TODO: implement your test here

    def test_socket_bind(self):
        # socket_create_mixin = SocketCreateMixin()
        # self.assertEqual(expected, socket_create_mixin.socket_bind(host, port, socket_class))
        assert False # TODO: implement your test here

class TestConnectionIteratorMixin(unittest.TestCase):
    def test_accept_socket(self):
        # connection_iterator_mixin = ConnectionIteratorMixin()
        # self.assertEqual(expected, connection_iterator_mixin.accept_socket(sock, listeners, connections))
        assert False # TODO: implement your test here

    def test_add_socket(self):
        # connection_iterator_mixin = ConnectionIteratorMixin()
        # self.assertEqual(expected, connection_iterator_mixin.add_socket(sock, listeners, connections))
        assert False # TODO: implement your test here

    def test_client_close(self):
        # connection_iterator_mixin = ConnectionIteratorMixin()
        # self.assertEqual(expected, connection_iterator_mixin.client_close(client, listeners, connections))
        assert False # TODO: implement your test here

    def test_close(self):
        # connection_iterator_mixin = ConnectionIteratorMixin()
        # self.assertEqual(expected, connection_iterator_mixin.close(sock))
        assert False # TODO: implement your test here

    def test_create_client(self):
        # connection_iterator_mixin = ConnectionIteratorMixin()
        # self.assertEqual(expected, connection_iterator_mixin.create_client(socket))
        assert False # TODO: implement your test here

    def test_exception_close(self):
        # connection_iterator_mixin = ConnectionIteratorMixin()
        # self.assertEqual(expected, connection_iterator_mixin.exception_close(sock, listeners, connections))
        assert False # TODO: implement your test here

    def test_fail_list(self):
        # connection_iterator_mixin = ConnectionIteratorMixin()
        # self.assertEqual(expected, connection_iterator_mixin.fail_list(xlist, listeners, connections))
        assert False # TODO: implement your test here

    def test_get_client_class(self):
        # connection_iterator_mixin = ConnectionIteratorMixin()
        # self.assertEqual(expected, connection_iterator_mixin.get_client_class())
        assert False # TODO: implement your test here

    def test_is_writable(self):
        # connection_iterator_mixin = ConnectionIteratorMixin()
        # self.assertEqual(expected, connection_iterator_mixin.is_writable(sock))
        assert False # TODO: implement your test here

    def test_loop_forever(self):
        # connection_iterator_mixin = ConnectionIteratorMixin()
        # self.assertEqual(expected, connection_iterator_mixin.loop_forever(listeners))
        assert False # TODO: implement your test here

    def test_raw_socket_match(self):
        # connection_iterator_mixin = ConnectionIteratorMixin()
        # self.assertEqual(expected, connection_iterator_mixin.raw_socket_match(client, listeners, connections))
        assert False # TODO: implement your test here

    def test_read_list(self):
        # connection_iterator_mixin = ConnectionIteratorMixin()
        # self.assertEqual(expected, connection_iterator_mixin.read_list(rlist, listeners, connections))
        assert False # TODO: implement your test here

    def test_select(self):
        # connection_iterator_mixin = ConnectionIteratorMixin()
        # self.assertEqual(expected, connection_iterator_mixin.select(listeners, writers, timeout))
        assert False # TODO: implement your test here

    def test_served(self):
        # connection_iterator_mixin = ConnectionIteratorMixin()
        # self.assertEqual(expected, connection_iterator_mixin.served())
        assert False # TODO: implement your test here

    def test_write_list(self):
        # connection_iterator_mixin = ConnectionIteratorMixin()
        # self.assertEqual(expected, connection_iterator_mixin.write_list(wlist, listeners, connections))
        assert False # TODO: implement your test here

    def test_writers(self):
        # connection_iterator_mixin = ConnectionIteratorMixin()
        # self.assertEqual(expected, connection_iterator_mixin.writers(listeners, connections))
        assert False # TODO: implement your test here


class TestServer(unittest.TestCase):
    def test_loop(self):
        # server = Server()
        # self.assertEqual(expected, server.loop())
        assert False # TODO: implement your test here

    def test_setup(self):
        # server = Server()
        # self.assertEqual(expected, server.setup(host, port))
        assert False # TODO: implement your test here

    def test_start(self):
        # server = Server()
        # self.assertEqual(expected, server.start(*args, **kw))
        assert False # TODO: implement your test here

if __name__ == '__main__':
    unittest.main()

class TestMain(unittest.TestCase):
    def test_main(self):
        # self.assertEqual(expected, main())
        assert False # TODO: implement your test here


'''
