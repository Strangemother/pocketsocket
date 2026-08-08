import std/hashes
import mummy

proc getWebSocketUUID*(websocket: WebSocket): uint64 =
    result = cast[uint64](hash(websocket))