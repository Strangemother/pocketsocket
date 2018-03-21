'''A group of session plugins to maange IO from sockets.
A 'digest' module is non-blocking for the incoming information. An event
method can return None or a tuple of (used, continue) pr _acted upon_ and _proceed_
with the next digest plugin.

If `continue` is false, the next consecutive plugins are not called.
'''
import re
from host.message import postmaster, broadcast
from host.plugin import PluginBase


class Announce(PluginBase):
    '''Send string messages to all siblings of the client on events 'add',
    'remove', 'text' and 'binary',
    '''
    def add_client(self, client, cid):
        '''A new client has connected to the server. Broadcast the 'new client'
        statement to all connected clients.
        '''
        ss = 'New client: {}'.format(cid)
        client.session.broadcast(ss,
                                 client,
                                 self.get_clients(client),
                                 cid=cid)

    def remove_client(self, client, cid):

        ss = 'Remove client: {}'.format(cid)
        client.session.broadcast(ss,
                                 client,
                                 self.get_clients(client),
                                 cid=cid)

    def text_message(self, message, client):

        ss = 'Text: {}'.format(client.id)
        client.session.broadcast(ss,
                                 client,
                                 self.get_clients(client),
                                 cid=client.id)

    def binary_message(self, message, client):

        ss = 'Binary: {}'.format(client.id)
        client.session.broadcast(ss,
                                 client,
                                 self.get_clients(client),
                                 cid=client.id)

    def decode_message(self, message, client):
        pass #perform_message('Text {}'.format(client.id), client, self.get_clients(client), cid=client.id)


class Broadcast(PluginBase):
    '''Given a text or binary message, send to all sibiling clients exluding the
    originating client.
    This should be placed at the bottom of a Session plugin call list to ensure
    authorized methods are tested first.'''

    def text_message(self, message, client):
        client.session.broadcast(message,
            client,
            self.get_clients(client),
            cid=client.id)

    def binary_message(self, message, client):
        client.session.broadcast(message,
            client,
            self.get_clients(client),
            True,
            cid=client.id)


class Mount(PluginBase):
    '''Add and instansiate new digest plugins to the SessionServer through
    a ":mount" command and a python import string.

    This is not production safe, as the given ":mount import.path"
    import path is imported and applied to the plugin list without distinction.
    '''
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

