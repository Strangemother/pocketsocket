#!/usr/bin/env python3
"""
Test the multi-process architecture with hook functionality.

This demonstrates the seamless user experience:
1. Register a hook function
2. Start the server (blocks, spawns background process)
3. Hook is called from Python main thread for each event
"""

import sys
sys.path.insert(0, 'python')

import pocketsocket

# Track events for verification
events_received = []

def my_hook(uuid, event_type, message_kind, data):
    """
    User hook - called from Python main thread for each WebSocket event.
    
    event_type: 0=connect, 1=message, 2=disconnect, 3=error
    """
    event_names = ['CONNECT', 'MESSAGE', 'DISCONNECT', 'ERROR']
    event_name = event_names[event_type] if event_type < len(event_names) else 'UNKNOWN'
    
    print(f"\n[HOOK] {event_name}")
    print(f"  UUID: {uuid}")
    print(f"  Message Kind: {message_kind}")
    print(f"  Data: {repr(data[:100] if data else '')}")
    
    events_received.append({
        'uuid': uuid,
        'event': event_type,
        'kind': message_kind,
        'data': data
    })
    
    # Echo messages back
    if event_type == 1:  # Message event
        response = f"Echo: {data}"
        print(f"  Sending response: {repr(response[:50])}")
        pocketsocket.send(uuid, 0, response)  # 0 = TextMessage

print("=" * 60)
print("pocketsocket Multi-Process Architecture Test")
print("=" * 60)
print("\nThis test demonstrates:")
print("1. Hook function registered in Python")
print("2. Server runs in separate Nim process")
print("3. Events sent via IPC to Python main thread")
print("4. Hook called seamlessly from main thread")
print("\n" + "=" * 60)

# Register the hook
print("\nRegistering hook...")
pocketsocket.hook(my_hook)

# Start server - this blocks and enters IPC event loop
print("Starting server on 0.0.0.0:8091...")
print("\nTo test:")
print("  1. Open: http://localhost:8091/")
print("  2. In browser console:")
print("     ws = new WebSocket('ws://localhost:8091/ws')")
print("     ws.onmessage = e => console.log('Received:', e.data)")
print("     ws.send('Hello from browser!')")
print("\n" + "=" * 60 + "\n")

try:
    pocketsocket.start_server('0.0.0.0', 8091)
except KeyboardInterrupt:
    print("\n\nShutting down...")
    print(f"Total events received: {len(events_received)}")
