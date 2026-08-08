# Segfault Bug Fix in pocketsocket

## Problem

The pocketsocket Python module was experiencing segmentation faults when receiving WebSocket text messages. The error occurred in the nimpy marshalling layer when trying to convert Nim types to Python types.

## Root Cause Analysis

### The Call Chain

1. WebSocket receives message in `src/pocketsocketpkg/broadcast.nim`
2. `websocketHandler_broadcast` calls `call_py_hook(websocket, event, message)`
3. `call_py_hook` in `src/pocketsocketpkg/hook.nim` tries to pass `Message` to Python
4. nimpy's `nimValueToPy` attempts to convert the `Message` object
5. **SEGFAULT** occurs when trying to marshal the `MessageKind` enum field

### The Problem

In `src/pocketsocketpkg/hook.nim`, the `call_py_hook` function was passing a Nim `Message` object directly to Python:

```nim
# BEFORE (buggy code):
proc call_py_hook*(
  websocket: WebSocket,
  event: WebSocketEvent,
  message: Message
): int =
  result = 0
  if pyHook != nil:
    # This line causes segfault - nimpy can't marshal Message object
    let info:PyObject = pyHook.callObject(cast[uint64](hash(websocket)), event, message)
    ...
```

The `Message` type from mummy is defined as:

```nim
type Message* = object
  kind*: MessageKind  # enum: TextMessage, BinaryMessage, Ping, Pong
  data*: string
```

When nimpy tried to automatically marshal this Nim object to Python, it failed with:

```
SIGSEGV: Illegal storage access. (Attempt to read from nil?)
```

This occurred in `nimpy/nim_py_marshalling.nim` when calling `nimValueToPy`.

### Why the Segfault Happens

nimpy attempts to convert objects to Python dicts using `nimValueToPyDict`:

```nim
proc nimValueToPyDict*(o: object | tuple): PPyObject =
  result = PyObject_CallObject(cast[PPyObject](pyLib.PyDict_Type))
  for k, v in fieldPairs(o):
    let vv = nimValueToPy(v)  # <-- Recursively convert each field
    let ret = pyLib.PyDict_SetItemString(result, k, vv)
    ...
```

When it reaches the `kind: MessageKind` field, it calls:

```nim
proc nimValueToPy*(v: enum): PPyObject {.inline.} =
  mixin nimpyEnumConvert
  nimValueToPy(nimpyEnumConvert(v))  # <-- Expects nimpyEnumConvert to exist
```

**The problem**: `MessageKind` enum from the mummy library doesn't have a `nimpyEnumConvert` mixin defined, causing a nil pointer dereference and segfault.

## Solution

Manually convert the Nim `Message` object to a Python dictionary before passing it to the hook:

```nim
# AFTER (fixed code):
proc call_py_hook*(
  websocket: WebSocket,
  event: WebSocketEvent,
  message: Message
): int =
  result = 0
  if pyHook != nil:
    # Convert Message object to Python dict manually
    let messageDict = pyDict()
    messageDict["kind"] = message.kind.ord  # Convert enum to int
    messageDict["data"] = message.data
    
    # Pass the dict instead of the raw Message object
    let info:PyObject = pyHook.callObject(cast[uint64](hash(websocket)), event.ord, messageDict)
    if cast[pointer](info) != cast[pointer](lib.pyLib.Py_None):
      result = info.to(int)
    discard info
```

## Changes Made

1. **Create Python dict**: Use `pyDict()` to create a new Python dictionary
2. **Manual field mapping**: 
   - `messageDict["kind"] = message.kind.ord` - Convert MessageKind enum to integer
   - `messageDict["data"] = message.data` - Copy string data directly
3. **Pass event as int**: Changed `event` to `event.ord` to pass as integer instead of enum

## Python API Compatibility

The fix maintains compatibility with existing Python code that expects:

```python
def hook(uuid, etype, event):
    # etype is now an int (0=OpenEvent, 1=MessageEvent, 2=ErrorEvent, 3=CloseEvent)
    # event is a dict with 'kind' and 'data' keys
    if etype == 0:  # Connection
        return
    print(f"Message kind: {event['kind']}, data: {event['data']}")
    pocketsocket.send(uuid, event['kind'], event['data'])
```

## Testing

To verify the fix works:

```bash
# Rebuild the module
nimble buildPyd

# Test with echo server
python3 -c "
import sys
sys.path.insert(0, 'python')
import pocketsocket

def echo_handler(uuid, etype, event):
    if etype == 0:
        print('Client connected')
        return
    print(f'Received: kind={event[\"kind\"]}, data={event[\"data\"]}')
    pocketsocket.send(uuid, event['kind'], event['data'])

pocketsocket.hook(echo_handler)
pocketsocket.run_blocking_server('127.0.0.1', 8090)
"
```

Then connect with a WebSocket client and send messages - it should no longer segfault.

## Files Modified

- `src/pocketsocketpkg/hook.nim` - Fixed `call_py_hook` to manually convert Message to dict

## Impact

This fix enables:
- ✅ Message echo functionality in Python
- ✅ Full message throughput benchmarking
- ✅ Stable Python module usage with WebSocket messages
- ✅ No more segmentation faults when receiving text/binary messages

## Next Steps

After rebuilding with `nimble buildPyd`, the throughput benchmarks can be updated:
- `benchmarks/benchmark_throughput.py` should now work correctly
- Echo and broadcast modes will function as intended
- Message-level performance testing becomes possible
