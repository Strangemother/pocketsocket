
from mixins import SocketCreateMixin, ConnectionIteratorMixin
from client import OPTION_CODE, SocketClient, Listener
from settings import auto_discover


def main():
    server = Server()
    server.setup('127.0.0.1', 8009)
    server.loop()


class SettingsMixin(object):
    '''
    Provide settings from config points.
    '''
    def configure(self, *args, **kw):
        '''
        Configure the server

        Inline ip and port are most important.

            configure('127.0.0.1', port=8001, host='', port=-1)
        '''

        host = kw.get('host', None)
        port = kw.get('port', None)

        if len(args) == 2:
            host, port = args
        elif len(args) == 1:
            port = args[0]

        v = auto_discover(host=host, port=port, **kw)
        return v

    def inherit_attributes(self, keys):
        hp = {x: self.settings.get(x, None) for x in keys}
        for x in hp:
            setattr(self, x, hp[x])


class Server(SocketCreateMixin, SettingsMixin, ConnectionIteratorMixin):
    '''
    Open a server socket, bind and listen for connection
    The server handles the Service, Client and Config
    '''
    client_class = SocketClient
    socket_class = Listener

    def __init__(self, *args, **kw):
        self._init_settings = kw
        self.listeners = []
        self.settings = None
        # super(cls, self).__init__(*args, **kwargs)

    def setup(self, **kw):
        self.settings = self.configure(**kw)
        # Copy back required native arguments for ease.
        keys = ['hosts', 'ports']
        self.inherit_attributes(keys)
        # After configure
        self.listeners = self.setup_listeners(**self.settings)

    def loop(self):
        self.loop_forever(self.listeners)

    def start(self, *args, **kw):
        ''' Perform setup and start '''
        if self.settings is None:
            self.setup(**kw)
        self.loop()


if __name__ == '__main__':
    main()
