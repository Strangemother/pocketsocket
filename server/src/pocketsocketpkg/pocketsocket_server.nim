#[
  The primary interface for the pocketsocket app, connecting to the ingress
  and service.
]#

# This is just an example to get you started. A typical hybrid package
# uses this file as the main entry point of the application.

import nimpy
import nimpy/py_lib as lib
import service
import hook
import ../mummy


proc hook*(p: PyObject): int {.exportpy.} =
  # Keep the function as the callable.
  hook.hook(p)


proc send_all*(etype: MessageKind, data: string, origin_uuid: PyObject): int {.exportpy.} =
  #[ send data:String of type:Message, originating from the uuid ]#
  var uuid: uint64 = 0
  if cast[pointer](origin_uuid) != cast[pointer](lib.pyLib.Py_None):
    # We have a uuid.
    uuid = origin_uuid.to(uint64)
  return service.send_all(etype, data, uuid)


proc send*(uuid: uint64, etype: MessageKind, data: string): int {.exportpy.} =
  #[ Send data to a single connected client.

     uuid is taken as a plain integer rather than a PyObject: this is the
     hottest exported call, and letting nimpy unbox it directly avoids
     allocating a wrapper per message.

     return 0 on success, 1 if the uuid is not connected.
  ]#
  return service.send(uuid, etype, data)


proc close_client*(uuid: uint64): void {.exportpy.} =
  #[ Close a single connection and drop it from the registry. ]#
  service.close_remove_client(uuid)


proc set_broadcast_mode*(mode: bool): void {.exportpy.} =
  #[ When enabled, every inbound message is fanned out to all other clients
     by Nim directly, with no python involvement. ]#
  service.set_broadcast_mode(mode)


proc set_echo_mode*(mode: bool): void {.exportpy.} =
  #[ When enabled, every inbound message is reflected back to its sender by
     Nim directly, with no python involvement. ]#
  service.set_echo_mode(mode)


proc set_print_mode*(mode: bool): void {.exportpy.} =
  #[ Enable per-event logging. Off by default: it is a write syscall per
     message. ]#
  service.set_print_mode(mode)


proc run_blocking_server*(
    address: string = "127.0.0.1",
    port: int = 8090,
    worker_threads: int = 0,
    max_message_len: int = 64 * 1024,
    max_body_len: int = 1024 * 1024,
    tcp_no_delay: bool = true
  ): void {.exportpy.} =
  #[ Start serving and block.

     worker_threads: 0 uses mummy's default of countProcessors() * 10, which
     oversubscribes small hosts. Set it explicitly to tune.
     max_message_len: largest inbound websocket message accepted, in bytes.
  ]#
  service.run_blocking_server(address, port, worker_threads,
                              max_message_len, max_body_len, tcp_no_delay)


proc shutdown_server*(): void {.exportpy.} =
  service.shutdown_server()
