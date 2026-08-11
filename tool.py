"""
Run:

python tool.py --test
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
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"


def run(command, cwd=ROOT):
    """Run a command and stop if it fails."""
    print(f"==> {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-t", "--test", action="store_true", help="run Nim tests"
    )
    parser.add_argument(
        "-c", "--compile", action="store_true", help="build native outputs"
    )
    parser.add_argument(
        "-b", "--benchmark", action="store_true", help="run benchmarks"
    )
    parser.add_argument(
        "-n", "--coverage-nim", action="store_true", help="run Nim coverage"
    )
    parser.add_argument(
        "-C", "--coverage-c", action="store_true", help="run C coverage"
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
    args, server_args = parser.parse_known_args()

    tasks = (
        args.test,
        args.compile,
        args.benchmark,
        args.coverage_nim,
        args.coverage_c,
        args.run,
    )
    if not any(tasks):
        parser.error("choose at least one task")
    if (args.tag or args.strip_prefix) and not args.benchmark:
        parser.error("--tag and --strip-prefix require --benchmark")
    if (args.debug or args.release) and not (args.run or args.compile):
        parser.error("--debug and --release require --run or --compile")

    if args.test:
        run(["nimble", "test"], ROOT / "server")
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
    if args.coverage_nim:
        run(["bash", "server/scripts/coverage.sh"])
    if args.coverage_c:
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


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)