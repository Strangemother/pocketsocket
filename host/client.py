from ws4py.websocket import WebSocket

from ws4py.manager import WebSocketManager
from ws4py import format_addresses, configure_logger

from session import get_session
from host.message import MetaMessage


logger = configure_logger()
def log(*a):
    logger.info(' '.join(map(str, a)))


class SessionClient(WebSocket):

    def received_message(self, message):
        """
        Automatically sends back the provided ``message`` to
        its originating endpoint.
        """
        # log('Recv > {}'.format(message))
        self.session.process_message(MetaMessage(message, self), self)
        # self.broadcast(message.data, message.is_binary, ignore=[self])

    def opened(self):
        """
        Called by the server when the upgrade handshake
        has succeeded.
        """
        session = get_session(self.local_address)

        if session is None:
            print('Client opened to no server?')
            return

        self.session = session
        self.id = session.add(self)

    def closed(self, code, reason=None):
        log('closed', self)
        self.session.remove(self)


