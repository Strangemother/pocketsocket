from host.digest import PluginBase
from host.switch import add_switches


# Persistent record of a channel, to cast as Channel for the ststem
CHANNELS = (
        ('test', dict(public=True), ),
        ('foo', dict(public=True), ),
        ('eric', dict(public=True, owner='eric'), ),
    )


def master_channels():
    '''
    Return the definition of the available master channels.
    These are public or persistent records of channels.
    '''
    return {x: y for x, y in CHANNELS}


class Channel(object):

    def __init__(self, definition):
        self.data = definition
        if 'clients' not  in self.data:
            self.data['clients'] = set()

    def add(self, client_id):
        self.data['clients'].add(client_id)


class Channels(PluginBase):
    '''Given a text or binary message, send to all self.client exluding the
    originating client.
    This should be placed at the bottom of a Session plugin call list to ensure
    authorized methods are tested first.'''

    def mounted(self, session):
        print('mounted channels')

        # duck mount the session, injecting clients alternation.
        if hasattr(session, 'channels') is False:
            print('Creating new channels')
            session.channels = {}

        print('add_switches')
        add_switches({
                'channel': set_channel,
                'channels': list_channels,
            })

        self.session = session

    def add_client(self, client, cid):

        # Write allowed channels to the client
        client.channels = set([])
        print(' -- build channels')
        # Ensure the channel exists for others to subscribe
        in_channels = cid in self.session.channels
        if in_channels is False:
            print('Adding new channel placeholder to client', cid)
            self.session.channels[cid] = set([])

    def remove_client(self, client, cid):
        print('Channels. Client was removed. Remove from channels.')
        # Remove the main channel
        for name in client.channels:
            if name in client.session.channels:
                del self.session.channels[name]

        if cid in client.session.channels:
            del self.session.channels[cid]

    def text_message(self, message, client):
        print('Channels text_message')
        # Only send to subscribed channels.
        pass
        # broadcast(message, client, self.get_clients(client), cid=client.id)

    def binary_message(self, message, client):
        print('Channels binary_message')
        #broadcast(message, client, self.get_clients(client), True, cid=client.id)

    def broadcast(self, message, client, clients, is_binary, ignore, cid):
        _continue = False
        _used = False
        #clients = client.session.get_clients(client)

        _clients = set()

        if hasattr(client,'channels'):
            for cname in client.channels:
                channel_clients = client.session.channels.get(cname, set())
                _clients = _clients.union(channel_clients)
                #client.channels.intersection(client.session.channels)

            _clients = {x: clients[x] for x in _clients}

        if _clients is None or len(_clients) == 0:
            _continue = True
            _clients = clients

        if _clients is None:
            print('Dropped all clients')
        else:
            for name in _clients:
                if _clients[name] in ignore:
                    continue

                # Copy message ensures each client receives a unique list
                # of content through the message mutation during plugin
                # iteration

                msg = message.copy() if hasattr(message, 'copy') else message
                # Full translate. Going though the session to ensure the system
                # performs mandatory translations - within, the `message.render()`
                # (if it exists) returns the final output.
                data = client.session.encode(msg, client, _clients, is_binary)
                _clients[name].send(data, is_binary)
                _used = True


        return _used, _continue


def list_channels(values, options, client, clients):
    return ('channels', client.channels, master_channels(), )


def set_channel(values, options, client, clients):

    print('setting channel', values)

    for value in values:
        if hasattr(client, 'channels') is False:
            return (value, False, 'Client has no channels')

        records = master_channels()
        if value not in records:
            # client.session.channels[value] = set()
            return (value, False, 'Channel "{}" does not exist'.format(value))

        channel_d = records[value]

        # Add channel name to client
        client.channels.add(value)

        # add client to system session channels
        if value not in client.session.channels:
            client.session.channels[value] = set()

        client.session.channels[value].add(client.id)

        return (value, True, client.session.channels[value])
