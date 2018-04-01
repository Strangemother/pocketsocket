from host.digest import PluginBase
import select, socket
import threading
import sys, time
#from host.print import print

def wait_peers(*address):

    print('Waiting on UDP Peers')
    bufferSize = 1024 # whatever you need
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(address)
    s.setblocking(0)

    run = True
    while run:
        result = select.select([s],[],[])
        msg = result[0][0].recv(bufferSize)
        print('Peers receiver:', msg)
        if msg == 'kill':
            print('Peer wait killed by pill.')
            run = False
            break
    print('Closing peer wait')
    s.close()


class UDP(PluginBase):

    def mounted(self, session):

        if hasattr(session, 'peers') is False:
            session.peers = {}

        self.session = session
        address = self.session.settings.UDP_ANNOUNCE
        self.address = address
        print('mounted peers', self)
        recvt = threading.Thread(target=wait_peers, args=address)
        recvt.start()
        self.recv_thread = recvt


        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        print('created peers', s)

        data =  ("B Message {}".format(repr(time.time()) + '\n')).encode()
        s.sendto(data, self.address)


    # def created(self):
