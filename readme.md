<div markdown=1 align="center">

# Pocketsocket v2

A standalone dependency-free zero-configuration WebSocket server for CLI or Python.

---

</div>


Pocketsocket _acts_ like its own stack. It handles itself, and the websocket process. With Pocketsocket you can implement websockets without thinking about it.

## Install It

<table border="0" width="100%">
<tr>
<td width="50%">

### Standalone

Download the latest binary release from [Releases](https://github.com/strangemother/pocketsocket-2/releases)


</td>
<td width="50%">
    
### Python

Or grab from [PyPi](https://pypi.org/project/pocketsocket/):

```bash
$ pip install pocketsocket
```

</td>
</tr>
</table>

## Run It

### Standalone CLI

Compiled for Windows, Linux, and MacOS:

```bash
$ ./pocketsocket-cli --run 
Run
Discovering: /workspaces/pocketsocket-2/server/templates/index.html
Template Set. Length: 278
Serving on http://127.0.0.1:8090
TTL: 664 microseconds and 116 nanoseconds
```

Navigate to [http://127.0.0.1:8090](http://127.0.0.1:8090) for the web interface, or connect with a WebSocket client to [ws://127.0.0.1:8090/](ws://127.0.0.1:8090/) (or [ws://127.0.0.1:8090/ws/](ws://127.0.0.1:8090/ws/) to be more explicit).


### Python

Ensure you have the latest version of pocketsocket installed, then run the following code:

```py
import pocketsocket

def ingress(uuid: str, event_type: int, event: dict):
    if event_type == 0:  # new connect event
        pocketsocket.send(uuid, 1, "Howdy...")
        return
    # Broadcast the message to everyone
    # excluding the origin socket.
    pocketsocket.send_all(event['kind'], event['data'], uuid)

# Ready to go.
pocketsocket.hook(ingress) 

address = '127.0.0.1'
port = 8090
pocketsocket.run_blocking_server(address, port) 
```

And you're ready to go. Connect to the waiting server using http or websockets.
    
    http://<address>:<port>
    ws://<address>:<port>/
    ws://<address>:<port>/ws/

PocketSocket handles the socket lifecycle, handshakes, decoding, and pongs. Your code doesn't.


## Verify a download

Each release includes `SHA256SUMS.txt`. In PowerShell, calculate the hash of the
downloaded executable:

```powershell
Get-FileHash .\pocketsocket-cli-*.exe -Algorithm SHA256
```

Compare the resulting `Hash` value with the matching entry in `SHA256SUMS.txt`.
A matching SHA-256 hash confirms that the downloaded file is identical to the
release asset. It does not replace antivirus scanning or code signing.


## Features

+ Not async

    The PocketSocket server is synchronous under the hood. You do not need to worry about incoming socket locks or the colour of functions. Thanks to Nim and the underlying package `mummy`, sockets are threaded by default.

+ Process and thread friendly

    Run a PocketSocket server on a Python process, thread, or main loop. Messages are thread-safe.

+ Singleton-style interconnected process hook

    All processes or threads can receive from the same hook. You don't need to worry about socket locks.
    
    - Lock Ignorant: GIL is handled before the `hook` function is called.
    - Thread Safe: One epoll thread handles all incoming sockets. 
    
+ It's quick

    The compiled server starts in **sub-millisecond time** on average, with a small compiled footprint. See the [benchmark summary](#benchmarks) for a quick look at the numbers.


+ Unmanaged sockets

    Socket handles are managed **before your python layer**. Your code does not need to solve any handshakes, decoding, or pongs.

    Ignore:

    - marshalling or unmarshalling
    - socket management 
    - lifecycle handling
    - pongs and keep-alives
    - locks or threading issues
    - flooding, throughput, and concurrency issues
    
    Pocketsocket handles all of this for you. Your code needs one hook function.

+ Tiny footprint:

    - No dependencies.
    - Small Binary: Near 1mb of code when compiled.
    - Minimal RAM usage: cli (windows) uses less than 4mb of RAM when idle.
    - Low memory overhead: 
        - A waiting socket consumes ~4kb of memory. 
        - A connected socket consumes ~40kb of memory. 
    - Fast: The server starts in sub-millisecond time on average.
    - Scalable: The server can handle thousands of concurrent connections with minimal overhead.


## API

The API is deliberately small:

| Function | Purpose |
| --- | --- |
| `hook(callback)` | Register the function that receives socket events. |
| `send(uuid, message_kind, message_data)` | Send a message to one socket. |
| `send_all(message_kind, message_data, origin_uuid)` | Broadcast to all sockets except `origin_uuid`. |
| `run_blocking_server(address, port)` | Start the server and block the current thread. |
| `shutdown_server()` | Stop the running server. |

Fundamentally, `hook` is the receiver for all events. Your application does not need to manage WebSocket handshakes, decoding, pongs, or socket iteration itself.


```py
import pocketsocket

def my_hook_func(uuid, event_type, data):
    ...
    return 0

pocketsocket.hook(my_hook_func)
pocketsocket.close_remove_client(uuid)
pocketsocket.send(uuid, message_kind, message_data)
pocketsocket.send_all(message_kind, message_data, origin_uuid)
pocketsocket.run_blocking_server(address, port)
pocketsocket.shutdown_server()
```

### Hook Event Data

Your hook receives three values:

| Value | Meaning |
| --- | --- |
| `uuid` | The numeric identifier for the socket. |
| `event_type` | The lifecycle event: `0` connect, `1` message, `2` error, or `3` close. |
| `event` | The event payload, containing `kind` and `data` for message events. |

The hook is the one place where your application receives socket events. 

- Return `1` to request that the current socket is closed
- return `0` or nothing to keep the socket open.

## Examples

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


## How does it Work

Pocketsocket is written in [nim-lang](https://nim-lang.org/), pre-compiled into an isolated `.pyd`. The Pocketsocket server runs independently of your python code, handling the life-cycle of incoming sockets. It's self-threading and process-safe, allowing you to leverage the Websocket stack without handling any of it.


1. Built on-top of nim-mummy server, and its websocket tooling
2. Pocketsocket runs isolated and independent of your python code
3. It exposes a single ingress hook, and some send methods

**Why is it built this way?**

I love websockets, but the underlying framework can be a hassle to functionalize correctly. The wider issues are solved (ingress management), but micro-challenges severely limit scalability.

In many frameworks within the python eco-system some issue occur when upscaling:

+ Throughput concurrency

    After a few hundred connections, most framework struggle to iterate the open sockets.

+ Socket floods

    Guarding against flooding is a challenge when python extrapolates the underlying pipe and socket iteration stages. Notably, managing _how much_ comes through a socket isn't always a choice. Compound that with many messages, a single socket can block hundreds of others.

+ Overhead

    Ingress routines do take time and memory. All sockets need allocating and this also takes memory. In addition larger solutions need processes or threading, and thus a router and shared memory space.
    When scaling horizontal, memory sharing and concurrency through the pipes becomes a challenge.

+ _The colour of a function_

    Initially I considered async as the next step to solve these challenges, but with that we change the colour of functions and correctly overloading each process is overhead.

**What we actually want**

+ Offload the boring, allow access to the significant events.
+ Concurrency management (many sockets), and an isolated error stack.
+ Zero barriers, no effort initial steps
+ ability to scale horizontal or vertical **without a refactor**

Essentially I want to _open sockets_ and just receive agnostic events. My internal framework does _whatever I want to do_; the websockets are irrelevant.

---

This solution absolutely exists for other protocols - for example _pipes_, _UDP sockets_, HTTP are all stackless (you don't need to manage the socket life-cycle.) and they will scale absolutely.

However websockets still has its limits when it comes to implementation. I maintain it's because Websockets are a hassle to scale.

---

Pocketsocket _acts_ like its own stack. It handles itself, and the websocket process. With Pocketsocket you (the developer) can implement websockets without thinking about it.


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
