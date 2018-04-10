from translate import JSONEncoderDecoder
from pydoc import locate
from host.message import postmaster, broadcast, handle_text, MetaMessage
from plugin import PluginMixin
from datetime import datetime
from pydoc import locate

global_sessions = {}
clients = {}
#_man = WebSocketManager()

def setup_session(server, settings=None):
    '''
    Setup and start a new global session for the given server.
    The new SystemSession is globalised and returned.
    '''
    ss = SystemSession(server, settings)
    address = server.address
    server.system_session = ss
    ss.server = server
    # port only
    global_sessions[str(address[1])] = ss

    return ss


def get_session(address):
    port = address[1]
    return global_sessions.get(str(port))


def get_clients():
    return clients


class Session(object):
    '''A Session is an active dictionary helping a client hoist plugins
    and server options.
    It can act as transient key value storage
    '''


class RawEncoder(object):

    terminator = '|'

    def __init__(self, terminator='|'):
        self.terminator = terminator

    def decode_message(self, message, client):
        return True, message

    def encode_message(self, message, client):
        output = message

        if hasattr(message, 'data'):
            output = message.data

        if hasattr(message, 'render'):
            output = message.render() or output
            ss =  self.terminator.join(["{}={}".format(x,y) for x,y in output])
            return True, ss
        return True, output


class TimestampEncoder(object):

    def encode_message(self, message, client):
        if hasattr(message, 'content'):
            message.content_keys.add('time_out')
            message.content += ( ('time_out', datetime.now()), )
        return True, message

    def decode_message(self, message, client):
        if hasattr(message, 'content'):
            message.content_keys.add('time_in')
            message.content += ( ('time_in', datetime.now()), )
        return True, message


class SystemSession(Session, PluginMixin):
    '''A global session for all other sessions and clients to interact with
    server configurations. One system_session exists for a server. All clients
    can use the global session
    '''
    plugins = ()

    def __init__(self, server, settings=None):
        self.settings = settings
        self.server = server
        self._plugins = {}

        self.translators = ()

        self.add_plugins(self.settings.SESSION_PLUGINS)
        self.create_translators(self.settings.SESSION_TRANSLATORS)

    def create_translators(self, trans):
        for name, imp_path, conf in trans:
            self.translators += (
                ( (name, locate(imp_path)(**{}), ), )
            )

    def get_clients(self, client=None, only=None):
        if only is not None:
            #print('get only', only)
            return [clients[x] for x in only]
        return clients

    def close(self):
        self.call_plugins('close')
        clients = list(self.get_clients().values())
        for cl in clients:
            cl.closed(0)


    def add(self, client):
        '''Add a client to the session, applying to the call list
        and executing the plugin list
        '''
        cid = id(client)
        clients[cid] = client
        self.call_plugins('add_client', client, cid)
        return cid

    def remove(self, client):
        '''Remove a client from the session, calling the 'remove_client' plugin
        chain
        '''
        if hasattr(client, 'id') is False:
            print('Could not cleanly remove a client', client)
            return None

        if client.id in clients:
            del clients[client.id]
            self.call_plugins('remove_client', client, client.id)
            return True
        return False

    def process_message(self, message, recv_client):
        '''Pump a message through the session from an originating client.'''

        res = self.decode(message, recv_client)
        if message.is_binary is False:
            self.call_plugins('text_message', res, recv_client)
            return

        self.call_plugins('binary_message', res, recv_client)
        print('Binary message processed')

    def decode(self, message, client):
        """Decode a given message, converting it through session formattersa"""
        res = self.decode_message(message, client)
        self.call_plugins('decode_message', res, client)
        return message

    def decode_message(self, message, client):
        '''Using the translators list, decode the data relative to the client'''
        res = message
        for name, decoder in self.translators:
            success, res = decoder.decode_message(res, client)
        return res

    def encode(self, message, client, clients, is_binary=False):
        """Encode a given message, converting it through session formatters
        """
        self.call_plugins('encode_message', message, client)
        output = self.translate_encode(message, client, clients)
        return output

    def translate_encode(self, message, client, clients):
        '''Using the translators list, encode (out) the data relative to the client'''
        res = message
        for name, encoder in self.translators:
            success, res = encoder.encode_message(res, client)
        return res

    def broadcast(self, data, client, _clients=None, is_binary=False, ignore=None, cid=None):
        #_man.broadcast(message.data, message.is_binary)
        ignore = ignore or []
        self.call_plugins('broadcast', data, client, _clients, is_binary, ignore, cid)
