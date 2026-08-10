# Autobahn WebSocket Conformance Suite

This suite runs the compiled `pocketsocket-cli` as the WebSocket server and
uses the official Autobahn Testsuite Docker image in `fuzzingclient` mode. That
is the mode Autobahn documents for testing WebSocket servers.

The runner starts Pocketsocket, waits for its TCP port, then runs:

```text
docker run --rm \
  --add-host host.docker.internal:host-gateway \
  -v <output>/config:/config:ro \
  -v <output>:/reports \
  crossbario/autobahn-testsuite:25.10.1 \
  wstest --mode fuzzingclient --spec /config/fuzzingclient.json
```

Inside the container, `host.docker.internal` points back to the machine
running the compiled CLI. The server binds to `0.0.0.0` so Docker can reach it.

## Run

Linux/macOS/WSL:

```bash
./tools/autobahn/run.sh
```

PowerShell:

```powershell
.\tools\autobahn\run.ps1
```

Command Prompt:

```bat
tools\autobahn\run.cmd
```

The scripts expect `dist/pocketsocket-cli` on Unix or
`dist/pocketsocket-cli.exe` on Windows. Override it with
`POCKETSOCKET_CLI=/path/to/binary` or `$env:POCKETSOCKET_CLI`.

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