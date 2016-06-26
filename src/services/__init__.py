import uuid
from logger import log
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
import os
import socket

if os.name != "nt":
    import fcntl
    import struct

    def get_interface_ip(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s',
                                                                            ifname[:15]))[20:24])


def get_lan_ip():
    ip = socket.gethostbyname(socket.gethostname())
    if ip.startswith("127.") and os.name != "nt":
        interfaces = [
            "eth0",
            "eth1",
            "eth2",
            "wlan0",
            "wlan1",
            "wifi0",
            "ath0",
            "ath1",
            "ppp0",
        ]

        for ifname in interfaces:
            try:
                ip = get_interface_ip(ifname)
                break
            except IOError:
                pass
    return ip


class Server(SimpleWebSocketServer):
    pass


class WebSocketService(object):

    # Class to handle client connections
    client_handler = WebSocket
    # The server class to build the service.
    server_handler = SimpleWebSocketServer
    # ip address to host
    server_ip = get_lan_ip()
    # access port
    server_port = 8004

    def run(self, ip=None, port=None, cb=None):
        self.uuid = uuid.uuid4()
        self._svc = self.create(ip, port)
        self.serve(self._svc, cb)

    def create(self, ip=None, port=None):
        server_ip = ip or self.server_ip
        server_port = port or self.server_port

        self.server_ip = server_ip
        self.server_port = server_port

        client_handler = self.client_handler

        log('creating service on {}:{}'.format(server_ip, server_port))

        hargs = [server_ip, server_port, client_handler]
        # print '\nwrite condition\n'
        # self._served_args = hargs
        svc = self.server_handler(*hargs)

        return svc

    def served(self):
        return True

    def serve(self, svc, callback=None):
        svc.served = self.served
        return svc.serveforever()

