"""Talk to a standalone PocketSocket CLI server from a terminal."""

import argparse
import asyncio

import websockets


async def chat(uri, name):
    async with websockets.connect(uri) as socket:
        print(f"Connected to {uri} as {name}. Press Ctrl+C to quit.")

        async def receive_messages():
            async for message in socket:
                print(f"\n{message}")
                print("> ", end="", flush=True)

        receiver = asyncio.create_task(receive_messages())
        try:
            while True:
                message = await asyncio.to_thread(input, "> ")
                await socket.send(f"{name}: {message}")
        finally:
            receiver.cancel()


def main():
    parser = argparse.ArgumentParser(description="PocketSocket CLI chat client")
    parser.add_argument("--name", default="client", help="name shown to other clients")
    parser.add_argument("--address", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()

    uri = f"ws://{args.address}:{args.port}/ws/"
    try:
        asyncio.run(chat(uri, args.name))
    except (KeyboardInterrupt, EOFError):
        pass


if __name__ == "__main__":
    main()
