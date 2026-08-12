# Cleanup Inventory

A literal list of things to remove or change, with the reason and a suggested
fix for each.

Verified against the tree on **2026-08-09**. Line numbers are real. Every
"unused"/"unreachable" claim below was checked with `grep` across `server/src`
and `server/tests`, not assumed.

Severity key:

| | meaning |
| --- | --- |
| **A** | Actively harmful — misleads readers, or breaks/silently corrupts something |
| **B** | Dead weight — safe to delete, costs nothing but confusion |
| **C** | Wart — works, but is surprising or fragile |

---

## A1. `service_orig.nim` — a working copy of the segfault bug

**File:** `server/src/pocketsocketpkg/service_orig.nim` (272 lines — the largest
file in the package)

**Reason:** Orphaned. Nothing imports it:

```
$ grep -rn "import.*service_orig" src/ tests/   ->   0 results
```

It is a pre-refactor snapshot of `service.nim` and it still contains the
**original, broken** `call_py_hook` — the one with no GIL acquisition that
segfaults the moment a WebSocket event fires:

```nim
# service_orig.nim:91
proc call_py_hook(websocket: WebSocket, event: WebSocketEvent, message: Message): int =
  if pyHook != nil:
    let info:PyObject = pyHook.callObject(cast[uint64](hash(websocket)), event, message)
```

This is the single most dangerous file in the repository. It is the exact code
a reader would copy if they were looking for "how does the hook work", and it
is guaranteed to crash. It also carries its own stale `clientSheet`, which is
the bug that made `send()` a silent no-op.

**Fix:** Delete it. It is in git history if anyone needs it.

```bash
git rm server/src/pocketsocketpkg/service_orig.nim
```

---

## A2. Duplicate hook invocation on socket drop

**File:** `server/src/pocketsocketpkg/broadcast.nim:117-123`

**Reason:** When a hook returns `1` ("drop this socket"), the handler closes
the socket, removes the client, and then calls the hook **again**:

```nim
  if infoInt == 1:
    if config.print_mode:
      echo "Drop socket ", websocket
    websocket.close()
    locked_remove_client(websocket)
    discard hook.call_py_hook(websocket, event, message)   # <- third call
```

For a `MessageEvent` the hook has already been called once at line 99. The
client is then handed the *same* event a second time, after its connection has
already been closed and deregistered. Any hook that counts messages, appends to
a log, or forwards to a queue will double-count. A hook that calls
`ps.send(uuid, ...)` on that uuid will fail silently, because the uuid was just
removed from the registry.

**Fix:** Drop the trailing call. The close path should not re-enter user code;
the `CloseEvent` that mummy dispatches is the correct notification.

```nim
  if infoInt == 1:
    if config.print_mode:
      echo "Drop socket ", websocket
    websocket.close()
    locked_remove_client(websocket)
```

**Test to add:** a hook returning `1` should be invoked exactly once per event.

---

## A3. Benchmark harness points at a path that no longer exists

**File:** `benchmarks/lib/harness.py:16`

```python
PYTHON_PKG = os.path.join(REPO_ROOT, "python")     # /workspaces/.../python
```

**Reason:** The repo reorganisation moved the Python package to `package/`.
`REPO_ROOT/python` does not exist:

```
$ ls python
ls: cannot access 'python': No such file or directory
```

The benchmarks still run — but only by accident. Every generated server does
`sys.path.insert(0, PYTHON_PKG)` with a non-existent directory, so the insert
is a no-op, and `import pocketsocket` falls through to the **pip editable
install**. On this machine that happens to resolve back to
`package/pocketsocket/__init__.py`, so it works.

On any machine without the editable install, or with a *different* version
installed, the benchmarks will either fail or — much worse — silently measure a
different build than the one you just compiled. That is precisely the class of
error that produced the debug-build mistake.

**Fix:** Point it at the real location and make the import explicit rather than
incidental.

```python
PYTHON_PKG = os.path.join(REPO_ROOT, "package")
```

Then add a guard in `harness.py` so a mismatch is loud rather than silent:

```python
def assert_local_module():
    import subprocess, sys
    out = subprocess.check_output(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r); import pocketsocket; print(pocketsocket.__file__)" % PYTHON_PKG],
        text=True).strip()
    if not out.startswith(PYTHON_PKG):
        raise RuntimeError(f"benchmarks would measure {out}, not {PYTHON_PKG}")
```

---

## A4. Template path is relative to the caller's working directory

**Files:**
- `server/src/pocketsocketpkg/service.nim:89` — `submodule.setLoadedTemplate("./server/templates/index.html")`
- `server/src/pocketsocketpkg/ingress.nim:45` — `getCachedLocalFileContents("./server/templates/index.html")`

**Reason:** Both hardcode a path relative to the process working directory, and
that path now assumes you launched from the repository root. Previously it was
`./templates/index.html`; the reorg moved the file but kept the pattern.

