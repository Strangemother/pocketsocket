# Tests for websocket_dispatch.nim
# Run with: nimble test

import unittest
import std/tables
import mummy

import pocketsocketpkg/websocket_dispatch

# Note: MessageKind is an enum from mummy that includes:
# - TextMessage (for text messages)
# - BinaryMessage (for binary messages)
# - Ping, Pong (for WebSocket control frames)
# We test the dispatch logic without actual WebSocket connections

suite "websocket_dispatch tests":
  
  test "send returns 1 when UUID does not exist in clientSheet":
    var clientSheet = initTable[uint64, WebSocket]()
    let result = send(clientSheet, 999'u64, TextMessage, "test message")
    check result == 1  # Error code for unknown UUID
  
  test "send returns 1 for any missing UUID":
    var clientSheet = initTable[uint64, WebSocket]()
    let result = send(clientSheet, 123'u64, TextMessage, "another test")
    check result == 1  # Should return 1 (error) for unknown UUID
  
  test "send_all returns 0 with empty clientSheet":
    var clientSheet = initTable[uint64, WebSocket]()
    # Empty table should still return 0 (success, just no recipients)
    let result = send_all(clientSheet, TextMessage, "broadcast message", 0'u64)
    check result == 0
  
  test "send_all handles exclude_uuid parameter":
    # This tests the logic - with empty table it should still work
    var clientSheet = initTable[uint64, WebSocket]()
    let excludeUuid = 123'u64
    let result = send_all(clientSheet, TextMessage, "test", excludeUuid)
    check result == 0  # Should return 0 (success)
  
  test "send handles BinaryMessage MessageKind":
    var clientSheet = initTable[uint64, WebSocket]()
    let result = send(clientSheet, 1'u64, BinaryMessage, "binary data")
    check result == 1  # UUID doesn't exist, should return error
  
  test "send_all with BinaryMessage MessageKind on empty sheet":
    var emptySheet = initTable[uint64, WebSocket]()
    let result = send_all(emptySheet, BinaryMessage, "binary broadcast", 0'u64)
    check result == 0  # Should succeed with 0 recipients
  
  test "send_all with different exclude values":
    var clientSheet = initTable[uint64, WebSocket]()
    # Test with no exclusion (0)
    let result1 = send_all(clientSheet, TextMessage, "hello", 0'u64)
    check result1 == 0
    
    # Test with specific exclusion
    let result2 = send_all(clientSheet, TextMessage, "hello", 999'u64)
    check result2 == 0
  
  test "send with Ping MessageKind":
    var clientSheet = initTable[uint64, WebSocket]()
    let result = send(clientSheet, 42'u64, Ping, "")
    check result == 1  # UUID doesn't exist
  
  test "send with Pong MessageKind":
    var clientSheet = initTable[uint64, WebSocket]()
    let result = send(clientSheet, 42'u64, Pong, "")
    check result == 1  # UUID doesn't exist
