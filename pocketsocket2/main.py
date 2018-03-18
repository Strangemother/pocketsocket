from pydoc import locate
import re
import json

from gevent import monkey; monkey.patch_all()
from ws4py.websocket import EchoWebSocket
from ws4py.server.geventserver import WSGIServer
from ws4py.server.wsgiutils import WebSocketWSGIApplication
from ws4py.client import WebSocketBaseClient

from ws4py.manager import WebSocketManager
from ws4py import format_addresses, configure_logger

from message import postmaster, perform_message, perform_command, broadcast

SWITCH = '/'

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

class PluginBase(object):

    def created(self):
        pass

    def mounted(self, session):
        print('mounted broadcast')
        self.session = session

    def add_client(self, client, cid):
        pass

    def remove_client(self, client, cid):
        pass

    def text_message(self, message, client):
        pass

    def binary_message(self, message, client):
        pass

    def decode_message(self, message, client):
        pass

    def encode_message(self, message, client):
        pass

    def extract_default(self, message, client):
        '''return the value of a dict or string
        '''
        if isinstance(message, dict):
            v = message.get('value', None)
            return 'value' in message, v

        return True, message


class Announce(PluginBase):
    def add_client(self, client, cid):
        perform_message('New client: {}'.format(cid), client, self.get_clients(), cid=cid)

    def remove_client(self, client, cid):
        perform_message('Remove client: {}'.format(cid), client, self.get_clients(), cid=cid)

    def text_message(self, message, client):
        perform_message('Text: {}'.format(client.id), client, self.get_clients(), cid=client.id)

    def binary_message(self, message, client):
        perform_message('Binary: {}'.format(client.id), client, self.get_clients(), cid=client.id)

    def decode_message(self, message, client):
        pass #perform_message('Text {}'.format(client.id), client, self.get_clients(), cid=client.id)


class Broadcast(PluginBase):
    '''Given a text or binary message, send to all self.client exluding the
    originating client.
    This should be placed at the bottom of a Session plugin call list to ensure
    authorized methods are tested first.'''

    def text_message(self, message, client):
        broadcast(message, client, self.get_clients(), cid=client.id)

    def binary_message(self, message, client):
        broadcast(message, client, self.get_clients(), True, cid=client.id)


class Mount(PluginBase):

    def mounted(self, session):
        self.session = session

    def text_message(self, message, client):

        proceed = True
        acted = False
        success, text = self.extract_default(message, client)

        if success and text.startswith(':mount'):
            acted = True
            items=list(map(str.strip, text.split(':mount')))[1:]

            for item in items:
                item = item.strip()
                print(item)
                self.session.add_plugin(item, item)

        return (acted, proceed)


class DirectMessage(PluginBase):
    '''
    Send a message to one or more named clients, using an @ symbol with
    an attached string name.

        @eric @mike this is a message
    '''

    reobj = re.compile("@(.[^ ]+)", re.IGNORECASE)
    def mounted(self, session):
        print('mounted')
        self.session = session

    def text_message(self, message, client):
        res = ()
        acted = False
        proceed = True
        success, text = self.extract_default(message, client)

        if success and text.startswith('@'):
            acted = True
            proceed = False
            result = self.reobj.findall(text)
            _clients = {}
            for name in result:
                cl = self.get_clients().get(name, None)
                if cl is not None:
                    _clients[cl.id] = cl
                res += ( (name, cl is not None) )
            broadcast(text, client, _clients, ignore=[client])
            # for item in items:
            #     item = item.strip()
            #     self.session.add_plugin(item, item)
        return (acted, proceed)


class Switch(PluginBase):

    def text_message(self, message, client):

        success, text = self.extract_default(message, client)
        if success:
            if len(text) > 1 and text[0] == SWITCH:
                data = perform_command(text, client, self.get_clients())
                return (True, False)

        return (False, True)


class PluginMixin(object):

    def add_plugins(self, plugins):
        res = {}

        for pls in plugins:
            res[pls] = self.add_plugin(pls, pls)

        return res

    def add_plugin(self, name, plugin_path):
        plugin = locate(plugin_path)

        if plugin is None:
            print('Plugin "{}" does not exist'.format(plugin_path))
            return None
        print('Adding plugin {}'.format(plugin_path))

        if callable(plugin):
            plugin = plugin()

        plugin.get_clients = self.get_clients

        if hasattr(plugin, 'created'):
            plugin.created()

        self._plugins[name] = plugin

        if hasattr(plugin, 'mounted'):
            plugin.mounted(self)

        return plugin

    def get_clients(self):
        return clients

    def remove_plugin(self, name):
        if name in self._plugins:
            del self._plugins[name]
            return True
        return False

    def get_plugins(self):
        return [x for x in self._plugins.values()]

    def call_plugins(self, name, *a, **kw):
        res = {}
        values = self.get_plugins()
        for p in values:
            func = getattr(p, name)
            if callable(func):
                can_continue = func(*a, **kw)
                used = False
                _continue = True

                if isinstance(can_continue, tuple):
                    used, _continue = can_continue
                elif isinstance(can_continue, bool):
                    used = True
                    _continue = can_continue

                if _continue is False:
                    print('Break Plugin iteration because', name)
                    return False

        return res


class JSONEncoderDecoder(PluginBase):

    def decode_message(self, message, client):

        try:
            print('Decoding')
            return True, json.loads(message)
        except json.decoder.JSONDecodeError:
            print('  Decoding JSON Failed')
            return False, message

    def encode_message(self, message, client):

        if isinstance(message, dict):
            try:
                print('Encoding', type(message))
                message['from'] = client.id
                v = json.dumps(message)
                return True, v
            except json.decoder.JSONEncodeError:
                print('  Encoding JSON Failed')
        return False, message



class SystemSession(Session, PluginMixin):
    '''A global session for all other sessions and clients to interact with
    server configurations. One system_session exists for a server. All clients
    can use the global session
    '''
    plugins = (
            'main.Announce',
            'main.Mount',
            'main.Switch',
            'main.DirectMessage',
            'main.Broadcast',
        )


    def __init__(self, address, server):
        self.address = address
        self.server = server
        self._plugins = {}

        self.translators = (
            ('json', JSONEncoderDecoder(),),
        )

        self.add_plugins(self.plugins)

    def add(self, client):
        cid = id(client)
        clients[cid] = client
        print('Adding client {} {}'.format(cid, client))
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
            text = self.decode_message(text, client, clients)
            self.call_plugins('text_message', text, client)

    def decode_message(self, message, client, clients):
        '''Using the translators list, decode the data relative to the client'''
        res = message
        for name, decoder in self.translators:
            success, res = decoder.decode_message(res, client)
        return res

    def encode_message(self, message, client, clients):
        '''Using the translators list, decode the data relative to the client'''
        res = message
        print('encode_message')
        for name, encoder in self.translators:
            success, res = encoder.encode_message(res, client)
        return res

    def decode(self, message, client, clients):
        """Decode a given message, converting it through session formatters
        """
        # print('session decode')
        self.call_plugins('decode_message', message, client)
        return message

    def encode(self, message, client, clients, is_binary=False):
        """Decode a given message, converting it through session formatters
        """
        print('session encode')
        self.call_plugins('encode_message', message, client)
        text = self.encode_message(message, client, clients)
        return text


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


class SessionClient(EchoWebSocket):

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
    server = WSGIServer(address, WebSocketWSGIApplication(handler_cls=SessionClient))
    #_man.start()
    #_man.run()
    setup_session(address, server)
    server.serve_forever()



if __name__ == '__main__':
    main()
