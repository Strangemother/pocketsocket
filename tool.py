#!/usr/bin/env python

"""
Run:

    python tool.py --test [nim|py|all]
    python tool.py --coverage [nim|py|c|all] ...
    python tool.py -C nim py
    python tool.py -C all
python tool.py --bump [major|minor|patch]
python tool.py --set-version <version>
python tool.py --test --compile
python tool.py --test --compile --benchmark --tag 2-0-4-2-cleanup --strip-prefix
python tool.py --test --compile --benchmark --tag 2-0-4-2-cleanup --strip-prefix --coverage-nim --coverage-c

1. Tests are all tests
    nimble test

2. compile is 'build' all the things
    python server/compile.py

3. benchmark is run the full suite
    python benchmarks/run_all.py --tag 2-0-4-2-cleanup --strip-prefix

4. coverage is run the coverage suite
    server/scripts/coverage.sh #nim
    server/scripts/c_coverage.sh #c
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
VERSION_FILE = ROOT / "server" / "VERSION"
VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-t",
        "--test",
        nargs="?",
        const="all",
        choices=("nim", "py", "all"),
        help="run tests (default: all; choices: nim, py, all)",
    )
    parser.add_argument(
        "-c", "--compile", action="store_true", help="build native outputs"
    )
    parser.add_argument(
        "-b", "--benchmark", action="store_true", help="run benchmarks"
    )
    parser.add_argument(
        "-C",
        "--coverage",
        nargs="+",
        action="extend",
        choices=("nim", "py", "c", "all"),
        metavar="TYPE",
        help="run coverage (types: nim, py, c, all; may be repeated)",
    )
    parser.add_argument(
        "-n", "--coverage-nim", action="store_true", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--coverage-c", action="store_true", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "-r", "--run", action="store_true", help="run the standalone server"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "-d", "--debug", action="store_true", help="use the debug server"
    )
    mode.add_argument(
        "--release", action="store_true", help="use the release server"
    )
    parser.add_argument(
        "--tag", default="", help="benchmark result tag"
    )
    parser.add_argument(
        "--strip-prefix",
        action="store_true",
        help="strip the date and tag prefix from benchmark reports",
    )
    version_group = parser.add_mutually_exclusive_group()
    version_group.add_argument(
        "--bump",
        nargs="?",
        const="patch",
        choices=("major", "minor", "patch"),
        help="bump VERSION by component (default: patch)",
    )
    version_group.add_argument(
        "--set-version",
        metavar="VERSION",
        help="set VERSION explicitly, for example 2.1.0",
    )
    args, server_args = parser.parse_known_args()

    version_changed = update_version(args.bump, args.set_version)

    coverage = set(args.coverage or [])
    if args.coverage_nim:
        coverage.add("nim")
    if args.coverage_c:
        coverage.add("c")
    if "all" in coverage:
        coverage.update(("nim", "py", "c"))

    tasks = (
        args.test is not None,
        args.compile,
        args.benchmark,
        bool(coverage),
        args.run,
    )
    if not any(tasks) and not version_changed:
        parser.error("choose at least one task")
    if (args.tag or args.strip_prefix) and not args.benchmark:
        parser.error("--tag and --strip-prefix require --benchmark")
    if (args.debug or args.release) and not (args.run or args.compile):
        parser.error("--debug and --release require --run or --compile")

    if args.test in ("nim", "all"):
        run(["nimble", "test"], ROOT / "server")
    if args.test in ("py", "all"):
        run(["pytest"], ROOT / "package")
    if args.compile:
        command = [sys.executable, "server/compile.py"]
        if args.debug:
            command.append("--debug")
        elif args.release:
            command.append("--release")
        run(command)
    if args.benchmark:
        command = [sys.executable, "benchmarks/run_all.py"]
        if args.tag:
            command += ["--tag", args.tag]
        if args.strip_prefix:
            command.append("--strip-prefix")
        run(command)
    if "nim" in coverage:
        run(["bash", "server/scripts/coverage.sh"])
    if "py" in coverage:
        run(["bash", "quicktest.sh", "-c"], ROOT / "package")
    if "c" in coverage:
        run(["bash", "server/scripts/c_coverage.sh"])
    if args.run:
        mode = "debug" if args.debug else "release"
        executable = DIST / f"pocketsocket-cli-{mode}"
        if os.name == "nt":
            executable = executable.with_suffix(".exe")
        if not executable.exists():
            command = [sys.executable, "server/compile.py", "exe"]
            if args.debug:
                command.append("--debug")
            run(command)
        run([str(executable), "--run", *server_args], DIST)


def run(command, cwd=ROOT):
    """Run a command and stop if it fails."""
    print(f"==> {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def read_version():
    """Read and validate the project version from the source-of-truth file."""
    version = VERSION_FILE.read_text(encoding="ascii").strip()
    if VERSION_PATTERN.fullmatch(version) is None:
        raise ValueError(f"Invalid version in {VERSION_FILE}: {version!r}")
    return version


def write_version(version):
    """Write VERSION and keep existing package metadata synchronized."""
    if VERSION_PATTERN.fullmatch(version) is None:
        raise ValueError(f"Invalid version: {version!r}")

    VERSION_FILE.write_text(f"{version}\n", encoding="ascii")

    pyproject = ROOT / "pyproject.toml"
    pyproject_text = pyproject.read_text(encoding="ascii")
    pyproject_text = re.sub(
        r'(?m)^version = "[^"]+"$',
        f'version = "{version}"',
        pyproject_text,
        count=1,
    )
    pyproject.write_text(pyproject_text, encoding="ascii")

    nimble = ROOT / "server" / "pocketsocket.nimble"
    nimble_text = nimble.read_text(encoding="ascii")
    nimble_text = re.sub(
        r"(?m)^version\s*=\s*\S+$",
        f"version       = \"{version}\"",
        nimble_text,
        count=1,
    )
    nimble.write_text(nimble_text, encoding="ascii")

    print(f"Version set to {version}")


def update_version(bump, explicit_version):
    """Apply a requested version change and return whether one was requested."""
    if bump is None and explicit_version is None:
        return False

    current = read_version()
    if explicit_version is not None:
        new_version = explicit_version
    else:
        major, minor, patch = (int(part) for part in current.split("."))
        if bump == "major":
            new_version = f"{major + 1}.0.0"
        elif bump == "minor":
            new_version = f"{major}.{minor + 1}.0"
        else:
            new_version = f"{major}.{minor}.{patch + 1}"

    write_version(new_version)
    return True 


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)