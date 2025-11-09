# Pocketsocket Benchmarks

This directory contains the performance benchmarking suite for pocketsocket.

## Benchmark Scripts

### 1. `benchmark.py` - Standalone CLI Binary Benchmark
Measures the startup time of the compiled `dist/pocketsocket-cli` binary.

**Usage:**
```bash
python3 benchmarks/benchmark.py -n 20
```

**What it measures:**
- Time To Launch (TTL) from process start to server ready
- Includes template loading and socket binding
- Pure Nim compiled binary performance

**Requirements:**
- Compiled CLI binary at `dist/pocketsocket-cli`
- Build with: `nimble buildCliCI -d:release -d:lto -d:strip`

---

### 2. `benchmark_python_module.py` - Python Module Benchmark
Measures the startup time of the Python module API (`pocketsocket.hook()` + `run_blocking_server()`).

**Usage:**
```bash
python3 benchmarks/benchmark_python_module.py -n 20
```

**What it measures:**
- Time To Launch (TTL) from server initialization to ready state
- Connection establishment time
- Python API overhead vs standalone CLI

**Requirements:**
- Installed pocketsocket Python module
- Build with: `nimble buildPyd` or `pip install -e .`

---

### 3. `benchmark_comparison.py` - Server Comparison Benchmark
Compares pocketsocket against other popular Python WebSocket servers.

**Usage:**
```bash
python3 benchmarks/benchmark_comparison.py -n 10
```

**What it measures:**
- Startup time comparison with websockets, Tornado, aiohttp, FastAPI
- Uses identical methodology for all servers (fair comparison)
- Subprocess-based measurement for consistency

**Requirements:**
```bash
pip install websockets tornado aiohttp fastapi uvicorn
```

**Servers tested:**
- `websockets` - Pure async WebSocket library
- `Tornado` - Async web framework with WebSocket support
- `aiohttp` - Async HTTP/WebSocket framework
- `FastAPI` - Modern web framework with WebSocket support (via Uvicorn)

---

## Running All Benchmarks

Use the master benchmark runner at the project root:

```bash
# From project root
./run_benchmarks.py -n 20 -o benchmarks/full_report.txt
```

**Options:**
- `-n` / `--iterations`: Number of iterations per benchmark (default: 10)
- `-o` / `--output`: Save report to file (default: benchmark_report.txt)
- `--skip-cli`: Skip CLI benchmark
- `--skip-python`: Skip Python module benchmark
- `--skip-comparison`: Skip comparison benchmark

---

## Benchmark Results

Result files are automatically saved in this directory:

- `benchmark_results.txt` - CLI benchmark results
- `benchmark_python_module_results.txt` - Python module results
- `benchmark_comparison_results.txt` - Comparison benchmark results
- `benchmark_report.txt` - Comprehensive report from `run_benchmarks.py`

---

## Methodology

All benchmarks measure **startup time** - the time from process start to the server being ready to accept connections.

**Why startup time matters:**
- Cold start performance for microservices
- Development iteration speed (server restarts)
- Scaling responsiveness (spinning up new instances)
- Testing overhead minimization

**Measurement approach:**
1. Start server process
2. Capture "Time To Launch" (TTL) from server logs
3. Verify server is accepting connections
4. Calculate statistics over multiple runs

**Fairness:**
- Same measurement methodology for all servers
- Subprocess-based execution (includes full initialization)
- Minimal configuration (comparable to real-world usage)
- Multiple iterations for statistical reliability

---

## Expected Results

Based on typical runs on Linux x86_64:

| Server | Average Startup | Speed Factor |
|--------|----------------|--------------|
| **Pocketsocket CLI** | **~0.8 ms** | **baseline** |
| **Pocketsocket Python** | **~1.0 ms** | **1.3x slower** |
| websockets | ~100 ms | 125x slower |
| Tornado | ~150 ms | 188x slower |
| aiohttp | ~230 ms | 288x slower |
| FastAPI | ~430 ms | 538x slower |

*Actual results may vary based on system configuration.*

---

### 4. `benchmark_throughput.py` - Client-to-Client Throughput Benchmark
Measures message passing throughput and latency between WebSocket clients.

**Usage:**
```bash
python3 benchmarks/benchmark_throughput.py -n 5 -m 1000
```

**What it measures:**
- Echo mode: Round-trip message latency (client -> server -> same client)
- Broadcast mode: Multi-client message distribution (1 sender -> N receivers)
- Batch mode: Rapid-fire send performance (send all, then receive all)
- Messages per second throughput
- Average latency per message

**Test Modes:**
```bash
# Run all throughput tests
python3 benchmarks/benchmark_throughput.py -n 5

# Echo only (round-trip latency)
python3 benchmarks/benchmark_throughput.py --echo-only -n 10 -m 1000

# Broadcast only (multi-client distribution)
python3 benchmarks/benchmark_throughput.py --broadcast-only -n 5 --clients 10

# Batch send only (maximum throughput)
python3 benchmarks/benchmark_throughput.py --batch-only -n 3 -m 10000
```

**Requirements:**
```bash
# pocketsocket module must be built
nimble buildPyd
pip install -e .

# Client library
pip install websockets
```

**Configuration Options:**
- `-n` / `--iterations`: Number of test iterations (default: 5)
- `-m` / `--messages`: Messages per iteration (default: 1000)
- `-s` / `--size`: Message size in bytes (default: 100)
- `--clients`: Number of clients for broadcast test (default: 5)
- `--echo-only`: Run only echo benchmark
- `--broadcast-only`: Run only broadcast benchmark
- `--batch-only`: Run only batch send benchmark

---

### 5. `benchmark_connections.py` - Connection Throughput Benchmark  
Measures WebSocket connection establishment and concurrent connection handling.

**Usage:**
```bash
python3 benchmarks/benchmark_connections.py -n 5 -c 100
```

**What it measures:**
- Sequential connection throughput (connections per second)
- Average connection establishment time
- Concurrent connection handling (N simultaneous connections)
- Connection stability under load

**Test Modes:**
```bash
# Run all connection tests
python3 benchmarks/benchmark_connections.py -n 5 -c 100

# Sequential only
python3 benchmarks/benchmark_connections.py --sequential-only -n 10 -c 200

# Concurrent only
python3 benchmarks/benchmark_connections.py --concurrent-only -n 5 -c 100
```

**Latest Results:**
- **Sequential:** ~1,300 connections/second, 0.78ms average
- **Concurrent:** 50 simultaneous connections in ~0.53s

---

For detailed benchmark results and analysis, see [BENCHMARKS.md](../BENCHMARKS.md) in the project root.
