#!/bin/bash
# Quick script to check if throughput benchmark can run

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "======================================================================"
echo "Checking Throughput Benchmark Dependencies"
echo "======================================================================"
echo ""

# Check Python
python3 benchmarks/archive/test_throughput_deps.py

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================================================"
    echo "Running a quick throughput test..."
    echo "======================================================================"
    echo ""
    python3 benchmarks/archive/benchmark_throughput.py --echo-only -n 3 -m 100
fi
