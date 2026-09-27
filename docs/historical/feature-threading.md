# Nonblocking Python Server Startup

## Status

Proposed feature plan.

This document describes adding `pocketsocket.run_nonblocking_server()` to the
Python API. The feature allows an application to start a waiting WebSocket
server without occupying the Python caller's thread.

The existing hook API, event format, send functions, blocking startup API, and
Mummy worker behavior remain unchanged.

## Motivation

The current Python entry point is:

```python
pocketsocket.hook(ingress)
pocketsocket.run_blocking_server("127.0.0.1", 8090)
```

`run_blocking_server()` performs all server setup and then enters Mummy's
blocking `serve()` loop. This is appropriate for a standalone server process,
but it requires an application that has other work to do to create its own
Python thread:

```python
import threading

threading.Thread(
    target=pocketsocket.run_blocking_server,
    args=("127.0.0.1", 8090),
    daemon=True,
).start()
```

That workaround leaves application code responsible for startup races, thread
lifecycle, and cleanup. It also makes it harder to report a bind or startup
failure to the caller.

The proposed API makes this common lifecycle a native server responsibility.

## Current Architecture

The Python package delegates its public functions to the compiled
`pocketsocket_server` extension. The native service layer currently owns one
module-level Mummy `Server` instance:

```text
Python application
    |
    v
pocketsocket.run_blocking_server()
    |
    v
pocketsocket_server.run_blocking_server()
    |
    v
service.run_blocking_server()
    |
    v
Mummy Server.serve()  ---- blocks the calling Python thread
    |
    +-- Mummy worker threads
            |
            +-- websocket dispatch
                    |
                    +-- hook.call_py_hook()
```

The current GIL arrangement is important:

1. The Python thread enters `serve()` while holding the GIL.
2. The service layer calls `gil.save_thread()` before entering the blocking
   loop, allowing other threads to acquire the GIL.
3. Mummy worker threads call the Python hook through `hook.nim`.
4. Each callback acquires the GIL with `gil.acquire_gil()` and releases it after
   all nimpy argument marshalling and callback work completes.

The new entry point must preserve steps 3 and 4. The hook contract is not part
of this feature.

## Proposed Architecture

The blocking and nonblocking APIs will share server construction and serving
logic. The only difference is which thread enters the serve loop.

```text
                         +-----------------------------+
                         | shared server setup         |
                         | Mummy Server + configuration |
                         +--------------+--------------+
                                        |
                    +-------------------+-------------------+
                    |                                       |
                    v                                       v
       run_blocking_server()                    run_nonblocking_server()
       current Python thread                   managed native server thread
                    |                                       |
                    v                                       v
             serve() blocks                         serve() blocks
                                                        |
                                                        v
                                           caller returns after readiness
```

The implementation belongs in `server/src/pocketsocketpkg/service.nim`, which
already owns the server instance, shutdown function, signal handler, and
blocking startup function.

The service layer will maintain synchronized lifecycle state for:

- whether startup is in progress;
- whether a server is listening;
- whether startup failed;
- the background server thread handle; and
- whether shutdown has been requested.

The native build already enables Nim threads through `server/nim.cfg` and the
build scripts. No separate Python `threading.Thread` is needed for the public
API.

## Public API

The new function will have the same arguments and defaults as the blocking
function:

```python
def run_nonblocking_server(
    address="127.0.0.1",
    port=8090,
    worker_threads=0,
    max_message_len=64 * 1024,
    max_body_len=1024 * 1024,
    tcp_no_delay=True,
):
    ...
```

The native extension will export the procedure, and the public Python package
will expose it as:

```python
import pocketsocket

pocketsocket.run_nonblocking_server("127.0.0.1", 8090)
```

The function returns `None`.

### Readiness guarantee

`run_nonblocking_server()` will not return merely because a thread was created.
It will return after Mummy has successfully created, bound, listened on, and
registered the server socket.

This allows the following pattern without an arbitrary sleep:

