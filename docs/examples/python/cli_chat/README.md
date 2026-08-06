# Standalone CLI Chat

PocketSocket runs as a standalone binary bridge. Python is used only for the clients through the `websockets` package; there is no Python server or Python socket module.

Build and start the bridge from the repository root:

```bash
(cd server && nimble buildCliCI)
./dist/pocketsocket-cli-linux_amd64 --run --broadcast
```

Install the client dependency:

```bash
python3 -m pip install websockets
```

In two more terminals, run:

```bash
python3 examples/python/cli_chat/cli_chat.py --name alice
python3 examples/python/cli_chat/cli_chat.py --name bob
```

Type in either terminal. The standalone CLI broadcasts each message to the other client.
