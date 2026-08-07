import std/locks, std/sets
import std/hashes, std/tables
import mummy

import hook
import websocket_dispatch
import config
## Connection registry and the WebSocket event handler.
##
## This module owns the authoritative `clientSheet`: it is the only writer,
## registering clients on OpenEvent and dropping them on CloseEvent. Everything
## that needs to reach a connected client goes through the `locked_*` procs
## below.

var
  lock: Lock
  clientSheet: Table[uint64, WebSocket]
  clients: HashSet[WebSocket]

initLock(lock)


proc send_all*(message_kind: MessageKind, message_data: string, exclude_uuid: uint64): int =
  #[ Send a message to _all_ clients. Provide an exclude for ignoring the
    receiver. Caller must hold `lock`. ]#
  for other_uuid, websocket in clientSheet:
    if other_uuid == exclude_uuid:
      continue
    websocket.send(message_data, message_kind)
  return 0


proc locked_send_all*(message_kind: MessageKind, message_data: string, exclude_uuid: uint64): int =
  {.gcsafe.}:
    withLock lock:
      result = send_all(message_kind, message_data, exclude_uuid)


proc locked_send*(uuid: uint64, message_kind: MessageKind, message_data: string): int =
  {.gcsafe.}:
    withLock lock:
      result = websocket_dispatch.send(clientSheet, uuid, message_kind, message_data)


proc locked_close_remove_client*(uuid: uint64): void =
  {.gcsafe.}:
    withLock lock:
      if clientSheet.hasKey(uuid):
        let websocket = clientSheet[uuid]
        websocket.close()
        clientSheet.del(uuid)


proc remove_client*(websocket: WebSocket): void =
  {.gcsafe.}:
    withLock lock:
      clientSheet.del(cast[uint64](websocket.hash()))


proc websocketHandler_broadcast*(
  websocket: WebSocket,
  event: WebSocketEvent,
  message: Message
) =
  var infoInt: int = 0
  case event:
  of OpenEvent:
    if config.print_mode:
      echo websocket, ": connected"
    {.gcsafe.}:
      withLock lock:
        clientSheet[cast[uint64](hash(websocket))] = websocket
    # return 0 to accept the connection, 1 to reject it.
    infoInt = hook.call_py_hook(websocket, event, message)

  of MessageEvent:
    if config.print_mode:
      echo message.kind, ": ", message.data
    # Reflect straight back to the sender without involving python at all.
    if config.echo_mode:
      websocket.send(message.data, message.kind)
    # A python hook returning 1 requests that the socket be dropped.
    infoInt = hook.call_py_hook(websocket, event, message)
    # Tested before taking the lock: the common case is broadcast_mode off,
    # and this runs on every inbound message.
    if config.broadcast_mode:
      {.gcsafe.}:
        withLock lock:
          discard send_all(message.kind, message.data,
                           cast[uint64](hash(websocket)))

  of ErrorEvent:
    if config.print_mode:
      echo "Error event: ", message
    discard hook.call_py_hook(websocket, event, message)

  of CloseEvent:
    if config.print_mode:
      echo websocket, ": close"
    remove_client(websocket)
    discard hook.call_py_hook(websocket, event, message)

  if infoInt == 1:
    if config.print_mode:
      echo "Drop socket ", websocket
    websocket.close()
    remove_client(websocket)
    discard hook.call_py_hook(websocket, event, message)
