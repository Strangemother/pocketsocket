#!/usr/bin/env python3
"""
Pocketsocket Server Startup Time Benchmark

Measures the startup time reported by pocketsocket itself (TTL),
extracted from multiple runs of the server.
"""

import sys
import time
import subprocess
import re
import select
from statistics import mean, median, stdev


def parse_ttl(text):
    """Parse TTL from server output.
    
    Formats:
      - "TTL: X milliseconds, Y microseconds, and Z nanoseconds"
      - "TTL: Y microseconds and Z nanoseconds"
    Returns: total time in milliseconds
    """
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
    
    return None


def run_single_test(cli_path):
    """Run one server startup test and capture TTL."""
    
    proc = subprocess.Popen(
        [cli_path, '--run'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,  # Use binary mode for better control
        bufsize=0    # Unbuffered
    )
    
    output = b''
    ttl = None
    
    try:
        # Read output for up to 2 seconds
        start_time = time.time()
        while time.time() - start_time < 2.0:
            # Use select to check if data is available
            ready, _, _ = select.select([proc.stdout], [], [], 0.1)
            
            if ready:
                chunk = proc.stdout.read(1024)
                if chunk:
                    output += chunk
                    # Check if we have TTL in the output
                    text = output.decode('utf-8', errors='ignore')
                    if 'TTL:' in text:
                        ttl = parse_ttl(text)
                        if ttl is not None:
                            break
            
            # Check if process has exited
            if proc.poll() is not None:
                # Read any remaining output
                remaining = proc.stdout.read()
                if remaining:
                    output += remaining
                break
        
        return ttl
        
    finally:
        # Cleanup
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


def main():
    import argparse
    import os
    
    parser = argparse.ArgumentParser(
        description='Benchmark pocketsocket server startup time'
    )
    parser.add_argument(
        '-n', '--iterations', 
        type=int, 
        default=10,
        help='Number of test iterations (default: 10)'
    )
    parser.add_argument(
        '--cli',
        default='dist/pocketsocket-cli',
        help='Path to CLI binary (default: dist/pocketsocket-cli)'
    )
    
    args = parser.parse_args()
    
    # Check if CLI exists
    if not os.path.exists(args.cli):
        print(f"Error: CLI binary not found at '{args.cli}'")
        print(f"Please build it first with: nimble buildCliCI -d:release")
        sys.exit(1)
    
    print("=" * 70)
    print("Pocketsocket Server Startup Benchmark")
    print("=" * 70)
    print()
    print(f"Testing: {args.cli}")
    print(f"Iterations: {args.iterations}")
    print()
    
    ttl_times = []
    
    for i in range(args.iterations):
        print(f"Run {i+1:2d}/{args.iterations}...", end=' ', flush=True)
        
        ttl = run_single_test(args.cli)
        
        if ttl is not None:
            ttl_times.append(ttl)
            print(f"✓ {ttl:7.4f} ms")
        else:
            print("✗ Failed to capture TTL")
        
        # Small delay between runs
        time.sleep(0.05)
    
    # Display results
    print()
    print("=" * 70)
    print("Results")
    print("=" * 70)
    print()
    
    if not ttl_times:
        print("No successful measurements captured.")
        sys.exit(1)
    
    print(f"Successful runs: {len(ttl_times)}/{args.iterations}")
    print()
    print("Server Startup Time (TTL):")
    print(f"  Minimum:  {min(ttl_times):7.4f} ms")
    print(f"  Maximum:  {max(ttl_times):7.4f} ms")
    print(f"  Average:  {mean(ttl_times):7.4f} ms")
    print(f"  Median:   {median(ttl_times):7.4f} ms")
    
    if len(ttl_times) > 1:
        print(f"  Std Dev:  {stdev(ttl_times):7.4f} ms")
    
    print()
    
    # Performance categories
    under_1ms = sum(1 for t in ttl_times if t < 1.0)
    under_10ms = sum(1 for t in ttl_times if t < 10.0)
    under_20ms = sum(1 for t in ttl_times if t < 20.0)
    
    print("Performance Distribution:")
    print(f"  < 1ms:    {under_1ms:2d}/{len(ttl_times)} ({under_1ms/len(ttl_times)*100:5.1f}%)")
    print(f"  < 10ms:   {under_10ms:2d}/{len(ttl_times)} ({under_10ms/len(ttl_times)*100:5.1f}%)")
    print(f"  < 20ms:   {under_20ms:2d}/{len(ttl_times)} ({under_20ms/len(ttl_times)*100:5.1f}%)")
    
    print()
    print("=" * 70)
    
    # Summary statement
    avg = mean(ttl_times)
    if avg < 1.0:
        perf = "sub-millisecond"
    elif avg < 10.0:
        perf = "extremely fast"
    elif avg < 50.0:
        perf = "very fast"
    else:
        perf = "fast"
    
    print(f"Summary: Server startup is {perf} (~{avg:.2f}ms average)")
    print("=" * 70)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
        sys.exit(130)
