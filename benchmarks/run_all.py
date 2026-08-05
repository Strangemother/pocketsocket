#!/usr/bin/env python3
"""
Run the whole benchmark suite and write dated reports into results/.

    python3 benchmarks/run_all.py
    python3 benchmarks/run_all.py --quick
    python3 benchmarks/run_all.py --tag postcleanup
"""

import argparse
import os
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")

SUITES = [
    ("startup", "bench_startup.py", []),
    ("message-path", "bench_message_path.py", []),
    ("compare", "bench_compare.py", []),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--tag", default="", help="suffix for the result filenames")
    ap.add_argument("--only", help="run a single suite by name")
    ap.add_argument("--clients", help="client counts for the concurrency sweep, "
                                      "e.g. 1,2,4,8,16,32 (message-path only)")
    args = ap.parse_args()

    os.makedirs(RESULTS, exist_ok=True)
    stamp = date.today().isoformat()
    tag = f"-{args.tag}" if args.tag else ""

    print(f"host: {os.cpu_count()} vCPU")

    failures = []
    for name, script, extra in SUITES:
        if args.only and args.only != name:
            continue
        out = os.path.join(RESULTS, f"{stamp}{tag}-{name}.txt")
        cmd = [sys.executable, os.path.join(HERE, script), "-o", out] + extra
        if args.quick:
            cmd.append("--quick")
        if args.clients and name == "message-path":
            cmd += ["--clients", args.clients]
        print(f"\n{'=' * 78}\n>>> {name}\n{'=' * 78}", flush=True)
        rc = subprocess.call(cmd)
        if rc != 0:
            failures.append(name)

    print(f"\nReports written to {RESULTS}")
    if failures:
        print(f"FAILED: {', '.join(failures)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