The consequence is silent: `getLocalFileContents` falls back to a small
built-in page when the file is missing, so a server started from anywhere other
than the repo root serves a different page with no warning. Verified — starting
the CLI from `/tmp` logs `Discovering: /tmp/templates/index.html` and serves the
141-byte fallback instead of the 278-byte real template.

For a binary whose selling point is "drop it anywhere and run", silently
depending on cwd is the wrong default.

**Fix:** Prefer an explicit override, then a path relative to the executable,
then the built-in fallback. Add a `--template` CLI flag and a `template_path`
argument to `run_blocking_server`. `os.getAppDir()` gives the binary's
directory.

At minimum, make the fallback loud:

```nim
if not fileExists(path):
  echo "template not found at ", path, " - serving built-in page"
```

---

## B1. `chat.nim` — orphaned example

**File:** `server/src/pocketsocketpkg/chat.nim` (55 lines)

**Reason:** Nothing imports it. It is the mummy chat example, kept as a
reference during early development. It duplicates logic that now lives in
`broadcast.nim`, and imports only `std/locks, std/sets`.

**Fix:** Delete, or move to `docs/examples/` if the reference value is wanted.
It should not sit in the package source tree where it looks like shipped code.

---

## B2. `imp.nim` — orphaned stub

**File:** `server/src/pocketsocketpkg/imp.nim` (14 lines)

**Reason:** Nothing imports it. No imports of its own. Contents are a stub.

**Fix:** Delete.

---

## B3. Unused `clients` HashSet

**File:** `server/src/pocketsocketpkg/broadcast.nim:20`

```nim
var
  lock: Lock
  clientSheet: Table[uint64, WebSocket]
  clients: HashSet[WebSocket]        # <- declared, never read or written
```

**Reason:** Superseded by `clientSheet` when the registry was consolidated. The
only occurrence in the file is the declaration itself. It also forces
`import std/sets` at line 1, which is otherwise unneeded.

**Fix:** Delete the field and the `std/sets` import.

---

## B4. Unused lock in `service.nim`

**File:** `server/src/pocketsocketpkg/service.nim:21` and `:30`

```nim
var
  lock: Lock # The lock for global memory
  ...
initLock(lock)
```

**Reason:** `service.nim` contains zero `withLock` calls — verified:

```
$ grep -c "withLock" src/pocketsocketpkg/service.nim
0
```

All locking moved to `broadcast.nim` when it became the single owner of the
client registry. This lock is initialised and never taken.

**Fix:** Delete both lines and drop `std/locks` from the import list if nothing
else needs it.

---

## B5. Commented-out declaration graveyard

**File:** `server/src/pocketsocketpkg/service.nim:1-26`

```nim
# This is just an example to get you started. A typical hybrid package
# uses this file as the main entry point of the application.
# import os
# import asyncdispatch
# import nimpy
#import terminal
# import nimpy/py_lib as lib
...
  # router: Router
  # receiveThread: Thread[void]
  # pyHook: PyObject
```

**Reason:** The header comment is Nim's project template boilerplate and has
been inaccurate since the file became the service layer. The commented imports
and variables are remnants of the pre-GIL-fix design (`receiveThread` and
`pyHook` belonged to an abandoned dedicated-callback-thread approach).

**Fix:** Delete all of it and replace the header with one line describing what
the module actually is: the server lifecycle and the Python-facing surface.

---

## C1. Every connection receives its own request headers as the first frame

**File:** `server/src/pocketsocketpkg/ingress.nim:30`

```nim
proc upgradeHandler(request: Request) =
  let websocket: WebSocket = request.upgradeToWebSocket()
  let uuid: uint64 = registerWebSocket(request, websocket)
  # Send the headers back down the pipe.
  websocket.send($request.headers)
```

**Reason:** Every client, on every connection, is immediately sent a text frame
containing a Nim-stringified representation of its own request headers:

```
[("Host", "127.0.0.1:8090"), ("Upgrade", "websocket"), ...]
```

This is almost certainly debug scaffolding that became permanent. Consequences:

- Every client must know to discard an unsolicited first message. The benchmark
  client needs a `drain_greeting` flag purely for this.
- It is not valid JSON and not a documented protocol, so no real client can do
  anything useful with it.
- It leaks request headers (including any `Cookie` or `Authorization`) straight
  back over the wire before the application has authenticated anything.
- It costs a frame encode plus an io-thread wakeup on every connect, which is
  the exact operation the connection benchmark measures.

**Fix:** Remove it by default. If the behaviour is wanted for the demo page,
gate it behind `config.print_mode` or a dedicated `set_greeting_mode(true)`,
and make it opt-in. The header data is already captured properly in
`connection_context`, which is the right way to expose it.

**Note:** removing this changes the wire protocol. Update
`benchmarks/lib/wsclient.py` (`drain_greeting`) and the demo page in the same
commit.

