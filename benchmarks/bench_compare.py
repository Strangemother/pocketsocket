#!/usr/bin/env python3
"""
pocketsocket vs other Python WebSocket servers.

Every server implements the same contract -- accept an upgrade, echo text
frames back -- and is driven by the same raw-socket client, so the comparison
is like for like.

Three things are measured:

  startup      cold spawn to accepting connections
  latency      round-trip, one message in flight
  throughput   batched, so client syscall cost does not dominate
  connections  handshake rate

pocketsocket appears twice on purpose: once through the Python callback
(ps-hook-echo, the equivalent feature to what the others offer) and once
through the pure-Nim path (ps-nim-echo, which the others have no equivalent
for).

    python3 benchmarks/bench_compare.py
    python3 benchmarks/bench_compare.py --quick -o benchmarks/results/compare.txt
"""

import argparse
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib import workloads as W                                    # noqa: E402
from lib.harness import (PYTHON_PKG, HOST, Report, ServerProcess,  # noqa: E402
                         free_port, human_size)
from lib.servers import (available_comparisons, comparison_code,   # noqa: E402
                         pocketsocket_code)

# Current pocketsocket connections begin with application frames, like the
# comparison servers. The workload default does not drain a greeting.
PS_MODES = ("ps-nim-echo", "ps-hook-echo")


def build(name, port):
    if name in PS_MODES:
        return pocketsocket_code(name, PYTHON_PKG, HOST, port), False
    return comparison_code(name, HOST, port), False


def start(name, port):
    code, greeting = build(name, port)
    return ServerProcess(code, port, label=name.replace("+", "_")), greeting


