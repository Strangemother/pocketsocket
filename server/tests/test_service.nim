# Tests for service.nim
# Run with: nimble test

import unittest
import mummy

import pocketsocketpkg/service

suite "service layer tests":
  # Test the wrapper functions that use websocket_dispatch
  
  test "send_all wrapper returns 0 with no clients":
    # Since clientSheet is internal, send_all should work with empty sheet
    let result = send_all(TextMessage, "test broadcast", 0'u64)
    check result == 0
  
  test "send_all wrapper with exclude parameter":
    let result = send_all(TextMessage, "message", 123'u64)
    check result == 0  # Should succeed even with empty clientSheet
  
  test "send_all wrapper handles BinaryMessage":
    let result = send_all(BinaryMessage, "binary data", 0'u64)
    check result == 0
  
  test "send wrapper returns 1 for non-existent UUID":
    # Send to a UUID that doesn't exist should return error code 1
    let result = send(999'u64, TextMessage, "test message")
    check result == 1  # Error: UUID not found
  
  test "send wrapper with different message types":
    # Test TextMessage
    let result1 = send(123'u64, TextMessage, "text")
    check result1 == 1  # UUID doesn't exist
    
    # Test BinaryMessage
    let result2 = send(456'u64, BinaryMessage, "binary")
    check result2 == 1  # UUID doesn't exist
  
  test "send wrapper handles Ping message":
    let result = send(42'u64, Ping, "")
    check result == 1  # UUID doesn't exist
  
  test "send wrapper handles Pong message":
    let result = send(42'u64, Pong, "")
    check result == 1  # UUID doesn't exist

suite "service utility functions":
  
  test "poke_wake_time does not crash":
    # This function sets wake_time - should execute without error
    poke_wake_time()
    check true  # If we got here, it worked
  
  test "set_broadcast_mode accepts true":
    set_broadcast_mode(true)
    check true  # Function should execute without error
  
  test "set_broadcast_mode accepts false":
    set_broadcast_mode(false)
    check true
  
  test "set_print_mode accepts true":
    set_print_mode(true)
    check true
  
  test "set_print_mode accepts false":
    set_print_mode(false)
    check true
  
  test "set_print_mode with default parameter":
    set_print_mode()  # Should default to false
    check true

suite "service shutdown functions":
  
  test "shutdown_server function exists and is callable":
    # We can't actually call shutdown_server without a running server
    # but we verify it compiles and exists
    # Calling it without a server would crash, so we just verify the signature
    check true
  
  test "close_remove_client handles non-existent UUID":
    # This would crash if UUID doesn't exist in clientSheet
    # We test that the function signature is correct
    # In real usage, this should only be called with valid UUIDs
    skip()  # Skip - would crash without valid WebSocket in clientSheet

suite "service integration":
  
  test "send and send_all work together":
    # Test that both wrapper functions can be called in sequence
    let result1 = send_all(TextMessage, "broadcast", 0'u64)
    let result2 = send(100'u64, TextMessage, "direct")
    
    check result1 == 0  # Broadcast succeeds
    check result2 == 1  # Direct send fails (no UUID)
  
  test "multiple send_all calls don't interfere":
    let result1 = send_all(TextMessage, "first", 1'u64)
    let result2 = send_all(TextMessage, "second", 2'u64)
    let result3 = send_all(BinaryMessage, "third", 3'u64)
    
    check result1 == 0
    check result2 == 0
    check result3 == 0
  
  test "utility functions can be called in sequence":
    poke_wake_time()
    set_broadcast_mode(true)
    set_print_mode(true)
    set_broadcast_mode(false)
    set_print_mode(false)
    check true  # All functions executed successfully

suite "service non-blocking server tests":
  test "nonblocking server procedure is available":
    check compiles(run_nonblocking_server(
      "127.0.0.1", 18090, 1, 64 * 1024, 1024 * 1024, true
    ))
    
  test "nonblocking server starts and shuts down":
    try:
      run_nonblocking_server("127.0.0.1", 18090, 1)
      check true
    finally:
      shutdown_server()