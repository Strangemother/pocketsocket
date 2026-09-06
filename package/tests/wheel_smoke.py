"""Exercise the installed wheel, without importing the source-tree package."""

import importlib.metadata
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

import pocketsocket
import pocketsocket_server
from websockets.sync.client import connect


def main():
    source_package = Path(__file__).resolve().parents[1]
    assert not Path(pocketsocket.__file__).resolve().is_relative_to(source_package)
    assert not Path(pocketsocket_server.__file__).resolve().is_relative_to(source_package)
    assert pocketsocket.version().lstrip("v") == importlib.metadata.version("pocketsocket")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    code = f"""
import pocketsocket as ps
def echo(uuid, event_type, message):
    if event_type == ps.MESSAGE:
        ps.send(uuid, message['kind'], message['data'])
    return 0
ps.hook(echo)
ps.run_blocking_server('127.0.0.1', {port}, worker_threads=2)
"""
    with tempfile.TemporaryFile(mode="w+") as log:
        process = subprocess.Popen([sys.executable, "-c", code], stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 20
            while True:
                if process.poll() is not None:
                    raise RuntimeError("wheel server exited before becoming ready")
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("wheel server did not become ready")
                    time.sleep(0.02)
            with connect(f"ws://127.0.0.1:{port}/ws", compression=None, open_timeout=5) as client:
                for payload in ("", "wheel echo", "x" * 16384, b"binary echo"):
                    client.send(payload)
                    assert client.recv(timeout=5) == payload
            assert process.poll() is None
        except BaseException:
            log.seek(0)
            print(log.read(), file=sys.stderr)
            raise
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    print("Installed wheel: native import, version, Python callback, and WebSocket echo OK")


if __name__ == "__main__":
    main()