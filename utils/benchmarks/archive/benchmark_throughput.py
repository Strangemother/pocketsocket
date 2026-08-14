#!/usr/bin/env python3
"""
Pocketsocket Client-to-Client Throughput Benchmark

Measures message throughput between WebSocket clients:
- Messages per second
- Round-trip latency
- Broadcast performance
- Echo performance

Requirements:
- pocketsocket module must be built and installed:
  $ nimble buildPyd
  $ pip install -e .
- websockets library for client connections:
  $ pip install websockets
"""

import argparse
import asyncio
import json
import socket
import statistics
import subprocess
import sys
import time
from datetime import datetime
import websockets


def wait_for_server(host='127.0.0.1', port=8090, timeout=5):
    """Wait for server to be ready by checking if port is accepting connections"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                # Port is open, give it a moment more
                time.sleep(0.1)
                return True
        except:
            pass
        time.sleep(0.1)
    return False


def start_server(mode='echo'):
    """Start pocketsocket server in a subprocess"""
    if mode == 'echo':
        server_code = """
import sys
sys.path.insert(0, '/workspaces/pocketsocket-2/package')
import pocketsocket

def echo_handler(uuid, etype, event):
    try:
        if etype == 0:  # Connection
            return
        # Echo message back to sender
        pocketsocket.send(uuid, event['kind'], event['data'])
    except Exception as e:
        print(f"Error in handler: {e}", flush=True)
        import traceback
        traceback.print_exc()

pocketsocket.hook(echo_handler)
pocketsocket.run_blocking_server('127.0.0.1', 8090)
"""
    else:  # broadcast
        server_code = """
import sys
sys.path.insert(0, '/workspaces/pocketsocket-2/package')
import pocketsocket

def broadcast_handler(uuid, etype, event):
    if etype == 0:  # Connection
        return
    # Broadcast to all clients except sender
    pocketsocket.send_all(event['kind'], event['data'], uuid)

