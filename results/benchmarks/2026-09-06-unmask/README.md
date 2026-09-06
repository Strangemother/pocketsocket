# Direct-to-Destination Unmasking

## Change

The WebSocket parser now unmasks each complete frame payload directly into
its independently owned message buffer. Previously it unmasked in the receive
buffer, then copied those bytes into the message buffer. The receive-buffer
compaction, allocation strategy, worker queues, and output writer are unchanged.

The new private `copyUnmaskedPayload` helper takes a read-only source
`openArray[char]`, a mutable destination `openArray[char]`, and a four-byte mask.
These are bounded views, not copied strings or unchecked pointers. The caller
first verifies that the full frame has arrived and grows the destination as
needed. Empty payloads skip view construction. Each fragment appends at the
current message offset, but its mask index restarts at zero.

## Why the First Attempt Was Replaced

The first fused loop directly indexed nested fields of `dataEntry` on each byte.
It passed correctness tests but regressed 16 KiB median throughput to 17,154
msg/s (pure Nim) and 14,754 msg/s (Python hook). Its results are retained in
[direct-unmask.json](direct-unmask.json).

Generated C inspection showed repeated variant-field checks, index arithmetic,
and `nimPrepareStrMutationV2` inside that loop. Moving the operation into the
bounded-view helper moves string mutation preparation and nested field access
outside the byte loop. Bounds checks remain enabled. This is the final version;
there is no SIMD, raw-pointer code, or global safety-check disabling.

This distinction matters when interpreting the result: the experiment combines
removing a payload pass with simplifying access inside the remaining loop.
It does not isolate the speedup attributable to each mechanism, and generated
C inspection is not a CPU profile of the final machine code.

## Method

- Same two-CPU Linux host, Python 3.12.1, Nim 2.2.10, release extension with ARC.
- Existing batched echo runner: one connection, 256 frames per client batch.
- Five fresh-server samples per target and payload, rotating target order.
- 100,000 messages per throughput sample at 64B/1 KiB; 12,000 at 16 KiB.
- 2,000 measured round trips per latency sample; 200 warmups per workload.
- aiohttp rerun as a control in every phase.
- The user's removal of the hook debug print is present in every build, including baseline. This parser change does not modify that file.
- Baseline is the existing batched writer with the original unmask/copy parser, not the August benchmark or the original unbatched writer.

The runner's printed title still says "write-path benchmark" because the same
runner was reused without modification. Labels distinguish the parser versions.

## Final Throughput

Medians of five samples:

| Path | Payload | Before msg/s | Final msg/s | Final / Before |
| --- | --- | ---: | ---: | ---: |
| Pure Nim | 64B | 233,355 | 313,329 | 1.34x |
| Pure Nim | 1 KiB | 104,425 | 112,819 | 1.08x |
| Pure Nim | 16 KiB | 20,528 | 28,773 | 1.40x |
| Python hook | 64B | 56,395 | 56,443 | 1.00x |
| Python hook | 1 KiB | 51,200 | 50,706 | 0.99x |
| Python hook | 16 KiB | 17,344 | 24,573 | 1.42x |
| aiohttp control | 64B | 94,907 | 92,928 | 0.98x |
| aiohttp control | 1 KiB | 78,652 | 73,749 | 0.94x |
| aiohttp control | 16 KiB | 43,846 | 40,532 | 0.92x |

The targeted 16 KiB workload improves in both PocketSocket modes. Pure Nim
still trails aiohttp at that size: 28,773 versus 40,532 msg/s in the final phase.
The Python-hook results at smaller payload sizes are effectively unchanged
at this experiment's precision.

## Latency and Limits

Median of each run's latency percentiles, in microseconds:

| Path | Payload | Before p50 | Final p50 | Before p99 | Final p99 |
| --- | --- | ---: | ---: | ---: | ---: |
| Pure Nim | 64B | 41.6 | 51.3 | 68.7 | 73.3 |
| Pure Nim | 1 KiB | 52.7 | 52.7 | 78.0 | 77.6 |
| Pure Nim | 16 KiB | 76.3 | 68.0 | 245.2 | 117.9 |
| Python hook | 64B | 53.5 | 52.2 | 107.8 | 107.7 |
| Python hook | 1 KiB | 65.0 | 64.8 | 109.6 | 250.8 |
| Python hook | 16 KiB | 91.4 | 83.1 | 161.8 | 164.6 |

This is not a uniform latency improvement: pure-Nim 64B p50 and Python-hook
1 KiB p99 increased. No statistical significance or confidence interval was
calculated. The phases ran sequentially on a shared host; the aiohttp control
also varied, decreasing by about 8% at 16 KiB. Treat the reported gains as
observations, not deployment guarantees. No new multicore, overload, or full
RFC 6455 conformance claim follows from these tests.

## Validation

Four new parser tests pass on both the original and final parser:

- Binary payload sizes 0-5, 125-127, 1 KiB, 16 KiB, 65,535, and 65,536 bytes, with nontrivial masking and patterned payloads.
- Fragmented messages with a three-byte first fragment and a large continuation using a different mask, forcing destination growth and a non-aligned message offset.
- Every split point of a short text frame, preserving incomplete input until the remainder arrives.
- A complete frame followed by an incomplete large frame, checking compaction and retention of the first delivered message.

The existing HTTP/WebSocket integration check passes on the rebuilt extension.
The full Nim suite passes with five pre-existing skips; the new parser tests
run in both release mode and the normal suite configuration. Other operating
systems were not exercised in this experiment.

## Artifacts and Reproduction

- [baseline.json](baseline.json): original parser.
- [direct-unmask.json](direct-unmask.json): superseded nested-index fused loop.
- [direct-unmask-views.json](direct-unmask-views.json): final bounded-view helper.
- [baseline.txt](baseline.txt), [direct-unmask.txt](direct-unmask.txt), and [direct-unmask-views.txt](direct-unmask-views.txt): readable summaries.

From the repository root:

```sh
nim c -r -d:release --hints:off server/tests/test_receive_unmask.nim
python3 server/compile.py pyd --release --no-setup
python3 utils/benchmarks/test_write_path.py
python3 utils/benchmarks/bench_write_path.py --label local-unmask --runs 5 -o /tmp/local-unmask.txt
```

Run `nimble test -y --hints:off` from the server directory for the full suite.
To repeat a comparison, rebuild each source version separately with unchanged
build settings and save distinct result paths. The benchmark runner does not
rebuild the extension itself.