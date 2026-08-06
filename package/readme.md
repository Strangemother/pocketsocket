# PocketSocket Python package

The `package/` project contains the public Python interface for PocketSocket.

It provides:

- the `pocketsocket` importable Python package;
- the Python callback and server API;
- Python integration tests;
- the build driver and Hatch build hook used to create wheels.

The WebSocket implementation and native extension are written in Nim under
`../server/`. The compiled extension is imported internally as
`pocketsocket_server`, while users import the public wrapper as `pocketsocket`.

## 1. What it is

The package layout is:

```text
package/
  pocketsocket/       Public Python wrapper
  tests/              Python integration tests
  build_whl.py        Full native build and wheel driver
  hatch_build.py      Hatch wheel hook for native artifacts
```

The public API includes server lifecycle functions, callback hooks, message
sending, client shutdown, and constants for connection and message events.

Minimal server example:

```python
import pocketsocket


def ingress(uuid, event_type, event):
    if event_type == pocketsocket.MESSAGE:
        pocketsocket.send(uuid, event["kind"], event["data"])


pocketsocket.hook(ingress)
pocketsocket.run_blocking_server("127.0.0.1", 8090)
```

## 2. How to test

The Python tests require the native extension to exist in `package/`. From the
repository root, build it first if necessary:

```bash
cd /workspaces/pocketsocket-2
./server/setup.sh
```

Run the focused Python integration test suite:

```bash
cd /workspaces/pocketsocket-2
./package/tests/run.sh
```

The same runner can be invoked from inside `package/`:

```bash
cd /workspaces/pocketsocket-2/package
./tests/run.sh
```

Run an individual test directly from the repository root:

```bash
cd /workspaces/pocketsocket-2
python3 package/tests/test_module_loading.py
```

For the full native test suite, use the server development instructions:

```bash
cd /workspaces/pocketsocket-2/server
nimble test
```

## 3. How to develop and compile

### Install the package in editable mode

From the repository root, install the package and development dependency
(`hatch`):

```bash
cd /workspaces/pocketsocket-2
python3 -m pip install -e ".[dev]"
```

A normal Python install does not compile Nim automatically. Build the native
extension explicitly with:

```bash
cd /workspaces/pocketsocket-2
./server/setup.sh
```

This also builds the standalone CLI and runs the Python API smoke test.

### Rebuild only the native Python extension

```bash
cd /workspaces/pocketsocket-2/server
nimble buildPyd
```

The ABI-specific extension is written to `../package/`:

```text
pocketsocket_server*.so    # Linux/macOS
pocketsocket_server*.pyd   # Windows
```

### Build the Python wheel

The complete build driver installs the editable development package, rebuilds
the Nim outputs, and creates a wheel:

```bash
cd /workspaces/pocketsocket-2
python3 package/build_whl.py
```

To build only the wheel after the native extension already exists:

```bash
cd /workspaces/pocketsocket-2
hatch build -t wheel
```

The wheel is written to `dist/` and contains both the `pocketsocket` wrapper
and the top-level `pocketsocket_server` native extension.

### Check the package import

```bash
cd /workspaces/pocketsocket-2
python3 -c "import pocketsocket; print(pocketsocket.__all__)"
```

If the import fails with `ModuleNotFoundError: pocketsocket_server`, build the
native extension with `./server/setup.sh` and retry.
