"""
WORKING EXAMPLE: Polling-based WebSocket event handling.

KEY INSIGHT: The polling must happen on the Python MAIN thread!
Run the server in a background thread and poll from main.
"""
import sys
sys.path.insert(0, '/workspaces/pocketsocket-2/package')

import pocketsocket
import threading
import time

def handle_event(uuid, event_type, message_kind, message_data):
    """Handle a WebSocket event"""
    if event_type == 0:
        print(f"✓ Client {uuid} connected", flush=True)
    elif event_type == 1:
        print(f"✓ Message: {message_data!r}", flush=True)
        # Echo back
        pocketsocket.send(uuid, message_kind, message_data)
    elif event_type == 2:
        print(f"✓ Client {uuid} disconnected", flush=True)

def run_server():
    """Run server in background thread"""
    print("[SERVER] Starting on 127.0.0.1:8091...", flush=True)
    pocketsocket.run_blocking_server('127.0.0.1', 8091)

# Initialize queue
print("Initializing event queue...", flush=True)
pocketsocket.startEventQueue()

# Start server in background thread
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Poll in main thread
print("Starting event polling in MAIN thread...", flush=True)
time.sleep(0.5)  # Let server start

poll_count = 0
try:
    while True:
        events = pocketsocket.pollEvents()
        poll_count += 1
        
        if poll_count % 1000 == 0:
            print(f"[POLL] {poll_count} polls", flush=True)
        
        if events:
            print(f"[POLL] Got {len(events)} events!", flush=True)
            for uuid, etype, kind, data in events:
                handle_event(uuid, etype, kind, data)
        
        time.sleep(0.001)  # 1ms
except KeyboardInterrupt:
    print("\nShutting down...")
