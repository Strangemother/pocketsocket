#!/usr/bin/env bash
# Restore the build environment and rebuild pocketsocket.
#
# /workspaces persists across a codespace stop/start, but $HOME does not survive
# a container rebuild -- and that is where the Nim toolchain lives. This script
# is idempotent: run it after any restart, rebuild or machine-type change.
#
#   ./setup.sh              # toolchain + deps + build
#   source ./setup.sh       # also leaves nim on PATH in your current shell
set -euo pipefail

NIM_VERSION="${NIM_VERSION:-2.2.10}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

export PATH="$HOME/.local/share/grabnim/nim-$NIM_VERSION/bin:$HOME/.nimble/bin:$PATH"

echo "==> host: $(nproc) vCPU"

if ! command -v nim >/dev/null 2>&1; then
  echo "==> nim not found, installing $NIM_VERSION"
  if ! command -v grabnim >/dev/null 2>&1; then
    echo "    grabnim missing too - install a Nim toolchain first, e.g.:"
    echo "    curl https://nim-lang.org/choosenim/init.sh -sSf | sh"
    exit 1
  fi
  grabnim "$NIM_VERSION"
  export PATH="$HOME/.local/share/grabnim/nim-$NIM_VERSION/bin:$PATH"
fi
echo "==> $(nim --version | head -1)"

echo "==> nim dependencies"
nimble install -d -y >/dev/null

echo "==> benchmark comparison servers"
pip install --quiet websockets tornado aiohttp fastapi uvicorn

echo "==> building python extension"
nimble buildPyd

echo "==> building standalone cli"
nimble build

echo "==> smoke test"
python3 - <<'PY'
import sys
sys.path.insert(0, 'python')
import pocketsocket as ps
missing = [n for n in ps.__all__ if not hasattr(ps, n)]
assert not missing, f"missing exports: {missing}"
print("    python API OK")
PY

cat <<EOF

Ready. To run the benchmarks:

    python3 benchmarks/run_all.py --tag \$(nproc)core

Add nim to your PATH in new shells with:

    export PATH="\$HOME/.local/share/grabnim/nim-$NIM_VERSION/bin:\$HOME/.nimble/bin:\$PATH"
EOF
