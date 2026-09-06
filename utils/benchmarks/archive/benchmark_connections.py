#!/usr/bin/env python3
"""
Pocketsocket Connection Throughput Benchmark

Since the Python module has issues and the CLI doesn't echo,
this benchmark measures connection establishment throughput instead.
"""

import argparse
import asyncio
import statistics
import subprocess
import sys
import time
import socket
from datetime import datetime
import websockets


def wait_for_server(host='127.0.0.1', port=8090, timeout=5):
    """Wait for server to be ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                time.sleep(0.1)
                return True
        except:
            pass
        time.sleep(0.1)
    return False


def start_cli_server():
    """Start pocketsocket CLI server"""
    cli_path = './dist/pocketsocket-cli'
    
    process = subprocess.Popen(
        [cli_path, '--run'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    if not wait_for_server():
        process.terminate()
        raise RuntimeError("CLI server failed to start")
    
    return process


async def connection_test(num_connections=100):
    """Test connection establishment throughput"""
    uri = "ws://127.0.0.1:8090/ws/"
    
    start_time = time.perf_counter()
    
    for i in range(num_connections):
        async with websockets.connect(uri) as websocket:
            # Just connect and disconnect
            pass
            
    end_time = time.perf_counter()
    
    duration = end_time - start_time
    connections_per_second = num_connections / duration
    avg_time_ms = (duration / num_connections) * 1000
    
    return {
        'connections': num_connections,
        'duration': duration,
        'connections_per_second': connections_per_second,
        'avg_time_ms': avg_time_ms
    }


async def concurrent_connections_test(num_connections=50):
    """Test concurrent connection handling"""
    uri = "ws://127.0.0.1:8090/ws/"
    
    async def connect_and_hold():
        async with websockets.connect(uri) as websocket:
            await asyncio.sleep(0.5)
    
    start_time = time.perf_counter()
    
    # Create all connections concurrently
    tasks = [connect_and_hold() for _ in range(num_connections)]
    await asyncio.gather(*tasks)
    
    end_time = time.perf_counter()
    
    duration = end_time - start_time
    
    return {
        'connections': num_connections,
        'duration': duration,
        'connections_per_second': num_connections / duration
    }


def run_connection_benchmark(iterations=5, num_connections=100):
    """Run connection throughput benchmark"""
    print("\n" + "="*70)
    print("CONNECTION ESTABLISHMENT BENCHMARK")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Server:         pocketsocket-cli (compiled binary)")
    print(f"  Iterations:     {iterations}")
    print(f"  Connections:    {num_connections} per iteration")
    print(f"  Test type:      Sequential connect/disconnect")
    
    server = start_cli_server()
    
    try:
        results = []
        
        print(f"\nRunning {iterations} iterations...")
        for i in range(iterations):
            result = asyncio.run(connection_test(num_connections))
            results.append(result)
            print(f"  Run {i+1}/{iterations}: {result['connections_per_second']:,.2f} conn/s, "
                  f"{result['avg_time_ms']:.3f}ms avg time")
        
        # Calculate statistics
        throughputs = [r['connections_per_second'] for r in results]
        times = [r['avg_time_ms'] for r in results]
        
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        print(f"\nConnection Throughput (connections per second):")
        print(f"  Minimum:   {min(throughputs):>12,.2f} conn/s")
        print(f"  Maximum:   {max(throughputs):>12,.2f} conn/s")
        print(f"  Average:   {statistics.mean(throughputs):>12,.2f} conn/s")
        print(f"  Median:    {statistics.median(throughputs):>12,.2f} conn/s")
        if len(throughputs) > 1:
            print(f"  Std Dev:   {statistics.stdev(throughputs):>12,.2f}")
        
        print(f"\nConnection Time:")
        print(f"  Minimum:   {min(times):>12.3f} ms")
        print(f"  Maximum:   {max(times):>12.3f} ms")
        print(f"  Average:   {statistics.mean(times):>12.3f} ms")
        print(f"  Median:    {statistics.median(times):>12.3f} ms")
        
        print("\n" + "="*70)
        print(f"Summary: {statistics.mean(throughputs):,.0f} connections/second average")
        print("="*70)
        
        return {
            'throughput': statistics.mean(throughputs),
            'avg_time': statistics.mean(times)
        }
        
    finally:
        server.terminate()
        server.wait(timeout=2)


def run_concurrent_benchmark(iterations=3, num_connections=50):
    """Run concurrent connection benchmark"""
    print("\n" + "="*70)
    print("CONCURRENT CONNECTION BENCHMARK")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Server:         pocketsocket-cli (compiled binary)")
    print(f"  Iterations:     {iterations}")
    print(f"  Connections:    {num_connections} simultaneous")
    print(f"  Test type:      Concurrent connections held for 0.5s")
    
    server = start_cli_server()
    
    try:
        results = []
        
        print(f"\nRunning {iterations} iterations...")
        for i in range(iterations):
            result = asyncio.run(concurrent_connections_test(num_connections))
            results.append(result)
            print(f"  Run {i+1}/{iterations}: {result['duration']:.3f}s total time")
        
        # Calculate statistics
        durations = [r['duration'] for r in results]
        
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        print(f"\nConcurrent Connection Handling:")
        print(f"  Connections:   {num_connections} simultaneous")
        print(f"  Avg Duration:  {statistics.mean(durations):.3f} seconds")
        print(f"  Min Duration:  {min(durations):.3f} seconds")
        print(f"  Max Duration:  {max(durations):.3f} seconds")
        
        print("\n" + "="*70)
        print(f"Summary: {num_connections} concurrent connections in ~{statistics.mean(durations):.2f}s")
        print("="*70)
        
        return {
            'connections': num_connections,
            'avg_duration': statistics.mean(durations)
        }
        
    finally:
        server.terminate()
        server.wait(timeout=2)


def main():
    parser = argparse.ArgumentParser(
        description='Benchmark pocketsocket connection throughput'
    )
    parser.add_argument(
        '-n', '--iterations',
        type=int,
        default=5,
        help='Number of iterations per test (default: 5)'
    )
    parser.add_argument(
        '-c', '--connections',
        type=int,
        default=100,
        help='Number of connections per iteration (default: 100)'
    )
    parser.add_argument(
        '--sequential-only',
        action='store_true',
        help='Run only sequential connection benchmark'
    )
    parser.add_argument(
        '--concurrent-only',
        action='store_true',
        help='Run only concurrent connection benchmark'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("POCKETSOCKET CONNECTION THROUGHPUT BENCHMARK")
    print("="*70)
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = {}
    
    # Run selected benchmarks
    if args.concurrent_only:
        all_results['concurrent'] = run_concurrent_benchmark(args.iterations, args.connections // 2)
    elif args.sequential_only:
        all_results['sequential'] = run_connection_benchmark(args.iterations, args.connections)
    else:
        # Run both
        all_results['sequential'] = run_connection_benchmark(args.iterations, args.connections)
        all_results['concurrent'] = run_concurrent_benchmark(args.iterations, args.connections // 2)
        
        # Print summary
        print("\n\n" + "="*70)
        print("OVERALL SUMMARY")
        print("="*70)
        print(f"\nSequential:     {all_results['sequential']['throughput']:>12,.0f} conn/s")
        print(f"                {all_results['sequential']['avg_time']:>12.3f} ms avg")
        print(f"\nConcurrent:     {all_results['concurrent']['connections']:>12,} connections")
        print(f"                {all_results['concurrent']['avg_duration']:>12.3f} s duration")
        print("\n" + "="*70)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
