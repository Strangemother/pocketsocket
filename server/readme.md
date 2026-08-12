# PocketSocket server

The `server/` project contains the Nim implementation of PocketSocket.

It provides:

- the native Python extension, `pocketsocket_server`;
- the standalone `pocketsocket-cli` executable;
- the WebSocket service, hooks, dispatch, and supporting Nim modules.

The Python wrapper lives in `../package/` and is imported by users as
`pocketsocket`.

## 1. What it is

The directory layout is:

```text
server/
  src/         Nim application and library source
  tests/       Nim tests
  templates/   Runtime HTML assets
  setup.sh     Toolchain, dependency, and build setup
  pocketsocket.nimble
```

The native extension is written in Nim and exposes the implementation used by
the Python package. The standalone CLI is built from `src/pocketsocket.nim`.

## 2. How to test

From the repository root, run the complete Nim test suite:

```bash
cd /workspaces/pocketsocket-2/server
nimble test
```

The same command from inside `server/` is:

```bash
nimble test
```

Run the Python integration tests from the repository root:

```bash
cd /workspaces/pocketsocket-2
./package/tests/run.sh
```

If the Nim toolchain or dependencies are missing, run the setup script first.
It installs or reuses Nim, installs Nimble dependencies, builds the native
outputs, and runs a Python API smoke test:

```bash
cd /workspaces/pocketsocket-2
./server/setup.sh
```

## 3. How to compile

### Full setup and build

This is the recommended hot-start command after a new checkout or container
rebuild:

```bash
cd /workspaces/pocketsocket-2
./server/setup.sh
```

It produces:

```text
package/pocketsocket_server*.so   # Linux/macOS Python extension
package/pocketsocket_server*.pyd  # Windows Python extension
dist/pocketsocket-cli*             # Standalone CLI
```

### Rebuild only the Python extension

```bash
cd /workspaces/pocketsocket-2/server
nimble buildPyd
```

The extension is written to `../package/` with the active Python ABI suffix.

### Rebuild only the standalone CLI

```bash
cd /workspaces/pocketsocket-2/server
nimble build
```

The release CLI is written to `../dist/pocketsocket-cli-release`.
For a debug build, use:

```bash
nimble buildDebug
```

This writes `../dist/pocketsocket-cli-debug`.

### Build native outputs directly

The Windows batch build scripts are consolidated in `compile.py`:

```bash
cd /workspaces/pocketsocket-2/server
python compile.py
python compile.py exe lib
python compile.py exe --debug
python compile.py --all
```

With no output arguments, the script runs the prepared Nimble release tasks:
`nimble buildPyd` followed by `nimble build`. Use `exe`, `lib`, or `pyd` to
select outputs. `--release` is the default; `--debug` selects the debug build
tasks where available. `lib` remains a direct `nim` build because it has no
Nimble task. Setup recovery is enabled by default: if `nimble` is missing,
`setup.sh` runs before the build is retried. Use `--no-setup` to let the
missing command error normally. `--setup=True` is also accepted explicitly.

### Build a Python wheel

From the repository root:

```bash
cd /workspaces/pocketsocket-2
python3 package/build_whl.py
```

The wheel is written to `dist/` and includes the Python wrapper and compiled
native extension.

### Check the installed Nim toolchain

```bash
nim --version
nimble --version
```

If `nim` is not found, use the full setup command above. The setup script adds
the required toolchain paths for its own process.
