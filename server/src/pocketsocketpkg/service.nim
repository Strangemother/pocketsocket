# This is just an example to get you started. A typical hybrid package
# uses this file as the main entry point of the application.

# import os
import std/locks, std/times, std/monotimes, std/cpuinfo
# import asyncdispatch
# import nimpy
#import terminal
# import nimpy/py_lib as lib
import mummy, mummy/routers
import submodule

from broadcast import websocketHandler_broadcast
import broadcast
import ingress
import gil
import config


var
  lock: Lock # The lock for global memory
  # router: Router
  server: Server
  # receiveThread: Thread[void]
  # pyHook: PyObject
  wake_time: MonoTime = getMonoTime()


# Remember to initialize the lock.
initLock(lock)


proc send_all*(message_kind: MessageKind, message_data: string, exclude_uuid: uint64): int =
  #[ Send a message to _all_ clients. Provide an exclude for ignoring the
    receiver]#
  # The connected clients are owned by `broadcast`, which registers them as
  # they connect.
  return broadcast.locked_send_all(message_kind, message_data, exclude_uuid)


proc send*(uuid: uint64, message_kind: MessageKind, message_data: string): int =
  #[ Send a message to the target UUID websocket, with the _kind_ being the
     message type, such as 0 for text.

     return int for success - 0 being ok, any other integer representing a
     error code (typically 1)
  ]#
  return broadcast.locked_send(uuid, message_kind, message_data)


proc close_remove_client*(uuid: uint64): void =
  broadcast.locked_close_remove_client(uuid)


proc ctrlc() {.noconv.} =
  echo "Ctrl+C fired!"
  server.close()


proc shutdown_server*(): void =
  echo "nim::shutdown_server"
  server.close()


proc poke_wake_time*(): void =
  wake_time = getMonoTime()


proc set_broadcast_mode*(mode:bool): void =
  config.set_broadcast_mode(mode)


proc set_echo_mode*(mode:bool): void =
  config.set_echo_mode(mode)


proc set_print_mode*(mode:bool = false): void =
  config.set_print_mode(mode)


proc run_blocking_server*(
    address: string = "127.0.0.1",
    port: int = 8090,
    worker_threads: int = 0,
    max_message_len: int = 64 * 1024,
    max_body_len: int = 1024 * 1024,
    tcp_no_delay: bool = true
  ): void =
  when isMainModule:
    echo(getWelcomeMessage())
  submodule.setLoadedTemplate("./server/templates/index.html")
  # mummy defaults to countProcessors() * 10 workers, which oversubscribes
  # small hosts badly. 0 keeps that default, anything else is taken literally.
  let workers =
    if worker_threads > 0: worker_threads
    else: max(countProcessors() * 10, 1)
  server = newServer(
      ingress.router,
      websocketHandler = broadcast.websocketHandler_broadcast,
      workerThreads = workers,
      maxMessageLen = max_message_len,
      maxBodyLen = max_body_len,
      tcpNoDelay = tcp_no_delay,
    )
  echo "Serving on http://", address, ":", port
  setControlCHook(ctrlc)
  let total_time: Duration = getMonoTime() - wake_time
  echo "TTL: ", $total_time
  # serve() blocks this (python) thread; hand the GIL back so mummy's worker
  # threads are able to acquire it when calling the python hook.
  let threadState = gil.save_thread()
  try:
    server.serve(Port(port), address)
  finally:
    gil.restore_thread(threadState)
  echo "Serve complete"