def measure_startup(name, iterations):
    samples = []
    for _ in range(iterations):
        port = free_port()
        try:
            srv, _ = start(name, port)
        except RuntimeError:
            continue
        samples.append(srv.ready_ms)
        srv.stop()
        srv.cleanup()
        time.sleep(0.05)
    return samples


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()

    scale = 0.25 if args.quick else 1.0

    def n(x):
        return max(100, int(x * scale))

    targets = list(PS_MODES) + available_comparisons()

    r = Report("pocketsocket vs Python WebSocket servers")
    r.env()
    r.data["options"] = {"quick": args.quick}
    r.data["benchmarks"] = {
        "startup": {}, "latency": {}, "throughput": {}, "connections": {},
    }
    r("All servers echo text frames. Same raw-socket client for all of them.")
    r("")
    r("Contenders:")
    for t in targets:
        note = {
            "ps-nim-echo": "pocketsocket, pure Nim path (no python per message)",
            "ps-hook-echo": "pocketsocket, python callback per message",
        }.get(t, "")
        r(f"  {t:<18}{note}")

    # -- startup ---------------------------------------------------------
    r.section("1. STARTUP  (spawn -> accepting connections, ms)")
    r(f"{'server':<18}{'runs':>6}{'min':>10}{'median':>10}{'mean':>10}{'max':>10}")
    startup = {}
    for name in targets:
        s = measure_startup(name, n(12))
        if not s:
            r(f"{name:<18}{'-':>6}   failed to start")
            continue
        startup[name] = statistics.median(s)
        r.data["benchmarks"]["startup"][name] = {
            "runs": len(s), "min_ms": min(s), "median_ms": statistics.median(s),
            "mean_ms": statistics.fmean(s), "max_ms": max(s),
        }
        r(f"{name:<18}{len(s):>6}{min(s):>10.1f}{statistics.median(s):>10.1f}"
          f"{statistics.fmean(s):>10.1f}{max(s):>10.1f}")
    if startup:
        best = min(startup.values())
        for name, value in startup.items():
            r.data["benchmarks"]["startup"][name]["relative_to_fastest"] = value / best
        r("")
        r("relative to fastest:")
        for name, v in sorted(startup.items(), key=lambda kv: kv[1]):
            r(f"  {name:<18}{v / best:>7.1f}x")

    # -- latency ---------------------------------------------------------
    r.section("2. ROUND-TRIP LATENCY  (1 connection, 1 in flight, microseconds)")
    for size in (64, 1024):
        r(f"payload {human_size(size)}")
        r(f"  {'server':<18}{'min':>9}{'p50':>9}{'p90':>9}{'p99':>9}"
          f"{'max':>10}{'msg/s':>11}")
        rows = []
        for name in targets:
            port = free_port()
            try:
                srv, greeting = start(name, port)
            except RuntimeError as e:
                r(f"  {name:<18}  failed: {e}")
                continue
            try:
                res = W.latency(port, n(3000), size, greeting=greeting)
                rows.append((name, res))
                r.data["benchmarks"]["latency"].setdefault(str(size), {})[name] = res
            except Exception as e:  # noqa: BLE001
                r(f"  {name:<18}  error: {e!r}")
            finally:
                srv.stop()
                srv.cleanup()
        for name, res in sorted(rows, key=lambda kv: kv[1]["p50"]):
            r(f"  {name:<18}{res['min']:>9.1f}{res['p50']:>9.1f}"
              f"{res['p90']:>9.1f}{res['p99']:>9.1f}{res['max']:>10.1f}"
              f"{res['rate']:>11,.0f}")
        r("")

    # -- throughput ------------------------------------------------------
    r.section("3. THROUGHPUT  (1 connection, 256 frames per syscall)")
    for size in (64, 1024, 16384):
        cnt = n(20000) if size <= 1024 else n(4000)
        r(f"payload {human_size(size)}")
        r(f"  {'server':<18}{'msgs':>9}{'sec':>8}{'msg/s':>12}{'MB/s':>10}"
          f"{'vs best':>10}")
        rows = []
        for name in targets:
            port = free_port()
            try:
                srv, greeting = start(name, port)
            except RuntimeError as e:
                r(f"  {name:<18}  failed: {e}")
                continue
            try:
                rows.append((name, W.batched(port, cnt, size, 256,
                                             greeting=greeting)))
                r.data["benchmarks"]["throughput"].setdefault(str(size), {})[name] = rows[-1][1]
            except Exception as e:  # noqa: BLE001
                r(f"  {name:<18}  error: {e!r}")
            finally:
                srv.stop()
                srv.cleanup()
        rows.sort(key=lambda kv: -kv[1]["rate"])
        best = rows[0][1]["rate"] if rows else 1
        for name, res in rows:
            r.data["benchmarks"]["throughput"][str(size)][name]["vs_best"] = res["rate"] / best
        for name, res in rows:
            r(f"  {name:<18}{res['count']:>9,}{res['duration']:>8.3f}"
              f"{res['rate']:>12,.0f}{res['mb_per_sec']:>10.1f}"
              f"{res['rate'] / best:>9.2f}x")
        r("")

    # -- connections -----------------------------------------------------
    r.section("4. CONNECTION ESTABLISHMENT")
    r(f"{'server':<18}{'conns':>7}{'sec':>8}{'conn/s':>11}{'ms each':>10}")
    rows = []
    for name in targets:
        port = free_port()
        try:
            srv, greeting = start(name, port)
        except RuntimeError as e:
            r(f"{name:<18}  failed: {e}")
            continue
        try:
            rows.append((name, W.connections(port, n(400), greeting=greeting)))
            r.data["benchmarks"]["connections"][name] = rows[-1][1]
        except Exception as e:  # noqa: BLE001
            r(f"{name:<18}  error: {e!r}")
        finally:
            srv.stop()
            srv.cleanup()
    for name, res in sorted(rows, key=lambda kv: -kv[1]["rate"]):
        r(f"{name:<18}{res['count']:>7,}{res['duration']:>8.3f}"
          f"{res['rate']:>11,.0f}{res['ms_each']:>10.3f}")

    r("")
    r.rule()
    r("NOTES")
    r.rule()
    r("* Fairness: minimal echo handler on every server, no middleware, no")
    r("  access logging, same client, same host, run back to back.")
    r("* The asyncio servers run a single-threaded event loop. pocketsocket")
    r("  runs a dedicated io thread plus a worker pool, which costs a thread")
    r("  handoff per message but scales across cores. On a small host that")
    r("  handoff is visible; on a larger host it is what buys headroom.")
    r("* ps-nim-echo has no equivalent among the others: the message never")
    r("  enters Python at all.")
    r("")

    if args.output:
        r.save(args.output)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.set_start_method("spawn", force=True)
    main()
