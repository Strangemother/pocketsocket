#[
  Runtime flags shared across the server modules.

  Lives in its own module so `websocket_dispatch` can read `print_mode`
  without importing `broadcast` (which imports it back).

  Nothing here is locked: both flags are plain bools written once during
  configuration, before the server starts accepting connections.
]#

var
  broadcast_mode* = false
  echo_mode* = false
  print_mode* = false


proc set_broadcast_mode*(mode: bool = false): void =
  broadcast_mode = mode
  if print_mode:
    echo "broadcast_mode: ", mode


proc set_echo_mode*(mode: bool = false): void =
  echo_mode = mode
  if print_mode:
    echo "echo_mode: ", mode


proc set_print_mode*(mode: bool = false): void =
  print_mode = mode
