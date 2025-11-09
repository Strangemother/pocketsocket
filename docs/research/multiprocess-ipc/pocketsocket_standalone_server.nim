#[
  Standalone WebSocket Server for pocketsocket
  
  This server runs as a separate process from Python, communicating
  via Unix domain socket. It has NO Python dependencies - pure Nim.
  
  Events are serialized to JSON and sent over IPC to the Python process
  where user hooks are called.
]#

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

# Initialize locks
initLock(ipcLock)
initLock(clientLock)

# Event types matching Python API
const
  EVENT_CONNECT = 0
  EVENT_MESSAGE = 1
  EVENT_DISCONNECT = 2
  EVENT_ERROR = 3

proc sendEventToIPC(uuid: uint64, eventType: int, messageKind: int, data: string) =
  ## Send event to Python process via IPC
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
  ## WebSocket event handler - called by mummy for each event
  let uuid = cast[uint64](websocket.hash())
  
  case event:
  of OpenEvent:
    # Store connection
    {.gcsafe.}:
      withLock clientLock:
        clientSheet[uuid] = websocket
    
    # Send connect event to Python
    sendEventToIPC(uuid, EVENT_CONNECT, 0, "")
  
  of MessageEvent:
    # Send message event to Python
    sendEventToIPC(uuid, EVENT_MESSAGE, message.kind.ord, message.data)
  
  of ErrorEvent:
    # Send error event to Python
    sendEventToIPC(uuid, EVENT_ERROR, 0, message.data)
  
  of CloseEvent:
    # Remove from client sheet
    {.gcsafe.}:
      withLock clientLock:
        clientSheet.del(uuid)
    
    # Send disconnect event to Python
    sendEventToIPC(uuid, EVENT_DISCONNECT, 0, "")

proc handleRoot(request: Request) =
  ## Simple root handler
  var headers: HttpHeaders
  headers["Content-Type"] = "text/html"
  request.respond(200, headers, """
<!DOCTYPE html>
<html>
<head><title>pocketsocket</title></head>
<body>
  <h1>pocketsocket WebSocket Server</h1>
  <p>Connect to <code>ws://""" & request.headers["Host"] & """/ws</code></p>
</body>
</html>
""")

proc handleWebSocket(request: Request) =
  ## Upgrade HTTP request to WebSocket
  discard request.upgradeToWebSocket()

proc ctrlc() {.noconv.} =
  ## Handle Ctrl+C
  echo "\nShutting down server..."
  if serverInstance != nil:
    serverInstance.close()
  quit(0)

proc main() =
  ## Main entry point
  echo "pocketsocket standalone server starting..."
  
  # Parse command line arguments
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
  
  # Handle Ctrl+C
  setControlCHook(ctrlc)
  
  # Start serving
  echo "Serving on http://", address, ":", port
  serverInstance.serve(Port(port), address)
  echo "Server stopped"

when isMainModule:
  main()
