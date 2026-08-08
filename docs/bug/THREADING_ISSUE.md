# Critical Threading Issue with Python Callbacks

## Problem Summary

**The Python callback feature (`pocketsocket.hook()`) is fundamentally incompatible with mummy's threading model.**

## Root Cause

1. **mummy** uses worker threads to handle HTTP/WebSocket requests
2. **nimpy** (Nim-Python bridge) is NOT thread-safe when:
   - Python interpreter is initialized on main thread
   - nimpy marshalling functions are called from worker threads
3. Even with locks, `nimValueToPy` crashes during string conversion in worker threads

## Evidence

```
Traceback (most recent call last)
/home/codespace/.nimble/pkgs2/mummy-0.4.7-.../mummy.nim(520) workerProc
.../nimpy.nim(953) call_py_hook
.../nimpy/nim_py_marshalling.nim nimValueToPy
SIGSEGV: Illegal storage access. (Attempt to read from nil?)
```

## Attempted Fixes (All Failed)

1. ✗ Manual dict creation with `pyDict()`
2. ✗ JsonNode conversion 
3. ✗ Separating parameters (4 params instead of 3)
4. ✗ Integer-only parameters
5. ✗ Python GIL acquisition (functions not available in nimpy)
6. ✗ Nim lock for serialization
7. ✗ `workerThreads=0` (server hangs completely)
8. ✗ `workerThreads=1` (still uses worker thread, different from main thread)

## Viable Solutions

### Option 1: Remove Python Callbacks (RECOMMENDED)
- Remove `hook()` functionality entirely
- Document that pocketsocket is send-only from Python
- Use external message queue (Redis, etc.) for bidirectional communication

### Option 2: Switch WebSocket Library
- Replace mummy with a single-threaded async library
- Requires major refactoring
- May impact performance

### Option 3: Message Queue to Main Thread
- Implement channel-based event queue
- Worker threads enqueue events
- Main thread dequeues and calls Python
- Complex architecture, may have latency issues

### Option 4: Separate Process Architecture
- Run Nim server in separate process
- Use IPC (sockets/pipes) to communicate with Python
- Most robust but adds complexity

## Recommendation

**Remove the `hook()` feature** from pocketsocket's Python API. The current architecture cannot safely support it.

Users needing bidirectional communication should:
- Use external message broker (Redis PubSub, RabbitMQ, etc.)
- Connect Python clients as WebSocket clients to receive messages
- Use pocketsocket.send() for Python→Client communication

This makes pocketsocket a high-performance **broadcast server** controlled by Python, not a Python-scriptable WebSocket handler.
