# Pocket Socket Version 2

A standalone or Python WebSocket server with zero configuration, built with Nim.

PocketSocket handles the socket lifecycle, handshakes, decoding, and pongs. You get the events and decide what your application does with them.

## Run It

### Standalone CLI

The CLI is the simplest path: run the binary from a directory containing `templates/index.html`.

Windows:

```bash
$ nim_src>dist\pocketsocket-cli.exe --run
Run
Discovering: .\nim_src\templates\index.html
Template Set. Length: 230
Serving on http://127.0.0.1:8090
TTL: 11 milliseconds, 795 microseconds, and 685 nanoseconds
```

Linux:

```bash
$ dist/pocketsocket-cli --run
Run
Discovering: /workspaces/pocketsocket-2/templates/index.html
Template Set. Length: 278
Serving on http://127.0.0.1:8090
TTL: 664 microseconds and 116 nanoseconds
```

### Python

Use the Python API when your application needs to handle events directly:

```py
import pocketsocket

address = '127.0.0.1'
port = 8090

def ingress(uuid, event_type, event):
    if event_type == 0:  # connect event
        pocketsocket.send(uuid, 1, "Howdy...")
        return
    # Broadcast the message to everyone, excluding the origin socket.
    pocketsocket.send_all(event['kind'], event['data'], uuid)


pocketsocket.hook(ingress)
pocketsocket.run_blocking_server(address, port)
```

Connect to the waiting server using HTTP or WebSockets:

    http://<address>:<port>
    ws://<address>:<port>/
    ws://<address>:<port>/ws/

## Features

+ Not async

    The PocketSocket server is synchronous under the hood. You do not need to worry about incoming socket locks or the colour of functions. Thanks to Nim and the underlying package `mummy`, sockets are threaded by default.

+ Process and thread friendly

    Run a PocketSocket server on a Python process, thread, or main loop. Messages are thread-safe.

+ Singleton-style interconnected process hook

    All processes or threads can receive from the same hook. The hook is shared at the application boundary, while each hooked function executes in its own thread. This keeps the socket layer lock-ignorant from your application's point of view.

+ It's teeny tiny and fast as bullets

    The compiled server starts in **sub-millisecond time** on average, with a small compiled footprint. See the [benchmark summary](#benchmarks) for a quick look at the numbers.

+ Unmanaged sockets

    Socket handles are managed **before your Python layer**. Your code does not need to solve handshakes, decoding, or pongs.

+ Small compiled footprint

    No dependencies and close to 1 MB when compiled.

## What You Receive

Your hook receives three values:

| Value | Meaning |
| --- | --- |
| `uuid` | The numeric identifier for the socket. |
| `event_type` | The lifecycle event: `0` connect, `1` message, `2` error, or `3` close. |
| `event` | The event payload, containing `kind` and `data` for message events. |

The hook is the one place where your application receives socket events. Return `1` to request that the current socket is closed; otherwise return `0` or nothing.

## API

Heh, the API is deliberately small:

| Function | Purpose |
| --- | --- |
| `hook(callback)` | Register the function that receives socket events. |
| `send(uuid, message_kind, message_data)` | Send a message to one socket. |
| `send_all(message_kind, message_data, origin_uuid)` | Broadcast to all sockets except `origin_uuid`. |
| `run_blocking_server(address, port)` | Start the server and block the current thread. |
| `shutdown_server()` | Stop the running server. |

Fundamentally, `hook` is the receiver for all events. Your application does not need to manage WebSocket handshakes, decoding, pongs, or socket iteration itself.

### Echo Server

Call `send` from inside the hook to echo a message back to its socket:

```py
import pocketsocket

address = '127.0.0.1'
port = 8090

def echo_receiver(uuid, event_type, event):
    pocketsocket.send(uuid, event['kind'], event['data'])


pocketsocket.hook(echo_receiver)
pocketsocket.run_blocking_server(address, port)
```

### Broadcast Server

```py
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

## Why PocketSocket?

PocketSocket is written in Nim and compiled into a standalone binary or an isolated Python extension. The server runs independently of your application code, handling the lifecycle of incoming sockets. It is self-threading and process-safe, so you can use the WebSocket stack without carrying its bookkeeping into your application.

I like WebSockets, but the underlying framework can make a simple event-driven server surprisingly fiddly. Handshakes, decoding, pongs, socket cleanup, concurrency, and process boundaries all arrive before the interesting part: deciding what a message means.

PocketSocket handles that boring layer in Nim and exposes a small set of calls. The standalone binary gives you a compact server with no Python runtime. The Python module gives you the same server core with a convenient application hook.

The goal is simple: open sockets, receive agnostic events, and keep your application logic in your own style. No async refactor required just because the transport is a WebSocket. The colour of your function stays yours.

### What the server takes care of

In many frameworks, scaling introduces several separate problems:

+ **Throughput concurrency:** iterating open sockets and running ingress routines without one slow connection holding up others.
+ **Socket floods:** controlling how much arrives through a socket before it affects the rest of the server.
+ **Process and thread overhead:** sharing messages and application state when the server runs across processes or threads.

PocketSocket moves those concerns below the Python layer. The socket handles are managed before your hook receives an event, and the hook gives you access to the significant parts without requiring a refactor around async functions.

This pattern is not unique to WebSockets; pipes, UDP, and HTTP can also hide their lifecycle behind a simpler interface. WebSockets are just unusually easy to make cumbersome. PocketSocket acts like its own small stack so the developer can work with messages rather than transport mechanics.

## Benchmarks

These are light reference numbers from Linux on x86_64. See [BENCHMARKS.md](docs/BENCHMARKS.md) for methodology and the full comparison.

| Test | Result |
| --- | --- |
| Standalone CLI startup | 0.8922 ms average, 80% under 1 ms |
| Python module startup | 1.0678 ms average, 50% under 1 ms |
| CLI versus other Python WebSocket servers | 7.8x to 34.5x faster at startup |

### Run the Benchmarks Yourself

```bash
# Run the complete suite and generate a report
./run_benchmarks.py -n 20 -o benchmark_report.txt
```

For build flags, memory notes, and other lower-level details, see [DEV_NOTES.md](docs/DEV_NOTES.md).
