# Step-by-Step Reimplementation Guide

This guide provides exact steps to reimplement the multi-process IPC architecture.

---

## Prerequisites

- Nim 2.2.6+
- Python 3.12+
- nimpy 0.2.1
- mummy 0.4.7

---

## Step 1: Create Standalone Server Binary

### File: `src/pocketsocket_standalone_server.nim`

```nim
import std/[json, net, locks, hashes, tables, os, strutils]
import mummy, mummy/routers

# Global state
var
  ipcSocket: Socket
  ipcLock: Lock
  clientSheet: Table[uint64, WebSocket]
  clientLock: Lock
  serverInstance: Server
  router: Router

initLock(ipcLock)
initLock(clientLock)

# Event type constants
const
  EVENT_CONNECT = 0
  EVENT_MESSAGE = 1
  EVENT_DISCONNECT = 2
  EVENT_ERROR = 3

proc sendEventToIPC(uuid: uint64, eventType: int, messageKind: int, data: string) =
  let eventJson = %*{
    "uuid": uuid,
    "event": eventType,
    "kind": messageKind,
    "data": data
  }
  
  {.gcsafe.}:
    withLock ipcLock:
      try:
        ipcSocket.send($eventJson & "\n")
      except CatchableError as e:
        echo "IPC send error: ", e.msg

proc websocketHandler(
  websocket: WebSocket,
  event: WebSocketEvent,
  message: Message
) {.gcsafe.} =
  let uuid = cast[uint64](websocket.hash())
  
  case event:
  of OpenEvent:
    {.gcsafe.}:
      withLock clientLock:
        clientSheet[uuid] = websocket
    sendEventToIPC(uuid, EVENT_CONNECT, 0, "")
  
  of MessageEvent:
    sendEventToIPC(uuid, EVENT_MESSAGE, message.kind.ord, message.data)
  
  of ErrorEvent:
    sendEventToIPC(uuid, EVENT_ERROR, 0, message.data)
  
  of CloseEvent:
    {.gcsafe.}:
      withLock clientLock:
        clientSheet.del(uuid)
    sendEventToIPC(uuid, EVENT_DISCONNECT, 0, "")

proc handleRoot(request: Request) =
  var headers: HttpHeaders
  headers["Content-Type"] = "text/html"
  request.respond(200, headers, """<!DOCTYPE html>
<html><head><title>pocketsocket</title></head>
<body><h1>pocketsocket WebSocket Server</h1>
<p>Connect to <code>ws://""" & request.headers["Host"] & """/ws</code></p>
</body></html>""")

proc handleWebSocket(request: Request) =
  discard request.upgradeToWebSocket()

proc ctrlc() {.noconv.} =
  echo "\nShutting down server..."
  if serverInstance != nil:
    serverInstance.close()
  quit(0)

proc main() =
  echo "pocketsocket standalone server starting..."
  
  let params = commandLineParams()
  if params.len < 3:
    echo "Usage: pocketsocket_standalone_server <ipc_socket_path> <address> <port>"
    quit(1)
  
  let
    socketPath = params[0]
    address = params[1]
    port = parseInt(params[2])
  
  echo "Connecting to IPC socket: ", socketPath
  
  # Connect to Python process IPC socket
  ipcSocket = newSocket(AF_UNIX, SOCK_STREAM, IPPROTO_IP)
  var connected = false
  for attempt in 1..10:
    try:
      ipcSocket.connectUnix(socketPath)
      connected = true
      echo "Connected to IPC socket"
      break
    except OSError as e:
      echo "Waiting for IPC socket (attempt ", attempt, "/10): ", e.msg
      sleep(100)
  
  if not connected:
    echo "Failed to connect to IPC socket"
    quit(1)
  
  # Setup router
  router.get("/", handleRoot)
  router.get("/ws", handleWebSocket)
  
  # Setup server
  serverInstance = newServer(router, websocketHandler)
  
  setControlCHook(ctrlc)
  
  echo "Serving on http://", address, ":", port
  serverInstance.serve(Port(port), address)
  echo "Server stopped"

when isMainModule:
  main()
```

**Key Points:**
- Uses Unix domain sockets (`AF_UNIX`, `connectUnix`)
- Thread-safe with `{.gcsafe.}` and locks
- JSON serialization for events
- Newline-delimited JSON protocol

---

## Step 2: Update Build System

