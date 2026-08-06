# This is just an example to get you started. A typical hybrid package
# uses this file as the main entry point of the application.

import os
import std/strutils, std/hashes, std/locks, std/tables
import asyncdispatch
#import terminal
import nimpy
import nimpy/py_lib as lib
import mummy, mummy/routers
import submodule


var
  lock: Lock # The lock for global memory
  router: Router
  server: Server
  receiveThread: Thread[void]
  pyHook: PyObject
  clientSheet: Table[uint64, WebSocket]


# Remember to initialize the lock.
initLock(lock)

proc hook*(p: PyObject): void =
  #[
    The exposed hook proc accepts a python _callable_, called upon
    message events.
  ]#
  # Keep the function as the callable.
  pyHook = p


proc upgradeHandler(request: Request) =
  #[
    Given a new request, assume a websocket and upgrade.
  ]#
  let websocket = request.upgradeToWebSocket()
  # Send the headers back down the pipe.
  websocket.send($request.headers)


proc print_headers(headers: HttpHeaders) =
  # Access request headers in an iterator
  for (key, value) in headers:
    echo "  ", key, " = ", value


proc indexHandler(request: Request) =
  # print_headers(request.headers)
  if request.path.startsWith("/ws") or "Upgrade" in request.headers:
      upgradeHandler(request)
      return

  var headers: HttpHeaders
  # Respond with the HTML
  headers["Content-Type"] = "text/html"
  # headers["Content-Type"] = "text/plain"
  # let index_html_content:string =
  # request.respond(200, headers, $request.headers)
  request.respond(200, headers, getCachedLocalFileContents("./server/templates/index.html"))


proc send_all*(message_kind: MessageKind, message_data: string, exclude_uuid: uint64): int =
  #[ Send a message to _all_ clients. Provide an exclude for ignoring the
    receiver]#
  for other_uuid, websocket in clientSheet:
    if other_uuid == exclude_uuid:
      echo "skipping exclude uuid: ", exclude_uuid
      continue
    websocket.send(message_data, message_kind)
  return 0


proc send*(uuid: uint64, message_kind: MessageKind, message_data: string): int =
  #[ Send a message to the target UUID websocket, with the _kind_ being the
     message type, such as 0 for text.

     return int for success - 0 being ok, any other integer representing a
     error code (typically 1)
  ]#
  if clientSheet.hasKey(uuid):
    clientSheet[uuid].send(message_data, message_kind)
    return 0
  else:
    echo "Attempted send() to unknown uuid: ", uuid
    return 1


proc call_py_hook(
  websocket: WebSocket,
  event: WebSocketEvent,
  message: Message
): int =
  result = 0
  if pyHook != nil:
    let info:PyObject = pyHook.callObject(cast[uint64](hash(websocket)), event, message)
    if cast[pointer](info) != cast[pointer](lib.pyLib.Py_None):
      # echo "Given: ", $info
      result = info.to(int)
    discard info



proc remove_client(websocket: WebSocket): void =
  {.gcsafe.}:
    withLock lock:
      clientSheet.del(cast[uint64](websocket.hash()))
      # echo "Client Sheet Size: ", $clientSheet.len


proc websocketHandler_print(
  websocket: WebSocket,
  event: WebSocketEvent,
  message: Message
) =
  case event:
  of OpenEvent:
    echo websocket, ": connected"
  of MessageEvent:
    # let message_data: string = move message.data
    echo message.kind, ": ", $message.data
  of ErrorEvent:
    echo "Error event occured: ", $event, " : ", $message
    # echo "socket closed:", getCurrentExceptionMsg()
  of CloseEvent:
    echo websocket, ": close"


