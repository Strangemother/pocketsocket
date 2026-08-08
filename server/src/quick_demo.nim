import unittest
import mummy
import pocketsocketpkg/socket_tools

let ws1 = WebSocket()
let ws2 = WebSocket()

echo getWebSocketUUID(ws1) == getWebSocketUUID(ws2)