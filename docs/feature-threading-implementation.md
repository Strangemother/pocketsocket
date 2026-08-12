# Nonblocking Server: Nim Implementation Plan

## Purpose

This document is the source-code companion to
[`feature-threading.md`](feature-threading.md). It describes the concrete Nim
changes required to add `run_nonblocking_server()`.

The examples use the repository's current symbols and APIs:

- `service.nim` owns the module-level `Server` and lifecycle functions.
- `pocketsocket_server.nim` exports Nim procedures to Python with `exportpy`.
- `mummy.nim` provides `Server`, `serve()`, `close()`, `waitUntilReady()`,
  `Thread`, and Mummy worker-thread cleanup.
- `gil.nim` provides the existing Python GIL transition helpers.

The snippets below are implementation shapes, not a patch to apply verbatim.
They must be compiled incrementally because Nim's `gcsafe`, `raises`, and thread
argument rules are part of the design.

## Change Map

| File | Required change |
| --- | --- |
| `server/src/pocketsocketpkg/service.nim` | Add lifecycle state, shared setup, serving-thread entry point, nonblocking startup, and joined shutdown. |
| `server/src/pocketsocketpkg/pocketsocket_server.nim` | Export `run_nonblocking_server()` to Python. |
| `server/src/mummy.nim` | No initial change; reuse the existing exported `waitUntilReady()`. |
| `server/src/pocketsocketpkg/hook.nim` | No change; preserve callback GIL acquisition. |
| `server/src/pocketsocketpkg/gil.nim` | No initial change; use existing helpers without applying caller-thread state APIs to the new thread. |
| `server/tests/test_service.nim` | Add focused lifecycle tests where native integration is practical. |
| `package/tests/` | Add Python integration coverage after the extension export exists. |

## Existing Service Code

The current service owns a single server pointer and starts Mummy directly:

```nim
var
  server: Server
  wake_time: MonoTime = getMonoTime()

proc run_blocking_server*(
    address: string = "127.0.0.1",
    port: int = 8090,
    worker_threads: int = 0,
    max_message_len: int = 64 * 1024,
    max_body_len: int = 1024 * 1024,
    tcp_no_delay: bool = true
  ): void =
  let workers =
    if worker_threads > 0: worker_threads
    else: max(countProcessors() * 10, 1)
  server = newServer(
      ingress.router,
      websocketHandler = broadcast.websocketHandler_broadcast,
      workerThreads = workers,
      maxMessageLen = max_message_len,
      maxBodyLen = max_body_len,
      tcpNoDelay = tcp_no_delay,
    )
  let threadState = gil.save_thread()
  try:
    server.serve(Port(port), address)
  finally:
    gil.restore_thread(threadState)
```

The first implementation task is to preserve this behavior while moving setup
and serving into reusable internal procedures.

## 1. Add Lifecycle Types and Synchronization

`service.nim` should import the standard lock and thread support already used by
Mummy:

```nim
import std/[cpuinfo, locks, monotimes, os, times]
```

The exact import list can remain narrower if the compiler resolves `Thread` and
`joinThread` through `mummy`, but `Lock`, `Cond`, `initLock`, `wait`, `signal`,
and `joinThread` should be explicit dependencies of the service layer.

A small lifecycle object makes the state that crosses the native thread
boundary explicit:

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

  ServerState = object
    server: Server
    thread: Thread[ServerThreadArgs]
    threadStarted: bool
    state: ServerLifecycle
    startupError: string
    lifecycleLock: Lock
    lifecycleCond: Cond
```

There are two viable representations:

1. Keep the state as module-level variables and protect every access with one
   module-level lock and condition.
2. Allocate a shared `ServerState` object and pass it to the thread.

The second form is easier to reason about when the serving thread needs to
publish state. The implementation must ensure that any object passed to a
native Nim thread is safe for the selected memory manager and remains alive
until the thread has joined.

A minimal module-level layout, matching the current service style, is:

```nim
var
  server: Server
  serverThread: Thread[ServerThreadArgs]
  lifecycleLock: Lock
  lifecycleCond: Cond
  lifecycleState = ServerIdle
  serverThreadStarted = false
  startupError = ""

initLock(lifecycleLock)
initCond(lifecycleCond)
```

Initialization and deinitialization must be designed together. If the module
uses global locks, do not deinitialize them while Python can still call the
extension. If the state is allocated, deinitialize the locks only after the
thread has joined and no public lifecycle call can access the state.

All reads and writes of `server`, `serverThreadStarted`, `lifecycleState`, and
`startupError` must occur under `lifecycleLock`, except for immutable local
copies made while holding that lock.

## 2. Extract Shared Server Construction

Move the current setup into an internal procedure. It should retain the current
configuration behavior exactly:

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

Template preparation and startup logging should also be extracted, but remain
on the caller side if they perform Python-facing or process-global work:

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

The final helper split may differ, but both public startup functions must use
the same `buildServer()` and preparation behavior. This avoids a subtle drift
where the nonblocking API has different routes, worker counts, templates, or
socket settings.

## 3. Keep the Blocking Path Behaviorally Stable

After extraction, the existing function should remain structurally equivalent:

```nim
proc run_blocking_server*(
    address: string = "127.0.0.1",
    port: int = 8090,
    worker_threads: int = 0,
    max_message_len: int = 64 * 1024,
    max_body_len: int = 1024 * 1024,
    tcp_no_delay: bool = true
  ): void =
  prepareServer(address, port)
  server = buildServer(
    worker_threads,
    max_message_len,
    max_body_len,
    tcp_no_delay,
  )

  let threadState = gil.save_thread()
  try:
    server.serve(Port(port), address)
  finally:
    gil.restore_thread(threadState)
