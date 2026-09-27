# Nonblocking Server: Exact Implementation Steps

This document turns `feature-threading.md` and
`feature-threading-implementation.md` into an implementation sequence for the
current repository.

The implementation adds `pocketsocket.run_nonblocking_server()` while keeping
the existing hook contract, event format, send functions, worker behavior, and
blocking startup API unchanged.

## Final File Changes

You will modify or add these files:

| File | Change |
| --- | --- |
| `server/src/mummy.nim` | Add a public readiness accessor. |
| `server/src/pocketsocketpkg/service.nim` | Add synchronized lifecycle state, managed thread startup, readiness handling, and joined shutdown. |
| `server/src/pocketsocketpkg/pocketsocket_server.nim` | Export the new native Python procedure. |
| `package/pocketsocket/__init__.py` | Expose the new public Python function. |
| `server/tests/test_service.nim` | Add native lifecycle tests. |
| `package/tests/test_nonblocking_server.py` | Add Python integration tests. |
| `package/tests/run.sh` | Run the new integration test. |
| `readme.md` | Document the public API. |
| `package/readme.md` | Document the Python package API. |

Do not change `hook.nim` or `gil.nim` unless compilation proves that an
additional GIL helper is required. The current `hook.nim` callback path already
uses `gil.acquire_gil()` and `gil.release_gil()` correctly.

## Step 0: Establish a Baseline

From the server directory:

```bash
cd /workspaces/pocketsocket-2/server
nimble test
nimble buildPyd
```

From the repository root:

```bash
cd /workspaces/pocketsocket-2
python3 package/tests/test_module_loading.py
```

Record failures before editing. Do not treat generated files under
`server/nimcache`, `server/coverage`, or `server/c_coverage` as source files.

## Step 1: Add Mummy Readiness Access

### File

`server/src/mummy.nim`

### Why this edit is required

`ServerObj.serving` is private to `mummy.nim`, so `service.nim` cannot inspect it
directly. The existing `waitUntilReady()` helper waits for readiness but can
only report a bind error after its timeout. The nonblocking API must return the
actual startup error promptly.

### Edit

Place this procedure immediately before or after `waitUntilReady*`:

```nim
proc isReady*(server: Server): bool =
  server.serving.load(moRelaxed)
```

Do not make `serving` public. Do not modify `serve()`, `close()`, or
`waitUntilReady()` in this step.

### Check

Compile the native tests:

```bash
cd /workspaces/pocketsocket-2/server
nimble test
```

If this fails because `moRelaxed` is unavailable in that scope, use the same
atomic import and memory-order spelling already used by `serve()` and
`waitUntilReady()` in the current Mummy source.

## Step 2: Add Lifecycle Types and State

### File

`server/src/pocketsocketpkg/service.nim`

### Imports

Extend the standard-library imports to include the lock and thread support
needed by the installed Nim version. The intended import set is:

```nim
import std/[cpuinfo, locks, monotimes, os, times]
```

Keep the existing project imports.

### Types

Add these private types below the imports:

```nim
type
  ServerLifecycle = enum
    ServerIdle
    ServerStarting
    ServerRunning
    ServerStopping
    ServerFailed

  ServerThreadArgs = object
    server: Server
    address: string
    port: Port
```

The thread argument contains only the server pointer and immutable startup
values. Do not pass Python objects, `PyObject`, or GC-managed application state
to the serving thread.

### State

Replace the current variable block:

```nim
var
  server: Server
  wake_time: MonoTime = getMonoTime()
```

with the existing server and lifecycle state:

```nim
var
  server: Server
  wake_time: MonoTime = getMonoTime()
  serverThread: Thread[ServerThreadArgs]
  serverThreadStarted = false
  lifecycleLock: Lock
  lifecycleCond: Cond
  lifecycleState = ServerIdle
  startupError = ""

initLock(lifecycleLock)
initCond(lifecycleCond)
```

Keep the locks alive for the lifetime of the native module. Do not add module
finalization that deinitializes them while Python can still call the extension.

### State rules

All reads and writes of these values must happen under `lifecycleLock`:

- `server`
- `serverThread`
- `serverThreadStarted`
- `lifecycleState`
- `startupError`

Use this lifecycle policy:

| State | New start |
| --- | --- |
| `ServerIdle` | Allowed. |
| `ServerStarting` | Raise a lifecycle error. |
| `ServerRunning` | Raise a lifecycle error. |
| `ServerStopping` | Raise a lifecycle error. |
| `ServerFailed` | Reclaim state first, then allow a later start. |

