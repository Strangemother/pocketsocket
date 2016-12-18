from mixins import SocketCreateMixin, ConnectionIteratorMixin
from client import OPTION_CODE, SocketClient, Listener


def main():
    server = Server()
    server.setup('127.0.0.1', 8009)
    server.loop()


class Server(SocketCreateMixin, ConnectionIteratorMixin):
    '''
    Open a server socket, bind and listen for connection
    The server handles the Service, Client and Config
    '''
    client_class = SocketClient
    socket_class = Listener

    def __init__(self, *args, **kw):
        if len(args) > 0:
            self.setup(*args, **kw)
        # super(cls, self).__init__(*args, **kwargs)

    def setup(self, host, port, *args, **kw):
        self.hosts = (host,)
        self.ports = (port,)
        self.listeners = self.setup_listeners()
        print 'Created listeners', self.listeners

    def loop(self):
        self.loop_forever(self.listeners)

    def start(self, *args, **kw):
        '''
        Perform setup and start
        '''
        if len(args) > 0:
            self.setup(*args)
        self.loop()


if __name__ == '__main__':
    main()
