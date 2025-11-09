"""
Test the polling-based WebSocket event handling.
"""
import sys
sys.path.insert(0, '/workspaces/pocketsocket-2/python')

import pocketsocket
import threading
import time

def handle_event(uuid, event_type, message_kind, message_data):
    """Handle a WebSocket event"""
    print(f"[EVENT] type={event_type}, kind={message_kind}, uuid={uuid}", flush=True)
    
    if event_type == 0:
        print(f"[EVENT] Client {uuid} connected", flush=True)
    elif event_type == 1:
        print(f"[EVENT] Message received: {message_data!r}", flush=True)
        # Echo back to client
        pocketsocket.send(uuid, message_kind, message_data)
        print(f"[EVENT] Echoed back to client", flush=True)
    elif event_type == 2:
        print(f"[EVENT] Client {uuid} disconnected", flush=True)

def poll_loop():
    """Poll for WebSocket events in a separate thread"""
    print("[POLL] Starting event polling thread...", flush=True)
    poll_count = 0
    print("[POLL] Entering loop...", flush=True)
    while True:
        poll_count += 1
        if poll_count % 100 == 0:
            print(f"[POLL] Poll #{poll_count}", flush=True)
        try:
            events = pocketsocket.pollEvents()
            if events:
                print(f"[POLL] Got {len(events)} events!", flush=True)
                for uuid, etype, kind, data in events:
                    handle_event(uuid, etype, kind, data)
        except Exception as e:
            print(f"[POLL] Error: {e}", flush=True)
            import traceback
            traceback.print_exc()
        time.sleep(0.001)  # 1ms poll interval

# Start event queue
print("Initializing event queue...", flush=True)
pocketsocket.startEventQueue()

# Start polling thread
print("Starting polling thread...", flush=True)
poll_thread = threading.Thread(target=poll_loop, daemon=False)  # NOT daemon!
poll_thread.start()

# Give thread time to start
time.sleep(0.1)
print(f"Poll thread alive? {poll_thread.is_alive()}", flush=True)

# Start server
print("Starting WebSocket server on 127.0.0.1:8091...", flush=True)
pocketsocket.run_blocking_server('127.0.0.1', 8091)