```python
pocketsocket.hook(ingress)
pocketsocket.run_nonblocking_server("127.0.0.1", 8090)

# The listener is ready here.
connect_to_websocket("ws://127.0.0.1:8090/ws/")
```

A failure to bind or initialize the server will be reported to the Python
caller. It must not disappear as an exception on an unmanaged background
thread.

### Shutdown guarantee

`shutdown_server()` remains the public shutdown function. For a nonblocking
server, it will:

1. signal the Mummy server to stop;
2. wait for the server thread to leave `serve()`;
3. complete the existing Mummy cleanup; and
4. return after the background server lifecycle has finished.

This makes cleanup deterministic:

```python
pocketsocket.run_nonblocking_server("127.0.0.1", 8090)
try:
    application_loop()
finally:
    pocketsocket.shutdown_server()
```

Shutdown must not attempt to join the current thread. The blocking API and
control-C path must continue to work without requiring a background thread.

## Lifecycle Rules

The native module currently has a singleton-style server state. The supported
model will remain one active server per native module.

The implementation should explicitly guard these cases:

| Situation | Expected behavior |
| --- | --- |
| Start one nonblocking server | Start and wait for readiness. |
| Start while another server is active | Raise a clear lifecycle error; do not overwrite the existing server. |
| Start while startup is in progress | Raise or wait according to the final synchronization contract, but never race global state. |
| Bind failure | Wake the waiting caller and raise the captured startup error. |
| Shutdown a running nonblocking server | Signal and join the server thread. |
| Shutdown after the server has stopped | Remain safe and avoid dereferencing invalid server state. |
| Existing blocking startup | Preserve its blocking behavior and public arguments. |

The implementation should avoid silently making `shutdown_server()` idempotent if
that changes existing behavior without tests. The final behavior should be
explicitly covered by lifecycle tests.

## GIL and Hook Invariants

The new server thread is a native Nim thread, not the Python thread that calls
`run_nonblocking_server()`.

The implementation must not use `gil.save_thread()` and
`gil.restore_thread()` as though the new thread were the Python caller. Those
functions pair with the Python thread state that entered the extension.

Instead, the native server thread must use the GIL helpers appropriate for a
new native thread before it performs any Python C-API work. The serve loop
itself should release the GIL while waiting for socket activity, just as the
current blocking path does.

The existing hook path remains the authority for callback safety:

- `hook()` still stores the same Python callable.
- Callback arguments remain `(uuid, event_type, event_dict)`.
- The event dictionary keeps the existing `kind` and `data` fields.
- Every worker-thread callback continues to acquire the GIL before nimpy
  marshalling and release it afterward.
- `send()`, `send_all()`, and client close behavior do not change.

No callback should be invoked merely because the server was started. Hook
invocation remains driven by the same WebSocket events as before.

## Thread-Safety Boundaries

This feature changes where the Mummy listening loop runs. It does not make
arbitrary application Python state thread-safe.

Applications must still protect shared Python state accessed by callbacks and
other application threads. The GIL protects Python object operations during a
callback, but it does not replace application-level coordination for compound
operations or external resources.

The native service layer must synchronize lifecycle state around:

- server creation and replacement;
- readiness notification;
- startup failure storage;
- shutdown requests; and
- background thread joining.

Existing broadcast and connection registries retain their current locking and
ownership rules.

## Usage Examples

### Blocking mode

Use the existing API when the server should own the current thread:

```python
import pocketsocket


def ingress(uuid, event_type, event):
    if event_type == pocketsocket.MESSAGE:
        pocketsocket.send(uuid, event["kind"], event["data"])


pocketsocket.hook(ingress)
pocketsocket.run_blocking_server("127.0.0.1", 8090)
```

### Nonblocking mode

Use the new API when the application has its own loop or work to perform:

```python
import pocketsocket


def ingress(uuid, event_type, event):
    if event_type == pocketsocket.MESSAGE:
        pocketsocket.send_all(
            event["kind"],
            event["data"],
            uuid,
        )


pocketsocket.hook(ingress)
pocketsocket.run_nonblocking_server("127.0.0.1", 8090)

try:
    run_application_loop()
finally:
    pocketsocket.shutdown_server()
```

