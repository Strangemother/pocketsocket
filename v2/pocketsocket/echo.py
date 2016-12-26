from ws import Client
from server import Server
from logger import log


def main_echo():
    server = EchoServer()
    server.start()


class EchoClient(Client):
    def recv(self, data, opcode):
        log('>', opcode, data)
        self.send_all(data, opcode)


class EchoServer(Server):
    ''' Basic instance of a server, instansiating ws.Client for
    socket clients '''
    client_class = EchoClient

    def __init__(self, *args, **kw):

        self.clients = {'hosts': {}, 'ports': {}}
        super(EchoServer, self).__init__(*args, **kw)

    def client_close(self, client, listeners, connections):
        h_h, h_p = client.socket.getsockname()
        v = super(EchoServer, self).client_close(client, listeners, connections)
        if v is True:
            self.clients['hosts'][h_h].remove(client)
            self.clients['ports'][h_p].remove(client)
        return v

    def accept_socket(self, sock, listeners, connections):
        v = super(EchoServer, self).accept_socket(sock, listeners, connections)
        print 'Accepting socket'
        host, port = sock.getsockname()

        self.clients['ports'][port].append(v)
        self.clients['hosts'][host].append(v)
        return v

    def socket_bind(self, host='127.0.0.1', port=None, socket_class=None, **kw):
        if self.clients['ports'].get(port, None) is None:
            self.clients['ports'][port] = []

        if self.clients['hosts'].get(host, None) is None:
            self.clients['hosts'][host] = []

        return super(EchoServer, self).socket_bind(host, port, socket_class, **kw)

    def send_all(self, data, opcode=None):
        for host in self.clients['hosts']:
            for client in self.clients['hosts'][host]:
                print 'sending to client', client
                client.send(data, opcode)


if __name__ == '__main__':
    main_echo()
