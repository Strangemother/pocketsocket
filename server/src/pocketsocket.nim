# Standalone WebSocket server. No Python involved: this binary links against
# libc only.
let doc = """
pocketsocket - a small, fast WebSocket server

Usage:
  pocketsocket --run [options]
  pocketsocket (-h | --help)
  pocketsocket --version

Options:
  -h --help             Show this screen.
  --version             Show version.
  --run                 Run the server.
  -a --address=<addr>   Bind address [default: 127.0.0.1].
  -p --port=<port>      Bind port [default: 8090].
  -t --template-dir=<dir>  Template directory [default: ].
  --echo                Reflect every message back to its sender.
  --broadcast           Relay every message to all other clients.
  --print               Log connections and messages to stdout.
  --workers=<n>         Worker threads. 0 uses mummy's default of
                        countProcessors() * 10 [default: 0].
  --max-message=<n>     Largest inbound message in bytes [default: 65536].

Examples:
  pocketsocket --run --echo
  pocketsocket --run --broadcast --address 0.0.0.0 --port 9000
"""

import std/strutils
import docopt
import pocketsocketpkg/service
import std/dirs 
import std/paths

const packageVersion = staticRead("../VERSION").strip()

let args = docopt(doc, version = "PocketSocket " & packageVersion)

if args["--run"]:
  service.poke_wake_time()

  if args["--print"]:
    service.set_print_mode(true)
  if args["--broadcast"]:
    service.set_broadcast_mode(true)
  if args["--echo"]:
    service.set_echo_mode(true)
  if args["--template-dir"]:
    let dir = $args["--template-dir"]
    let path = Path(dir)
    if dir.len != 0 and dirExists(path):
      echo "Setting template directory: ", dir
      service.set_template_dir(dir)
    else:
      echo "Template directory does not exist: ", dir, " l: ", dir.len
      quit(1)
  else:
    echo "No template directory specified; using default templates."
    

  service.run_blocking_server(
      address = $args["--address"],
      port = parseInt($args["--port"]),
      worker_threads = parseInt($args["--workers"]),
      max_message_len = parseInt($args["--max-message"]),
    )