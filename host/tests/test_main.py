import unittest
from main import EchoClient
import main
from mock import Mock


class TestEchoClient(unittest.TestCase):

    def test_broadcast(self):
        '''Ensure the broadcase can ignore self.
        '''
        main.clients = {
            "one": Mock(),
            "two": Mock(),
        }

        cl = EchoClient(Mock())
        cl.send = Mock()
        cl.broadcast('data', ignore=[cl])
        self.assertFalse(cl.send.called)

        for client in main.clients:
            self.assertTrue(main.clients[client].send.called)

        main.clients = {}

    def test_opened(self):
        cl = EchoClient(Mock())

        old_clients = main.get_clients()
        cl.opened()
        clients = main.get_clients()

        self.assertTrue(id(cl) in clients)

    def test_closed(self):
        cl = EchoClient(Mock())

        cl.opened()
        clients = main.get_clients()
        self.assertTrue(id(cl) in clients)

        cl.closed(0)

        clients = main.get_clients()
        self.assertFalse(id(cl) in clients)
