from gevent import monkey; monkey.patch_all()
from ws4py.websocket import EchoWebSocket
from ws4py.server.geventserver import WSGIServer
from ws4py.server.wsgiutils import WebSocketWSGIApplication
from ws4py.client import WebSocketBaseClient

from ws4py.manager import WebSocketManager
from ws4py import format_addresses, configure_logger

from message import postmaster, perform_message
from pydoc import locate

logger = configure_logger()


def log(*a):
    logger.info(' '.join(map(str, a)))


clients = {}
#_man = WebSocketManager()

global_sessions = {}


class Session(object):
    '''A Session is an active dictionary helping a client hoist plugins
    and server options.
    It can act as transient key value storage
    '''

class Broadcast(object):

    def created(self):
        pass

    def mounted(self, session):
        print('mounted broadcast')
        self.session = session

    def add_client(self, client, cid):
        perform_message('New client {}'.format(cid), client, self.clients, cid=cid)

    def remove_client(self, client, cid):
        perform_message('Remove client {}'.format(cid), client, self.clients, cid=cid)

    def text_message(self, message, client):
        perform_message('Text {}'.format(client.id), client, self.clients, cid=client.id)

    def binary_message(self, message, client):
        perform_message('Binary {}'.format(client.id), client, self.clients, cid=client.id)

    def decode_message(self, message, client):
        pass #perform_message('Text {}'.format(client.id), client, self.clients, cid=client.id)


class Mount(Broadcast):

    def mounted(self, session):
        self.session = session


    def text_message(self, message, client):

        if message.startswith(':mount'):
            items=list(map(str.strip, message.split(':mount')))[1:]

            for item in items:
                item = item.strip()
                self.session.add_plugin(item, item)

        # perform_message('Text {}'.format(client.id), client, self.clients, cid=client.id)



class PluginMixin(object):

    def add_plugins(self, plugins):
        res = {}

        for pls in plugins:
            res[pls] = self.add_plugin(pls, pls)

        return res

    def add_plugin(self, name, plugin_path):
        plugin = locate(plugin_path)
        print('Adding plugin {}'.format(plugin_path))

        if callable(plugin):
            plugin = plugin()

        self._plugins[name] = plugin
        plugin.clients = clients
        if hasattr(plugin, 'created'):
            plugin.created()

        if hasattr(plugin, 'mounted'):
            plugin.mounted(self)

        return plugin

    def remove_plugin(self, name):
        if name in self._plugins:
            del self._plugins[name]
            return True
        return False

    def call_plugins(self, name, *a, **kw):
        res = {}

        for p in self._plugins.values():
            func = getattr(p, name)
            if callable(func):
                res[name] = func(*a, **kw)
        return res


SWITCH = '/'

class SystemSession(Session, PluginMixin):
    '''A global session for all other sessions and clients to interact with
    server configurations. One system_session exists for a server. All clients
    can use the global session
    '''
    plugins = (
            'main.Broadcast',
            'main.Mount',
        )

    def __init__(self, address, server):
        self.address = address
        self.server = server
        self._plugins = {}
        self.add_plugins(self.plugins)

    def add(self, client):
        cid = id(client)
        clients[cid] = client
        self.call_plugins('add_client', client, cid)
        return cid

    def remove(self, client):
        if client.id in clients:
            del clients[client.id]
            self.call_plugins('remove_client', client, client.id)
            return True
        return False

    def message(self, message, client):

        if message.is_binary is False:
            text = postmaster(message, client, clients)

            if text[0] == SWITCH:
                data = perform_command(text, client, clients)
            else:
                # A standard message for normal protocols.
                data = perform_message(text, client, clients)

            self.call_plugins('text_message', text, client)




    def decode(self, message, client, clients):
        """Decode a given message, converting it through session formatters
        """
        # print('session decode')
        self.call_plugins('decode_message', message, client)
        return message


def setup_session(address, server):
    '''
    Setup and start a new global session for the given server.
    The new SystemSession is globalised and returned.
    '''
    ss = SystemSession(address, server)
    server.system_session = ss
    # port only
    global_sessions[str(address[1])] = ss

    return ss


def get_clients():
    return clients


class EchoClient(EchoWebSocket):

    def received_message(self, message):
        """
        Automatically sends back the provided ``message`` to
        its originating endpoint.
        """
        # log('Recv > {}'.format(message))
        self.session.message(message, self)
        # self.broadcast(message.data, message.is_binary, ignore=[self])

    def opened(self):
        """
        Called by the server when the upgrade handshake
        has succeeded.
        """
        peer_id = str(self.local_address[1])
        session = global_sessions.get(peer_id)
        self.session = session

        if session is None:
            print('Client opened to no server?')
            return

        self.id = session.add(self)

    def closed(self, code, reason=None):
        log('closed', self)
        self.session.remove(self)


def main(address=None):
    address = address or ('localhost', 8009,)
    log('Run', address)
    server = WSGIServer(address, WebSocketWSGIApplication(handler_cls=EchoClient))
    #_man.start()
    #_man.run()
    setup_session(address, server)
    server.serve_forever()



if __name__ == '__main__':
    main()
