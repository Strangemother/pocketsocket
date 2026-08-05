# Browser Chat

This demo uses the standalone PocketSocket CLI as a WebSocket bridge and a tiny browser client. Open this page in multiple browser tabs to see messages move between clients.

## Start the bridge

From the repository root:

```bash
nimble buildCliCI
./dist/pocketsocket-cli-linux_amd64 --run --broadcast
```

On Windows, run the generated `.exe` with `--run --broadcast` instead.

## Serve the page

In this folder, start Python's static file server:

```bash
cd examples/python/web_chat
python -m http.server 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in two or more tabs, click **Connect**, and send messages.
