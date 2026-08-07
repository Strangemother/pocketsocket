"""Build PocketSocket's native outputs."""

import argparse
import os
import subprocess
from pathlib import Path


SERVER_DIR = Path(__file__).parent


def build_environment():
    """Return an environment containing the setup script's tool paths."""
    environment = os.environ.copy()
    nim_version = environment.get("NIM_VERSION", "2.2.10")
    paths = [
        Path.home() / ".nimble" / "bin",
        Path.home() / ".local" / "share" / "grabnim" / f"nim-{nim_version}" / "bin",
    ]
    environment["PATH"] = os.pathsep.join(
        [str(path) for path in paths] + [environment.get("PATH", "")]
    )
    return environment


def run_build(command, setup, environment):
    """Run a build, setting up Nim once when Nimble is unavailable."""
    try:
        subprocess.run(
            command,
            cwd=SERVER_DIR,
            check=True,
            env=environment,
        )
    except FileNotFoundError:
        if not setup or command[0] != "nimble":
            raise
        print("Nimble not found; running setup.sh...")
        subprocess.run(["bash", "setup.sh"], cwd=SERVER_DIR, check=True)
        subprocess.run(
            command,
            cwd=SERVER_DIR,
            check=True,
            env=build_environment(),
        )


def build_command(output, debug):
    """Return the Nim command for an output kind."""
    if output == "exe":
        if not debug:
            return ["nimble", "build"]
        return [
            "nimble", "c", "--app:console",
            "--out:../dist/pocketsocket-cli.exe",
            "--threads:on",
            "--tlsEmulation:off",
            "-d:lto",
            "--mm:arc",
            "-d:useMalloc",
            "--excessiveStackTrace:on",
            "--passL:-static",
            "src/pocketsocket.nim",
        ]

    if output == "pyd":
        return ["nimble", "buildPydDebug" if debug else "buildPyd"]

    if output == "lib":
        command = [
            "nim", "c", "--app:lib",
            "--out:../dist/lib/imp.dll",
            "--threads:on",
            "--tlsEmulation:off",
            "--passl:-static -static-libgcc -static-libstdc++",
            "src/pocketsocketpkg/imp.nim",
        ]
        if debug:
            return command
        return (
            command[:4]
            + ["-d:release", "--opt:size"]
            + command[4:]
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "outputs",
        nargs="*",
        choices=("exe", "lib", "pyd"),
        help="outputs to build (default: exe and pyd)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="build exe, lib, and pyd",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--debug", action="store_true", help="build debug outputs")
    mode.add_argument(
        "--release",
        action="store_true",
        help="build release outputs (the default)",
    )
    parser.add_argument(
        "--setup",
        "--setup=True",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="run setup.sh when Nimble is missing (default: true)",
    )
    args = parser.parse_args()

    outputs = ("exe", "lib", "pyd") if args.all else args.outputs
    if not outputs:
        outputs = ("pyd", "exe")

    for output in outputs:
        print(f"Building {output}...")
        run_build(build_command(output, args.debug), args.setup, build_environment())


if __name__ == "__main__":
    main()