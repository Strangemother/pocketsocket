from host.digest import PluginBase
from host.switch import add_switches


# Persistent record of a channel, to cast as Channel for the ststem
CHANNELS = (
        ('test', dict(public=True), ),
        ('foo', dict(public=True), ),
        ('eric', dict(public=True, owner='eric'), ),
    )


HOSTS = []

MASTER_PATH = '{base_path}/channels/list/json'
DB_CONNECTION = None


import os
import urllib.request
import json


class Database(object):

    def __init__(self, uri):
        self.uri = uri
        self._channels = None
        self.populated = False

    def remote_call(self):
        uri = self.uri
        with urllib.request.urlopen(uri) as url:
            data = json.loads(url.read().decode())
            return self._clean_data(data)

    def populate(self):
        self._channels = tuple(self.remote_call())
        self.populated = True

    def _clean_data(self, data):
        return tuple((x['name'], x,) for x in data)

    def channels(self):
        return self._channels


def master_channels():
    '''
    Return the definition of the available master channels.
    These are public or persistent records of channels.
    '''
    if DB_CONNECTION.populated is False:
        DB_CONNECTION.populate()
    channels = CHANNELS + DB_CONNECTION.channels()
    try:
        return {x: y for x, y in channels}
    except Exception as exc:
        import pdb; pdb.set_trace()  # breakpoint 6250617bx //


def get_channel(value, client=None):
    records = master_channels()

    if value not in records:
        # client.session.channel_data[value] = set()
        return get_service_channel(value, client)

    channel_d = records[value]

    return True, channel_d


def get_service_channel(value, client=None):

    if client is None:
        return False, 'Channel "{}" does not exist'.format(value)

    wss = client.environ.get('WEBSOCKET_SESSION', None)
    if wss is not None:
        if value in wss.channel_data:
            return True, wss.channel_data[value]
    return False, 'Channel "{}" does not exist'.format(value)


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

        # duck mount the session, injecting clients alternation.
        if hasattr(session, 'channels') is False:
            print('Adding new channels service to session')
            session.channel_data = {}
            session.channels = self
            global DB_CONNECTION

        if DB_CONNECTION is None:
            base_path = "http://localhost:{1}".format(*session.server.address)
            uri = MASTER_PATH.format(base_path=base_path)
            DB_CONNECTION = Database(uri)

        add_switches({
                'channel': set_channel,
                'channels': list_channels,
                'add-channel': add_channel,
                'rem-channel': remove_channel,
                'add-host': add_host,
                'rem-host': rem_host,
            })

        self.session = session

    def create_channel(self, name, data):
        global CHANNELS
        CHANNELS += ( (name, data, ), )
        #self.session.channel_data[name] = data
        #return name in self.session.channel_data

    def add_client(self, client, cid):

        # Write allowed channels to the client
        client.channels = set([])
        print(' -- build channels')
        # Ensure the channel exists for others to subscribe
        in_channels = cid in self.session.channel_data
        if in_channels is False:
            print('Adding new channel placeholder to client', cid)
            self.session.channel_data[cid] = set([])

    def remove_client(self, client, cid):
        print('Channels. Client was removed. Remove from channels.')
        # Remove the main channel
        for name in client.channels:
            if name in client.session.channel_data:
                del self.session.channel_data[name]

        if cid in client.session.channel_data:
            del self.session.channel_data[cid]

    def text_message(self, message, client):
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
                channel_clients = client.session.channel_data.get(cname, set())
                _clients = _clients.union(channel_clients)
                #client.channels.intersection(client.session.channel_data)

            _clients = {x: clients.get(x, None) for x in _clients}

        if _clients is None or len(_clients) == 0:
            _continue = True
            _clients = clients

        if _clients is None:
            print('Dropped all clients')
        else:
            for name in _clients:
                if _clients[name] in ignore:
                    continue

                if _clients[name] is None:
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


def add_host(values, options, client, clients):
    """Add a channel host for channel list services"""
    for v in values:
        HOSTS.append(v)

    return HOSTS


def rem_host(values, options, client, clients):

    for v in values:
        HOSTS.remove(v)

    return HOSTS


def add_channel(values, options, client=None, clients=None, session=None):

    print(' -- add_channel')
    for value in values:

        res = []
        if client is not None:

            if hasattr(client, 'channels') is False:
                print('client has no channels')
                return (value, False, 'Client has no channels')

            success, channel_d = get_channel(value, client=client)
            if success is False:
                print('Did not succeed with get_channel')
                return channel_d

            # Add channel name to client
            client.channels.add(value)
            session = client.session

        if session is not None:
            # add client to system session channels
            if value not in session.channel_data:
                print('Adding "{}" to session'.format(value))
                session.channel_data[value] = set()

            res = session.channel_data[value]

            if client is not None:
                session.channel_data[value].add(client.id)
        else:
            print('Did not add Channel "{}" to a service '.format(value))

        return (value, True, res)


def remove_channel(values, options, client, clients):

    print(' -- remove_channel')
    for value in values:
        if hasattr(client, 'channels') is False:
            return (value, False, 'Client has no channels')

        success, channel_d = get_channel(value, client=client)
        if success is False:
            return channel_d


        # Add channel name to client
        if value in client.channels:
            client.channels.remove(value)

        # add client to system session channels
        if value in client.session.channel_data:
            client.session.channel_data[value].remove(client.id)

        return (value, True, client.session.channel_data[value])


def set_channel(values, options, client, clients):

    print(' -- set_channel')
    for value in values:
        if hasattr(client, 'channels') is False:
            return (value, False, 'Client has no channels')

        success, channel_d = get_channel(value, client=client)
        if success is False:
            return channel_d


        # Add channel name to client
        client.channels = set([value])

        # add client to system session channels
        if value not in client.session.channel_data:
            client.session.channel_data[value] = set()

        client.session.channel_data[value].add(client.id)

        return (value, True, client.session.channel_data[value])
