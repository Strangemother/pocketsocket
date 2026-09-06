"""Wire-level regression checks against the locally built native extension."""

import concurrent.futures
import http.client
import unittest

from lib.harness import HOST, PYTHON_PKG, ServerProcess, free_port
from lib.servers import pocketsocket_code
from lib.wsclient import WSClient


class WritePathTests(unittest.TestCase):
    def exercise_connection(self, port, client_number):
        payloads = [b""] + [
            (f"{client_number}:{index}:".encode() + b"x" * size)
            for index, size in enumerate((1, 64, 125, 126, 1024, 16384, 65000) * 8)
        ]
        with WSClient(HOST, port, timeout=10) as client:
            frames = []
            for index, payload in enumerate(payloads):
                opcode = 1 if index % 2 else 2
                frame = WSClient.frame(payload)
                frames.append(bytes([0x80 | opcode]) + frame[1:])
            client.send_frame(b"".join(frames))
            for index, expected in enumerate(payloads):
                client._fill(2)
                self.assertEqual(client.buf[0], 0x81 if index % 2 else 0x82)
                self.assertEqual(client.recv(), expected)
            close_frame = WSClient.frame(b"")
            client.send_frame(b"\x88" + close_frame[1:])
            client._fill(2)
            self.assertEqual(client.buf[0], 0x88)
            self.assertEqual(client.recv(), b"")

    def test_ordered_echoes_on_concurrent_connections(self):
        for mode in ("ps-nim-echo", "ps-hook-echo"):
            with self.subTest(mode=mode):
                port = free_port()
                server = ServerProcess(
                    pocketsocket_code(mode, PYTHON_PKG, HOST, port), port,
                )
                try:
                    connection = http.client.HTTPConnection(HOST, port, timeout=10)
                    try:
                        bodies = []
                        for headers in ({}, {"Connection": "close"}):
                            connection.request("GET", "/", headers=headers)
                            response = connection.getresponse()
                            self.assertEqual(response.status, 200)
                            body = response.read()
                            self.assertEqual(len(body), int(response.getheader("Content-Length")))
                            bodies.append(body)
                        self.assertEqual(bodies[0], bodies[1])
                        self.assertTrue(response.will_close)
                    finally:
                        connection.close()
                    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                        futures = [executor.submit(self.exercise_connection, port, index)
                                   for index in range(4)]
                        for future in futures:
                            future.result(timeout=30)
                    self.assertTrue(server.alive(), server.tail())
                finally:
                    server.stop()
                    server.cleanup()


if __name__ == "__main__":
    unittest.main()