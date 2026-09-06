#!/usr/bin/env python3
"""
pocketsocket startup benchmark.

Measures cold start: process spawn to accepting connections, plus the Nim-side
"time to launch" the server reports itself (socket bind and template load,
excluding interpreter boot).

    python3 benchmarks/bench_startup.py -n 20
    python3 benchmarks/bench_startup.py -o results/benchmarks/startup.txt
"""

import argparse
import os
import re
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.harness import (PYTHON_PKG, HOST, REPO_ROOT, Report,   # noqa: E402
                         ServerProcess, free_port, summarise)
from lib.servers import pocketsocket_code                       # noqa: E402

TTL_RE = re.compile(
    r"TTL:\s*(?:(\d+)\s+millisecond)?[^0-9]*(?:(\d+)\s+microsecond)?"
    r"[^0-9]*(?:(\d+)\s+nanosecond)?")


def parse_ttl(text):
    best = None
    for line in text.splitlines():
        if "TTL:" not in line:
            continue
        m = TTL_RE.search(line)
        if not m:
            continue
        ms, us, ns = (int(g) if g else 0 for g in m.groups())
        best = ms + us / 1000 + ns / 1e6
    return best


def run(mode, iterations):
    ttls, readys = [], []
    for _ in range(iterations):
        port = free_port()
        try:
            srv = ServerProcess(pocketsocket_code(mode, PYTHON_PKG, HOST, port),
                                port, label=mode)
        except RuntimeError:
            continue
        readys.append(srv.ready_ms)
        ttl = parse_ttl(srv.log_text())
        if ttl is not None:
            ttls.append(ttl)
        srv.stop()
        srv.cleanup()
        time.sleep(0.03)
    return ttls, readys


def row(name, s):
    if not s:
        return f"{name:<22}{'no samples':>12}"
    return (f"{name:<22}{len(s):>6}{min(s):>10.4f}"
            f"{statistics.median(s):>11.4f}{statistics.fmean(s):>10.4f}"
            f"{max(s):>10.4f}{statistics.pstdev(s):>10.4f}")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", "--iterations", type=int, default=20)
    ap.add_argument("--quick", action="store_true", help="fewer iterations")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    iterations = max(5, int(args.iterations * 0.25)) if args.quick else args.iterations

    r = Report("pocketsocket - Startup Benchmark")
    r.env()
    r(f"Iterations : {iterations}")
    r.data["options"] = {"iterations": iterations, "quick": args.quick}
    r.data["benchmarks"] = {"nim_time_to_launch_ms": {},
                             "spawn_to_ready_ms": {}, "standalone_cli": {}}

    r.section("1. NIM TIME-TO-LAUNCH (ms)")
    r("Reported by the server itself: template load, router and socket bind.")
    r("Excludes interpreter startup and module import.")
    r("")
    r(f"{'mode':<22}{'runs':>6}{'min':>10}{'median':>11}{'mean':>10}"
      f"{'max':>10}{'stdev':>10}")
    for mode in ("ps-ingest", "ps-nim-echo", "ps-hook-echo"):
        ttls, _ = run(mode, iterations)
        r(row(mode, ttls))
        r.data["benchmarks"]["nim_time_to_launch_ms"][mode] = summarise(ttls) if ttls else {"n": 0}

    r.section("2. SPAWN -> ACCEPTING CONNECTIONS (ms)")
    r("Wall clock from fork/exec to the first successful connect. Dominated")
    r("by CPython interpreter startup and the extension module import.")
    r("")
    r(f"{'mode':<22}{'runs':>6}{'min':>10}{'median':>11}{'mean':>10}"
      f"{'max':>10}{'stdev':>10}")
    for mode in ("ps-ingest", "ps-nim-echo", "ps-hook-echo"):
        _, readys = run(mode, iterations)
        r(row(mode, readys))
        r.data["benchmarks"]["spawn_to_ready_ms"][mode] = summarise(readys) if readys else {"n": 0}

    r.section("3. STANDALONE CLI BINARY")
    cli = os.path.join(REPO_ROOT, "dist", "pocketsocket-cli")
    if os.path.exists(cli):
        r(f"Binary present: {cli}")
        r(f"Size          : {os.path.getsize(cli):,} bytes")
        r("Build with: nimble buildCliCI -d:release -d:lto -d:strip")
        r.data["benchmarks"]["standalone_cli"] = {
            "present": True, "path": cli, "size_bytes": os.path.getsize(cli),
            "build_command": "nimble buildCliCI -d:release -d:lto -d:strip",
        }
    else:
        r("Not built. Run `nimble build` to produce dist/pocketsocket-cli.")
        r.data["benchmarks"]["standalone_cli"] = {"present": False}

    r("")
    r.rule()
    r("Registering a python hook should not affect startup: the callback is")
    r("stored, not invoked, until the first event arrives. Any difference")
    r("between the three modes above is noise.")
    r("")

    if args.output:
        r.save(args.output)


if __name__ == "__main__":
    main()
