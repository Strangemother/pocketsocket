from session import get_session, setup_session
from ws4py.server.geventserver import WSGIServer
from host.wsgi import SessionServer
from host.client import SessionClient
from host.settings import create_settings
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", dest='WS_PORT', type=int, default=None)
parser.add_argument("-i", "--host", dest='WS_HOST', type=str, default=None)
parser.add_argument("-s", "--settings", type=str, default=None)


def main(address=None):
    args = parser.parse_args()
    conf = create_settings(args=args)

    address = address or conf.get_address()
    print('Run', address)

    server = WSGIServer(address, SessionServer(handler_cls=SessionClient))
    session = setup_session(server, settings=conf)
    server.environ['WEBSOCKET_SESSION'] = session
    server.serve_forever()


if __name__ == '__main__':
    main()

