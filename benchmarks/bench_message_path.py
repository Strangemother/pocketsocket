#!/usr/bin/env python3
"""
pocketsocket message-path benchmark.

Measures the steady-state message path -- wire -> mummy worker -> (optionally)
the nimpy/GIL bridge into a Python callback -> back out -- rather than startup
time.

The value of this suite is the cost decomposition: the same workload is run
against the pure-Nim paths and the Python-callback paths, so the bridge cost is
isolated rather than inferred.

    python3 benchmarks/bench_message_path.py
    python3 benchmarks/bench_message_path.py --quick
    python3 benchmarks/bench_message_path.py -o benchmarks/results/latest.txt
"""

import argparse
import multiprocessing
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib import workloads as W                                  # noqa: E402
from lib.harness import (PYTHON_PKG, HOST, Report, ServerProcess,  # noqa: E402
                         free_port, human_size)
from lib.servers import pocketsocket_code                       # noqa: E402


def server(mode, port):
    return ServerProcess(pocketsocket_code(mode, PYTHON_PKG, HOST, port),
                         port, label=mode)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="fewer iterations")
    ap.add_argument("--clients", help="comma separated client counts for the "
                                     "concurrency sweep, e.g. 1,2,4,8,16,32. "
                                     "Defaults to a sweep sized from cpu count.")
    ap.add_argument("-o", "--output", help="write the report to a file")
    args = ap.parse_args()

    scale = 0.2 if args.quick else 1.0
    cpus = os.cpu_count() or 1

    if args.clients:
        client_counts = [int(x) for x in args.clients.split(",") if x.strip()]
    else:
        # Client processes share the host with the server, so sweep to roughly
        # 2x cpus: enough to find the knee without pure scheduler thrash.
        client_counts = [1, 2, 4, 8]
        while client_counts[-1] < cpus * 2:
            client_counts.append(client_counts[-1] * 2)

    def n(x):
        return max(200, int(x * scale))

    r = Report("pocketsocket - Message Path Benchmark")
    r.env()
    r.data["options"] = {"quick": args.quick, "clients": client_counts}
    r.data["benchmarks"] = {
        "client_calibration": {}, "latency": {}, "throughput": {},
        "cost_decomposition": {}, "concurrency": {}, "broadcast": {},
        "connections": {}, "hot_path_logging": {},
    }
    r("All client load is raw sockets with pre-built frames. Concurrent load")
    r("uses separate processes so client-side GIL contention cannot be")
    r("mistaken for server-side contention.")
    r("")
    r("Modes:")
    r("  ps-ingest         no callback, message dropped   (framing floor)")
    r("  ps-nim-echo       Nim reflects to sender          (no python)")
    r("  ps-nim-broadcast  Nim fans out to others          (no python)")
    r("  ps-hook-noop      python callback, no send        (bridge cost only)")
    r("  ps-hook-echo      python callback + ps.send()     (real-world)")
    r("  ps-hook-broadcast python callback + ps.send_all()")

    # -- 0 ---------------------------------------------------------------
    r.section("0. CLIENT CALIBRATION  (no server, no kernel)")
    r("How fast this benchmark's own client can parse frames. Any throughput")
    r("figure approaching these numbers is measuring Python, not pocketsocket.")
    r("")
    r(f"{'size':>8}{'client ceiling msg/s':>24}")
    for size in (64, 1024, 16384):
        res = W.client_parse_ceiling(size, n(20000) if size < 16384 else n(5000))
        r.data["benchmarks"]["client_calibration"][str(size)] = res
        r(f"{human_size(size):>8}{res['rate']:>24,.0f}")

    # -- 1 ---------------------------------------------------------------
    r.section("1. ROUND-TRIP LATENCY  (1 connection, 1 message in flight)")
    r(f"{'mode':<18}{'size':>7}{'min':>9}{'p50':>9}{'p90':>9}{'p99':>9}"
      f"{'max':>10}{'msg/s':>11}")
    r(f"{'':<18}{'':>7}{'us':>9}{'us':>9}{'us':>9}{'us':>9}{'us':>10}{'':>11}")
    for mode in ("ps-nim-echo", "ps-hook-echo"):
        for size in (64, 1024, 16384):
            port = free_port()
            with server(mode, port):
                res = W.latency(port, n(3000), size)
            r.data["benchmarks"]["latency"].setdefault(mode, {})[str(size)] = res
            r(f"{mode:<18}{human_size(size):>7}{res['min']:>9.1f}"
              f"{res['p50']:>9.1f}{res['p90']:>9.1f}{res['p99']:>9.1f}"
              f"{res['max']:>10.1f}{res['rate']:>11,.0f}")
        r("")

    # -- 2 ---------------------------------------------------------------
    r.section("2. THROUGHPUT  (1 connection, 256 frames per syscall)")
    r("Batched so client syscall cost cannot dominate; see section 0.")
    r("")
    r(f"{'mode':<18}{'size':>8}{'msgs':>9}{'sec':>8}{'msg/s':>12}{'MB/s':>10}")
    for mode in ("ps-nim-echo", "ps-hook-echo"):
        for size in (64, 1024, 16384, 65536):
            cnt = n(20000) if size <= 1024 else n(4000)
            port = free_port()
            with server(mode, port):
                res = W.batched(port, cnt, size, 256)
            r.data["benchmarks"]["throughput"].setdefault(mode, {})[str(size)] = res
            r(f"{mode:<18}{human_size(size):>8}{res['count']:>9,}"
              f"{res['duration']:>8.3f}{res['rate']:>12,.0f}"
              f"{res['mb_per_sec']:>10.1f}")
        r("")

    # -- 3 ---------------------------------------------------------------
    r.section("3. COST DECOMPOSITION  (64B, N messages fully handled)")
    r("The same workload against progressively more expensive paths. Every")
    r("row except the first is acknowledged, so these are true 'processed N")
    r("messages' rates.")
    r("")
    r(f"{'mode':<18}{'msgs':>9}{'sec':>8}{'msg/s':>12}{'MB/s':>8}"
      f"{'vs floor':>10}{'stdout B':>11}")
    floor = None
    plan = [
        ("ps-ingest", "send_only"),
        ("ps-nim-echo", "batched"),
        ("ps-hook-noop", "sentinel"),
        ("ps-hook-echo", "batched"),
    ]
    for mode, how in plan:
        cnt = n(30000)
        port = free_port()
        with server(mode, port) as srv:
            before = srv.log_bytes()
            if how == "send_only":
                # No ack is possible here, so the only backstop is TCP
                # backpressure. Send far more than the socket buffers hold,
                # otherwise this times memcpy into the kernel.
                res = W.send_only(port, cnt * 10, 64)
            elif how == "sentinel":
                res = W.sentinel(port, cnt, 64)
            else:
                res = W.batched(port, cnt, 64, 256)
            grew = srv.log_bytes() - before
        if floor is None:
            floor = res["rate"]
        r.data["benchmarks"]["cost_decomposition"][mode] = dict(
            res, stdout_bytes=grew, vs_floor=(res["rate"] / floor * 100))
        r(f"{mode:<18}{res['count']:>9,}{res['duration']:>8.3f}"
          f"{res['rate']:>12,.0f}{res['mb_per_sec']:>8.1f}"
          f"{res['rate'] / floor * 100:>9.0f}%{grew:>11,}")
    r("")
    r("HOW TO READ THIS")
    r("  ps-ingest and ps-hook-noop are ONE-WAY: inbound only, one thread")
    r("  handoff per message (io thread -> worker).")
    r("  ps-nim-echo and ps-hook-echo are ROUND TRIP: they add the outbound")
    r("  path, which is a second handoff back to the io thread.")
    r("")
    r("  If ps-nim-echo and ps-hook-echo land close together, the Python")
    r("  bridge is NOT the limiting factor -- mummy's per-message thread")
    r("  handoff is. Optimising the GIL bridge further would then be wasted")
    r("  effort for this workload.")

    # -- 4 ---------------------------------------------------------------
    r.section("4. CONCURRENCY SCALING  (echo, 64B, window=64)")
    r("mummy claims a websocket per worker thread and drains its queue in")
    r("order, so one connection is serviced serially. Contention only appears")
    r("across connections.")
    if cpus <= 4:
        r("")
        r(f"  !! {cpus} vCPU host. Client processes compete with the server for")
        r("     CPU, so anything past ~2 clients reflects host oversubscription")
        r("     rather than pocketsocket. Shape only, not absolute numbers.")
    r("")
    r(f"client counts: {', '.join(str(c) for c in client_counts)}")
    r("")
    r(f"{'mode':<18}{'clients':>8}{'msgs':>9}{'sec':>8}{'total msg/s':>13}"
      f"{'per-client':>12}{'scaling':>9}")
    for mode in ("ps-nim-echo", "ps-hook-echo"):
        base = None
        for clients in client_counts:
            port = free_port()
            with server(mode, port) as srv:
                res = W.concurrent(port, clients, n(8000), 64, 64)
                died = not srv.alive()
                tail = srv.tail(6) if died else ""
            if "error" in res:
                r(f"{mode:<18}{clients:>8}  ERROR: {res['error']}")
                continue
            if base is None:
                base = res["rate"]
            r.data["benchmarks"]["concurrency"].setdefault(mode, {})[str(clients)] = res
            r.data["benchmarks"]["concurrency"][mode][str(clients)]["scaling"] = res["rate"] / base
            r(f"{mode:<18}{clients:>8}{res['count']:>9,}{res['duration']:>8.3f}"
              f"{res['rate']:>13,.0f}{res['per_client']:>12,.0f}"
              f"{res['rate'] / base:>8.2f}x")
            if died:
                r(f"  SERVER DIED:\n{tail}")
        r("")

    # -- 5 ---------------------------------------------------------------
    r.section("5. BROADCAST FAN-OUT  (1 sender -> N receivers, 64B)")
    r(f"{'mode':<18}{'recv':>6}{'in msg/s':>11}{'out msg/s':>12}{'MB/s':>9}"
      f"{'delivered':>15}")
    for mode in ("ps-nim-broadcast", "ps-hook-broadcast"):
        for receivers in (2, 8):
            port = free_port()
            with server(mode, port):
                res = W.fanout(port, receivers, n(3000), 64)
            r.data["benchmarks"]["broadcast"].setdefault(mode, {})[str(receivers)] = res
            ok = f"{res['delivered']:,}/{res['expected']:,}"
            r(f"{mode:<18}{receivers:>6}{res['in_rate']:>11,.0f}"
              f"{res['out_rate']:>12,.0f}{res['mb_per_sec']:>9.1f}{ok:>15}")
        r("")

    # -- 6 ---------------------------------------------------------------
    r.section("6. CONNECTION ESTABLISHMENT  (handshake + connect callback)")
    r(f"{'mode':<18}{'conns':>7}{'sec':>8}{'conn/s':>11}{'ms each':>10}")
    for mode in ("ps-ingest", "ps-nim-echo", "ps-hook-echo"):
        port = free_port()
        with server(mode, port):
            res = W.connections(port, n(500))
        r.data["benchmarks"]["connections"][mode] = res
        r(f"{mode:<18}{res['count']:>7,}{res['duration']:>8.3f}"
          f"{res['rate']:>11,.0f}{res['ms_each']:>10.3f}")

    # -- 7 ---------------------------------------------------------------
    r.section("7. HOT-PATH LOGGING VOLUME")
    r("Any per-message stdout write is a syscall on the hot path. This should")
    r("read zero for every mode unless set_print_mode(True) is on.")
    r("")
    r(f"{'mode':<18}{'msgs':>9}{'stdout bytes':>15}{'bytes/msg':>12}")
    for mode in ("ps-nim-echo", "ps-hook-echo", "ps-hook-broadcast"):
        cnt = n(5000)
        port = free_port()
        with server(mode, port) as srv:
            before = srv.log_bytes()
            if mode == "ps-hook-broadcast":
                W.fanout(port, 2, cnt, 64)
            else:
                W.pipelined(port, cnt, 64, 64)
            grew = srv.log_bytes() - before
        r.data["benchmarks"]["hot_path_logging"][mode] = {
            "messages": cnt, "stdout_bytes": grew, "bytes_per_message": grew / cnt,
        }
        r(f"{mode:<18}{cnt:>9,}{grew:>15,}{grew / cnt:>12.2f}")

    r("")
    r.rule()
    r("NOTES")
    r.rule()
    r("* Latency includes the whole client->kernel->server->kernel->client")
    r("  loop on loopback. Subtract roughly 20-40us to approximate the")
    r("  server-only cost.")
    r("* Every Python callback serialises on the GIL. That is inherent to")
    r("  CPython, not to pocketsocket's bridge. The ps-nim-* rows show the")
    r("  ceiling available when python is not in the message path.")
    r("")

    if args.output:
        r.save(args.output)


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    main()