The call returns only after the listener is ready, so an application can
connect clients or start dependent work immediately afterward.

### Migrating from manual Python threading

Before this feature:

```python
import threading

server_thread = threading.Thread(
    target=pocketsocket.run_blocking_server,
    args=("127.0.0.1", 8090),
    daemon=True,
)
server_thread.start()
# The caller must guess when the listener is ready.
```

After this feature:

```python
pocketsocket.run_nonblocking_server("127.0.0.1", 8090)
# The listener is ready and shutdown_server() owns cleanup.
```

Applications should not start both APIs for the same native module.

## Implementation Plan

### 1. Refactor the service lifecycle

In `service.nim`:

- extract shared configuration and Mummy server construction;
- preserve template loading, worker count defaults, logging, control-C
  handling, and socket options;
- preserve the existing blocking path;
- add synchronized lifecycle state and a managed thread handle; and
- centralize cleanup so both startup modes release resources consistently.

### 2. Add native nonblocking startup

Add a service procedure with the same arguments as
`run_blocking_server()` that:

- validates the singleton lifecycle state;
- creates the managed native thread;
- starts the shared serving routine;
- communicates bind readiness or startup failure to the caller; and
- returns only after one of those outcomes is known.

### 3. Export the API

Update:

- `server/src/pocketsocketpkg/pocketsocket_server.nim`;
- `package/pocketsocket/__init__.py`; and
- `__all__` in the public wrapper.

No hook or event API changes are required.

### 4. Add tests

Native tests should cover service lifecycle state and compilation of the new
procedure. Python integration tests should cover:

- the function returning while the process remains usable;
- an immediate client connection after return;
- hook invocation from the Mummy worker thread;
- startup failure propagation, such as a port already in use;
- duplicate-start protection; and
- synchronous shutdown without a hanging native thread.

Tests must clean up the server in `finally` blocks and use dedicated ports.

### 5. Update public documentation

The package and root README files should show the new function briefly and
link here for the complete design, lifecycle contract, and migration notes.

## Verification Plan

Run the following checks after implementation:

```bash
cd /workspaces/pocketsocket-2/server
nimble buildPyd
nimble test
```

Then run the focused Python lifecycle test and relevant existing module-loading
and callback tests:

```bash
cd /workspaces/pocketsocket-2
python3 package/tests/test_nonblocking_server.py
python3 package/tests/test_module_loading.py
```

A manual smoke test should confirm this sequence:

1. Register a hook.
2. Call `run_nonblocking_server()`.
3. Connect immediately.
4. Exchange a message and observe the unchanged hook arguments.
5. Call `shutdown_server()`.
6. Confirm the process exits without a hanging native thread.

The test suite should also exercise a failed bind and verify that the caller
receives an exception rather than returning as if the server were ready.

## Non-Goals

This feature does not introduce:

- Python `asyncio` integration;
- an awaitable server object;
- multiple independent server instances in one native module;
- a new callback or hook signature;
- changes to Mummy's worker-thread count or dispatch model;
- changes to WebSocket framing, routing, or message semantics; or
- automatic management of arbitrary application threads.

`run_nonblocking_server()` means that the server's native serving loop does not
block the Python caller. It does not make the entire application asynchronous.

## Related Code

- [`service.nim`](../server/src/pocketsocketpkg/service.nim) owns server lifecycle.
- [`pocketsocket_server.nim`](../server/src/pocketsocketpkg/pocketsocket_server.nim) exports the native Python API.
- [`hook.nim`](../server/src/pocketsocketpkg/hook.nim) owns Python callback registration and callback GIL handling.
- [`gil.nim`](../server/src/pocketsocketpkg/gil.nim) provides GIL transition helpers.
- [`__init__.py`](../package/pocketsocket/__init__.py) exposes the public Python package API.
