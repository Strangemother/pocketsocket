# Pocketsocket v2

**A standalone WebSocket server with a small Python API.**

> Standalone · Dependency-free · Zero-configuration

Pocketsocket runs the WebSocket server separately from your application. It
manages connections and protocol details, then gives your Python code events
to handle.

## On this page

- [Quick start](#quick-start)
- [Install](#install)
- [Compatibility](#compatibility)
- [Run](#run)
- [Verify a download](#verify-a-download)
- [Features](#features)
- [API](#api)
- [Examples](#examples)
- [How it works](#how-it-works)
- [Benchmarks](#benchmarks)

## Quick start

Install the Python package:

```bash
python -m pip install pocketsocket
```

Save this as `server.py`:

```python
import pocketsocket


def echo(uuid, event_type, event):
    if event_type == pocketsocket.MESSAGE:
        pocketsocket.send(uuid, event["kind"], event["data"])


pocketsocket.hook(echo)
pocketsocket.run_blocking_server()
```

Run `python server.py`, then connect a WebSocket client to
[`ws://127.0.0.1:8090/`](ws://127.0.0.1:8090/).

## Install

### Standalone CLI

Download the latest binary release from
[Releases](https://github.com/strangemother/pocketsocket/releases).

### Python

Install the package from [PyPI](https://pypi.org/project/pocketsocket/):

```bash
pip install pocketsocket
```

## Compatibility

The Python package declares Python 3.10 or newer. The current release build
matrix validates regular, GIL-enabled CPython 3.10–3.14; free-threaded CPython
is not supported.

The current CI build matrix covers:

- **Standalone CLI:** Windows x64, Linux x64 and ARM64, and macOS Intel and
  Apple Silicon.
- **Python wheels:** Linux x64 and ARM64, macOS Intel and Apple Silicon, and
  Windows x86 and x64.

Check the [release assets](https://github.com/strangemother/pocketsocket/releases)
and [PyPI](https://pypi.org/project/pocketsocket/) for the artifacts available
for a particular release.

## Run

### Standalone CLI

Available for Windows, Linux, and macOS:

```console
$ ./pocketsocket-cli --run
```

Open [http://127.0.0.1:8090](http://127.0.0.1:8090) for the web interface, or
connect with a WebSocket client:

- [ws://127.0.0.1:8090/](ws://127.0.0.1:8090/)
- [ws://127.0.0.1:8090/ws/](ws://127.0.0.1:8090/ws/)

## Verify a download

Each release includes `SHA256SUMS.txt`. In PowerShell, calculate the hash of
the downloaded executable:

```powershell
Get-FileHash .\pocketsocket-cli-*.exe -Algorithm SHA256
```

Compare the resulting `Hash` value with the matching entry in `SHA256SUMS.txt`.
A matching SHA-256 hash confirms that the downloaded file is identical to the
release asset. It does not replace antivirus scanning or code signing.

## Features

### Synchronous Python API, threaded server

You can use Pocketsocket without `async`/`await`. The server handles network
work on worker threads, while your Python callback processes the events. See
[Receiving events](#receiving-events) for callback behavior and threading
guidance.

### Managed WebSocket lifecycle

Pocketsocket handles connection handshakes, socket lifecycle, message decoding,
and ping/pong frames. Your callback handles application logic; validate
incoming data and keep callback work appropriate for your workload.

### Small footprint

- No Python package dependencies
- Compiled binary near 1 MB
- Windows CLI uses less than 4 MB of RAM while idle
- Approximate memory use:
  - Waiting socket: ~4 KB
  - Connected socket: ~40 KB

These are reference figures, not guarantees; actual usage varies by platform,
build, and workload.

## API

Pocketsocket provides a small Python API for receiving WebSocket events,
sending messages, and controlling the server. It handles the connection
lifecycle, handshakes, decoding, pongs, and socket iteration for you.

### Receiving events

Register a callback with `hook(callback)`. Pocketsocket calls it with the
socket ID, an event code, and an event dictionary:

```python
import pocketsocket


def on_event(uuid, event_type, event):
    if event_type == pocketsocket.CONNECT:
        print(f"Connected: {uuid}")
    elif event_type == pocketsocket.MESSAGE:
        print(event["kind"], event["data"])


pocketsocket.hook(on_event)
```

The callback runs on a server worker thread. Keep callback work short so it
does not tie up a worker, and synchronize application state that is shared
across threads.

The callback arguments are:

| Argument | Description |
| --- | --- |
| `uuid` | Numeric ID of the socket. |
| `event_type` | Lifecycle event code. Use the constants below instead of numeric values. |
| `event` | Dictionary with `kind` (message kind) and `data` (message payload). The payload is meaningful for message events. |

Event constants:

| Constant | Value | When it is sent |
| --- | ---: | --- |
| `pocketsocket.CONNECT` | `0` | A client connects. Return `1` to reject the connection. |
| `pocketsocket.MESSAGE` | `1` | A client sends a message. |
| `pocketsocket.ERROR` | `2` | An error occurs on the connection. |
| `pocketsocket.CLOSE` | `3` | A client disconnects. |

Return `1` from the callback to close the current connection; return `0` or
`None` to leave it open.

### Message kinds

Use these constants for the `etype` argument to `send` and `send_all`:

| Constant | Value | Message type |
| --- | ---: | --- |
| `pocketsocket.TEXT` | `0` | Text |
| `pocketsocket.BINARY` | `1` | Binary |
| `pocketsocket.PING` | `2` | Ping |
| `pocketsocket.PONG` | `3` | Pong |

### Sending and closing connections

#### `send(uuid, etype, data)`

Send a message to one connected socket. `uuid` is the socket ID, `etype` is a
message-kind constant, and `data` is the message string. Returns `0` on
success or `1` if the socket is not connected.

```python
pocketsocket.send(uuid, pocketsocket.TEXT, "Hello")
```

#### `send_all(etype, data, origin_uuid)`

Send a message to every connected socket except `origin_uuid`. Pass `None` to
broadcast to everyone. Returns `0`.

```python
# Relay a message to everyone except its sender.
pocketsocket.send_all(event["kind"], event["data"], uuid)

# Send to every connected socket.
pocketsocket.send_all(pocketsocket.TEXT, "Server announcement", None)
```

#### `close_client(uuid)`

Close the specified connection and remove it from the active client registry.

```python
pocketsocket.close_client(uuid)
```

### Starting and stopping the server

Both server functions accept the same options:

```python
pocketsocket.run_blocking_server(
    address="127.0.0.1",
    port=8090,
    worker_threads=0,
    max_message_len=64 * 1024,
    max_body_len=1024 * 1024,
    tcp_no_delay=True,
)
```

| Option | Default | Description |
| --- | --- | --- |
| `address` | `"127.0.0.1"` | Address to bind the server to. |
| `port` | `8090` | Port to listen on. |
| `worker_threads` | `0` | Worker count. `0` uses the server's default based on the available processors; set a positive value to choose a count explicitly. |
| `max_message_len` | `65536` | Maximum accepted WebSocket message size, in bytes. |
| `max_body_len` | `1048576` | Maximum accepted HTTP request body size, in bytes. |
| `tcp_no_delay` | `True` | Configure TCP_NODELAY for the server's sockets. |

- `run_blocking_server(...)` serves on the calling thread and blocks until the
  server stops.
- `run_nonblocking_server(...)` starts the server on a background thread and
  returns once it is ready.
- `shutdown_server()` stops the running server.
- `is_server_running()` returns `True` if the server is running, otherwise
  `False`.
- `get_port()` returns the bound port, or `0` when no server has been created.

Use one server instance at a time.

### Server modes

These options are disabled by default and can be enabled or disabled with a
boolean:

```python
pocketsocket.set_broadcast_mode(True)
pocketsocket.set_echo_mode(True)
pocketsocket.set_print_mode(True)
```

| Function | Effect |
| --- | --- |
| `set_broadcast_mode(mode)` | Automatically forwards each inbound message to every other client, without requiring the Python callback to relay it. |
| `set_echo_mode(mode)` | Automatically reflects each inbound message back to its sender. |
| `set_print_mode(mode)` | Enables per-event logging. Logging is off by default. |

These modes do not replace the event hook; the hook still receives events.

### Package version

`version()` returns the installed package version as a string, prefixed with
`v`:

```python
print(pocketsocket.version())
```

## Examples

### Echo server

Call `send` from inside the hook to echo a message back to its socket:

```python
import pocketsocket

address = '127.0.0.1'
port = 8090

def echo_receiver(uuid, event_type, event):
    pocketsocket.send(uuid, event['kind'], event['data'])


pocketsocket.hook(echo_receiver)
pocketsocket.run_blocking_server(address, port)
```

### Broadcast server

```python
import pocketsocket

address = '127.0.0.1'
port = 8090

def broadcast_receiver(uuid, event_type, event):
    if event_type == 0:  # connect event
        pocketsocket.send_all(1, f"Connected:{uuid}", uuid)
        return
    pocketsocket.send_all(event['kind'], event['data'], uuid)


pocketsocket.hook(broadcast_receiver)
pocketsocket.run_blocking_server(address, port)
```

## How it works

The Python package uses a compiled native extension written in
[Nim](https://nim-lang.org/) and the `nim-mummy` server. The server manages
WebSocket connections and protocol events; Python receives connect, message,
error, and close events through one callback and can send messages through the
API.

This keeps socket lifecycle and protocol handling in the server while leaving
application behavior in Python.

## Benchmarks

These are startup reference numbers from Linux on x86_64. They do not measure
message throughput or maximum connection capacity, and results vary by
hardware and workload. See [BENCHMARKS.md](docs/BENCHMARKS.md) for methodology
and the full comparison.

| Test | Result |
| --- | --- |
| Standalone CLI startup | 0.8922 ms average, 80% under 1 ms |
| Python module startup | 1.0678 ms average, 50% under 1 ms |
| CLI versus other Python WebSocket servers | 7.8x to 34.5x faster at startup |

### Run the benchmarks yourself

```bash
# Run the complete suite and generate a report
./run_benchmarks.py -n 20 -o benchmark_report.txt
```

For build flags, memory notes, and other lower-level details, see
[DEV_NOTES.md](docs/DEV_NOTES.md).
