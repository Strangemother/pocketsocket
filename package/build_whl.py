#!/usr/bin/env python3
"""Build the Nim outputs and Python wheel from the repository root.

Manual:
    # Install Hatch once
    python -m pip install -e ".[dev]"

    # Build Nim dependencies, Python extension, and standalone CLI
    ./server/setup.sh

    # Build the Python wheel
    hatch build -t wheel
"""

from pathlib import Path
import shutil
import subprocess
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]


def run(*command: str) -> None:
    subprocess.run(command, cwd=ROOT_DIR, check=True)


def main() -> None:
    if shutil.which("hatch") is None:
        raise SystemExit(
            "hatch is not installed; run: "
            f"{sys.executable} -m pip install -e '.[dev]'"
        )

    run(sys.executable, "-m", "pip", "install", "-e", ".[dev]")
    run("bash", "server/setup.sh")
    run("hatch", "build", "-t", "wheel")


if __name__ == "__main__":
    main()
