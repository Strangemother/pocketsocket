# Forking mummy: A Speed-Oriented Change Plan

Assumes mummy is vendored into `server/src/` and becomes ours to modify.

Everything below was read out of **mummy 0.4.8** source. Line numbers refer to
that version. Verify them against whatever you vendor — the structure is stable
across 0.4.x but the line numbers will drift.

> **Read [PERFORMANCE.md](PERFORMANCE.md) first.** It establishes the measured
> baseline and, more importantly, the list of hypotheses that were already
> tested and rejected. Do not re-tune worker threads.

---

## 1. Why fork, and what it buys

The measured ceiling is ~45k round-trips/sec, and it does not respond to cores,
connections or worker threads. A single connection saturates the server. The
cause is that **all socket io runs on one thread**, and that thread does far
more syscall work per message than it needs to.

Two independent problems, and it matters that they are independent:

| problem | fix | expected |
| --- | --- | --- |
| **P1** — one io thread for the whole server | shard connections across N io threads | scales with cores |
| **P2** — ~4 syscalls + 3 epoll round trips per reply | batch and inline the write path | 2-4x on the single thread |

**P2 is much cheaper to implement than P1 and does not depend on it.** Do P2
first: it is contained within the write path, it is measurable in isolation,
and it makes P1's payoff larger because each io thread gets more efficient.

### Licence

mummy is **MIT**, author Ryan Oldenburg. Vendoring and modifying is fine.
Keep the copyright header in every vendored file and add a `NOTICE` or a
section in the root `LICENSE` recording the origin, the version forked, and
that it has been modified.

### Suggested layout

```
server/src/pocketsocketpkg/
  transport/
    LICENSE.mummy         # upstream MIT text, unmodified
    ORIGIN.md             # version forked, commit, list of our divergences
    server.nim            # was mummy.nim
    internal.nim
    common.nim
    routers.nim
    multipart.nim
    fileloggers.nim
```

Drop `zippy` (gzip for HTTP responses) and `multipart` if the HTTP side stays
minimal — they are dependencies pocketsocket does not need for a WebSocket
server, and removing them shrinks both the binary and the build.

**Keep a pristine copy of the upstream file** alongside your edits during the
port (`server.orig.nim`, gitignored) so `diff` tells you exactly what you have
changed. You will want that when a bug appears.

---

## 2. Architecture as it stands

```
                    ┌──────────────────────────────────────┐
   client sockets ──┤  io thread  (ONE, for entire server) │
                    │   selectInto(-1, readyKeys[64])      │
                    │   read  -> parse -> enqueue task     │
                    │   write <- drain global sendQueue    │
                    └───────────┬──────────────────────────┘
                                │ taskQueue + Cond
                    ┌───────────▼──────────────────────────┐
                    │  worker threads (countProcessors*10) │
                    │   run handler, call send()           │
                    │   send() -> global sendQueue         │
                    │        -> trigger(sendQueued) eventfd│
                    └──────────────────────────────────────┘
```

Key structures (`mummy.nim:88-110`):

```nim
ServerObj = object
  selector: Selector[DataEntry]        # ONE selector
  responseQueued, sendQueued, shutdown: SelectEvent
  taskQueue: Deque[WorkerTask]; taskQueueLock: Lock; taskQueueCond: Cond
  sendQueue: Deque[OutgoingBuffer]; sendQueueLock: Lock   # ONE global send queue
  websocketClaimed: Table[WebSocket, bool]
  websocketQueues: Table[WebSocket, Deque[WebSocketUpdate]]
  websocketQueuesLock: Lock
```

### What one reply message actually costs

Traced through `send()` (`:262`) and `loopForever` (`:1150`):

| # | step | syscall | source |
| --- | --- | --- | --- |
| 1 | encode header, alloc `buffer1` | — | `:271-281` |
| 2 | lock global `sendQueueLock`, append | futex (contended) | `:285-287` |
| 3 | `trigger(sendQueued)` — queue was empty, which it always is in request/response | **write(eventfd)** | `:289-290` |
| 4 | io thread returns from `selectInto` | epoll_wait return | `:1164` |
| 5 | drain queue, `updateHandle2(fd, {Read, Write})` | **epoll_ctl** | `:1252-1255` |
| 6 | next loop, Write ready → `send(buffer1)` — *header only* | **send** | `:1345` |
| 7 | next loop, Write ready → `send(buffer2)` — *payload* | **send** | `:1353` |
| 8 | fully sent → `updateHandle2(fd, {Read})` | **epoll_ctl** | `:1107-1108` |

**~5 syscalls and 3 epoll_wait round trips to deliver one small frame.**

The two that should be most surprising:

**Steps 6 and 7 are separate syscalls.** The Write branch sends *either* from
`buffer1` *or* from `buffer2`, never both:

```nim
# mummy.nim:1340
if Write in readyKey.events:
  let
    outgoingBuffer = dataEntry.outgoingBuffers.peekFirst()   # ONE buffer
    bytesSent =
      if outgoingBuffer.bytesSent < outgoingBuffer.buffer1.len:
        send(buffer1[...])          # header this time round
      else:
        send(buffer2[...])          # payload next time round
```

A 64-byte echo therefore costs a 2-byte `send()` followed by a 64-byte `send()`,
each requiring its own epoll wakeup.

**Only one `outgoingBuffer` is drained per Write event.** With N frames queued
for a connection you pay N epoll round trips, even though they could all go in
one `writev`.

---

## 3. Speed changes, ranked

### S1. Drain the whole outgoing queue with `writev` — do this first

**Expected: 2-4x on the reply path. Contained, low risk, independently
measurable.**

Replace the single-buffer Write branch with a loop that gathers every pending
buffer into an iovec and writes until `EAGAIN`.

```nim
# transport/server.nim, replacing the `if Write in readyKey.events` branch

if Write in readyKey.events:
  var iovs: array[IOV_MAX_BATCH, IOVec]     # 32 is plenty
  while dataEntry.outgoingBuffers.len > 0:
    var
      n = 0
      idx = 0
    # Gather: first buffer may be partially sent, the rest start at 0.
    for buf in dataEntry.outgoingBuffers:
      if n >= iovs.len - 1: break
      var off = if idx == 0: buf.bytesSent else: 0
      if off < buf.buffer1.len:
        iovs[n].iov_base = buf.buffer1[off].addr
        iovs[n].iov_len = csize_t(buf.buffer1.len - off)
        inc n
        off = 0
      else:
        off -= buf.buffer1.len
      if buf.buffer2.len - off > 0:
        iovs[n].iov_base = buf.buffer2[off].addr
        iovs[n].iov_len = csize_t(buf.buffer2.len - off)
        inc n
      inc idx

    let written = writev(readyKey.fd.cint, iovs[0].addr, n.cint)
    if written < 0:
      if errno == EAGAIN or errno == EWOULDBLOCK: break
      needClosing.incl(readyKey.fd.SocketHandle); break
    # Retire fully-sent buffers, leave a partial one at the head.
    var remaining = written
    while remaining > 0 and dataEntry.outgoingBuffers.len > 0:
      let head = dataEntry.outgoingBuffers.peekFirst()
      let total = head.buffer1.len + head.buffer2.len
      let need = total - head.bytesSent
      if remaining >= need:
        head.bytesSent = total
        remaining -= need
        if head.isCloseFrame: dataEntry.closeFrameSent = true
        dataEntry.outgoingBuffers.shrink(fromFirst = 1)
      else:
        head.bytesSent += remaining
        remaining = 0
  if dataEntry.outgoingBuffers.len == 0:
    server.selector.updateHandle2(readyKey.fd.SocketHandle, {Read})
```

Collapses steps 6-7 into one syscall, and N queued frames into one syscall
instead of N epoll round trips.

**Correctness notes.** `writev` is atomic with respect to ordering, so frame
order is preserved. A partial write must leave the head buffer partially
consumed — the `bytesSent` bookkeeping above handles it. Do not skip the
partial case; it will only show up under load, as corrupted frames.

**Simpler variant if you want the win without iovec bookkeeping:** concatenate
`buffer1` and `buffer2` into a single string at encode time in `send()`. That
costs one copy of the payload but removes the two-syscall split entirely, and
for payloads under a few KB the copy is far cheaper than a syscall. Measure
both — the concat version may well win for typical message sizes and is much
less code to get wrong.

### S2. Try an inline write from the worker thread

**Expected: removes 2 syscalls and a full epoll round trip from the reply path.
Medium risk — this is where you can corrupt a stream if you get it wrong.**

In `send()`, attempt to write immediately rather than always queueing.

```nim
proc send*(websocket: WebSocket, data: sink string, kind = TextMessage) =
  var encodedFrame = OutgoingBuffer()
  ...
  # Fast path: if nothing is queued for this connection and no other thread
  # holds the write lock, write straight from this worker.
  if tryAcquire(conn.writeLock):
    if conn.outgoingBuffers.len == 0:
      let n = writev(...)
      if n == total:
        release(conn.writeLock)
        return                        # done, no io-thread involvement at all
      # partial: fall through and queue the remainder
    release(conn.writeLock)
  # Slow path: queue and wake the io thread as before.
```

**The invariant that must hold:** exactly one thread may write to a given fd at
a time, and queued data must never overtake inline data. A per-connection
`writeLock` plus the `outgoingBuffers.len == 0` check gives you both — if
anything is queued, the io thread owns the stream and the worker must queue.

