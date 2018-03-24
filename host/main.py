from gevent import monkey; monkey.patch_all()
from ws4py.websocket import WebSocket
from ws4py.server.geventserver import WSGIServer
from ws4py.server.wsgiutils import WebSocketWSGIApplication
from ws4py.client import WebSocketBaseClient

from ws4py.manager import WebSocketManager
from ws4py import format_addresses, configure_logger

from session import get_session, setup_session
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


import os
import sys

import django
from django.core.handlers.wsgi import WSGIHandler

def setup_django_wsgi():
    sys.stdout = sys.stderr
    #fp = os.path.abspath(os.path.dirname(__file__))
    fp = "C:/Users/jay/Documents/GitHub/pocketsocket/website"
    sys.path.insert(0, fp)
    os.environ["DJANGO_SETTINGS_MODULE"] = "website.settings"
    django.setup(set_prefix=False)
    application = WSGIHandler()
    return application

class SessionServer(WebSocketWSGIApplication):
    base_html = None
    dev_mode = True

    def __init__(self, protocols=None, extensions=None, handler_cls=WebSocket):
        super().__init__(protocols, extensions, handler_cls)
        self.application = setup_django_wsgi()

    def __call__(self, environ, start_response):

        ws_token = environ.get("HTTP_UPGRADE", None)
        if ws_token is None:

            if environ['SERVER_PROTOCOL'] == 'HTTP/1.1':

                return self.application(environ, start_response)

                # fn = get_asset
                # if environ['PATH_INFO'] == '/':
                #     fn = index_response
                # return fn(environ, start_response)

        elif environ.get('REQUEST_METHOD') != 'GET':
            raise HandshakeError('HTTP method must be a GET')

        return super(SessionServer, self).__call__(environ, start_response)


def index_response(environ, start_response):

    headers = [
            ('Content-Type','text/html'),
        ]
    #start_response('302 Found', [('Location','http://google.com')])

    with open('templates/index.html') as stream:
        base_html = stream.read()
        base_html = base_html.encode()

    bl = len(base_html)
    ch = ('Content-Length', str(bl))
    headers.append(ch)

    start_response('200 OK', headers)

    return [base_html]

def get_asset(env, start_response):
    start_response('404 NOT FOUND', [])
    return []

def main(address=None):
    address = address or ('localhost', 8009,)
    log('Run', address)
    server = WSGIServer(address, SessionServer(handler_cls=SessionClient))
    #_man.start()
    #_man.run()
    setup_session(address, server)
    server.serve_forever()



if __name__ == '__main__':
    main()
