#!/bin/bash
# Quick script to check if throughput benchmark can run

echo "======================================================================"
echo "Checking Throughput Benchmark Dependencies"
echo "======================================================================"
echo ""

# Check Python
python3 benchmarks/test_throughput_deps.py

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================================================"
    echo "Running a quick throughput test..."
    echo "======================================================================"
    echo ""
    python3 benchmarks/benchmark_throughput.py --echo-only -n 3 -m 100
fi
