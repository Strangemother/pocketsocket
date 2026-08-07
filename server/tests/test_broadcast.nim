# Tests for broadcast.nim
# Run with: nimble test

import unittest
import pocketsocketpkg/broadcast
from mummy import Message, TextMessage, WebSocket, OpenEvent

suite "broadcast tests":
    
    test "send_all returns 0 with no clients":
        let result = send_all(TextMessage, "test message", 0'u64)
        check result == 0  # Should succeed even with empty clientSheet
    
    test "send_all with exclude parameter":
        let result = send_all(TextMessage, "message", 123'u64)
        check result == 0  # Should succeed even with empty clientSheet
    
    test "locked_send_all returns 0 with no clients":
        let result = locked_send_all(TextMessage, "test message", 0'u64)
        check result == 0
    
    test "locked_send returns 1 for non-existent UUID":
        let result = locked_send(999'u64, TextMessage, "test message")
        check result == 1  # Error: UUID not found

    test "websocketHandler_broadcast accepts OpenEvent":
        let message = Message(kind: TextMessage, data: "test message")
        let ws = WebSocket()  # Create a dummy WebSocket instance
        websocketHandler_broadcast(ws, OpenEvent, message)
        check true