proc websocketHandler_hooked(
  websocket: WebSocket,
  event: WebSocketEvent,
  message: Message
) =
  var infoInt:int = 0
  case event:
  of OpenEvent:
    # echo websocket, ": connected"
    {.gcsafe.}:
      withLock lock:
        let uuid = cast[uint64](hash(websocket))
        clientSheet[uuid] = websocket
        # echo "Client Sheet Size: ", $clientSheet.len
    discard call_py_hook(websocket, event, message)

  of MessageEvent:
    # let message_data: string = move message.data
    # echo message.kind, ": ", message_data
    # If the python hook returns an int,
    # test the int for force socket closure.
    infoInt = call_py_hook(websocket, event, message)
    # echo "resp ", type(info), ":", info
    # websocket.send(message_data, message.kind)
  of ErrorEvent:
    echo "Error event occured: ", $event, " : ", $message
    # websocket.close()
    remove_client(websocket)
    discard call_py_hook(websocket, event, message)

  of CloseEvent:
    # echo websocket, ": close"
    # Lock global memory and remove the websocket.
    remove_client(websocket)
    discard call_py_hook(websocket, event, message)

  if infoInt == 1:
    # echo "Drop socket", $websocket
    websocket.close()
    remove_client(websocket)
    discard call_py_hook(websocket, event, message)


var broadcast_mode*:bool = false

proc websocketHandler_broadcast(
  websocket: WebSocket,
  event: WebSocketEvent,
  message: Message
) =
  var infoInt:int = 0
  case event:
  of OpenEvent:
    # echo websocket, ": connected"
    {.gcsafe.}:
      withLock lock:
        let uuid = cast[uint64](hash(websocket))
        clientSheet[uuid] = websocket
        # echo "Client Sheet Size: ", $clientSheet.len
    discard call_py_hook(websocket, event, message)

  of MessageEvent:
    # let message_data: string = move message.data
    # echo message.kind, ": ", message_data
    # If the python hook returns an int,
    # test the int for force socket closure.
    infoInt = call_py_hook(websocket, event, message)
    {.gcsafe.}:
      withLock lock:
        if broadcast_mode:
          let uuid = cast[uint64](hash(websocket))
          discard send_all(message.kind, message.data, uuid)
    # echo "resp ", type(info), ":", info
    # websocket.send(message_data, message.kind)
  of ErrorEvent:
    echo "Error event occured: ", $event, " : ", $message
    # websocket.close()
    remove_client(websocket)
    discard call_py_hook(websocket, event, message)

  of CloseEvent:
    # echo websocket, ": close"
    # Lock global memory and remove the websocket.
    remove_client(websocket)
    discard call_py_hook(websocket, event, message)

  if infoInt == 1:
    # echo "Drop socket", $websocket
    websocket.close()
    remove_client(websocket)
    discard call_py_hook(websocket, event, message)


router.get("/**", indexHandler)
# router.get("/ws", upgradeHandler)


proc ctrlc() {.noconv.} =
  echo "Ctrl+C fired!"
  server.close()


proc shutdownThreadProc() =
  echo "nim::shutdownThreadProc"

  waitFor:
    sleepAsync(900)
  echo "closing"
  try:
    echo "Should close server"
    quit(0)
  except:
    echo "Fatal error in receive thread: ", getCurrentExceptionMsg()
    quit(1)


proc shutdown_server*(): void =
  echo "nim::shutdown_server"
  sleep 1000 # Sleeps for 1000ms = 1s
  createThread(receiveThread, shutdownThreadProc)


proc run_timeout_server*(timeout: float = 10): void =
  server = newServer(router, websocketHandler_hooked)
  setControlCHook(ctrlc)
  server.waitUntilReady(timeout)
  echo "Serve complete"


proc run_blocking_server*(address: string = "127.0.0.1", port: int = 8090): void =
  # if isatty(stdout):
  #   run_blocking_server()
  when isMainModule:
    echo(getWelcomeMessage())
  load_lib()
  submodule.setLoadedTemplate("./server/templates/index.html")
  server = newServer(router, websocketHandler_broadcast)
  # server = newServer(router, websocketHandler)
  echo "Serving on http://", address, ":", port
  setControlCHook(ctrlc)
  server.serve(Port(port), address)
  echo "Serve complete"
