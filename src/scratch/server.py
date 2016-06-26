import threading
import time

from SimpleWebSocketServer import WebSocket, SimpleWebSocketServer
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-10s) %(message)s',
                    )

def main():
    server = Server()
    server.start()
    return server


class Server(threading.Thread):

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        threading.Thread.__init__(self, group=group, target=target, name=name,
                                  verbose=verbose)
        self.args = args
        self.kwargs = kwargs
        return

    def run(self):
        n = threading.currentThread().getName()
        logging.debug('{0} running'.format(n))
        host = '0.0.0.0'
        port = 9000
        ps = SimpleWebSocketServer(host, port, WebSocket)
        ps.serveforever()
        print ps


def shutdown(server):
    print 'Shutdown FTP'


if __name__ == '__main__':
    main()