Rejecting a concurrent start is preferable to waiting because the native module
supports only one server and waiting can deadlock startup/shutdown callers.

## Step 3: Extract Shared Server Construction

### File

`server/src/pocketsocketpkg/service.nim`

Add a private helper before `run_blocking_server`:

```nim
proc buildServer(
    worker_threads: int,
    max_message_len: int,
    max_body_len: int,
    tcp_no_delay: bool
  ): Server =
  let workers =
    if worker_threads > 0: worker_threads
    else: max(countProcessors() * 10, 1)

  result = newServer(
      ingress.router,
      websocketHandler = broadcast.websocketHandler_broadcast,
      workerThreads = workers,
      maxMessageLen = max_message_len,
      maxBodyLen = max_body_len,
      tcpNoDelay = tcp_no_delay,
    )
```

Add a second helper for the setup that must be shared by both APIs:

```nim
proc prepareServer(address: string, port: int) =
  when isMainModule:
    echo(getWelcomeMessage())

  if config.template_dir.len != 0:
    echo "Using template directory: ", config.template_dir
    submodule.setLoadedTemplate("index.html")

  echo "Serving on http://", address, ":", port
  setControlCHook(ctrlc)
```

Do not move Python C-API work into these helpers. Preserve the current template
loading and startup output exactly.

## Step 4: Refactor Blocking Startup

### File

`server/src/pocketsocketpkg/service.nim`

Replace the setup portion of `run_blocking_server` with calls to the helpers:

```nim
prepareServer(address, port)
server = buildServer(
    worker_threads,
    max_message_len,
    max_body_len,
    tcp_no_delay,
  )
```

Keep the existing TTL calculation and this GIL pairing unchanged:

```nim
let threadState = gil.save_thread()
try:
  server.serve(Port(port), address)
finally:
  gil.restore_thread(threadState)
```

Before assigning the new server, protect the singleton:

```nim
withLock lifecycleLock:
  if lifecycleState != ServerIdle:
    raise newException(ValueError, "pocketsocket server is already running")
```

The blocking path must continue to block the Python caller. It must not create
or join the managed nonblocking thread.

## Step 5: Add the Native Serving Thread

### File

`server/src/pocketsocketpkg/service.nim`

Add a private procedure before `run_nonblocking_server`.

The exact `raises` and `gcsafe` annotations must be accepted by the installed
Nim compiler. Begin with the least restrictive version that compiles, then
narrow it only if required by compiler diagnostics.

The procedure must follow this behavior:

```nim
proc serveThread(args: ServerThreadArgs) =
  try:
    args.server.serve(args.port, args.address)
    withLock lifecycleLock:
      if lifecycleState == ServerRunning:
        lifecycleState = ServerIdle
      signal(lifecycleCond)
  except Exception as error:
    withLock lifecycleLock:
      startupError = error.msg
      lifecycleState = ServerFailed
      signal(lifecycleCond)
```

Adjust the normal-return state handling after testing. A normal return is
usually caused by `close()`, so shutdown must remain responsible for joining
and clearing the global server state.

Important rules:

- Do not call `gil.save_thread()` in this procedure.
- Do not call `gil.restore_thread()` in this procedure.
- Do not call the Python hook from this procedure.
- Do not let an exception escape the native thread.
- Signal the condition after publishing failure state.

The Python hook continues to run only from Mummy worker threads through the
existing GIL acquisition in `hook.nim`.

## Step 6: Implement Nonblocking Startup

### File

`server/src/pocketsocketpkg/service.nim`

Add this public procedure with the same arguments and defaults as the blocking
procedure:

```nim
proc run_nonblocking_server*(
    address: string = "127.0.0.1",
    port: int = 8090,
    worker_threads: int = 0,
    max_message_len: int = 64 * 1024,
    max_body_len: int = 1024 * 1024,
    tcp_no_delay: bool = true
  ): void =
```

Implement it in this order.

### 6.1 Prepare and build before publishing state

```nim
prepareServer(address, port)
let newServer = buildServer(
    worker_threads,
    max_message_len,
    max_body_len,
    tcp_no_delay,
  )
```

If `buildServer` raises, do not call shutdown. No thread exists and the global
lifecycle must remain idle.

### 6.2 Publish state and create the thread

Under `lifecycleLock`:

