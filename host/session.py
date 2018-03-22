from translate import JSONEncoderDecoder
from pydoc import locate
from host.message import postmaster, broadcast, handle_text, MetaMessage
from plugin import PluginMixin


global_sessions = {}
clients = {}
#_man = WebSocketManager()

def setup_session(address, server):
    '''
    Setup and start a new global session for the given server.
    The new SystemSession is globalised and returned.
    '''
    print('Creating new system session')
    ss = SystemSession(address, server)
    server.system_session = ss
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

    def decode_message(self, message, client):
        return True, message

    def encode_message(self, message, client):
        print('Translate raw')

        output = message

        if hasattr(message, 'data'):
            output = message.data

        if hasattr(message, 'render'):
            output = message.render() or output
            ss =  '|'.join(["{}={}".format(x,y) for x,y in output])
            return True, ss
        return True, output


from datetime import datetime 

class TimestampEncoder(object):


    def encode_message(self, message, client):
        if hasattr(message, 'content'):
            print('Translate encoder', id(client))
            message.content_keys.add('time_out')
            message.content += ( ('time_out', datetime.now()), )
        return True, message

    def decode_message(self, message, client):
        if hasattr(message, 'content'):
            print('Translate decoder')
            message.content_keys.add('time_in')
            message.content += ( ('time_in', datetime.now()), )
        return True, message


class SystemSession(Session, PluginMixin):
    '''A global session for all other sessions and clients to interact with
    server configurations. One system_session exists for a server. All clients
    can use the global session
    '''
    plugins = (
            'host.digest.Announce',
            'host.digest.Mount',
            'host.switch.Switch',
            'host.digest.DirectMessage',
            'host.channels.Channels',
            'host.digest.Broadcast',
        )

    def __init__(self, address, server):
        self.address = address
        self.server = server
        self._plugins = {}

        self.translators = (
            ('timestamp', TimestampEncoder(),),
            #('raw', RawEncoder(),),
            ('json', JSONEncoderDecoder(),),
            
        )

        self.add_plugins(self.plugins)

    def get_clients(self, client=None):
        return clients

    def add(self, client):
        '''Add a client to the session, applying to the call list
        and executing the plugin list
        '''
        cid = id(client)
        clients[cid] = client
        print('Adding client {} {}'.format(cid, client))
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

        if message.is_binary is False:
            res = self.decode(message, recv_client) 
            self.call_plugins('text_message', message, recv_client)
            return

        print('Binary message not implemented')

    def decode(self, message, client):
        """Decode a given message, converting it through session formattersa"""
        # print('session decode')
        res = self.decode_message(message, client)
        self.call_plugins('decode_message', res, client)
        return message

    def decode_message(self, message, client):
        '''Using the translators list, decode the data relative to the client'''
        print('Calling session decode_message')
        res = message
        for name, decoder in self.translators:
            success, res = decoder.decode_message(res, client)
        return res

    def encode(self, message, client, clients, is_binary=False):
        """Encode a given message, converting it through session formatters
        """
        print('session encode:', message)
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
