from ws import Client
from client import ClientListMixin
from server import Server
from logger import log


def main():
    server = EchoServer(client_class=LogClient)
    server.start()


class LogClient(Client):

    def setup(self, *args, **kw):
        s = 'Setup of new client: {}'.format(self)
        log(s)
        super(LogClient, self).setup(*args, **kw)

    def accept(self, socket, server):
        self.server = server
        v = super(Client, self).accept(socket, server)
        s = 'New Client: {} for {}'.format(self, server)
        log(s)
        self.send_all(s, ignore=[self])
        return v

    def recv(self, data, opcode):
        s = 'Got message from: {}'.format(self)
        self.send('Thanks.')
        self.send_all(s, ignore=[self])

    def recv_text(self, data):
        log('Recevied text:', data)

    def recv_binary(self, data):
        log('Recevied binary: Len:', len(data))

    def send(self, data, opcode=None):
        log('Send:', data)
        return self.sendMessage(data, opcode)

    def close(self, status, reason):
        s = 'Client close: {}'.format(self)
        log(s)
        self.send_all(s, ignore=[self])
        super(LogClient, self).close(status, reason)


class EchoServer(ClientListMixin, Server):
    pass


if __name__ == '__main__':
    main()