---

## C2. `getWebSocketUUID` is a hash, and hashes collide

**File:** `server/src/pocketsocketpkg/socket_tools.nim:4`

```nim
proc getWebSocketUUID*(websocket: WebSocket): uint64 =
    result = cast[uint64](hash(websocket))
```

**Reason:** The identity handed to Python — the value every `ps.send(uuid, ...)`
call depends on — is a `Hash` (a 64-bit int derived from mummy's internal
WebSocket object) cast to `uint64`. Two concerns:

1. **Not guaranteed unique.** `hash()` is not an identity function. A collision
   would route a message to the wrong client. Unlikely at 64 bits, but the
   failure mode is silent cross-talk between connections, which is a security
   issue, not just a bug.
2. **Reuse after close.** mummy may reuse the underlying object for a new
   connection, yielding the same uuid for a different client.

**Fix:** Issue a monotonic counter at `OpenEvent` and keep two maps:
`uuid -> WebSocket` and `WebSocket -> uuid`. This makes the uuid a genuine
identity, makes reuse impossible, and removes the cast. Cost is one extra table
lookup per send — negligible next to the ~26 µs outbound path.

---

## C3. `send_all` fans out while holding the registry lock

**File:** `server/src/pocketsocketpkg/broadcast.nim:26-33`, called under lock
from `:35-38` and `:102-106`

```nim
proc send_all*(...): int =
  for other_uuid, websocket in clientSheet:
    if other_uuid == exclude_uuid:
      continue
    websocket.send(message_data, message_kind)   # holds `lock` for all N sends
```

**Reason:** The registry lock is held for the entire fan-out. With N clients
that is N frame encodes and N send-queue appends inside the critical section,
during which no client can connect, disconnect, or be sent to individually.

Visible in the fan-out benchmark: inbound rate collapses from 20,535 msg/s at
2 receivers to 5,688 at 8 receivers, while outbound only rises from 41,069 to
45,502 — the sender is being throttled by the lock, not by bandwidth.

**Fix:** Snapshot the target list under the lock, release it, then send.

```nim
proc locked_send_all*(kind: MessageKind, data: string, exclude_uuid: uint64): int =
  var targets: seq[WebSocket]
  {.gcsafe.}:
    withLock lock:
      targets = newSeqOfCap[WebSocket](clientSheet.len)
      for uuid, ws in clientSheet:
        if uuid != exclude_uuid:
          targets.add(ws)
  for ws in targets:
    ws.send(data, kind)
  return 0
```

Costs one `seq` allocation per broadcast; removes an O(N) critical section.
A send to a client that disconnects mid-fan-out is already safe — mummy
tolerates sending to a closed socket.

---

## C4. `hook.nim` carries commented-out header marshalling

**File:** `server/src/pocketsocketpkg/hook.nim:31-35`

```nim
      # Extract headers from the websocket and pass them to the hook as a dict.
      # let headersDict = pyDict()
      # for header in websocket.headers:
      #   headersDict[header.key] = header.value
      # messageDict["headers"] = headersDict
```

**Reason:** This sits in the hottest function in the codebase. It is also
misleading: `connection_context` already stores exactly this data, so the
commented approach is not the one a future implementation should take. Note the
trailing comma and blank argument left behind at line 40-42 from the same edit.

**Fix:** Delete the comment block and tidy the call. If per-message header
access is wanted, expose it as a separate `get_context(uuid)` export reading
from `connection_context` — never rebuild a dict per message.

---

## C5. `quick_demo.nim` is a test living in `src/`

**File:** `server/src/quick_demo.nim` (7 lines, imports `unittest`)

**Reason:** It is a unit test, but it sits in `src/` alongside shipped modules
and is compiled as an entry point. `server/tests/` already contains
`test_socket_tools.nim`.

**Fix:** Fold into `server/tests/test_socket_tools.nim` and delete.

---

## Suggested order

Mechanical and zero-risk first, so the diff for the riskier items stays small.

| step | items | risk |
| --- | --- | --- |
| 1 | A1, B1, B2, B3, B4, B5, C5 — delete dead code | none, nothing references them |
| 2 | A3 — fix benchmark paths | none, test-only |
| 3 | A2 — remove duplicate hook call | low, add a test first |
| 4 | C3 — snapshot fan-out targets | low, measurable win |
| 5 | C4 — tidy hook | none |
| 6 | A4 — template resolution | medium, changes CLI behaviour |
| 7 | C1 — remove greeting frame | **breaking**, wire protocol change |
| 8 | C2 — real uuids | medium, touches identity everywhere |

Steps 1-2 remove roughly 350 lines with no behaviour change.

After each step:

```bash
cd server && nimble test && nimble buildPyd && nimble build
python3 benchmarks/run_all.py --quick --tag stepN
```
