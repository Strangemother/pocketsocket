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

The wheel hook includes only the extension matching the build interpreter's
`EXT_SUFFIX`. Compile and build with the same Python. A distributable wheel
fails if that extension is missing; editable installation remains available
before compilation. Benchmark outputs and development executables are not
included in runtime wheels.

### Release validation

GitHub Actions uses Nim 2.2.10 on Linux x64/ARM64, macOS Intel/Apple Silicon,
and Windows x64 (with both x86 and x64 Python wheels). Each runner builds and launches the CLI, runs the native
writer/receive regression tests, and builds wheels with cibuildwheel. Each
installed wheel must import its native module, report the metadata version,
and echo text and binary WebSocket messages through a Python callback.

Free-threaded CPython wheels (`cp*t-*`) are excluded: the current native
integration segfaulted during the CPython 3.14t installed-wheel smoke test.
Regular GIL-enabled CPython 3.10 through 3.14 remains in the build matrix.
Free-threaded support requires a separate native compatibility fix and runtime
validation before those wheels can be distributed.

Windows Python extensions use Visual C++ Build Tools, including the C++ desktop
workload and Windows SDK already installed on the hosted Windows runner. The
native build selects x86 for Python's `win32` suffix and x64 for `win_amd64`,
independently of the host Nim compiler's architecture. Both release and debug
extension tasks use this selection; the standalone CLI build is unchanged.

Run the packaging selection tests locally with Hatchling installed:

```bash
python3 -m unittest discover -s package/tests -p test_wheel_build.py
```

To reproduce one Linux wheel build, including repair and installed-wheel
testing, install Docker and cibuildwheel 3.1.1 and run from the repository root:

```bash
CIBW_BUILD='cp312-manylinux_x86_64' python3 -m cibuildwheel --platform linux
```

Source archives contain the Nim sources but do not compile them during a normal
`pip install`. To build from an extracted source archive, install Nim and a C
toolchain, run `nimble install --depsOnly -y` in `server/`, then compile with
`POCKETSOCKET_PYTHON=python nimble buildPyd -d:release` before building the wheel
from the archive root. On Windows, set `POCKETSOCKET_PYTHON` using PowerShell's
`$env:POCKETSOCKET_PYTHON = "python"` first.

Keep Python and Nim metadata synchronized with `server/VERSION` using
`python3 utils/tool.py --set-version VERSION` before tagging. The release
workflow currently publishes to **TestPyPI**, not production PyPI. A successful
local Linux check does not replace the complete hosted platform matrix.

### Check the package import

```bash
cd /workspaces/pocketsocket-2
python3 -c "import pocketsocket; print(pocketsocket.__all__)"
```

If the import fails with `ModuleNotFoundError: pocketsocket_server`, build the
native extension with `./server/setup.sh` and retry.
