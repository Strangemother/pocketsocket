#!/usr/bin/env python3
"""Regression check for the current no-greeting WebSocket protocol."""

import base64
import hashlib
import socket
import struct
import threading

from lib.wsclient import WSClient


def _read_frame(conn):
    header = conn.recv(2)
    length = header[1] & 0x7F
    mask = conn.recv(4)
    payload = bytearray(conn.recv(length))
    for index in range(length):
        payload[index] ^= mask[index % 4]
    return bytes(payload)


def _serve(listener):
    conn, _ = listener.accept()
    try:
        request = b""
        while b"\r\n\r\n" not in request:
            request += conn.recv(4096)
        key = request.split(b"Sec-WebSocket-Key: ", 1)[1].split(b"\r\n", 1)[0]
        accept = base64.b64encode(
            hashlib.sha1(key + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest()
        ).decode()
        conn.sendall((
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
        ).encode())
        payload = _read_frame(conn)
        conn.sendall(struct.pack("!BB", 0x81, len(payload)) + payload)
    finally:
        conn.close()


def main():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    thread = threading.Thread(target=_serve, args=(listener,))
    thread.start()
    client = WSClient("127.0.0.1", listener.getsockname()[1])
    client.send(b"first application frame")
    assert client.recv() == b"first application frame"
    client.close()
    listener.close()
    thread.join()


if __name__ == "__main__":
    main()