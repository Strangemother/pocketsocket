import mummy
import std/tables

import config


proc send_all*(clientSheet: Table[uint64, WebSocket], message_kind: MessageKind, message_data: string, exclude_uuid: uint64): int =
  #[ Send a message to _all_ clients. Provide an exclude for ignoring the
    receiver]#
  for other_uuid, websocket in clientSheet:
    if other_uuid == exclude_uuid:
      continue
    websocket.send(message_data, message_kind)
  return 0


proc send*(clientSheet: Table[uint64, WebSocket], uuid: uint64, message_kind: MessageKind, message_data: string): int =
  #[ Send a message to the target UUID websocket, with the _kind_ being the
     message type, such as 0 for text.

     return int for success - 0 being ok, any other integer representing a
     error code (typically 1)
  ]#
  if clientSheet.hasKey(uuid):
    clientSheet[uuid].send(message_data, message_kind)
    return 0
  if config.print_mode:
    echo "Attempted send() to unknown uuid: ", uuid
  return 1
