'''
Setup a super simple remote tool for keyboard and mouse events over websocket.
'''
from pocketsocket.ws import Client
from pocketsocket.server import Server
from pocketsocket.logger import log
from pocketsocket.client import ClientListMixin
import win32com.client

shell = win32com.client.Dispatch("WScript.Shell")


def main():
    server = EchoServer(client_class=CommandClient)
    server.start()


class CommandClient(Client):

    is_slave = True

    def recv(self, data, opcode):
        str_val  = str(data)
        log('>', self, opcode, type(data), str_val, data)
        # if self.is_slave:
            # shell.SendKeys(str_val)
        self.send_all(data, opcode, ignore=[self])


class EchoServer(ClientListMixin, Server):
    ''' Basic instance of a server, instansiating ws.Client for
    socket clients '''
    ports = (9004, 9005, )
    client_class = CommandClient



if __name__ == '__main__':
    main()
