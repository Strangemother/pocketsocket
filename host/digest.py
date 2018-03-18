import re
from message import postmaster, perform_message, perform_command, broadcast


SWITCH = '/'

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
        perform_message('New client: {}'.format(cid), client, self.get_clients(client), cid=cid)

    def remove_client(self, client, cid):
        perform_message('Remove client: {}'.format(cid), client, self.get_clients(client), cid=cid)

    def text_message(self, message, client):
        perform_message('Text: {}'.format(client.id), client, self.get_clients(client), cid=client.id)

    def binary_message(self, message, client):
        perform_message('Binary: {}'.format(client.id), client, self.get_clients(client), cid=client.id)

    def decode_message(self, message, client):
        pass #perform_message('Text {}'.format(client.id), client, self.get_clients(client), cid=client.id)


class Broadcast(PluginBase):
    '''Given a text or binary message, send to all self.client exluding the
    originating client.
    This should be placed at the bottom of a Session plugin call list to ensure
    authorized methods are tested first.'''

    def text_message(self, message, client):
        broadcast(message, client, self.get_clients(client), cid=client.id)

    def binary_message(self, message, client):
        broadcast(message, client, self.get_clients(client), True, cid=client.id)


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
                data = perform_command(text, client, self.get_clients(client))
                return (True, False)

        return (False, True)
