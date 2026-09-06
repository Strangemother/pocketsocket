# import std/hashes
import ../mummy

proc getWebSocketUUID*(websocket: WebSocket): uint64 =
    result = websocket.uuid
    # result = cast[uint64](hash(websocket))