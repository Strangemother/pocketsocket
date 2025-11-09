#!/usr/bin/env python3
"""
WebSocket client to test the multi-process server.
"""

import asyncio
import websockets

async def test_client():
    uri = "ws://localhost:8091/ws"
    
    print(f"Connecting to {uri}...")
    async with websockets.connect(uri) as websocket:
        print("Connected!")
        
        # Send a message
        message = "Hello from Python client!"
        print(f"Sending: {message}")
        await websocket.send(message)
        
        # Receive response
        response = await websocket.recv()
        print(f"Received: {response}")
        
        # Send another message
        message2 = "Second message"
        print(f"Sending: {message2}")
        await websocket.send(message2)
        
        response2 = await websocket.recv()
        print(f"Received: {response2}")
        
        print("\nTest complete!")

if __name__ == "__main__":
    asyncio.run(test_client())
