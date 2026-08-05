# Python Terminal Chat

This version runs the PocketSocket server from Python and connects with a small terminal client.

Install the client dependency:

```bash
python3 -m pip install websockets
```

Start the server:

```bash
PYTHONPATH=python python3 examples/python/terminal_chat/chat_server.py
```

In two more terminals, run:

```bash
python3 examples/python/terminal_chat/chat_client.py
```

The server broadcasts each message to the other connected clients.