**Do not** attempt this without S1 in place; you want a single well-tested
gather-write routine used by both paths, not two implementations.

Note this helps *latency* and removes syscalls, but on its own it does not lift
the throughput ceiling, because the read side is still single-threaded.

### S3. Per-connection send queues

**Expected: modest alone, but a prerequisite for S4.**

`sendQueue` + `sendQueueLock` are server-wide (`:105-106`). Every worker
replying to every connection contends on one mutex, and the io thread takes the
same lock to drain. Move the queue into `DataEntry` with its own lock.

This also removes the `clientId` re-validation scan at `:1242` — with a
per-connection queue the frame is already attached to its connection.

Ordering constraint: the eventfd trigger currently fires only when the global
queue was empty. Per-connection, trigger when *that connection's* queue was
empty, and keep a lock-free "connections with pending writes" list (or an
`Atomic[bool] pendingWrite` per connection scanned on wake) so the io thread
does not have to walk every connection.

### S4. Multiple io threads via `SO_REUSEPORT`

**Expected: near-linear with cores. This is the only change that lifts the
ceiling.**

The cleanest shape, and the one that avoids almost all shared state:

```
for i in 0 ..< ioThreads:
  socket = newSocket(); setsockopt(SO_REUSEPORT); bind(); listen()
  createThread(ioThread[i], loopForever, ownSelector)
```

Each io thread has **its own** listening socket, selector, and connection set.
The kernel load-balances incoming connections across them. A connection lives
on exactly one io thread for its lifetime, so:

- no cross-thread selector access
- no shared `clientSockets` set
- `DataEntry` is owned by one thread and needs no locking

What stays shared: the worker task queue (or give each io thread its own worker
pool), and pocketsocket's client registry, which is already lock-protected.

**Watch out for:**

- `send()` from a worker must reach *the right* io thread. With S3's
  per-connection queues this is automatic — the connection knows its thread.
- **Broadcast becomes cross-thread.** `send_all` touches connections on every
  io thread. Per-connection queues plus per-thread wakeups handle it, but this
  is the case to test hardest.
- `SO_REUSEPORT` balances by hashing the 4-tuple; a benchmark opening all
  connections from one source IP will still distribute, but real-world skew is
  possible. Measure with the concurrency sweep, not a single connection.

**Sizing:** one io thread does ~38-45k round-trips/sec on the reference host.
The harness client ceiling is ~480k msg/s, so there is roughly 10x of
measurable headroom before the benchmark itself needs reworking.

### S5. Replace the hashed client id — you already have a real one

**Expected: no throughput change. Do it for correctness; it is nearly free.**

