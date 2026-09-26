# import std/hashes

import ../mummy
import std/dynlib
import nimpy
import nimpy/py_lib as lib
import nimpy/py_types
import nimpy/py_utils
import socket_tools
import gil
import std/atomics

type PyObjectVectorcall = proc(
  callable: PPyObject,
  args: ptr PPyObject,
  nargs: csize_t,
  kwnames: PPyObject
): PPyObject {.cdecl, gcsafe.}

var
  pyHook: PyObject
  pythonHookRegistered: Atomic[bool]
  pyObjectVectorcall: PyObjectVectorcall

proc hasPythonHook*(): bool {.gcsafe, raises: [].} =
  pythonHookRegistered.load(moAcquire)

proc loadVectorcall() {.gcsafe.} =
  if pyObjectVectorcall.isNil and not lib.pyLib.module.isNil:
    pyObjectVectorcall = cast[PyObjectVectorcall](
      lib.pyLib.module.symAddr("PyObject_Vectorcall")
    )

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
      # if message.kind.ord == 0:
      #   echo "open"
      # messageDict["headers"] = headersDict

      loadVectorcall()
      if pyObjectVectorcall.isNil:
        let info: PyObject = pyHook.callObject(
          getWebSocketUUID(websocket),
          event.ord,
          messageDict,
        )
        if info != nil and
            cast[pointer](info.privateRawPyObj) != cast[pointer](lib.pyLib.Py_None):
          result = info.to(int)
      else:
        var args = [
          nimValueToPy(getWebSocketUUID(websocket)),
          nimValueToPy(event.ord),
          messageDict.privateRawPyObj,
        ]
        let info = pyObjectVectorcall(
          pyHook.privateRawPyObj,
          addr args[0],
          args.len.csize_t,
          nil,
        )
        decRef args[0]
        decRef args[1]
        if info.isNil:
          raisePythonError()
        try:
          if cast[pointer](info) != cast[pointer](lib.pyLib.Py_None):
            pyValueToNim(info, result)
        finally:
          decRef info
    finally:
      gil.release_gil(gilState)


proc hook*(p: PyObject): void =
  #[
    The exposed hook proc accepts a python _callable_, called upon
    message events.
  ]#
  # Keep the function as the callable.
  gil.ensure_gil_procs()
  loadVectorcall()
  pythonHookRegistered.store(true, moRelease)
  pyHook = p
  if p == nil:
    pythonHookRegistered.store(false, moRelease)
