import unittest
import socket
import sys

from server import Listener, SocketCreateMixin
import ws

# For testing
from smpq import ProcessQueue
# websocket-client lib
from websocket import create_connection
import multiprocessing


server_result = None
VER = sys.version_info[0]


def byte_str(string):
    r = bytearray(mdict if VER >= 3 else ord(mdict) for mdict in string)
    return r


class TestClient(ws.WebsocketClient):

    def accept(self, sock):
        v = super(TestClient, self).accept(sock)
        self.sendMessage('Howdy')
        return v

    def text_opcode(self, data):
        super(TestClient, self).text_opcode(data)
        addr = self.socket.getpeername()
        self.mdict[addr[1]] = data


class TestServer(ws.WebsocketServer):
    client_class = TestClient

    def create_client(self, sock):
        v = super(TestServer, self).create_client(sock)
        v[1].mdict = self.mdict
        return v


def start_server(v):
    addr, mdict = v
    s = TestServer(*addr)
    s.mdict = mdict
    s.start()


class TestWebsockets(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def open_server(self):
        '''
        Open a server, returning

        tuple( address<tuple>,
               dict<Manager>,
               client<SocketClient>
               queue<ProcessQueue>
               )

        '''
        address = ('127.0.0.1', 9101, )
        url = 'ws://{0}:{1}'.format(*address)
        pq = ProcessQueue(start_server)

        mgr = multiprocessing.Manager()
        mdict = mgr.dict()

        pq.start([(address, mdict,)])
        client = create_connection(url)
        return address, mdict, client, pq

    def close_server(self, client, pq):
        client.close()
        pq.stop()

    def test_server_start(self):
        ''' Can open a server and process a message '''

        address, mdict, client, pd = self.open_server()
        addr = client.sock.getsockname()

        s = "My old man's a milkman"
        client.send(s)

        self.close_server(client, pd)

        # Check port in readouts
        v = mdict.get(addr[1], None)
        self.assertIsNotNone(v)

        # Create comparison string
        r = byte_str(s)
        self.assertEqual(r, v)
