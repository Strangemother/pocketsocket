# Performance: What Was Done, How, and What Is Left

Two halves:

1. **[Completed work](#part-1--completed-work)** — each change, the method used
   to find it, and the measured result.
2. **[Remaining opportunities](#part-2--remaining-opportunities)** — ranked by
   expected payoff, with the evidence for each.

All figures from a 16 vCPU AMD EPYC 9V74 codespace, release build, recorded in
`benchmarks/results/2026-08-05-16core-release-*.txt`.

---

## Current baseline

| metric | value |
| --- | --- |
| Echo round-trip, 64B | 45,501 msg/s |
| Echo round-trip, 1KB | 34,184 msg/s |
| Echo round-trip, 16KB | 16,904 msg/s (264 MB/s) |
| Latency p50, 64B | 84.1 µs |
| Latency p50, 1KB | 80.0 µs |
| Inbound only (no reply) | 115,344 msg/s |
| Connections | 4,885/s |
| Startup | 20.1 ms |
| Python hook overhead | ~5 µs/message |

Versus the field on the same host: **startup 5.4-19.2x faster** than every
asyncio framework tested, **connections ~1.5x faster** than the best of them,
**throughput ~0.52x of aiohttp**.

---

# Part 1 — Completed work

## 1. The Python callback bridge (GIL acquisition)

**Symptom:** `SIGSEGV` on the first WebSocket event whenever a Python hook was
registered. The feature was completely unusable.

**Method.** Two prior investigations existed and disagreed. Rather than trust
either, the crash was reproduced with a dependency-free raw-socket client, then
the competing hypotheses were tested against the dependency's source:

- The claimed cause (a missing `nimpyEnumConvert` mixin) was falsified with one
  `grep` — nimpy ships a generic default at `nim_py_marshalling.nim:6`. A
  missing `mixin` is also a *compile-time* error and cannot segfault.
- The real cause was confirmed by crash position: the fault is inside
  `nimValueToPy` during *argument marshalling*, and it fires on `OpenEvent`
  where the payload is an empty string. Data-dependent theories were therefore
  eliminated; the thread was the variable.

mummy dispatches handlers on worker threads created with `createThread`. CPython
requires the GIL and a valid `PyThreadState` for any C-API call. nimpy does
neither.

The second investigation had the diagnosis right but concluded the fix was
impossible: `PyGILState_Ensure` appeared to need `Python.h`, which collides with
nimpy's `Py_None`. **That premise was false.** nimpy already `dlopen`s libpython
and exposes the handle as `pyLib.module`, and uses `symAddr` on it in four
places internally. The GIL functions can be resolved the same way — no header,
no collision.

**The non-obvious part:** the fix has two halves and *each half alone makes
things worse*. `PyGILState_Ensure` on its own deadlocks, because nimpy's
`exportpy` wrappers hold the GIL for the entire duration of the blocking
`run_blocking_server` call. `PyEval_SaveThread` on its own still segfaults. Only
together do they work — which is why sequential hypothesis testing produced two
negative results and a false impossibility proof.

**Implementation:** `server/src/pocketsocketpkg/gil.nim`

```nim
pyGILStateEnsure = cast[typeof(pyGILStateEnsure)](m.symAddr("PyGILState_Ensure"))
```

- Worker threads: `acquire_gil()` / `release_gil()` around the callback.
- Main thread: `save_thread()` / `restore_thread()` around `server.serve()`.
- `try`/`finally` is mandatory, not stylistic — nimpy converts a Python
  exception into a Nim exception, and a leaked GIL wedges every worker
  permanently.

**Result:** crash → working. Cost measured at **~5 µs/message**.

**Transferable lesson:** when a dependency blocks you, read its source for how
*it* solves the same problem. The technique needed was already in the library
being consulted.

---

## 2. Removing per-message debug output

**Method.** The benchmark harness captures server stdout to a file and reports
its growth per message — making log volume a *measured metric* rather than
something to eyeball.

It read **51 bytes/message**. Source:

```nim
proc send*(uuid: PyObject, etype: MessageKind, data: string): int {.exportpy.} =
  echo "-- nim - Send to: ", type(uuid), ", ", $uuid     # every single send
```

Plus `"skipping exclude uuid"` per broadcast skip, and an unconditional
`ErrorEvent` echo on every abrupt disconnect. Each is a string format plus a
`write` syscall on the hot path.

**Fix:** all hot-path logging moved behind `config.print_mode`, off by default.
`config.nim` was created so `websocket_dispatch` could read the flag without an
import cycle back through `broadcast`.

**Result:** 51 → **0 bytes/message**, asserted by the benchmark so it cannot
regress.

**Related:** `broadcast_mode` is now tested *before* taking the registry lock.
Previously every inbound message acquired a mutex to discover the feature was
disabled.

---

## 3. The debug build — the single largest win

**Method.** Accidental, and the way it surfaced is worth recording. The
standalone CLI measured **51,331 msg/s** on the pure-Nim echo path while the
Python-hosted build measured **24,527** — same Nim code, same host. A 2x gap
with no plausible explanation meant something structural differed.

Comparing compiler invocations:

```
nimble build     (CLI):  opt: speed; options: -d:release
nimble buildPyd  (.so):  opt: none (DEBUG BUILD, `-d:release` generates faster code)
```

**Cause:** `nimble build` injects `-d:release` automatically. A **custom nimble
`task` does not**. `buildPyd` is a custom task, so it silently produced an
unoptimised module. Everyone who ever ran `nimble buildPyd` or
`pip install -e .` was running a debug build.

**Fix:** `switch("define", "release")` in the `buildPyd` and `buildCliCI` tasks.
`buildPydDebug` added for when symbols are actually wanted.

**Result:**

| | debug | release | change |
| --- | --- | --- | --- |
| 64B | 24,527 | 45,501 | +86% |
| 1KB | 18,014 | 34,184 | +90% |
| 16KB | 4,803 | 16,904 | **+252%** |
| 64KB | 1,456 | 6,438 | **+342%** |
| p50 latency | 109.1 µs | 84.1 µs | −23% |
| conn/s | 3,291 | 4,885 | +48% |
| `.so` size | 899 KB | 452 KB | −50% |

Large payloads gained most — the frame-copy path with no optimiser.

**Transferable lesson:** an unexplained constant-factor gap between two builds
of the same source is a build-configuration difference until proven otherwise.
The signal was visible from the start (the two binaries had very different
sizes) and was misread as "different entry points".

---

## 4. Correcting the benchmark methodology

Three measurement bugs produced wrong numbers before they were caught. All are
now guarded in the harness.

**Client-side masking.** WebSocket client frames must be masked (per-byte XOR).
Doing it inline in Python made the *client* the bottleneck at 16KB+. Frames are
now built once via `WSClient.frame()` using a single big-integer XOR.

**Client-side syscalls.** One `sendall` + one `recv` per message caps the client
around 15-20k msg/s. The `batched()` workload packs 256 frames per syscall.

**Fictional floors.** Sending 6,000 × 64B and timing it measures `memcpy` into
the socket buffer — it all fits. One-way workloads now either use a sentinel
acknowledgement (valid because mummy drains a connection's queue in order,
`mummy.nim:483-500`) or send far past buffer capacity so backpressure dominates.

**The permanent guard:** `client_parse_ceiling()` reports how fast the harness
can parse frames with no server and no kernel — ~480k msg/s. Any result
approaching it is measuring Python, not pocketsocket. This is section 0 of every
message-path report.

---

## 5. Hypotheses that were tested and rejected

Recorded so nobody spends time re-testing them.

| hypothesis | test | outcome |
| --- | --- | --- |
| Worker-thread oversubscription is the ceiling | swept `worker_threads` 1 → 160 on 2 and 16 vCPU | **Rejected.** Completely flat. One worker performs as well as 160. |
| The thread handoff buys cross-core scaling | ran 2 vCPU vs 16 vCPU | **Rejected.** 8x cores bought ~10%. |
| More concurrent connections will scale throughput | swept 1 → 32 clients | **Rejected.** One connection already saturates; 32 is slightly *slower*. |
| `send()` taking `PyObject` costs a wrapper allocation | changed to `uint64`, re-measured | **Rejected.** Within noise. Signature kept as it is cleaner. |
| The Python/GIL bridge is the bottleneck | compared `ps-nim-echo` vs `ps-hook-echo` | **Rejected.** ~1% apart. |

---

# Part 2 — Remaining opportunities

## The ceiling: mummy has one io thread

This is the finding that governs everything else.

```
ps-nim-echo    1 client   37,246 msg/s
ps-nim-echo    2 clients  38,902
ps-nim-echo    8 clients  36,713
ps-nim-echo   32 clients  34,457
```

A single connection saturates the server. Confirmed in mummy's source, not
inferred: one `Selector` (`mummy.nim:97`) driven by one `selectInto` loop
(`mummy.nim:1164`). Worker threads only execute handlers — **every byte on every
socket passes through one thread**.

```
worker threads  -> parallel handler execution   (scales)
io thread       -> all socket read/write        (count = 1, never scales)
```

For an echo workload the handler is trivial, so the pool has nothing to
parallelise and the io thread is effectively 100% of the cost. This explains all
three rejected hypotheses above at once.

Supporting decomposition (64B, release build):

| path | rate | per message |
| --- | --- | --- |
| inbound only (`ps-ingest`) | 115,344/s | ~8.7 µs |
| inbound + hook (`ps-hook-noop`) | 65,605/s | ~15.2 µs |
| full round trip (`ps-nim-echo`) | 45,389/s | ~22.0 µs |

The outbound leg roughly doubles the cost. mummy's `WebSocket.send()` appends to
a server-wide queue and fires a `SelectEvent` to wake the io thread
(`mummy.nim:286-291`); in request/response the queue is empty every time, so
that wakeup fires on **every message** — an eventfd write plus an epoll wakeup
plus a context switch.

---

## Ranked opportunities

### 1. Multiple io threads — the only change that lifts the ceiling

**Expected: 2-8x on multi-core hosts.** Everything else is single-digit percent.

> Superseded in detail by [MUMMY_FORK.md](MUMMY_FORK.md), which assumes mummy
> is vendored and gives the concrete change plan. Note that document revises
> the priority: the **write path** (~5 syscalls per reply) is a cheaper and
> larger first win than the io-thread split, and does not depend on it.

Shard connections across N independent epoll loops, one per core, via
`SO_REUSEPORT` — each thread `accept`s and services its own connections
end-to-end with no cross-thread handoff for the common case.

This requires replacing or forking mummy's io layer. Three routes:

| route | effort | notes |
| --- | --- | --- |
| Fork mummy, add io threads | medium | Keeps HTTP, routing, framing, and mummy's well-tested frame parser. Highest value per unit effort. |
| `ws` + `asyncdispatch` | medium | Single-threaded per loop; would need multiple loops anyway to beat the current number. |
| Hand-rolled epoll | high | Full control, and you own RFC 6455 correctness forever. |

**Sizing:** one io thread does ~38k round-trips/sec here. N threads should
approach N × that until the NIC or client saturates. The harness client ceiling
is ~480k msg/s, so there is roughly **12x of measurable headroom** before the
benchmark itself needs reworking.

**Do this first, before any micro-optimisation.** At 22 µs per round trip with
~5 µs of that being Python, shaving microseconds off the bridge cannot matter
until the io thread stops being the wall.

### 2. Direct write from the worker thread

**Expected: latency improvement, no ceiling change.**

In `WebSocket.send()`, attempt a direct `write()` on the socket from the calling
worker and fall back to the queue + `SelectEvent` only on `EAGAIN`. Removes one
eventfd write, one epoll wakeup and one context switch from the reply path.

Worth doing as the **cheap probe before committing to option 1** — it tells you
how much of the outbound cost is the wakeup versus the syscall itself. But note
it cannot lift the throughput ceiling, because the *read* side remains
single-threaded.

Requires patching mummy.

### 3. Snapshot broadcast targets outside the lock

**Expected: meaningful for fan-out; see [INVENTORY C3](INVENTORY.md#c3-send_all-fans-out-while-holding-the-registry-lock).**

Fan-out currently holds the registry lock for all N sends. Evidence: inbound
rate collapses 20,535 → 5,688 msg/s going from 2 to 8 receivers while outbound
barely moves. Copy the target list under the lock, release, then send.

### 4. Remove the per-connection greeting frame

**Expected: small, but it is pure waste — see [INVENTORY C1](INVENTORY.md#c1-every-connection-receives-its-own-request-headers-as-the-first-frame).**

Every connection is sent its own request headers as an unsolicited first frame:
one frame encode plus one io-thread wakeup per connect, on the exact path the
connection benchmark measures. Also a header-leak concern.

### 5. Avoid the per-message dict allocation

**Expected: 1-2 µs/message. Do not bother until item 1 is done.**

`call_py_hook` builds a fresh `pyDict` per message with two `SetItem` calls.
Passing four positional scalars `(uuid, etype, kind, data)` would avoid the dict
entirely.

**This is a public API break** — every example and the readme use
`event['kind']` / `event['data']`. Given the hook is only ~5 µs of a ~22 µs
round trip, the win is inside measurement noise on the current architecture. Do
not spend the API breakage on it now. Revisit only if item 1 lands and the
bridge becomes a visible fraction.

### 6. Free-threaded CPython (3.13+ `--disable-gil`)

**Expected: unknown, worth measuring once available.**

`PyGILState_Ensure` remains valid and required under a free-threaded build (it
still attaches the thread), but the serialisation ceiling disappears. If item 1
lands and multiple io threads drive multiple concurrent Python callbacks, this
becomes the next wall. The bridge is already written correctly for it.

---

## How to validate any of this

```bash
cd server && ./setup.sh          # verify the hint line reads: opt: speed, -d:release
cd .. && python3 benchmarks/run_all.py --tag before
# ... make the change ...
cd server && nimble test && nimble buildPyd
cd .. && python3 benchmarks/run_all.py --tag after
```

Compare `benchmarks/results/*-before-*` against `*-after-*`. The rows that
matter for the ceiling work are **section 3 (cost decomposition)** and
**section 4 (concurrency scaling)** of the message-path report. If section 4
starts sloping upward with client count, the io-thread work is succeeding.

Do not run anything else on the host while benchmarking — client processes
already compete with the server for CPU.