```

The actual implementation should also preserve the existing TTL output and
any required lifecycle guard. The important constraint is that the blocking
call continues to block the Python caller and keeps its existing GIL pairing.

## 4. Add the Native Serving Thread Entry Point

Mummy's `serve()` performs the bind and listen operations before setting its
internal `serving` flag. Its existing public helper is:

```nim
proc waitUntilReady*(server: Server, timeout: float = 10) =
  if server.serving.load(moRelaxed):
    return
  # Poll until ready or timeout.
```

`service.nim` must not access `ServerObj.serving` directly because the field is
private to `mummy.nim`.

The thread entry point should own the blocking `serve()` call and publish all
outcomes. A code-shaped example is:

```nim
proc serveThread(args: ServerThreadArgs) {.raises: [].} =
  try:
    args.server.serve(args.port, args.address)
    withLock lifecycleLock:
      lifecycleState = ServerIdle
      signal(lifecycleCond)
  except CatchableError as error:
    withLock lifecycleLock:
      startupError = error.msg
      lifecycleState = ServerFailed
      signal(lifecycleCond)
```

The exact exception type must match the compiler's inferred `raises` set. If
`MummyError` and selector errors are not covered by `CatchableError` in this
context, catch `Exception` or the concrete types required by the build.

The thread procedure must also distinguish startup failure from an unexpected
server failure after readiness. At minimum, it must record the message and
signal the condition in both cases. A later implementation can add a separate
`runtimeError` field if the public API needs to expose failures after startup.

### GIL requirement for the native thread

The new serving thread must not call `gil.save_thread()` and
`gil.restore_thread()`. Those functions operate on the Python thread state that
entered the extension.

The serving thread should avoid Python C-API work while it is in the Mummy
loop. Mummy worker threads already acquire the GIL through `hook.nim` when they
invoke the registered Python callback. If the serving thread itself must call
Python-facing code for error reporting, it must use the attach/acquire helper
appropriate to a newly created native thread and release it immediately after
that operation.

## 5. Implement Readiness-Aware Nonblocking Startup

The public service procedure should follow this order:

1. Lock lifecycle state.
2. Reject `ServerStarting`, `ServerRunning`, or `ServerStopping`.
3. Clear the previous startup error.
4. Build and store the new server.
5. Set `ServerStarting`.
6. Create the native serving thread.
7. Wait for either readiness, startup failure, or thread completion.
8. Return only after readiness, or raise on failure.

A code-shaped outline is:

```nim
proc run_nonblocking_server*(
    address: string = "127.0.0.1",
    port: int = 8090,
    worker_threads: int = 0,
    max_message_len: int = 64 * 1024,
    max_body_len: int = 1024 * 1024,
    tcp_no_delay: bool = true
  ): void =
  prepareServer(address, port)

  let newServer = buildServer(
    worker_threads,
    max_message_len,
    max_body_len,
    tcp_no_delay,
  )

  withLock lifecycleLock:
    if lifecycleState != ServerIdle:
      raise newException(ValueError, "pocketsocket server is already running")
    server = newServer
    startupError = ""
    lifecycleState = ServerStarting
    let args = ServerThreadArgs(
      server: newServer,
      address: address,
      port: Port(port),
    )
    createThread(serverThread, serveThread, args)
    serverThreadStarted = true

  try:
    newServer.waitUntilReady()
  except CatchableError:
    shutdown_server()
    raise

  withLock lifecycleLock:
    if startupError.len > 0:
      let errorMessage = startupError
      lifecycleState = ServerIdle
      raise newException(IOError, errorMessage)
    lifecycleState = ServerRunning
```

This outline exposes two synchronization issues that the implementation must
resolve:

- `waitUntilReady()` polls Mummy's readiness flag but does not wake immediately
  when `serve()` fails during bind.
- The lifecycle condition must be checked in a loop, not just once, because
  condition notifications can be spurious or arrive before the waiter begins.

The preferred implementation is to combine Mummy's readiness check with the
service condition. If the existing Mummy helper cannot be interrupted, use a
short bounded wait loop and inspect `startupError` between checks. The final
implementation must still propagate the original bind error rather than only a
generic timeout.

Also, `buildServer()` can itself fail before a thread exists. That failure must
leave lifecycle state as `ServerIdle` and must not call `shutdown_server()` on a
nil or partially initialized server.

## 6. Update Shutdown and Joining

The current shutdown implementation is unsafe for an uninitialized server and
does not know about a managed serving thread:

```nim
proc shutdown_server*(): void =
  echo "nim::shutdown_server"
  server.close()
