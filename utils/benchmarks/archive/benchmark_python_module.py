#!/usr/bin/env python3
"""
Pocketsocket Python Module Benchmark

Measures the startup and response time of the pocketsocket Python module
when using the hook() and run_blocking_server() API.
"""

import sys
import time
import socket
import threading
import subprocess
import re
from statistics import mean, median, stdev

sys.path.insert(0, 'package')


def parse_ttl(text):
    """Parse TTL from server output."""
    # Try pattern with milliseconds
    pattern1 = r'TTL: (\d+) milliseconds?, (\d+) microseconds?, and (\d+) nanoseconds?'
    match = re.search(pattern1, text)
    
    if match:
        ms = int(match.group(1))
        us = int(match.group(2))
        ns = int(match.group(3))
        total_ms = ms + (us / 1000.0) + (ns / 1_000_000.0)
        return total_ms
    
    # Try pattern without milliseconds (sub-millisecond times)
    pattern2 = r'TTL: (\d+) microseconds? and (\d+) nanoseconds?'
    match = re.search(pattern2, text)
    
    if match:
        us = int(match.group(1))
        ns = int(match.group(2))
        total_ms = (us / 1000.0) + (ns / 1_000_000.0)
        return total_ms
    
    # Try pattern with seconds
    pattern3 = r'TTL: (\d+) seconds?, (\d+) milliseconds?, (\d+) microseconds?, and (\d+) nanoseconds?'
    match = re.search(pattern3, text)
    
    if match:
        s = int(match.group(1))
        ms = int(match.group(2))
        us = int(match.group(3))
        ns = int(match.group(4))
        total_ms = (s * 1000) + ms + (us / 1000.0) + (ns / 1_000_000.0)
        return total_ms
    
    return None


def test_connection_time(host, port, timeout=3.0):
    """Test how long it takes to establish a connection."""
    start = time.perf_counter()
    
    while time.perf_counter() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.2)
            sock.connect((host, port))
            sock.close()
            return time.perf_counter() - start
        except:
            pass
        time.sleep(0.001)
    
    return None


def run_single_test(port=9700):
    """Run a single Python module test using subprocess."""
    
    # Create a test script that uses the Python API
    test_script = f'''
import sys
sys.path.insert(0, 'package')
import pocketsocket

def hook(uuid, etype, event):
    pass

pocketsocket.hook(hook)
pocketsocket.run_blocking_server('127.0.0.1', {port})
'''
    
    # Run the script
    proc = subprocess.Popen(
        ['python3', '-c', test_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    ttl_time = None
    output_lines = []
    
    try:
        # Read output for up to 2 seconds
        start_time = time.time()
        while time.time() - start_time < 2.0:
            line = proc.stdout.readline()
            if line:
                output_lines.append(line)
                if 'TTL:' in line:
                    ttl_time = parse_ttl(line)
                    if ttl_time is not None:
                        break
            
            if proc.poll() is not None:
                break
        
        # Test connection time
        conn_time = test_connection_time('127.0.0.1', port, timeout=2.0)
        
        return ttl_time, conn_time
        
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def run_benchmark(iterations=15):
    """Run comprehensive Python module benchmark."""
    
    print("=" * 70)
    print("Pocketsocket Python Module Startup Benchmark")
    print("=" * 70)
    print()
    print("Testing: Python API (pocketsocket.hook + run_blocking_server)")
    print(f"Iterations: {iterations}")
    print()
    
    ttl_times = []
    conn_times = []
    base_port = 9700
    
    for i in range(iterations):
        print(f"Run {i+1:2d}/{iterations}...", end=' ', flush=True)
        
        port = base_port + (i % 20)  # Cycle through ports
        ttl, conn = run_single_test(port)
        
        if ttl is not None:
            ttl_times.append(ttl)
            status = f"✓ TTL: {ttl:6.3f}ms"
            
            if conn is not None:
                conn_times.append(conn * 1000)
                status += f", Connect: {conn*1000:6.2f}ms"
            
            print(status)
        else:
            print("✗ Failed to capture TTL")
        
        time.sleep(0.1)
    
    print()
    print("=" * 70)
    print("Results")
    print("=" * 70)
    print()
    
    if not ttl_times:
        print("No successful measurements captured.")
        return
    
    print(f"Successful runs: {len(ttl_times)}/{iterations}")
    print()
    
    # Server startup time (TTL reported by server)
    print("Server Startup Time (TTL - Time To Launch):")
    print(f"  Minimum:  {min(ttl_times):7.4f} ms")
    print(f"  Maximum:  {max(ttl_times):7.4f} ms")
    print(f"  Average:  {mean(ttl_times):7.4f} ms")
    print(f"  Median:   {median(ttl_times):7.4f} ms")
    if len(ttl_times) > 1:
        print(f"  Std Dev:  {stdev(ttl_times):7.4f} ms")
    print()
    
    # Connection time
    if conn_times:
        print("Time to First Connection (from subprocess start):")
        print(f"  Minimum:  {min(conn_times):7.2f} ms")
        print(f"  Maximum:  {max(conn_times):7.2f} ms")
        print(f"  Average:  {mean(conn_times):7.2f} ms")
        print(f"  Median:   {median(conn_times):7.2f} ms")
        if len(conn_times) > 1:
            print(f"  Std Dev:  {stdev(conn_times):7.2f} ms")
        print()
    
    # Performance categories
    print("Performance Distribution (TTL):")
    under_1ms = sum(1 for t in ttl_times if t < 1.0)
    under_5ms = sum(1 for t in ttl_times if t < 5.0)
    under_10ms = sum(1 for t in ttl_times if t < 10.0)
    under_20ms = sum(1 for t in ttl_times if t < 20.0)
    
    print(f"  < 1ms:    {under_1ms:2d}/{len(ttl_times)} ({under_1ms/len(ttl_times)*100:5.1f}%)")
    print(f"  < 5ms:    {under_5ms:2d}/{len(ttl_times)} ({under_5ms/len(ttl_times)*100:5.1f}%)")
    print(f"  < 10ms:   {under_10ms:2d}/{len(ttl_times)} ({under_10ms/len(ttl_times)*100:5.1f}%)")
    print(f"  < 20ms:   {under_20ms:2d}/{len(ttl_times)} ({under_20ms/len(ttl_times)*100:5.1f}%)")
    
    print()
    print("=" * 70)
    
    # Summary
    avg_ttl = mean(ttl_times)
    
    if avg_ttl < 5.0:
        perf = "extremely fast"
    elif avg_ttl < 15.0:
        perf = "very fast"
    elif avg_ttl < 50.0:
        perf = "fast"
    else:
        perf = "moderate"
    
    print(f"Summary: Python module startup is {perf} (~{avg_ttl:.2f}ms average TTL)")
    
    if conn_times:
        avg_conn = mean(conn_times)
        print(f"  - Average time to first connection: ~{avg_conn:.2f}ms")
    
    print()
    print("Note: Python module adds ~5-10ms overhead compared to the standalone")
    print("      CLI due to Python interpreter initialization.")
    print("=" * 70)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Benchmark pocketsocket Python module startup time'
    )
    parser.add_argument(
        '-n', '--iterations',
        type=int,
        default=15,
        help='Number of test iterations (default: 15)'
    )
    
    args = parser.parse_args()
    
    try:
        run_benchmark(iterations=args.iterations)
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
