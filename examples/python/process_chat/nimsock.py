"""Run pocketsocket on a new process, bind the server hook to a function to
broadcast through server send all.
"""

import os
import time
from threading import Thread
from multiprocessing import Process

from pocketsocket import pocketsocket_server as pocketsocket

## Prints twice. for each Process
# print(os.getpid(), dir(pocketsocket))

clients = {}

def example(uuid, etype, event):
    print(os.getpid(), 'Example hook recv', uuid, etype, event)

    if etype == 0:
        # connect

        clients[uuid] = {}

    broadcast(etype, event, uuid)
    return 4


pocketsocket.hook(example)


def broadcast(etype, event, uuid):
    print('-- py - Sending to all - from ', uuid)
    pocketsocket.send_all(event['kind'], event['data'], uuid)


def run(ip, port):
    print(os.getpid(), ' -- Running server')
    pocketsocket.run_blocking_server(ip, port)


if __name__ == '__main__':
    p = Process(target=run, args=('127.0.0.1', 8090))
    p.start()
    p.join()