pocketsocket.hook(broadcast_handler)
pocketsocket.run_blocking_server('127.0.0.1', 8090)
"""
    
    process = subprocess.Popen(
        [sys.executable, '-c', server_code],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Combine stderr with stdout
        text=True
    )
    
    # Wait for server to be ready
    if not wait_for_server():
        process.terminate()
        raise RuntimeError("Server failed to start within timeout")
    
    return process


async def echo_throughput_test(num_messages=1000, message_size=100):
    """Test echo throughput: client -> server -> same client"""
    uri = "ws://127.0.0.1:8090/ws/"
    
    async with websockets.connect(uri) as websocket:
        # Prepare message
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


async def broadcast_throughput_test(num_clients=5, num_messages=100, message_size=100):
    """Test broadcast throughput: one sender -> multiple receivers"""
    uri = "ws://127.0.0.1:8090/ws/"
    
    # Connect all clients
    clients = []
    for _ in range(num_clients):
        client = await websockets.connect(uri)
        clients.append(client)
    
    sender = clients[0]
    receivers = clients[1:]
    
    payload = "x" * message_size
    
    # Warm up
    await sender.send("warmup")
    for receiver in receivers:
        await receiver.recv()
    
    start_time = time.perf_counter()
    
    # Send messages from sender
    for i in range(num_messages):
        await sender.send(payload)
        
        # Each receiver should get the message
        for receiver in receivers:
            await receiver.recv()
    
    end_time = time.perf_counter()
    
    # Close all connections
    for client in clients:
        await client.close()
    
    duration = end_time - start_time
    total_messages = num_messages * len(receivers)  # Total messages received
    messages_per_second = total_messages / duration
    avg_latency_ms = (duration / num_messages) * 1000
    
    return {
        'num_clients': num_clients,
        'messages_sent': num_messages,
        'total_messages_received': total_messages,
        'duration': duration,
        'messages_per_second': messages_per_second,
        'avg_latency_ms': avg_latency_ms,
        'message_size': message_size
    }


async def batch_send_test(num_messages=10000, message_size=100):
    """Test rapid fire sending without waiting for responses"""
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
    print("ECHO THROUGHPUT BENCHMARK")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Iterations:     {iterations}")
    print(f"  Messages/test:  {num_messages}")
    print(f"  Message size:   {message_size} bytes")
    print(f"  Test type:      Round-trip (send + receive)")
    
    server = start_server(mode='echo')
    
    try:
        results = []
        
        print(f"\nRunning {iterations} iterations...")
        for i in range(iterations):
            result = asyncio.run(echo_throughput_test(num_messages, message_size))
            results.append(result)
            print(f"  Run {i+1}/{iterations}: {result['messages_per_second']:.2f} msg/s, "
                  f"{result['avg_latency_ms']:.3f}ms avg latency")
        
        # Calculate statistics
        throughputs = [r['messages_per_second'] for r in results]
        latencies = [r['avg_latency_ms'] for r in results]
        
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        print(f"\nThroughput (messages per second):")
        print(f"  Minimum:   {min(throughputs):,.2f} msg/s")
        print(f"  Maximum:   {max(throughputs):,.2f} msg/s")
        print(f"  Average:   {statistics.mean(throughputs):,.2f} msg/s")
        print(f"  Median:    {statistics.median(throughputs):,.2f} msg/s")
        print(f"  Std Dev:   {statistics.stdev(throughputs) if len(throughputs) > 1 else 0:.2f}")
        
        print(f"\nRound-trip Latency:")
        print(f"  Minimum:   {min(latencies):.3f} ms")
        print(f"  Maximum:   {max(latencies):.3f} ms")
        print(f"  Average:   {statistics.mean(latencies):.3f} ms")
        print(f"  Median:    {statistics.median(latencies):.3f} ms")
        
        print("\n" + "="*70)
        print(f"Summary: {statistics.mean(throughputs):,.0f} messages/second average")
        print("="*70)
        
        return {
            'type': 'echo',
            'throughput': statistics.mean(throughputs),
            'latency': statistics.mean(latencies),
            'results': results
        }
        
    finally:
        server.terminate()
        server.wait(timeout=2)


def run_broadcast_benchmark(iterations=3, num_clients=5, num_messages=100, message_size=100):
    """Run broadcast throughput benchmark"""
    print("\n" + "="*70)
    print("BROADCAST THROUGHPUT BENCHMARK")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Iterations:     {iterations}")
    print(f"  Clients:        {num_clients} (1 sender, {num_clients-1} receivers)")
    print(f"  Messages/test:  {num_messages}")
    print(f"  Message size:   {message_size} bytes")
    
    server = start_server(mode='broadcast')
    
    try:
        results = []
        
        print(f"\nRunning {iterations} iterations...")
        for i in range(iterations):
            result = asyncio.run(broadcast_throughput_test(num_clients, num_messages, message_size))
            results.append(result)
            print(f"  Run {i+1}/{iterations}: {result['messages_per_second']:.2f} msg/s total, "
                  f"{result['avg_latency_ms']:.3f}ms avg latency")
        
        # Calculate statistics
        throughputs = [r['messages_per_second'] for r in results]
        latencies = [r['avg_latency_ms'] for r in results]
        
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        print(f"\nThroughput (total messages per second):")
        print(f"  Minimum:   {min(throughputs):,.2f} msg/s")
        print(f"  Maximum:   {max(throughputs):,.2f} msg/s")
        print(f"  Average:   {statistics.mean(throughputs):,.2f} msg/s")
        print(f"  Median:    {statistics.median(throughputs):,.2f} msg/s")
        
        print(f"\nBroadcast Latency:")
        print(f"  Average:   {statistics.mean(latencies):.3f} ms per message to all receivers")
        
        print("\n" + "="*70)
        print(f"Summary: {statistics.mean(throughputs):,.0f} total messages/second")
        print(f"         ({statistics.mean(throughputs)/(num_clients-1):,.0f} msg/s per receiver)")
        print("="*70)
        
        return {
            'type': 'broadcast',
            'throughput': statistics.mean(throughputs),
            'latency': statistics.mean(latencies),
            'results': results
        }
        
    finally:
        server.terminate()
        server.wait(timeout=2)


def run_batch_benchmark(iterations=3, num_messages=10000, message_size=100):
    """Run batch send throughput benchmark"""
    print("\n" + "="*70)
    print("BATCH SEND THROUGHPUT BENCHMARK")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Iterations:     {iterations}")
    print(f"  Messages/test:  {num_messages}")
    print(f"  Message size:   {message_size} bytes")
    print(f"  Test type:      Batch send then receive all")
    
    server = start_server(mode='echo')
    
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
        print(f"  Minimum:   {min(throughputs):,.2f} msg/s")
        print(f"  Maximum:   {max(throughputs):,.2f} msg/s")
        print(f"  Average:   {statistics.mean(throughputs):,.2f} msg/s")
        print(f"  Median:    {statistics.median(throughputs):,.2f} msg/s")
        
        print("\n" + "="*70)
        print(f"Summary: {statistics.mean(throughputs):,.0f} messages/second (batch mode)")
        print("="*70)
        
        return {
            'type': 'batch',
            'throughput': statistics.mean(throughputs),
            'results': results
        }
        
    finally:
        server.terminate()
        server.wait(timeout=2)


def check_pocketsocket():
    """Check if pocketsocket module is available"""
    try:
        import sys
        sys.path.insert(0, '/workspaces/pocketsocket-2/package')
        import pocketsocket
        return True
    except ImportError:
        return False


def main():
    # Check dependencies
    if not check_pocketsocket():
        print("\n❌ Error: pocketsocket module not found", file=sys.stderr)
        print("\nPlease build and install pocketsocket first:", file=sys.stderr)
        print("  nimble buildPyd", file=sys.stderr)
        print("  pip install -e .", file=sys.stderr)
        sys.exit(1)
    
    parser = argparse.ArgumentParser(
        description='Benchmark pocketsocket client-to-client message throughput'
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
        '--broadcast-only',
        action='store_true',
        help='Run only broadcast benchmark'
    )
    parser.add_argument(
        '--batch-only',
        action='store_true',
        help='Run only batch send benchmark'
    )
    parser.add_argument(
        '--clients',
        type=int,
        default=5,
        help='Number of clients for broadcast test (default: 5)'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("POCKETSOCKET THROUGHPUT BENCHMARK SUITE")
    print("="*70)
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = {}
    
    # Run selected benchmarks
    if args.echo_only:
        all_results['echo'] = run_echo_benchmark(args.iterations, args.messages, args.size)
    elif args.broadcast_only:
        all_results['broadcast'] = run_broadcast_benchmark(
            args.iterations, args.clients, args.messages, args.size
        )
    elif args.batch_only:
        all_results['batch'] = run_batch_benchmark(args.iterations, args.messages * 10, args.size)
    else:
        # Run all benchmarks
        all_results['echo'] = run_echo_benchmark(args.iterations, args.messages, args.size)
        all_results['broadcast'] = run_broadcast_benchmark(
            args.iterations, args.clients, args.messages, args.size
        )
        all_results['batch'] = run_batch_benchmark(args.iterations, args.messages * 10, args.size)
        
        # Print summary
        print("\n\n" + "="*70)
        print("OVERALL SUMMARY")
        print("="*70)
        print(f"\nEcho Mode:      {all_results['echo']['throughput']:>12,.0f} msg/s")
        print(f"                {all_results['echo']['latency']:>12.3f} ms avg latency")
        print(f"\nBroadcast Mode: {all_results['broadcast']['throughput']:>12,.0f} msg/s total")
        print(f"                {all_results['broadcast']['latency']:>12.3f} ms avg latency")
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