### File: `pocketsocket.nimble`

Add these tasks:

```nim
task buildStandalone, "build standalone server binary":
  switch("out", "python" / "pocketsocket" / "pocketsocket_standalone_server")
  switch("d", "release")
  switch("opt", "speed")
  setCommand "c", srcDir / "pocketsocket_standalone_server.nim"

task buildAll, "build both Python extension and standalone server":
  exec "nimble buildPyd"
  exec "nimble buildStandalone"
```

**Build:**
```bash
nimble buildStandalone
# Creates: python/pocketsocket/pocketsocket_standalone_server
```

---

## Step 3: Modify Python Wrapper

### File: `python/pocketsocket/wrapper.py`

Add these imports:

```python
import socket
import subprocess
import json
import os
import sys
import atexit
from pathlib import Path
```

Add global state:

```python
_hook_callback = None
_server_process = None
_ipc_socket = None
_ipc_server_socket = None
```

Add hook registration:

```python
def hook(callback):
    """Register Python callback for WebSocket events"""
    global _hook_callback
    _hook_callback = callback
```

Add cleanup function:

```python
def _cleanup():
    """Cleanup function to terminate server process"""
    global _server_process, _ipc_server_socket
    
    if _server_process:
        print("Shutting down server process...")
        _server_process.terminate()
        try:
            _server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_process.kill()
            _server_process.wait()
    
    if _ipc_server_socket:
        try:
            _ipc_server_socket.close()
        except:
            pass
```

Add binary finder:

```python
def _find_server_binary():
    """Locate the standalone server binary"""
    candidates = [
        Path(__file__).parent / "pocketsocket_standalone_server",
        Path(__file__).parent / "bin" / "pocketsocket_standalone_server",
        Path(__file__).parent.parent.parent / "src" / "pocketsocket_standalone_server",
    ]
    
    for path in candidates:
        if path.exists():
            return str(path)
    
    raise FileNotFoundError("Could not find pocketsocket_standalone_server binary")
```

Add main server function:

```python
def start_server(address='0.0.0.0', port=8090):
    """Start WebSocket server in separate process"""
    global _server_process, _ipc_socket, _ipc_server_socket
    
    atexit.register(_cleanup)
    
    sock_path = f"/tmp/pocketsocket_{os.getpid()}.sock"
    server_binary = _find_server_binary()
    
    # Create IPC socket FIRST
    if os.path.exists(sock_path):
        os.remove(sock_path)
    
    _ipc_server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    _ipc_server_socket.bind(sock_path)
    _ipc_server_socket.listen(1)
    print(f"IPC socket listening on: {sock_path}")
    
    # Launch Nim server
    _server_process = subprocess.Popen(
        [server_binary, sock_path, address, str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    print(f"Started server process (PID: {_server_process.pid})")
    
    # Print server output in background
    import threading
    def print_server_output():
        try:
            for line in _server_process.stdout:
                print(f"[SERVER] {line.rstrip()}")
        except:
            pass
    
    threading.Thread(target=print_server_output, daemon=True).start()
    
    # Wait for connection
    print("Waiting for server process to connect...")
    _ipc_socket, _ = _ipc_server_socket.accept()
    print("Server connected via IPC, starting event loop...")
    
    # IPC EVENT LOOP - BLOCKS HERE
    buffer = ""
    try:
        while True:
            data = _ipc_socket.recv(4096).decode('utf-8')
            if not data:
                break
            
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if not line.strip():
                    continue
                
                try:
                    event = json.loads(line)
                    if _hook_callback:
                        _hook_callback(
                            event['uuid'],
                            event['event'],
                            event['kind'],
                            event['data']
                        )
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON: {line[:100]}")
                except Exception as e:
                    print(f"Error calling hook: {e}")
                    import traceback
                    traceback.print_exc()
    
    except KeyboardInterrupt:
        print("\nReceived interrupt, shutting down...")
    finally:
        if _ipc_socket:
            _ipc_socket.close()
        _cleanup()
        if os.path.exists(sock_path):
            os.remove(sock_path)
```

---

## Step 4: Update __init__.py

### File: `python/pocketsocket/__init__.py`

```python
from .wrapper import hook, start_server, shutdown_server
from .pocketsocket_server import send, send_all

__all__ = ['hook', 'start_server', 'shutdown_server', 'send', 'send_all']
```

