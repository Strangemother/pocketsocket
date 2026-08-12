# Cleanup & Speed-Up Guide

Working notes for making pocketsocket smaller, clearer and faster.

Written for two audiences: the maintainer, and future agents picking up the
work cold. Everything here was verified against the tree on **2026-08-09** —
paths, line numbers and measurements are real, not inferred. Where something is
an estimate or an untested idea it is labelled as such.

## The documents

| file | purpose |
| --- | --- |
| [INVENTORY.md](INVENTORY.md) | Literal file-by-file list: what to remove or change, why, and the suggested fix. Start here. |
| [PERFORMANCE.md](PERFORMANCE.md) | Speed work already done, the method used for each, and the measured result. Plus the remaining opportunities ranked by expected payoff. |
| [MUMMY_FORK.md](MUMMY_FORK.md) | Plan for vendoring mummy into `server/src/` and rewriting its io path. The client-id change and the syscall-level speed work live here. |

Benchmark *methodology* lives in [`benchmarks/README.md`](../../benchmarks/README.md)
and is not duplicated here. Read it before trusting any number you produce.

## The two rules that matter most

**1. Verify the build is optimised before measuring anything.**

`nimble build` injects `-d:release` automatically. A custom nimble `task` does
**not**. This silently shipped an unoptimised extension module for a long time
— worth ~2x throughput. Check the compiler hint:

```
Hint: mm: arc; threads: on; opt: speed; options: -d:release   <- correct
Hint: mm: arc; threads: on; opt: none (DEBUG BUILD, ...)      <- do not measure this
```

**2. Measure before and after, on the same host, in the same run.**

Several confident conclusions in this project's history turned out to be wrong.
Two prior documents concluded the Python callback was architecturally
impossible and recommended deleting the feature; it costs about 5 µs. The
per-message thread handoff was blamed for the throughput ceiling; the real
cause was mummy's single io thread. Both errors came from reasoning instead of
measuring.

## Quick start for an agent

```bash
cd server && ./setup.sh                     # toolchain, deps, build, smoke test
cd server && nimble test                    # unit tests
cd .. && python3 benchmarks/run_all.py --quick       # sanity pass
python3 benchmarks/run_all.py --tag mychange
```

Compare your `--tag` output against
`benchmarks/results/2026-08-05-16core-release-*.txt`, which is the current
reference. Earlier result files are labelled and were produced against a debug
build — do not quote their absolute figures.

## Current state in one paragraph

The Python callback bridge works and is cheap (~5 µs/message). Per-message
debug logging is gone (0 bytes/message). The extension builds optimised.
Startup is the standout metric at ~20 ms versus 108-385 ms for asyncio
frameworks, and connection establishment leads at ~4,900/s. Raw echo
throughput is ~45k msg/s, roughly half of aiohttp, and is capped by mummy's
**single io thread** — a limit that does not respond to cores, connections or
worker-thread count. Lifting it requires a transport with multiple io threads.
