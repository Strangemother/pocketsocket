'''A Service provides a communication layer to service protocol transfer.

# Basic Service.

Map a Service for pipe communication using JSON

# Reboot Service.

Serve a handler, reboot the service using run for live changes.

# Code

Provide a code layer, remote debugger

# SSH

SSH keyswap for safe data communcation

# Command

Run remote commands through channels, receive input.

'''

import json
from logger import log
from SimpleWebSocketServer import WebSocket
import sys, traceback


class BaseClient(WebSocket):

    def handleMessage(self):
        """
            Called when websocket frame is received.
            To access the frame data call self.data.

            If the frame is Text then self.data is a unicode object.
            If the frame is Binary then self.data is a bytearray object.
        """
        self.message(self.data)

    def message(self, data):
        d = self.decode(data)
        self.receive(d)

    def handleConnected(self):
        """Called when a websocket client connects to the server."""
        self.connect()
        print 'handleConnected'

    def handleClose(self):
        """Called when a websocket server gets a Close frame from a client."""
        print 'handleClose'

    def handleError(self, msg, exc=None, client=None):
        self.error(msg, exc, client=client or self)
        print 'Error:', msg
        print exc
        print client
        print "Exception in user code:"
        print '-'*60
        traceback.print_exc(file=sys.stdout)
        print '-'*60

    def close(self, status=1000, reason=u''):
        super(BaseClient, self).close(status, reason)

    def sendMessage(self, data):
        """
            Send websocket data frame to the client.

            If data is a unicode object then the frame is sent as Text.
            If the data is a bytearray object then the frame is sent as Binary.
        """
        d = self.encode(data)
        if isinstance(d, str):
            d = unicode(d)
        return super(BaseClient, self).sendMessage(d)

    def connect(self):
        pass

    def error(self, msg, exc=None, client=None):
        pass

    def encode(self, data):
        'encode the message before the sendMessage'
        return data

    def send_all(self, message):
         return [x.send(message) for x in self.server.connections.values()]

    def send(self, data):
        'send a message'
        return self.sendMessage(data)

    def decode(self, data):
        'decode the message before the receive'
        return data

    def receive(self, data):
        'Receive a decoded message ready to digest'
        return data


class BasicServiceExample(BaseClient):

    def encode(self, data):
        'encode the message before the sendMessage'
        return data

    def send(self, data):
        'send a message'
        print 'BasicServiceExample send'
        super(BasicServiceExample, self).send(data)

    def decode(self, data):
        'decode the message before the receive'
        return data

    def receive(self, data):
        'Receive a decoded message ready to digest'
        return data

    def error(self, msg, exc=None, client=None):
        pass


class Transaction(object):
    '''read a many communication process into a completed chunk'''
    active = False
    name = None

    transactions = []

    def __init__(self, name):
        print 'create', name
        self.name = name


    def read(self, data, client=None):
        'transaction in from decode, send changes to transaction state'
        return data

    def receive(self, data, client=None):
        'transaction in from decode, send changes to transaction state'
        return data

    def send(self, data, client=None):
        return data


client_keys = {
    'dave': 33
}


class EchoTransaction(Transaction):
    '''
    Every message received is sent to all connected clients, not including
    the receiver client.
    '''

    def receive(self, data, client):
        client.send_all(data)
        return data


class NamedTransaction(Transaction):
    '''
    A client can be named. A message may be directed to a specific client
    through the name.
    '''
    def read(self, data, client=None):
        log('EchoTransaction', data)
        if data.type == 'json':
            data = self._decode(data.data, client)
        return data

    def _decode(self, data, client):
        'decode the information to enact commands'
        v = data.get('command', 'pass')
        name = 'command_{}'.format(v)
        if hasattr(self, name):
            d = getattr(self, name)(data, client)
            data = d or data
        return data

    def command_pass(self, data, client):
        client.send_all('got pass')
        return data

    def command_name(self, data, client):
        '''Name command, set the transaction and client as the same name.
        '''
        name = data.get('name', self.name)
        self.name = name
        client.name = self.name
        client.send('client name is {}'.format(self.name))

    def command_rename(self, data, client):
        'rename another client by name reference'
        client_name = data.get('client', None)
        new_name = data.get('name', None)

        if client_name is None:
            client.send('cannot rename without client reference')
            return
        if new_name is None:
            client.send('cannot rename without name refereence')
            return
        s = "You've been renamed by {} to name {}".format(client.name, new_name)
        self.send_to(client, client_name, s)
        # send rename
        d = dict(command='name', name=new_name)
        c = self.get_client(client_name, client)
        if c is not None:
            c.message(d)
        else:
            client.send('{} does not exist'.format(client_name))

    def get_client(self, name, client):
        'get a client by name reference'
        connections = client.server.connections
        for client_i in connections:
            # jsonclient object
            client = connections[client_i]
            if client.name == name:
                return client

    def send_to(self, client, name, data):
        'send a message to a client by name reference'
        c = self.get_client(name, client)
        if c is not None:
            c.send(data)


class RSATranscation(Transaction):

    transactions = [
        'start', 'receive_name'
    ]

    _si = 0
    key = None

    def read(self, data, client=None):
        k = self.key or self.name
        print 'Transaction receive', self.name, data.get(self.name)

        if k in data:
            self.transact(self.name, data[self.name], data)
        return data

    def transact(self, name, value, data):
        'step transaction'

        if hasattr(self, value):
            pos = self.transactions.index(value)
            if pos == self._si:
                getattr(self, value)(data)
                print value, self.key, self._si
            else:
                print 'Out of position'

    def start(self, data):
        print 'start RSA'
        self._si += 1
        # Need this key next.
        self.key = 'name'

    def receive_name(self, data):
        self.key = client_keys[data]
        print 'RSA', self.key, data


class TransactionMixin(object):
    _trans = None

    def transaction_decode(self, data):
        for t in self._trans:
            data = t.read(data, client=self)
        return data

    def transaction_receive(self, data):
        '''read the transactional state; returning mutated data'''
        for t in self._trans:
            data = t.receive(data, client=self)
        return data

    def transaction_send(self, data):
        '''read the transactional state; returning mutated data'''
        for t in self._trans:
            data = t.send(data, client=self)
        return data


from collections import namedtuple

Package = namedtuple('Package', 'type data')


class JSONClient(BaseClient, TransactionMixin):

    name = None

    def connect(self):
        self._trans = [
            NamedTransaction('name'),
            EchoTransaction('echo'),
            # RSATranscation('rsa'),
        ]

        self.send_all('New Client')

    def encode(self, data):
        'encode the message before the sendMessage'
        # log('encode message')
        data = self.transaction_send(data)
        return data

    def send(self, data):
        'send a message'
        if isinstance(data, (unicode, str,)) is False:
            data = json.dumps(data)
        super(JSONClient, self).send(data)

    def decode(self, data):
        'decode the message before the receive'
        self.send('decoding message')
        d = data
        try:
            d = json.loads(data)
            package = Package('json', d)
            self.send('loaded json')
        except TypeError as e:
            log('::Received wrong datatype', type(data))
            self.send(str(e))
            t = 'raw'
            if isinstance(d, dict):
                t = 'json'
            package = Package(t, d)

        except ValueError as e:
            log('::Could not decode data', e)
            self.send('did not receive json')
            package = Package('raw', d)
        decoded = self.transaction_decode(package)
        return decoded

    def receive(self, data):
        'Receive a decoded message ready to digest'
        self.send_all('Client: {} sent message'.format(self.name))
        data = self.transaction_receive(data)
        return data

    def error(self, msg, exc=None, client=None):
        log('error message', msg)
