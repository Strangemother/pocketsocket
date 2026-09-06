import ../mummy, ../mummy/routers
import std/strutils
import pocketsocketpkg/socket_tools
import submodule
import connection_context

var
  # lock: Lock # The lock for global memory
  router*: Router

proc registerWebSocket*(request: Request, websocket: WebSocket): uint64 =
  #[
    Register a new websocket connection.
  ]#
  let uuid = getWebSocketUUID(websocket)
  registerContext(uuid, ConnectionContext(
    headers: request.headers,
    remoteAddress: request.remoteAddress,
    path: request.path
  ))
  result = uuid

proc upgradeHandler(request: Request) =
  #[
    Given a new request, assume a websocket and upgrade.
  ]#
  let websocket: WebSocket = request.upgradeToWebSocket()
  let uuid: uint64 = registerWebSocket(request, websocket)
  # Send the headers back down the pipe.
  # websocket.send($request.headers)


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
  echo "Responding with index.html"
  request.respond(200, headers, getCachedLocalFileContents("./index.html"))


router.get("/**", indexHandler)
