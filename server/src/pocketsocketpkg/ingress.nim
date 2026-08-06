import mummy, mummy/routers
import std/strutils
import submodule

var
  # lock: Lock # The lock for global memory
  router*: Router


proc upgradeHandler(request: Request) =
  #[
    Given a new request, assume a websocket and upgrade.
  ]#
  let websocket = request.upgradeToWebSocket()
  # Send the headers back down the pipe.
  websocket.send($request.headers)


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


router.get("/**", indexHandler)