---

## Step 5: Test Implementation

### Create test file: `test_multiprocess.py`

```python
import sys
sys.path.insert(0, 'python')
import pocketsocket

def my_hook(uuid, event_type, message_kind, data):
    event_names = ['CONNECT', 'MESSAGE', 'DISCONNECT', 'ERROR']
    print(f"\n[HOOK] {event_names[event_type]}")
    print(f"  UUID: {uuid}")
    print(f"  Data: {repr(data[:100] if data else '')}")
    
    if event_type == 1:  # Message
        print(f"  Echo response...")
        # Note: send() won't work yet without bidirectional IPC

print("Registering hook...")
pocketsocket.hook(my_hook)

print("Starting server on 0.0.0.0:8091...")
pocketsocket.start_server('0.0.0.0', 8091)
```

### Run test:

```bash
python3 test_multiprocess.py
```

### Test with WebSocket client:

```bash
# In another terminal
python3 -c "
import asyncio
import websockets

async def test():
    async with websockets.connect('ws://localhost:8091/ws') as ws:
        await ws.send('Hello!')
        response = await ws.recv()
        print(f'Got: {response}')

asyncio.run(test())
"
```

---

## Step 6: Verify

Expected output in server terminal:

```
[HOOK] CONNECT
  UUID: 1234567890
  Data: ''

[HOOK] MESSAGE
  UUID: 1234567890
  Data: 'Hello!'
```

✅ If you see this, hooks are working!

---

## Step 7: Add Bidirectional IPC (Future Work)

To implement `send()` and `send_all()`:

### Nim side - add command reader thread:

```nim
proc commandReader() {.thread.} =
  var cmdBuffer = ""
  while true:
    try:
      let data = ipcSocket.recv(4096)
      cmdBuffer.add(data)
      
      while "\n" in cmdBuffer:
        let parts = cmdBuffer.split("\n", maxsplit=1)
        let line = parts[0]
        cmdBuffer = if parts.len > 1: parts[1] else: ""
        
        let cmd = parseJson(line)
        case cmd["cmd"].getStr:
        of "send":
          let uuid = cmd["uuid"].getBiggestInt.uint64
          let data = cmd["data"].getStr
          {.gcsafe.}:
            withLock clientLock:
              if clientSheet.hasKey(uuid):
                clientSheet[uuid].send(data)
        of "send_all":
          # Implement broadcast
        of "close":
          # Implement close
    except:
      break

var cmdThread: Thread[void]
createThread(cmdThread, commandReader)
```

### Python side - update send():

```python
def send(uuid, kind, data):
    """Send message back to client"""
    cmd = json.dumps({
        "cmd": "send",
        "uuid": uuid,
        "kind": kind,
        "data": data
    }) + "\n"
    
    _ipc_socket.send(cmd.encode('utf-8'))
```

---

## Troubleshooting

### Server won't start
- Check binary exists: `ls python/pocketsocket/pocketsocket_standalone_server`
- Check permissions: `chmod +x python/pocketsocket/pocketsocket_standalone_server`
- Check socket path: `ls /tmp/pocketsocket_*.sock`

### IPC connection fails
- Ensure Python creates socket BEFORE spawning server
- Check Nim is using `connectUnix()` not `connect()`
- Verify socket path matches on both sides

### Hooks not called
- Check JSON formatting (newline-delimited)
- Verify hook is registered before `start_server()`
- Look for Python exceptions in output

### Performance issues
- Unix sockets should be sub-millisecond
- Check for blocking operations in hook
- Monitor buffer sizes

---

## Platform Notes

### Linux ✅
- Works out of the box
- Unix domain sockets native

### Mac ⚠️
- Should work (untested)
- Unix domain sockets supported

### Windows ❌
- Needs named pipes instead
- Replace `socket.AF_UNIX` with `socket.AF_PIPE`
- Or use TCP localhost as fallback

---

## Next Steps

1. Test on your target platform
2. Add error handling
3. Implement bidirectional IPC
4. Add reconnection logic
5. Create integration tests
6. Benchmark performance
7. Package binary with Python module

---

## Success Criteria

You'll know it's working when:
1. Server starts without errors
2. WebSocket clients can connect
3. Hook is called on connection
4. Hook receives messages
5. No crashes or deadlocks

That's it! You've successfully reimplemented the multi-process IPC architecture.
