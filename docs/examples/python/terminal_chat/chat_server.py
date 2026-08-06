"""Run a tiny PocketSocket terminal chat server."""

from pocketsocket import pocketsocket_server as pocketsocket


ADDRESS = "127.0.0.1"
PORT = 8090


def chat_hook(uuid, event_type, event):
    if event_type == 0:
        print(f"client {uuid} connected", flush=True)
        return

    if event_type == 1:
        pocketsocket.send_all(event["kind"], event["data"], uuid)
        return

    if event_type == 3:
        print(f"client {uuid} disconnected", flush=True)


def main():
    pocketsocket.hook(chat_hook)
    print(f"Chat server listening on ws://{ADDRESS}:{PORT}/ws/", flush=True)
    pocketsocket.run_blocking_server(ADDRESS, PORT)


if __name__ == "__main__":
    main()
