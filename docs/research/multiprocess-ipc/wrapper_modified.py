"""
Wrapper module for pocketsocket with multi-process architecture.

This module manages the standalone Nim server process and handles
IPC communication for event hooks.
"""

import socket
import subprocess
import json
import os
import sys
import atexit
from pathlib import Path
from pocketsocket import pocketsocket_server


# Global state
_hook_callback = None
_server_process = None
_ipc_socket = None
_ipc_server_socket = None


class IngressReceiver:
    uuid = None

    def __init__(self, uuid):
        self.uuid = uuid

    def recv(self, data):
        print('IngressReceiver::recv', data)

    def send(self, data):
        """Send a message to this socket
        """
        pocketsocket_server.send(self.uuid, 1, data)

    def broadcast(self, data):
        """Send a message to all clients, excluding self.
        """
        pocketsocket_server.send_all(1, data, self.uuid)


def hook(callback):
    """
    Register a Python callback function for WebSocket events.
    
    The callback will be called with:
        callback(uuid, event_type, message_kind, data)
    
    Where:
        uuid (int): Unique identifier for the WebSocket connection
        event_type (int): 0=connect, 1=message, 2=disconnect, 3=error
        message_kind (int): 0=text, 1=binary (only for message events)
        data (str): Message data (empty for connect/disconnect)
    
    Example:
        def my_hook(uuid, event_type, message_kind, data):
            if event_type == 1:  # Message received
                print(f"Received: {data}")
                pocketsocket.send(uuid, 0, data.upper())
        
        pocketsocket.hook(my_hook)
    """
    global _hook_callback
    _hook_callback = callback


def _cleanup():
    """Cleanup function to terminate server process on exit"""
    global _server_process, _ipc_server_socket
    
    if _server_process:
        print("Shutting down server process...")
        _server_process.terminate()
        try:
            _server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Server didn't terminate, killing...")
            _server_process.kill()
            _server_process.wait()
    
    if _ipc_server_socket:
        try:
            _ipc_server_socket.close()
        except:
            pass


def _find_server_binary():
    """Locate the standalone server binary"""
    # Try multiple possible locations
    candidates = [
        # Same directory as this Python file
        Path(__file__).parent / "pocketsocket_standalone_server",
        # In bin subdirectory
        Path(__file__).parent / "bin" / "pocketsocket_standalone_server",
        # In parent src directory (development)
        Path(__file__).parent.parent.parent / "src" / "pocketsocket_standalone_server",
    ]
    
    for path in candidates:
        if path.exists():
            return str(path)
    
    raise FileNotFoundError(
        "Could not find pocketsocket_standalone_server binary. "
        "Searched: " + ", ".join(str(p) for p in candidates)
    )





def start_server(address='0.0.0.0', port=8090):
    """
    Start the WebSocket server in a separate process.
    
    This function blocks and enters an IPC event loop, calling the
    registered hook function for each WebSocket event.
    
    Args:
        address (str): Address to bind to (default: '0.0.0.0')
        port (int): Port to listen on (default: 8090)
    
    Example:
        pocketsocket.hook(my_hook)
        pocketsocket.start_server('0.0.0.0', 8090)  # Blocks here
    """
    global _server_process
    
    # Register cleanup
    atexit.register(_cleanup)
    
    # Create IPC socket path
    sock_path = f"/tmp/pocketsocket_{os.getpid()}.sock"
    
    # Find server binary
    try:
        server_binary = _find_server_binary()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("\nPlease build the standalone server:", file=sys.stderr)
        print("  nim c -d:release src/pocketsocket_standalone_server.nim", file=sys.stderr)
        raise
    
    print(f"Using server binary: {server_binary}")
    
    # Create IPC socket FIRST, before launching server
    global _ipc_socket, _ipc_server_socket
    
    if os.path.exists(sock_path):
        os.remove(sock_path)
    
    _ipc_server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    _ipc_server_socket.bind(sock_path)
    _ipc_server_socket.listen(1)
    print(f"IPC socket listening on: {sock_path}")
    
    # Launch Nim server as subprocess
    _server_process = subprocess.Popen(
        [server_binary, sock_path, address, str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1  # Line buffered
    )
    
    print(f"Started server process (PID: {_server_process.pid})")
    
    # Start a thread to print server output
    import threading
    def print_server_output():
        try:
            for line in _server_process.stdout:
                print(f"[SERVER] {line.rstrip()}")
        except:
            pass
    
    output_thread = threading.Thread(target=print_server_output, daemon=True)
    output_thread.start()
    
    # Wait for server to connect and enter event loop
    print("Waiting for server process to connect...")
    _ipc_socket, _ = _ipc_server_socket.accept()
    print("Server connected via IPC, starting event loop...")
    
    # Enter IPC event loop (BLOCKS HERE)
    buffer = ""
    try:
        while True:
            data = _ipc_socket.recv(4096).decode('utf-8')
            
            if not data:
                print("Server process disconnected")
                break
            
            buffer += data
            
            # Process complete JSON lines
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                
                if not line.strip():
                    continue
                
                try:
                    event = json.loads(line)
                    
                    # Call user's Python hook if registered
                    if _hook_callback:
                        _hook_callback(
                            event['uuid'],
                            event['event'],
                            event['kind'],
                            event['data']
                        )
                
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON from server: {line[:100]}")
                    print(f"Error: {e}")
                except Exception as e:
                    print(f"Error calling hook: {e}")
                    import traceback
                    traceback.print_exc()
    
    except KeyboardInterrupt:
        print("\nReceived interrupt, shutting down...")
    except Exception as e:
        print(f"IPC event loop error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if _ipc_socket:
            _ipc_socket.close()
        _cleanup()
        # Clean up socket file
        if os.path.exists(sock_path):
            os.remove(sock_path)


def shutdown_server():
    """
    Shutdown the server process gracefully.
    """
    _cleanup()


# Backwards compatibility - expose original blocking server
def run_blocking_server(address='0.0.0.0', port=8090):
    """
    Legacy function - use start_server() instead.
    This now uses the multi-process architecture.
    """
    start_server(address, port)
