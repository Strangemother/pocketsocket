"""Connect to the PocketSocket terminal chat server."""

import asyncio

import websockets


ADDRESS = "127.0.0.1"
PORT = 8090


async def chat():
    async with websockets.connect(f"ws://{ADDRESS}:{PORT}/ws/") as socket:
        print("Connected. Type a message and press Enter. Use Ctrl+C to quit.")

        async def receive_messages():
            async for message in socket:
                print(f"\n{message}")
                print("> ", end="", flush=True)

        receiver = asyncio.create_task(receive_messages())
        try:
            while True:
                message = await asyncio.to_thread(input, "> ")
                await socket.send(message)
        finally:
            receiver.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(chat())
    except (KeyboardInterrupt, EOFError):
        pass
