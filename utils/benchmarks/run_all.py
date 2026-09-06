#!/usr/bin/env python3
"""
Run the whole benchmark suite and write dated reports into results/benchmarks/.

    python3 benchmarks/run_all.py
    python3 benchmarks/run_all.py --quick
    python3 benchmarks/run_all.py --tag postcleanup
"""

import argparse
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RESULTS = os.path.join(REPO_ROOT, "results", "benchmarks")

SUITES = [
    ("startup", "bench_startup.py", []),
    ("message-path", "bench_message_path.py", []),
    ("compare", "bench_compare.py", []),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--tag", default="", help="suffix for the result filenames")
    ap.add_argument("--dir", dest="output_dir", help="exact output directory")
    ap.add_argument("--strip-prefix", action="store_true",
                    help="remove the date/tag prefix from files in the run directory")
    ap.add_argument("--only", help="run a single suite by name")
    ap.add_argument("--clients", help="client counts for the concurrency sweep, "
                                      "e.g. 1,2,4,8,16,32 (message-path only)")
    args = ap.parse_args()

    stamp = date.today().isoformat()
    prefix = f"{stamp}-{args.tag}" if args.tag else stamp
    tag_parts = [part for part in args.tag.split("-") if part]
    if tag_parts:
        strip_prefix = f"{stamp}-{'-'.join(tag_parts[:-1])}-"
    else:
        strip_prefix = f"{stamp}-"
    output_dir = Path(args.output_dir) if args.output_dir else Path(RESULTS) / prefix
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"host: {os.cpu_count()} vCPU")

    failures = []
    for name, script, extra in SUITES:
        if args.only and args.only != name:
            continue
        out = str(output_dir / f"{prefix}-{name}.txt")
        cmd = [sys.executable, os.path.join(HERE, script), "-o", out] + extra
        if args.quick:
            cmd.append("--quick")
        if args.clients and name == "message-path":
            cmd += ["--clients", args.clients]
        print(f"\n{'=' * 78}\n>>> {name}\n{'=' * 78}", flush=True)
        rc = subprocess.call(cmd)
        if rc != 0:
            failures.append(name)

    if args.strip_prefix:
        for path in output_dir.iterdir():
            if path.is_file() and path.name.startswith(strip_prefix):
                path.rename(path.with_name(path.name[len(strip_prefix):]))

    print(f"\nReports written to {output_dir}")
    if failures:
        print(f"FAILED: {', '.join(failures)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
