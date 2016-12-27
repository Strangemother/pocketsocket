from ws import Client
from server import Server


def main():
    server = Server(client_class=ReplyClient)
    server.start()


class ReplyClient(Client):

    def recv(self, data, opcode):
        self.send('Thank you.')


if __name__ == '__main__':
    main()
