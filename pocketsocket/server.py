
from pocketsocket.mixins import SocketCreateMixin, ConnectionIteratorMixin
from pocketsocket.client import OPTION_CODE, SocketClient, Listener
from pocketsocket.settings import auto_discover, SettingsMixin


def main():
    server = Server()
    server.setup('127.0.0.1', 8009)
    server.loop()


class Server(SocketCreateMixin, SettingsMixin, ConnectionIteratorMixin):
    '''
    Open a server socket, bind and listen for connection
    The server handles the Service, Client and Config
    '''
    client_class = SocketClient
    socket_class = Listener

    def __init__(self, *args, **kw):
        self._init_kw = kw
        self._init_settings = kw.get('settings', {})
        self.listeners = []
        self._kw = {}
        self.settings = None
        # super(cls, self).__init__(*args, **kwargs)

    def setup(self, **kw):
        self.settings = self.configure(**kw)
        # Copy back required native arguments for ease.
        keys = ['hosts', 'ports', 'client_class']
        self.inherit_attributes(keys)
        # After configure
        self.listeners = self.setup_listeners(**self.settings)

    def loop(self):
        self.loop_forever(self.listeners)

    def start(self, *args, **kw):
        ''' Perform setup and start '''
        self._kw.update(self._init_kw)
        self._kw.update(self._init_settings or {})
        self._kw.update(kw)

        if self.settings is None:
            self.settings = self.setup(**self._kw)

        self.loop()


if __name__ == '__main__':
    main()
