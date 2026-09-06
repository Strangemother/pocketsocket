# Batched Output Experiment

## Scope

The native writer now gathers queued headers and payloads using Linux
`sendmsg(MSG_NOSIGNAL)`. Each writable event drains at most 256 KiB or 16
syscalls, with at most 16 vectors per syscall. A short write retains the exact
offset; `EAGAIN` leaves output queued; `EINTR` retries within the syscall budget.
Connection-closing output is a batching boundary. Other platforms retain
scalar sends with the same bounded draining and error handling.

Worker scheduling, worker count, the receive parser, Python callbacks, and
selector ownership were not changed.

## Method

- Same 2-CPU Linux host, Python 3.12.1, Nim 2.2.10, ARC and release builds.
- Existing benchmark server definitions and raw-socket client.
- Default worker count, one connection, batches of 256 frames.
- Five fresh-server samples for every target and payload; target order rotates.
- Each throughput sample measures 100,000 messages at 64B/1KB, or 12,000 at 16KB.
- Each latency sample measures 2,000 round trips. Both workloads have 200 warmups.
- aiohttp is rerun as a control. Other competitors were not rerun in this experiment.
- Values below are medians of the five samples, not a comparison to the August run.

Raw samples and environment metadata are in [baseline.json](baseline.json) and
[vectored-drain.json](vectored-drain.json). Text summaries are in
[baseline.txt](baseline.txt) and [vectored-drain.txt](vectored-drain.txt).

## Throughput

| Path | Payload | Before msg/s | After msg/s | After / Before |
| --- | --- | ---: | ---: | ---: |
| Pure Nim | 64B | 74,406 | 286,288 | 3.85x |
| Pure Nim | 1KB | 52,938 | 109,243 | 2.06x |
| Pure Nim | 16KB | 19,912 | 22,616 | 1.14x |
| Python hook | 64B | 40,493 | 51,134 | 1.26x |
| Python hook | 1KB | 36,485 | 48,305 | 1.32x |
| Python hook | 16KB | 15,292 | 18,848 | 1.23x |
| aiohttp control | 64B | 97,973 | 102,958 | 1.05x |
| aiohttp control | 1KB | 72,724 | 79,921 | 1.10x |
| aiohttp control | 16KB | 48,180 | 46,989 | 0.98x |

Pure Nim is ahead of aiohttp at 64B and 1KB in this workload. It remains behind
at 16KB, as does the Python-hook path at every measured payload size.

## Latency and Limitations

Pure-Nim round-trip latency, in microseconds:

| Payload | Before p50 | After p50 | Before p99 | After p99 |
| --- | ---: | ---: | ---: | ---: |
| 64B | 55.5 | 49.9 | 84.5 | 67.1 |
| 1KB | 56.8 | 52.4 | 71.7 | 84.3 |
| 16KB | 78.7 | 74.6 | 131.1 | 157.3 |

Median latency improves, but p99 is higher at 1KB and 16KB. These are short
shared-host runs, not evidence of a universal tail-latency improvement. The
aiohttp control varies by up to 10% between phases. After-change pure-Nim
16KB samples range from 15,412 to 24,185 msg/s, so its modest median gain should
not be treated as a stable percentage improvement.

The client's in-memory parse ceilings after the change are approximately 859k,
558k, and 271k msg/s respectively, above the reported throughputs. This does
not eliminate all client/kernel overhead. The single-connection benchmark does
not establish multicore scalability, sustained overload behavior, or production
capacity. Syscall counts were not separately profiled.

## Reproduce

Run from the repository root, with Nim dependencies and aiohttp installed:

```sh
python3 server/compile.py pyd --release --no-setup
python3 utils/benchmarks/bench_write_path.py --label local --runs 5 -o /tmp/pocketsocket-write-path.txt
nim c -r -d:release --hints:off server/tests/test_write_path.nim
python3 utils/benchmarks/test_write_path.py
cd server && nimble test -y --hints:off
```

To obtain a new before/after pair, build and measure the original writer first,
then rebuild with the writer change and rerun the identical command with a new
label/output path. The benchmark does not rebuild the extension automatically.

## Validation

Nine focused Nim tests cover partial header/body offsets, multiple vectors,
empty payloads, close boundaries, real socket backpressure and recovery,
per-event budgets, and peer closure without SIGPIPE. A wire-level integration
test covers HTTP keep-alive/close responses and four concurrent WebSocket clients
through each echo mode, checking ordered text/binary payloads, empty frames,
large frames, and close replies. The full Nim suite passes with five existing
skips. The Windows fallback passes `nim check --os:windows --cpu:amd64`; Windows
runtime behavior and other OS targets were not tested. EINTR retry handling is
implemented but not exercised by a signal-injection test.