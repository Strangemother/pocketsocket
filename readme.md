# Pocket Socket Version 2

Zero config websocket implementation for standalone and python implementation.

Standalone:

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
@Strangemother ➜ /workspaces/pocketsocket-2 (main) $ dist/pocketsocket-cli --run 
Run
Discovering: /workspaces/pocketsocket-2/templates/index.html
Template Set. Length: 278
Serving on http://127.0.0.1:8090
TTL: 664 microseconds and 116 nanoseconds
```

Python:

```py
import pocketsocket

def ingress(uuid, etype, event):
    if etype == 0: # connect event
        pocketsocket.send(uuid, 1, "Howdy...")
        return
    # broadcast the message to everyone, excluding the origin socket
    pocketsocket.send_all(event['kind'], event['data'], uuid)


# Add a function or method to run.
pocketsocket.hook(ingress)
# start the server
pocketsocket.run_blocking_server('127.0.0.1', port=8090)
```

That's everything. Connect to the waiting server using http or websockets.

    http://127.0.0.1:8090
    ws://127.0.0.1:8090/
    ws://127.0.0.1:8090/ws/


## Features

+ Not Async!

    The pocketsocket server is sync under the hood. So you don't need to worry about incoming socket locks or the colour of functions. Thanks to nim and the underlying package `mummy`, sockets are threaded by default.

+ Process and Thread executable:

    Run a pocketsocket server on a python Process, Thread, or main loop. Messages are thread-safe.

+ _Singleton style_ Interconnected process hook (lock-ignorant)

    All processes or thread can receive from the same hook. Threading occurs on execution of the hooked function.

+ It's frickin quick:

    Compiled in nim to python as a c-like asset, it's fast as a bullet. The primary server will start in **less than 1 millisecond** on average. See [BENCHMARKS.md](BENCHMARKS.md) for detailed performance metrics.

+ Unmanaged sockets!

    Socket handles are managed **before your python layer**. Your code does not need to solve any handshakes, decoding, or pongs.

+ Tiny tiny tiny:

    No dependencies, Near 1mb of code when compiled.



## API

Heh, It's almost childs-play:

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


Fundamentally the `pocketsocket.hook` function is the receiver for all events.


### An Echo Server:

You can create an echo server py calling functions within the hook:

```py
import pocketsocket

def echo_receiver(uuid, event_type, data):
    pocketsocket.send(uuid, event_type, data)


pocketsocket.hook(echo_receiver)

pocketsocket.run_blocking_server(address, port)
```


### A Broadcast Server

```py
import pocketsocket

def broadcast_receiver(uuid, event_type, data):
    if etype == 0: # connect event
        pocketsocket.send_all(1, f"Connected:{uuid}", uuid)
        return
    # Send the message to everyone
    pocketsocket.send_all(event['kind'], event['data'], uuid)

pocketsocket.hook(broadcast_receiver)

pocketsocket.run_blocking_server(address, port)
```


## How does it Work

Pocketsocket is written in nim-lang, pre-compiled into an isolated `.pyd`. The Pocketsocket server runs independently of your python code, handling the life-cycle of incoming sockets. It's self-threading and process-safe, allowing you to leverage the Websocket stack without handling any of it.


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

Therefore Pocketsocket _acts_ like its own stack. It handles itself, and the websocket process. With Pocketsocket you (the developer) can implement websockets without thinking about it.


---

## Dev Notes


    # Compile on Windows:
    nim c --app:lib --out:mymodule.pyd --threads:on --tlsEmulation:off --passL:-static mymodule
    # Compile on everything else:
    nim c --app:lib --out:mymodule.so --threads:on mymodule


### Memory Leak for incoming sockets

All sockets leak for ingress. With `-d:useMalloc` the leak is 4KB. Without the switch, the leak is near `~40KB`.

#### Issue:

    https://github.com/nim-lang/Nim/issues/24693
    https://github.com/nim-lang/Nim/pull/24701
    https://github.com/nim-lang/Nim/issues/22510

#### Solution

Partial fix until Nim 2.0 is changed will reduce the overhead:

        --mm:arc
        -d:useMalloc


## Benchmarks

Pocketsocket is exceptionally fast. The server starts in **sub-millisecond time** (< 1ms average).

### 🚀 Quick Start - Run All Benchmarks

```bash
# Run complete benchmark suite and generate a report
./run_benchmarks.py -n 20 -o benchmark_report.txt
```

This will:
- ✓ Benchmark the standalone CLI binary
- ✓ Benchmark the Python module
- ✓ Compare against other WebSocket servers (websockets, Tornado, aiohttp, FastAPI)
- ✓ Generate a comprehensive report

### Individual Benchmarks

**Startup Time:**
```bash
# Benchmark the standalone CLI binary
python3 benchmarks/benchmark.py -n 20

# Benchmark the Python module
python3 benchmarks/benchmark_python_module.py -n 20

# Compare against other WebSocket servers
python3 benchmarks/benchmark_comparison.py -n 10
```

**Connection Throughput:**
```bash
# Test WebSocket connection establishment
python3 benchmarks/benchmark_connections.py -n 5 -c 100

# Sequential connections only
python3 benchmarks/benchmark_connections.py --sequential-only -n 10 -c 200

# Concurrent connections only
python3 benchmarks/benchmark_connections.py --concurrent-only -n 5 -c 100
```

For detailed benchmark results and methodology, see [BENCHMARKS.md](BENCHMARKS.md).

### Latest Results

**Standalone CLI (50 iterations):**
- Average: 0.80ms
- Median: 0.80ms
- 94% of startups under 1ms

**Python Module (20 iterations):**
- Average: 1.07ms
- Median: 0.99ms
- 50% of startups under 1ms

**Comparison to Other Servers:**
Pocketsocket is **7.8-34.5x faster** than other popular Python WebSocket servers (websockets, Tornado, aiohttp, FastAPI). See [BENCHMARKS.md](BENCHMARKS.md) for detailed comparison.