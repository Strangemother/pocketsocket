# SocketSpy Pocketsocket PoC

This is a one-shot smoke and fuzz test against the compiled Pocketsocket CLI.
It does not import the Python package. The target is started with `--echo`, so
SocketSpy can connect, send finite mutations, and receive responses.

## Run

Build the native CLI first if `dist/` is empty:

```bash
(cd server && nimble build)
```

Then provide SocketSpy either as an installed command or as a local checkout:

```bash
SOCKETSPY_REPO=/path/to/socketspy ./tools/socketspy-poc/run.sh
```

For the checkout used during development:

```bash
SOCKETSPY_REPO=/tmp/socketspy-review ./tools/socketspy-poc/run.sh
```

The runner calls `prepare-socketspy.sh`, which reuses the ignored
`output/socketspy-bin` when present. If it is missing, the helper uses an
installed `socketspy`, copies `SOCKETSPY_BIN=/path/to/socketspy`, or compiles
from `SOCKETSPY_REPO=/path/to/socketspy`. `POCKETSOCKET_CLI` selects a
different Pocketsocket binary. Override `PORT`, `MUTATIONS`, or `OUTPUT_DIR`
when needed.

## Outputs

Results are written to `tools/socketspy-poc/output/` by default:

- `fuzz-text.txt`
- `fuzz-json.json`
- `fuzz-html.html`
- `fuzz-sarif.sarif`
- `fuzz-junit.xml`
- `pocketsocket.log`
- `run.txt`

Reports and logs in the output directory are kept in Git for inspection. Only
the locally compiled `output/socketspy-bin` is ignored.

An exit status of 2 means SocketSpy found a condition at its configured
severity threshold; the reports are still retained. Exit status 1 or a
timeout means the PoC itself failed to run.