1. Check that `lifecycleState == ServerIdle`.
2. Assign `server = newServer`.
3. Set `startupError = ""`.
4. Set `lifecycleState = ServerStarting`.
5. Create `serverThread` with `ServerThreadArgs(server: newServer, address: address, port: Port(port))`.
6. Set `serverThreadStarted = true` only after `createThread` succeeds.

If thread creation fails, restore `server = nil`, reset the state to idle, and
re-raise the original exception.

### 6.3 Wait for readiness or failure

Do not call only `newServer.waitUntilReady()`. It cannot promptly expose a bind
failure.

Use a loop that:

1. Checks `newServer.isReady()`.
2. Checks `lifecycleState` and `startupError` under `lifecycleLock`.
3. Returns when ready.
4. Raises the captured startup error when state is failed.
5. Sleeps briefly between checks, for example `sleep(10)` milliseconds.
6. Uses a bounded startup timeout to prevent an infinite wait.

When readiness is observed, acquire `lifecycleLock` again and change
`ServerStarting` to `ServerRunning`, unless failure or shutdown has already
been published.

The startup error must retain the original Mummy error message, especially for
an occupied port.

### 6.4 Clean up failed startup

When startup fails:

1. Copy `startupError` under the lifecycle lock.
2. Call the internal close operation if the server exists.
3. Join the serving thread if it was created and the current thread is not the serving thread.
4. Clear the server pointer and thread state under the lifecycle lock.
5. Set the lifecycle state to `ServerIdle`.
6. Raise a Nim exception containing the captured error.

Do not leave a failed native thread detached.

## Step 7: Replace Shutdown

### File

`server/src/pocketsocketpkg/service.nim`

The current implementation unconditionally calls `server.close()`, which is
unsafe when no server exists. Replace it with a two-phase shutdown.

### 7.1 Snapshot under the lock

Under `lifecycleLock`, copy:

- the active `server` pointer;
- whether `serverThreadStarted` is true; and
- the managed thread handle if needed.

If a server exists, set `lifecycleState = ServerStopping`.

### 7.2 Close outside the lock

Call `activeServer.close()` only when `activeServer != nil`.

Do not hold `lifecycleLock` while calling Mummy cleanup. Mummy cleanup joins
its worker threads and can invoke code that needs other locks.

### 7.3 Join the serving thread

If a managed thread was created, join it from the caller unless the caller is
the serving thread itself.

Do not invent a thread comparison. Check the Nim version’s supported thread
identity API during compilation. If the API is not portable, keep self-join
avoidance in the serving-thread entry point and use a separate internal
close-only helper for control-C.

### 7.4 Clear state after join

After Mummy close and the serving-thread join complete, acquire the lock and
set:

```nim
server = nil
serverThreadStarted = false
startupError = ""
lifecycleState = ServerIdle
signal(lifecycleCond)
```

Never clear `server` before the serving thread has exited.

### 7.5 Separate control-C behavior

`ctrlc()` should request server close without attempting a potentially unsafe
self-join. Use an internal helper such as `closeActiveServer()` for this path.
The public `shutdown_server()` performs the join when called from another
thread.

## Step 8: Export the Native Procedure

### File

`server/src/pocketsocketpkg/pocketsocket_server.nim`

Place this procedure next to `run_blocking_server`:

```nim
proc run_nonblocking_server*(
    address: string = "127.0.0.1",
    port: int = 8090,
    worker_threads: int = 0,
    max_message_len: int = 64 * 1024,
    max_body_len: int = 1024 * 1024,
    tcp_no_delay: bool = true
  ): void {.exportpy.} =
  service.run_nonblocking_server(
    address,
    port,
    worker_threads,
    max_message_len,
    max_body_len,
    tcp_no_delay,
  )
```

Do not create a Python thread in this wrapper.

Build immediately:

```bash
cd /workspaces/pocketsocket-2/server
nimble buildPyd
```

## Step 9: Expose the Python API

### File

`package/pocketsocket/__init__.py`

Add the alias beside `run_blocking_server`:

```python
run_nonblocking_server = pocketsocket_server.run_nonblocking_server
```

Add the name to `__all__` beside the blocking function:

```python
"run_blocking_server", "run_nonblocking_server", "shutdown_server",
```

Check the module export:

```bash
cd /workspaces/pocketsocket-2
python3 - <<'PY'
import sys
sys.path.insert(0, "package")
import pocketsocket
assert hasattr(pocketsocket, "run_nonblocking_server")
assert "run_nonblocking_server" in pocketsocket.__all__
print("nonblocking API exported")
PY
```

## Step 10: Add Native Tests

### File

`server/tests/test_service.nim`

