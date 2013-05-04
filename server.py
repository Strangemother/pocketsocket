'''
This is the localwebsocket server to provide
an async service for itunes integration to the interface.
This needs to be booted as a seperate process and
'''
from vendor.ISocketServer.SimpleWebSocketServer import WebSocket, SimpleWebSocketServer
from vendor.poo.overloader import overload
from vendor.serializers import json_serialize


class SimpleMultiClient(WebSocket):

    def receive(self, msg):
        '''method to hook data received for user override'''
        pass

    def handleMessage(self):
        if self.data is None:
            self.data = ''
        self.data = str(self.data)
        self.receive(self.data)
        self._iter_send(self.data)

    def send_to_all(self, *args, **kwargs):

        o = {
            'address': self.address[0],
            'port': self.address[1],
        }

        # import pdb; pdb.set_trace()
        if len(args) > 1:
            o = overload(o, args[0], args[1])
        else:
            o['data'] = args[0]

        self._iter_send(o, **kwargs)

    def _iter_send(self, o, **kwargs):

        for client in self.server.connections.itervalues():
            if kwargs.get('client_safe', True):
                if client != self:
                    self.__send_to(client, o)
            else:
                # import pdb; pdb.set_trace()
                self.__send_to(client, o)

    def __send_to(self, client, msg):
        # import pdb; pdb.set_trace()
        j = json_serialize(msg)
        try:
            print 'send', j
            client.sendMessage(str(j))
            # client.sendMessage(str(self.address[0]) + ' - ' + str(self.data))
        except Exception as n:
            print n

    def handleConnected(self):
        self.send_to_all('client.connected',  str(self.address[0]))

    def handleClose(self):
        self.send_to_all('client.disconnected', str(self.address[0]))

from json import loads


class InterfaceSocket(SimpleMultiClient):

    def receive(self, msg):
        self.send_to_all('socket', 'receive', client_safe=False)
        print "Receive:", msg


def main(wsc=None, host='', port=8001):
    s = InterfaceSocket if wsc is None else wsc
    server = SimpleWebSocketServer(host, port, s)
    print 'Ready', host, port
    server.serveforever()

if __name__ == '__main__':
    main()
