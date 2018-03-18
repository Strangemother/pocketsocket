from digest import PluginBase
from switch import add_switches


def _injected_get_clients(orig_func):

    def get_clients_wrapper(session, client=None):
        if client is None:
            return orig_func(client)

        # collect from session channels
        session.channels.get()

    return get_clients_wrapper


class Channels(PluginBase):
    '''Given a text or binary message, send to all self.client exluding the
    originating client.
    This should be placed at the bottom of a Session plugin call list to ensure
    authorized methods are tested first.'''

    def mounted(self, session):
        print('mounted broadcast')

        # duck mount the session, injecting clients alternation.
        session.get_clients = _injected_get_clients(session.get_clients)
        if hasattr(session, 'channels') is False:
            session.channels = {}

        add_switches({
                'channel': set_channel,
                'channels': set_channels,
            })

        self.session = session

    def add_client(self, client, cid):

        # Write allowed channels to the client
        client.channels = set([cid])

        # Ensure the channel exists for others to subscribe
        in_channels = cid in self.session.channels
        if in_channels is False:
            self.session.channels[cid] = set()


    def text_message(self, message, client):
        print('Channels text_message')

        #broadcast(message, client, self.get_clients(client), cid=client.id)

    def binary_message(self, message, client):
        print('Channels binary_message')
        #broadcast(message, client, self.get_clients(client), True, cid=client.id)


def set_channel(value, options, client, clients):

    print('setting channel value')
    if hasattr(clients, 'channels') is False:
        return (value, False, )

    clients.channels.add(value)

def set_channels(value, options, client, clients):

    print('setting channel value')
    if hasattr(clients, 'channels') is False:
        return (value, False, )

    clients.channels.extend(value)