Add a compile-level test:

```nim
test "nonblocking server procedure is available":
  check compiles(run_nonblocking_server(
    "127.0.0.1", 18090, 1, 64 * 1024, 1024 * 1024, true
  ))
```

Add a live test with a dedicated port:

```nim
test "nonblocking server starts and shuts down":
  try:
    run_nonblocking_server("127.0.0.1", 18090, 1)
    check true
  finally:
    shutdown_server()
```

Add tests for:

- duplicate start raises a lifecycle error;
- an occupied port raises the original startup error;
- shutdown after a successful start returns;
- shutdown when idle is safe;
- failed startup can be followed by a later valid startup.

Keep live tests serial. The service is singleton-scoped. Use separate ports
when a previous server may still be cleaning up.

Run after each native test change:

```bash
cd /workspaces/pocketsocket-2/server
nimble test
```

## Step 11: Add Python Integration Tests

### File

Create `package/tests/test_nonblocking_server.py`.

The test should:

1. Add `package/` to `sys.path` like the existing tests.
2. Import `pocketsocket`.
3. Allocate or select dedicated loopback ports.
4. Start the server with `worker_threads=1`.
5. Immediately perform a TCP, HTTP, or WebSocket connection without sleeping.
6. Verify Python execution continues after startup.
7. Register a hook and verify the unchanged callback shape:
   `(uuid, event_type, event_dict)`.
8. Verify event fields `kind` and `data`.
9. Verify duplicate startup raises.
10. Occupy a port and verify bind failure is raised by the caller.
11. Call `shutdown_server()` in every `finally` block.

Use only dependencies already available to the project, or use a minimal
loopback socket test if a WebSocket client dependency is unavailable.

Run it directly:

```bash
cd /workspaces/pocketsocket-2
python3 package/tests/test_nonblocking_server.py
```

## Step 12: Update the Python Test Runner

### File

`package/tests/run.sh`

Keep the existing test and add the focused lifecycle test:

```bash
python3 package/tests/test_segfault_fix.py
python3 package/tests/test_nonblocking_server.py
```

Run:

```bash
cd /workspaces/pocketsocket-2
./package/tests/run.sh
```

## Step 13: Update Documentation

### Files

- `readme.md`
- `package/readme.md`

Add a short example:

```python
import pocketsocket

pocketsocket.hook(ingress)
pocketsocket.run_nonblocking_server("127.0.0.1", 8090)

try:
    run_application_loop()
finally:
    pocketsocket.shutdown_server()
```

State that the function returns only after the listener is ready. State that
`shutdown_server()` waits for the managed native serving thread to finish.
Mention that applications should not start both blocking and nonblocking APIs
for the same native module.

Add a link to:

- `docs/feature-threading.md`
- `docs/feature-threading-implementation.md`

Update the API table in `readme.md` with:

```text
run_nonblocking_server(address, port) | Start the server and return after readiness.
```

## Step 14: Full Verification

Run the complete native build and tests:

```bash
cd /workspaces/pocketsocket-2/server
nimble buildPyd
nimble test
```

Run the Python checks:

```bash
cd /workspaces/pocketsocket-2
python3 package/tests/test_module_loading.py
python3 package/tests/test_nonblocking_server.py
./package/tests/run.sh
```

Perform this manual smoke test:

```python
import pocketsocket

pocketsocket.hook(ingress)
pocketsocket.run_nonblocking_server("127.0.0.1", 8090)

try:
    # Connect immediately. No arbitrary startup sleep should be necessary.
    run_application_loop()
finally:
    pocketsocket.shutdown_server()
```

Also verify manually that:

- starting a second server raises without replacing the first;
- starting on an occupied port raises synchronously;
- shutdown returns after the listener thread exits; and
- the Python process exits without a hanging native thread.

## Required Invariants

Before considering the implementation complete, confirm all of these:

- The blocking function still blocks the caller.
- The blocking function still pairs `gil.save_thread()` with
  `gil.restore_thread()`.
- The native serving thread never uses those caller-thread GIL functions.
- Worker-thread hook callbacks still acquire and release the GIL.
- Callback arguments remain `(uuid, event_type, event_dict)`.
- Event dictionaries still contain `kind` and `data`.
- No Python thread is created by the new API.
- Only one native server can be active.
- Startup failure reaches the Python caller.
- Shutdown does not dereference a nil server.
- Shutdown does not join the current thread.
- The global server pointer is not cleared before the serving thread exits.
- Mummy worker cleanup remains owned by Mummy.