pocketsocket currently derives identity like this
([INVENTORY C2](INVENTORY.md#c2-getwebsocketuuid-is-a-hash-and-hashes-collide)):

```nim
proc getWebSocketUUID*(websocket: WebSocket): uint64 =
    result = cast[uint64](hash(websocket))
```

That hashes the whole `WebSocket` object. **mummy already assigns a unique
64-bit id at accept time** — it is simply not exported:

```nim
# mummy.nim:55-58
WebSocket* = object
  server: Server
  clientSocket: SocketHandle
  clientId: uint64        # <- private

# mummy.nim:1312, at accept
dataEntry.clientId = server.rand.next()
```

Once vendored, export it and delete the hash entirely:

```nim
WebSocket* = object
  server: Server
  clientSocket: SocketHandle
  clientId*: uint64                       # exported

proc id*(websocket: WebSocket): uint64 {.inline.} = websocket.clientId
```

```nim
# socket_tools.nim
proc getWebSocketUUID*(websocket: WebSocket): uint64 {.inline.} =
  websocket.clientId
```

This removes a hash computation from every message and every registry
operation, and removes the collision and fd-reuse concerns in one step.

**While you are there, consider making it monotonic.** `rand.next()` is fine
for uniqueness but a counter is debuggable, sorts by connection age, and makes
"is this id from this run?" answerable:

```nim
dataEntry.clientId = server.nextClientId.fetchAdd(1, moRelaxed) + 1
```

Never hand out `0` — pocketsocket already uses `0` as a sentinel in
`locked_record_client`.

### S6. Stop the `updateHandle2` churn

**Expected: 2 syscalls per message.**

Every message toggles the fd's interest set `{Read}` → `{Read, Write}` → `{Read}`
(`:1252` and `:1107`), which is two `epoll_ctl` calls.

With S2 in place most replies never register for Write at all. For the rest,
consider registering `{Read, Write}` permanently and tolerating spurious Write
wakeups — but only if you switch the selector to **edge-triggered** (`EPOLLET`),
otherwise a level-triggered always-writable socket spins the loop at 100% CPU.
Edge-triggered means you must drain reads and writes until `EAGAIN` every time,
which S1 already does for writes.

This is the highest-risk item on the list. Leave it until S1-S4 are stable and
you have a benchmark that would catch a busy-loop regression.

### S7. Small, cheap wins

| item | source | change |
| --- | --- | --- |
| Select batch size is 64 | `mummy.nim:38` | `maxEventsPerSelectLoop = 64` caps events drained per wake. Raise to 256-1024 for high connection counts. One-line change, measure it. |
| `zippy` / gzip | HTTP response path | Not needed for a WebSocket server. Dropping it removes a dependency and shrinks the binary. |
| `Table[WebSocket, ...]` keyed by object | `:107-108` | Once S5 lands, key by `uint64` instead. Cheaper hashing, smaller entries. |
| `recvBuf` growth | `DataEntry` | Check the growth policy against your expected message size; pre-sizing avoids reallocation per connection. |
| `epochTime()` on close | `:1247` | A `float64` clock call on the close path. Trivial, but it is in a hot-ish path under churn. |

---

## 4. Recommended order

Each step is independently measurable. Do not batch them — you will not know
which one moved the number.

| step | change | risk | expected |
| --- | --- | --- | --- |
| 0 | Vendor, build, prove **zero** change vs baseline | none | 0% (this is the point) |
| 1 | S5 export `clientId` | low | 0%, correctness |
| 2 | S1 gather-write / concat | low | **2-4x reply path** |
| 3 | S7 batch size, drop zippy | low | small |
| 4 | S3 per-connection queues | medium | modest, enables S4 |
| 5 | S2 inline worker write | medium | latency |
| 6 | S4 multiple io threads | high | **scales with cores** |
| 7 | S6 edge-triggered | high | 2 syscalls/msg |

**Step 0 is not optional.** Vendor the code unmodified, build it, and confirm
the benchmark reproduces the current numbers. If vendoring alone moves the
result, something about your build differs from the reference and every later
measurement is suspect.

---

## 5. Validating each step

```bash
cd server && nimble test && nimble buildPyd     # confirm: opt: speed, -d:release
cd .. && python3 benchmarks/run_all.py --tag sN-description
```

Compare against `benchmarks/results/2026-08-05-16core-release-*.txt`.

**The rows that matter:**

| section | what it tells you |
| --- | --- |
| 3, cost decomposition | `ps-nim-echo` vs `ps-ingest` — how much the outbound path costs. S1/S2 should close this gap. |
| 4, concurrency scaling | Currently flat. **If S4 works this starts sloping upward.** This is the headline test. |
| 1, latency p50/p99 | S2 should show up here first. |
| 5, fan-out | The cross-thread broadcast case. Regressions from S4 will appear here. |

Add a syscall count to your evidence — it is more diagnostic than timing:

```bash
strace -f -c -p $(pgrep -f pocketsocket-cli) &   # then run a fixed 10k messages
```

Track `sendto`/`writev`, `epoll_ctl`, `epoll_wait`, `write`. Target: **1
`writev` and 0 `epoll_ctl` per message** once S1+S2 land. That number is
unambiguous in a way that microseconds on a shared codespace are not.

---

## 6. Correctness you must not break

A rewrite of a WebSocket transport can pass a benchmark and still be wrong.
Things this code currently gets right that are easy to lose:

- **Per-connection event ordering.** `websocketClaimed` (`:483-500`) guarantees
  exactly one worker processes a connection's events at a time, in order. The
  benchmark's sentinel technique depends on it, and so does any user hook.
  Preserve this or the API changes meaning.
- **Frame ordering under partial writes.** A partially written frame must be
  completed before the next one starts. See S1's `bytesSent` handling.
- **Close handshake.** `closeFrameQueuedAt` / `closeFrameSent` sequence the
  closing handshake after queued messages. Do not let an inline write bypass it.
- **fd reuse.** `clientId` is re-checked before every queued write (`:1242`)
  precisely because a file descriptor can be recycled for a new client. Keep
  that check, or make it structurally impossible via per-connection ownership.
- **Fragmented and control frames.** Continuation frames, ping/pong, and
  close-during-fragment are all handled in the recv path. Do not simplify the
  frame parser to make the benchmark faster — that is where the CVEs live.
- **`maxMessageLen` enforcement.** Removing it is a trivially exploitable
  memory-exhaustion DoS.

Before starting, capture the current behaviour as tests: `server/tests/` has
the harness, and an [Autobahn|Testsuite](https://github.com/crossbario/autobahn-testsuite)
run against the vendored-but-unmodified build gives you a conformance baseline
to re-run after every step. That is worth the setup time — it is the only thing
that will catch a subtle framing regression.
