import pocketsocket_server


class IngressReceiver:
    uuid = None

    def __init__(self, uuid):
        self.uuid = uuid

    def recv(self, data):
        print('IngressReceiver::recv', data)

    def send(self, data):
        """Send a message to this socket
        """
        pocketsocket_server.send(self.uuid, 1, data)

    def broadcast(self, data):
        """Send a message to all clients, excluding self.
        """
        pocketsocket.send_all(event_kind, data, self.uuid)
