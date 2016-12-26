from ws import Client
from client import ClientListMixin
from server import Server
from logger import log


def main_echo():
    server = EchoServer()
    server.start()


class EchoClient(Client):
    def recv(self, data, opcode):
        log('>', self, opcode, data)
        self.send_all(data, opcode, ignore=[self])

    def send(self, data, opcode=None):
        log('<', self, opcode, data)
        return self.sendMessage(data, opcode)

class EchoServer(ClientListMixin, Server):
    ''' Basic instance of a server, instansiating ws.Client for
    socket clients '''
    client_class = EchoClient


if __name__ == '__main__':
    main_echo()
