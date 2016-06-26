#!/usr/bin/python
# simple example to talk to the server

def main():
    from websocket import create_connection
    ws = create_connection("ws://192.168.1.104:8004/")
    print "Sending 'Hello, World'..."
    ws.send("Hello, World")
    print "Sent"
    print "Receiving..."
    result = ws.recv()
    print "Received '%s'" % result
    # ws.close()

