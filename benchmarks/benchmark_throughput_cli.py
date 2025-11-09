#!/usr/bin/env python3
"""
Pocketsocket CLI Throughput Benchmark

Measures message throughput using the compiled pocketsocket-cli binary
as the server (which is more stable than the Python module for this test).
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


async def echo_throughput_test(num_messages=1000, message_size=100):
    """Test echo throughput using CLI server"""
    uri = "ws://127.0.0.1:8090/ws/"
    
    async with websockets.connect(uri) as websocket:
        payload = "x" * message_size
        
        start_time = time.perf_counter()
        
        for i in range(num_messages):
            await websocket.send(payload)
            response = await websocket.recv()
            
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        messages_per_second = num_messages / duration
        avg_latency_ms = (duration / num_messages) * 1000
        
        return {
            'messages': num_messages,
            'duration': duration,
            'messages_per_second': messages_per_second,
            'avg_latency_ms': avg_latency_ms,
            'message_size': message_size
        }


async def batch_send_test(num_messages=10000, message_size=100):
    """Test rapid fire sending"""
    uri = "ws://127.0.0.1:8090/ws/"
    
    async with websockets.connect(uri) as websocket:
        payload = "x" * message_size
        
        start_time = time.perf_counter()
        
        # Send all messages
        for i in range(num_messages):
            await websocket.send(payload)
        
        # Receive all responses
        for i in range(num_messages):
            await websocket.recv()
        
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        messages_per_second = num_messages / duration
        
        return {
            'messages': num_messages,
            'duration': duration,
            'messages_per_second': messages_per_second,
            'message_size': message_size
        }


def run_echo_benchmark(iterations=5, num_messages=1000, message_size=100):
    """Run echo throughput benchmark"""
    print("\n" + "="*70)
    print("ECHO THROUGHPUT BENCHMARK (using CLI server)")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Server:         pocketsocket-cli (compiled binary)")
    print(f"  Iterations:     {iterations}")
    print(f"  Messages/test:  {num_messages}")
    print(f"  Message size:   {message_size} bytes")
    print(f"  Test type:      Round-trip (send + receive)")
    
    server = start_cli_server()
    
    try:
        results = []
        
        print(f"\nRunning {iterations} iterations...")
        for i in range(iterations):
            result = asyncio.run(echo_throughput_test(num_messages, message_size))
            results.append(result)
            print(f"  Run {i+1}/{iterations}: {result['messages_per_second']:,.2f} msg/s, "
                  f"{result['avg_latency_ms']:.3f}ms avg latency")
        
        # Calculate statistics
        throughputs = [r['messages_per_second'] for r in results]
        latencies = [r['avg_latency_ms'] for r in results]
        
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        print(f"\nThroughput (messages per second):")
        print(f"  Minimum:   {min(throughputs):>12,.2f} msg/s")
        print(f"  Maximum:   {max(throughputs):>12,.2f} msg/s")
        print(f"  Average:   {statistics.mean(throughputs):>12,.2f} msg/s")
        print(f"  Median:    {statistics.median(throughputs):>12,.2f} msg/s")
        if len(throughputs) > 1:
            print(f"  Std Dev:   {statistics.stdev(throughputs):>12,.2f}")
        
        print(f"\nRound-trip Latency:")
        print(f"  Minimum:   {min(latencies):>12.3f} ms")
        print(f"  Maximum:   {max(latencies):>12.3f} ms")
        print(f"  Average:   {statistics.mean(latencies):>12.3f} ms")
        print(f"  Median:    {statistics.median(latencies):>12.3f} ms")
        
        print("\n" + "="*70)
        print(f"Summary: {statistics.mean(throughputs):,.0f} messages/second average")
        print("="*70)
        
        return {
            'throughput': statistics.mean(throughputs),
            'latency': statistics.mean(latencies)
        }
        
    finally:
        server.terminate()
        server.wait(timeout=2)


def run_batch_benchmark(iterations=3, num_messages=10000, message_size=100):
    """Run batch send throughput benchmark"""
    print("\n" + "="*70)
    print("BATCH SEND THROUGHPUT BENCHMARK (using CLI server)")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Server:         pocketsocket-cli (compiled binary)")
    print(f"  Iterations:     {iterations}")
    print(f"  Messages/test:  {num_messages}")
    print(f"  Message size:   {message_size} bytes")
    print(f"  Test type:      Batch send then receive all")
    
    server = start_cli_server()
    
    try:
        results = []
        
        print(f"\nRunning {iterations} iterations...")
        for i in range(iterations):
            result = asyncio.run(batch_send_test(num_messages, message_size))
            results.append(result)
            print(f"  Run {i+1}/{iterations}: {result['messages_per_second']:,.2f} msg/s")
        
        # Calculate statistics
        throughputs = [r['messages_per_second'] for r in results]
        
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        print(f"\nThroughput (messages per second):")
        print(f"  Minimum:   {min(throughputs):>12,.2f} msg/s")
        print(f"  Maximum:   {max(throughputs):>12,.2f} msg/s")
        print(f"  Average:   {statistics.mean(throughputs):>12,.2f} msg/s")
        print(f"  Median:    {statistics.median(throughputs):>12,.2f} msg/s")
        
        print("\n" + "="*70)
        print(f"Summary: {statistics.mean(throughputs):,.0f} messages/second (batch mode)")
        print("="*70)
        
        return {
            'throughput': statistics.mean(throughputs)
        }
        
    finally:
        server.terminate()
        server.wait(timeout=2)


def main():
    parser = argparse.ArgumentParser(
        description='Benchmark pocketsocket CLI message throughput'
    )
    parser.add_argument(
        '-n', '--iterations',
        type=int,
        default=5,
        help='Number of iterations per test (default: 5)'
    )
    parser.add_argument(
        '-m', '--messages',
        type=int,
        default=1000,
        help='Number of messages per iteration (default: 1000)'
    )
    parser.add_argument(
        '-s', '--size',
        type=int,
        default=100,
        help='Message size in bytes (default: 100)'
    )
    parser.add_argument(
        '--echo-only',
        action='store_true',
        help='Run only echo benchmark'
    )
    parser.add_argument(
        '--batch-only',
        action='store_true',
        help='Run only batch send benchmark'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("POCKETSOCKET CLI THROUGHPUT BENCHMARK")
    print("="*70)
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = {}
    
    # Run selected benchmarks
    if args.batch_only:
        all_results['batch'] = run_batch_benchmark(args.iterations, args.messages * 10, args.size)
    elif args.echo_only:
        all_results['echo'] = run_echo_benchmark(args.iterations, args.messages, args.size)
    else:
        # Run both
        all_results['echo'] = run_echo_benchmark(args.iterations, args.messages, args.size)
        all_results['batch'] = run_batch_benchmark(args.iterations, args.messages * 10, args.size)
        
        # Print summary
        print("\n\n" + "="*70)
        print("OVERALL SUMMARY")
        print("="*70)
        print(f"\nEcho Mode:      {all_results['echo']['throughput']:>12,.0f} msg/s")
        print(f"                {all_results['echo']['latency']:>12.3f} ms avg latency")
        print(f"\nBatch Mode:     {all_results['batch']['throughput']:>12,.0f} msg/s")
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
