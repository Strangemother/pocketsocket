# import std/hashes

import ../mummy
import nimpy
import nimpy/py_lib as lib
import socket_tools
import gil

var
  pyHook: PyObject

proc call_py_hook*(
  websocket: WebSocket,
  event: WebSocketEvent,
  message: Message
): int =
  result = 0
  {.gcsafe.}:
    if pyHook == nil:
      return 0

    # This runs on a mummy worker thread, so the GIL must be held around every
    # python C-API call below - including nimpy's argument marshalling.
    let gilState = gil.acquire_gil()
    try:
      # Marshal by hand; mummy's `Message` object is handed to python as a
      # plain dict of {"kind": int, "data": str}.
      let messageDict = pyDict()
      messageDict["kind"] = message.kind.ord
      messageDict["data"] = message.data
      ## TODO: Add headers to the python hook call.
      if message.kind.ord == 0:
        echo "open"
      # messageDict["headers"] = headersDict

      let info: PyObject = pyHook.callObject(
          getWebSocketUUID(websocket),
          event.ord,
          messageDict,
          
        )
      if info != nil and
          cast[pointer](info.privateRawPyObj) != cast[pointer](lib.pyLib.Py_None):
        result = info.to(int)
    finally:
      gil.release_gil(gilState)


proc hook*(p: PyObject): void =
  #[
    The exposed hook proc accepts a python _callable_, called upon
    message events.
  ]#
  # Keep the function as the callable.
  gil.ensure_gil_procs()
  pyHook = p