```

The new implementation needs a two-phase operation:

```nim
proc shutdown_server*(): void =
  var activeServer: Server
  var shouldJoin = false

  withLock lifecycleLock:
    activeServer = server
    shouldJoin = serverThreadStarted
    if activeServer != nil:
      lifecycleState = ServerStopping

  if activeServer != nil:
    activeServer.close()

  if shouldJoin and not isCurrentServerThread():
    joinThread(serverThread)

  withLock lifecycleLock:
    server = nil
    serverThreadStarted = false
    startupError = ""
    lifecycleState = ServerIdle
    signal(lifecycleCond)
```

The actual self-thread check must use a Nim-supported thread identity mechanism;
do not invent a comparison that does not compile on all supported platforms.
The control-C handler should signal shutdown without joining if it can execute
on the serving thread. A separate internal `closeServer()` helper can keep the
signal handler, Python shutdown function, and startup-failure cleanup from
recursively calling one another.

The Mummy server's `close()` already triggers its shutdown event and joins its
worker threads through its cleanup path. The service layer's join is for the
additional serving thread created by this feature. The order must prevent the
serving thread from using `server` after the pointer is cleared.

### Shutdown cases to implement explicitly

```text
no server             -> safe no-op or documented error
starting              -> close, wake readiness waiter, join
running               -> close, join, clear state
failed before ready   -> reclaim server state, do not join an uncreated thread
already stopped       -> join if needed, then clear state
called by server thread -> close without self-join
```

These cases should be represented in tests before changing behavior in the
public wrapper.

## 7. Export the New Procedure

`pocketsocket_server.nim` needs one wrapper next to the existing blocking
wrapper:

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

The wrapper should not create a Python thread or alter callback registration.
The Python package alias and `__all__` update belong to the public API change,
but no additional Nim behavior belongs in this wrapper.

## 8. Mummy Source Decision

No initial edit to `server/src/mummy.nim` is required.

The required Mummy APIs already exist:

```nim
server.serve(Port(port), address)
server.waitUntilReady()
server.close()
```

Do not expose `ServerObj.serving` or duplicate its atomic flag in
`service.nim`. If implementation testing proves that `waitUntilReady()` cannot
provide the needed failure behavior, the smallest Mummy follow-up would be a
new exported readiness callback or a timeout-aware status helper. That should
be a separate change because it affects the reusable Mummy layer.

## 9. GIL and Hook Files: No Functional Changes

`hook.nim` already handles the worker-thread boundary:

```nim
let gilState = gil.acquire_gil()
try:
  let info: PyObject = pyHook.callObject(...)
finally:
  gil.release_gil(gilState)
```

Do not move this code into `service.nim`, do not call the hook from the serving
thread, and do not change the callback arguments. `gil.nim` also remains
unchanged unless compilation demonstrates that a native thread needs a new
explicit attach/detach helper.

## 10. Native Test Examples

The existing native service suite mainly tests wrappers with no live server.
Threaded lifecycle tests need a dedicated serial fixture because the service is
singleton-scoped.

A first compile-level test can verify the new symbol is available:

```nim
test "nonblocking server procedure is available":
  check compiles(run_nonblocking_server(
    "127.0.0.1", 18090, 1, 64 * 1024, 1024 * 1024, true
  ))
```

A live test should always clean up:

```nim
test "nonblocking server starts and shuts down":
  try:
    run_nonblocking_server("127.0.0.1", 18090, 1)
    check true
  finally:
    shutdown_server()
```

The final test should additionally make an HTTP or WebSocket client connection
and verify that the hook path remains functional. Use a dedicated loopback
port, run lifecycle tests serially, and avoid calling `shutdown_server()` from
an unrelated test after the server state has already been cleared.

## 11. Build Order

Implement and validate in this order:

1. Add the lifecycle types and compile the service module.
2. Extract `buildServer()` without changing the blocking API.
3. Add the serving thread procedure and compile with `--threads:on`.
4. Add readiness and startup error coordination.
5. Update shutdown and test the native lifecycle.
6. Add the `exportpy` wrapper.
7. Build the Python extension.
8. Add Python integration coverage for immediate readiness, hook dispatch,
   bind failure, duplicate starts, and joined shutdown.

Useful commands:

```bash
cd /workspaces/pocketsocket-2/server
nimble buildPyd
nimble test

cd /workspaces/pocketsocket-2
python3 package/tests/test_module_loading.py
python3 package/tests/test_nonblocking_server.py
```

## Implementation Constraints

- Preserve `run_blocking_server()` arguments and blocking semantics.
- Preserve hook registration, callback arguments, and GIL acquisition.
- Do not access Mummy's private `ServerObj` fields from `service.nim`.
- Do not clear the global `Server` pointer before the serving thread exits.
- Do not join a thread from itself.
- Do not let startup exceptions disappear on a detached thread.
- Do not add a Python `threading.Thread` wrapper to the native API.
- Keep the first implementation to one active server per native module.
