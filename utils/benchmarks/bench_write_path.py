"""Repeated echo throughput and latency measurements for write-path changes."""

import argparse
import statistics

from lib import workloads
from lib.harness import HOST, PYTHON_PKG, Report, ServerProcess, free_port
from lib.servers import available_comparisons, comparison_code, pocketsocket_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--label", required=True)
    parser.add_argument("--targets", nargs="+", default=[
        "ps-nim-echo", "ps-hook-echo", "aiohttp",
    ])
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    available = {"ps-nim-echo", "ps-hook-echo", *available_comparisons()}
    if set(args.targets) - available:
        parser.error(f"unavailable targets: {sorted(set(args.targets) - available)}")

    report = Report("Echo write-path benchmark: " + args.label)
    report.env()
    report.data["options"] = vars(args)
    report.data["benchmarks"] = {"throughput": {}, "latency": {}}
    report("Release extension; default worker count; one connection; batch=256.")
    report("Each sample uses a fresh server and 200 warmup echoes per workload.")

    for size in (64, 1024, 16384):
        samples = {target: [] for target in args.targets}
        latency_samples = {target: [] for target in args.targets}
        for repetition in range(args.runs):
            offset = repetition % len(args.targets)
            targets = args.targets[offset:] + args.targets[:offset]
            for target in targets:
                port = free_port()
                code = (pocketsocket_code(target, PYTHON_PKG, HOST, port)
                        if target.startswith("ps-")
                        else comparison_code(target, HOST, port))
                server = ServerProcess(code, port, label=target)
                try:
                    samples[target].append(workloads.batched(
                        port, 100000 if size <= 1024 else 12000, size, 256,
                    ))
                    latency_samples[target].append(workloads.latency(
                        port, 2000, size,
                    ))
                finally:
                    server.stop()
                    server.cleanup()
        report.section(f"Payload {size} bytes")
        for target in args.targets:
            rate = statistics.median(sample["rate"] for sample in samples[target])
            p50 = statistics.median(sample["p50"] for sample in latency_samples[target])
            p99 = statistics.median(sample["p99"] for sample in latency_samples[target])
            report(f"{target:<20} {rate:>12,.0f} msg/s  p50={p50:.1f} us  p99={p99:.1f} us")
            report.data["benchmarks"]["throughput"].setdefault(str(size), {})[target] = {
                "median_rate": rate, "samples": samples[target],
            }
            report.data["benchmarks"]["latency"].setdefault(str(size), {})[target] = {
                "median_p50_us": p50, "median_p99_us": p99,
                "samples": latency_samples[target],
            }
        report.data.setdefault("client_parse_ceiling", {})[str(size)] = (
            workloads.client_parse_ceiling(size)
        )
    report.save(args.output)


if __name__ == "__main__":
    main()