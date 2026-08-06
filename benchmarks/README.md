# pocketsocket benchmarks

```
benchmarks/
  bench_startup.py       cold start: spawn -> accepting, and Nim-side TTL
  bench_message_path.py  the steady-state message path, with cost decomposition
  bench_compare.py       pocketsocket vs websockets / tornado / aiohttp / uvicorn
  run_all.py             runs all three, writes dated reports to results/
  lib/                   shared client, harness, server definitions, workloads
  results/               generated reports
  archive/               the pre-2026-08 suite, kept for historical reference
```

## Running

```bash
python3 benchmarks/run_all.py                 # full suite -> results/
python3 benchmarks/run_all.py --quick         # ~5x faster, indicative only
python3 benchmarks/run_all.py --tag postfix   # label the output files

python3 benchmarks/bench_message_path.py      # or run one suite directly
python3 benchmarks/bench_compare.py -o /tmp/compare.txt
```

Requires a built module (`nimble buildPyd`). `bench_compare.py` additionally
needs the servers it compares against; it silently skips any that are missing:

```bash
pip install websockets tornado aiohttp fastapi uvicorn
```

---

## Methodology

These notes exist because most of them were learned the hard way, by producing
numbers that turned out to be measuring the wrong thing.

### The client must not be the bottleneck

All load is generated with raw blocking sockets and a hand-rolled RFC 6455
framer (`lib/wsclient.py`). An asyncio client library becomes the limiting
factor well before the server does, at which point every server under test
looks identical -- because you are benchmarking the client.

Three specific traps:

* **Masking cost.** Client-to-server frames must be masked, which is a per-byte
  XOR. Doing that in a Python comprehension inside the timed loop caps the
  client at a few thousand messages/second on 16KB payloads. Frames are built
  once via `WSClient.frame()` and reused, using a single big-integer XOR rather
  than a byte loop.

* **Syscall cost.** One `sendall()` plus one `recv()` per message is two
  syscalls per message on the client. On a small host that alone caps the
  measurement around 15-20k msg/s. The `batched()` workload concatenates N
  frames into one `sendall()` and parses many frames out of each `recv()`.

* **Client GIL.** Concurrent load uses `multiprocessing`, not threads. A
  multi-threaded Python client contends on its own GIL, which shows up in the
  results looking exactly like server-side contention.

`bench_message_path.py` section 0 reports `client_parse_ceiling()`: how fast the
client can parse frames with no server and no kernel involved. **Any throughput
figure approaching that number is measuring Python, not pocketsocket.** On the
reference host it is ~800k msg/s at 64B, comfortably above anything measured.

### A workload is only complete when the server says so

Fire-and-forget send rates measure the kernel socket buffer, not the server.
Sending 6,000 x 64B and timing it just times `memcpy` into a socket buffer that
swallowed the lot.

Two acknowledgement strategies are used:

* **Round-trip** -- every message is acknowledged by its reply. Used wherever
  the server replies per message.
* **Sentinel** -- for one-way modes, a trailing `__PING__` that the server
  *does* reply to. This is only valid because mummy claims a websocket and
  drains its queue in order (`mummy.nim:483-500`), so the sentinel reply proves
  every preceding message was handled. It must never be used against a mode
  that replies to every message, or the first `recv()` returns that mode's
  first echo instead of the sentinel.

`send_only()` has no acknowledgement available at all and is therefore an
**upper bound**, not a measurement. It is used only for `ps-ingest`, and only
with a volume far exceeding the socket buffers so backpressure dominates.

### Server stdout goes to a file, never a pipe

An unread `subprocess.PIPE` fills at 64KB and silently blocks the server
mid-benchmark. `ServerProcess` captures to a temp file, which doubles as the
measurement for hot-path logging volume.

### Warmup

Every workload sends a couple of hundred messages before timing. The first
Python callback on each mummy worker thread allocates a `PyThreadState` via
`PyGILState_Ensure` -- a one-time per-thread cost that would otherwise land in
the samples.

---

## Interpreting the message path results

`bench_message_path.py` runs the same workload through progressively more
expensive paths so the costs separate cleanly:

| mode | what it exercises |
| --- | --- |
| `ps-ingest` | framing only; message parsed and dropped |
| `ps-nim-echo` | Nim reflects to sender; **no Python in the message path** |
| `ps-nim-broadcast` | Nim fans out to all others; no Python |
| `ps-hook-noop` | Python callback fires, sends nothing |
| `ps-hook-echo` | Python callback + `ps.send()` -- the real-world path |
| `ps-hook-broadcast` | Python callback + `ps.send_all()` |

The single most useful comparison is **`ps-nim-echo` vs `ps-hook-echo`**. If
they land close together, the Python bridge is not the limiting factor and
optimising it further is wasted effort.

### One-way vs round-trip

`ps-ingest` and `ps-hook-noop` are one-way: one thread handoff per message
(io thread -> worker). `ps-nim-echo` and `ps-hook-echo` are round trips and add
the outbound path, a second handoff back to the io thread. Do not compare a
one-way row against a round-trip row and call the difference "Python overhead".

### Build the module with -d:release before measuring anything

`nimble build` injects `-d:release` automatically. A custom nimble `task` does
not. `buildPyd` is a custom task, so for a long time it silently produced an
unoptimised extension module -- worth **~2x throughput** and half the binary
size. It is fixed now, but check the compiler hint if a number looks wrong:

```
Hint: mm: arc; threads: on; opt: speed; options: -d:release   <- correct
Hint: mm: arc; threads: on; opt: none (DEBUG BUILD, ...)      <- do not measure this
```

`nimble buildPydDebug` exists when you actually want an unoptimised build.

### Architecture context

mummy has exactly **one io thread**: a single `Selector` (`mummy.nim:97`)
driven by a single `selectInto` loop (`mummy.nim:1164`). Worker threads only
execute handlers -- every byte read from or written to every socket passes
through that one thread.

```
worker threads  -> parallel handler execution   (scales)
io thread       -> all socket read/write        (count = 1, does not scale)
```

For an echo workload the handler is trivial, so the worker pool has nothing to
parallelise and the io thread is effectively 100% of the cost. Measured on
16 vCPU with a release build, a **single connection already saturates the
server** at ~37k round-trips/sec, and 32 concurrent connections produce no more
throughput than one.

This was tested rather than assumed. The original hypothesis -- that mummy's
per-message thread handoff is a cost that buys cross-core parallelism -- is not
supported: 8x the cores changed nothing, and `worker_threads` is flat from 1 to
160. Neither is a lever for this workload.

Anything that needs to beat that ceiling requires **multiple io threads**, e.g.
`SO_REUSEPORT` with one epoll loop per core. Removing the worker handoff alone
would improve latency but not the ceiling, because the read side stays
single-threaded.

Where pocketsocket wins decisively is **startup** (~20 ms vs 108-385 ms) and
**connection establishment** (~4,900/s, ahead of every asyncio server tested),
because there is no framework import graph to walk.

---

## Reference hosts

Results in `results/` were produced on two GitHub codespaces:

| tag | host | notes |
| --- | --- | --- |
| `postcleanup` | 2 vCPU, 8 GB | debug-build module, understated |
| `16core` | 16 vCPU AMD EPYC 9V74, 62 GB | debug-build module, understated |
| `16core-release` | 16 vCPU AMD EPYC 9V74, 62 GB | **current, use these** |

Only `16core-release` reflects an optimised build. The earlier two are kept
because the deltas between them are still informative, but do not quote their
absolute figures.

Running on both host sizes mattered: the 2 vCPU numbers were ambiguous because
the client competed with the server for CPU, and conclusions drawn from them
turned out to be wrong once there was headroom. If you only have a small host,
treat concurrency scaling as shape-only and trust the latency percentiles and
the relative costs between modes instead.

The two hosts are different hardware, not just different core counts -- the
16 vCPU machine is roughly 1.5x faster per core. Compare within a run, not
across runs.

---

## Archive

`archive/` holds the previous suite. Those scripts drive the module via
`import pocketsocket; pocketsocket.hook(...)`. That import path was broken for
a period when `python/pocketsocket/__init__.py` was empty (from commit
`bfb6042` until it was restored), so the committed `*_results.txt` files in
that folder could not be reproduced at the time this suite was written, and
should be treated as historical only.
