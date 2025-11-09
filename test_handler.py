"""
Test hook handler module.
This module will be loaded by Nim in its own thread.
"""

def hook_callback(uuid, event_type, message_kind, message_data):
    """
    Called when WebSocket events occur.
    
    Args:
        uuid: Client connection identifier (int)
        event_type: Event type (0=connect, 1=message, 2=disconnect)
        message_kind: Message kind (0=text, 1=binary)
        message_data: Message content (str)
    
    Returns:
        int: 0 for success
    """
    print(f"[HANDLER] Event: type={event_type}, kind={message_kind}, uuid={uuid}", flush=True)
    
    if event_type == 0:
        print(f"[HANDLER] Client {uuid} connected", flush=True)
    elif event_type == 1:
        print(f"[HANDLER] Received message: {message_data!r}", flush=True)
        # Echo back to the client
        import pocketsocket
        pocketsocket.send(uuid, message_kind, message_data)
    elif event_type == 2:
        print(f"[HANDLER] Client {uuid} disconnected", flush=True)
    
    return 0
