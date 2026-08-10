# Autobahn WebSocket Conformance Suite

This suite tests an already-running Pocketsocket WebSocket server with the
official Autobahn Testsuite Docker image in `fuzzingclient` mode. That is the
mode Autobahn documents for testing WebSocket servers.

Start Pocketsocket by hand on `0.0.0.0`, then run the suite. The runner checks
the TCP port before starting:

```text
docker run --rm \
  --add-host host.docker.internal:host-gateway \
  -v <output>/config:/config:ro \
  -v <output>:/reports \
  crossbario/autobahn-testsuite:25.10.1 \
  wstest --mode fuzzingclient --spec /config/fuzzingclient.json
```

Inside the container, `host.docker.internal` points back to the machine
running Pocketsocket. The server must bind to `0.0.0.0` so Docker can reach it.

## Run

Linux/macOS/WSL:

```bash
dist/pocketsocket-cli --run --print \
  --template-dir server/templates --address 0.0.0.0 --port 18091 \
  --max-message 65536
```

In another terminal:

```bash
./tools/autobahn/run.sh
```

PowerShell:

```powershell
.\tools\autobahn\run.ps1
```

Command Prompt:

```bat
tools\autobahn\start-pocketsocket.cmd
tools\autobahn\run.cmd
```

The Windows helper starts `dist\pocketsocket-cli.exe` in a separate window.
Override its path with `POCKETSOCKET_CLI`. The test runners do not start or
stop Pocketsocket; stop the manually started process yourself after testing.

## Options

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `18091` | Host Pocketsocket port |
| `OUTPUT_DIR` | `tools/autobahn/reports` | Autobahn reports and server log |
| `AUTOBAHN_IMAGE` | `crossbario/autobahn-testsuite:25.10.1` | Docker image/tag |
| `AUTOBAHN_CONTAINER_NAME` | `pocketsocket-autobahn` | Temporary container name |
| `POCKETSOCKET_CLI` | `dist/pocketsocket-cli*` | Compiled server path |

The Autobahn config excludes cases `9.*`, `12.*`, and `13.*`, matching the
project's documented Docker example: mass/performance tests and compression
tests are excluded by default. Remove those entries from the generated config
if the implementation is ready to evaluate those areas.

Reports are written below `tools/autobahn/reports/` and are kept in Git. The
config under `reports/config/` is generated for the selected port.