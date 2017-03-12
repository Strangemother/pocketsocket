from ws import Client
from client import ClientListMixin
from server import Server
from logger import log
import re


def main_echo():
    server = ChannelServer()
    server.start()


class PragmaMessage(str):

    def __init__(self, s):
        self.message = s
        self.pragma = {}

    def add(self, key, value):
        '''
        Add pragma meta data
        '''
        self.pragma[key] = value

    def has_pragma(self):
        return len(self.pragma.keys()) != 0


class PragmaDecoder(object):
    '''
    Perform and message commands to the client using a simple
    pragma regex.
    '''
    sep = ' '
    pragmas = tuple()

    def get_pragmas(self):
        return self.pragmas

    def create_pragmas(self, pragmas=None):
        '''
        generate instances of all pragma classes
        '''
        pragmas = pragmas or self.get_pragmas()
        r = {}
        for p in pragmas:
            pi = p()
            r[p.__name__] = pi

            for n in p.names:
                r[n] = pi
        return r

    def _compile_regex(self):
        self._re = re.compile(r"^\s*#(.*)[\r\n]", re.MULTILINE)

    def text_opcode(self, data):
        m = self.inspect_message(data)
        return super(PragmaDecoder, self).text_opcode(m)

    def inspect_message(self, message):
        '''
        Read the message, checking for a pragma headers.
        If message does not start with a prama statement, the original
        data is returned.
        Pragma statements are read for parsing.
        mutation may occur depending on the statement
        '''
        pm = PragmaMessage(message)

        for match in self._re.finditer(message):
            print 'Matched', match
            mg = match.group()
            els = mg.split(self.sep)
            a = els[1:]
            if len(els) == 2:
                els[0] = els[0][1:]
                a = els

            pm.add(*self.execute_pragma(*a))
        pm.message = self._re.sub("", message)
        return pm

    def execute_pragma(self, key, value):
        '''
        Perform actions with the given key and value
        '''
        print 'Execute pragma', key, value
        return str(key), str(value)


class PragmaNamedClient(object):

    names = ('name', 'client')

    # If a client is not detected, should the client default to
    # broadcasting the message to all clients
    # If False, the message will not be sent to any client
    broadcast_default = True

    def call(self, client, key, value, pragma_message, opcode):

        method = getattr(self, '{}_call'.format(key), None)

        if method is not None:
            return method(client, key, value, pragma_message, opcode)

    def name_call(self, client, key, value, pragma_message, opcode):
        n = getattr(client, 'name', None)
        if n is not None:
            print 'Rename client', client.name, 'to', n
        else:
            print 'Name client', client, 'to', value
        client.name = value

    def client_call(self, client, key, value, pragma_message, opcode):
        client_g = client.server.clients_iter(ignore=[client])
        sent = self.broadcast_default

        for client in client_g:
            name = getattr(client, 'name', None)
            if name == value:
                print 'Send pragma_message to', name
                client.send(pragma_message.message, opcode)
                sent = True
        return sent


class ChannelClient(PragmaDecoder, Client):

    pragmas = (
            PragmaNamedClient,
        )

    def init(self, *a, **kw):
        self._compile_regex()
        self._pragmas = self.create_pragmas()

    def recv(self, data, opcode):
        #log('>', self, opcode, data)
        log('recv', len(data.message))
        # self.pragma_handler.recv(self._pragmas, data, opcode)
        # self.send_all(data, opcode, ignore=[self])

        pragmas = self._pragmas
        has_p = data.has_pragma()
        skip = None

        for n in data.pragma:
            pragma = pragmas.get(n, None)
            if pragma is not None:
                value = data.pragma.get(n)
                sv = pragma.call(self, n, value, data, opcode)
                skip = skip or sv
            else:
                print 'Uncaptured Pragma:', n

        if has_p is False or skip is not True:
            self.send_all(data.message, opcode, ignore=[self])

    def send(self, data, opcode=None):
        log('<', self, opcode, data)
        return self.sendMessage(data, opcode)


class ChannelServer(ClientListMixin, Server):
    ''' Basic instance of a server, instansiating ws.Client for
    socket clients '''
    ports = (9004, )
    client_class = ChannelClient


if __name__ == '__main__':
    main_echo()
