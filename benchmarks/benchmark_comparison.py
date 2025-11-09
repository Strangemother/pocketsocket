#!/usr/bin/env python3
"""
WebSocket Server Startup Comparison Benchmark

Compares startup times of various Python WebSocket servers:
- Pocketsocket (CLI and Python module)
- websockets library
- Tornado
- aiohttp
- FastAPI with uvicorn (if available)

All servers are tested using the same methodology: time from process start
to accepting the first connection.
"""

import sys
import time
import socket
import subprocess
import tempfile
import os
from statistics import mean, median, stdev
from pathlib import Path


def test_connection(host, port, timeout=5.0):
    """Test when server accepts connections."""
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


def run_server_test(script_content, port, timeout=10.0):
    """Run a server script and measure time to first connection."""
    
    proc = subprocess.Popen(
        ['python3', '-c', script_content],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    start = time.perf_counter()
    
    try:
        # Test connection
        conn_time = test_connection('127.0.0.1', port, timeout=timeout)
        
        if conn_time is not None:
            return conn_time * 1000  # Convert to ms
        
        return None
        
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def benchmark_pocketsocket_python(port=10001, iterations=5):
    """Benchmark pocketsocket Python module."""
    
    script = f'''
import sys
sys.path.insert(0, 'python')
import pocketsocket

def hook(uuid, etype, event):
    pass

pocketsocket.hook(hook)
pocketsocket.run_blocking_server('127.0.0.1', {port})
'''
    
    times = []
    for i in range(iterations):
        result = run_server_test(script, port)
        if result:
            times.append(result)
        time.sleep(0.1)
    
    return times


def benchmark_websockets(port=10002, iterations=5):
    """Benchmark websockets library."""
    
    script = f'''
import asyncio
import websockets

async def handler(websocket, path):
    pass

async def main():
    async with websockets.serve(handler, "127.0.0.1", {port}):
        await asyncio.Future()

asyncio.run(main())
'''
    
    times = []
    for i in range(iterations):
        result = run_server_test(script, port, timeout=15.0)
        if result:
            times.append(result)
        time.sleep(0.1)
    
    return times


def benchmark_tornado(port=10003, iterations=5):
    """Benchmark Tornado WebSocket server."""
    
    script = f'''
import tornado.ioloop
import tornado.web
import tornado.websocket

class WSHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        pass
    def on_message(self, message):
        pass

app = tornado.web.Application([
    (r"/", WSHandler),
])

app.listen({port}, address="127.0.0.1")
tornado.ioloop.IOLoop.current().start()
'''
    
    times = []
    for i in range(iterations):
        result = run_server_test(script, port, timeout=15.0)
        if result:
            times.append(result)
        time.sleep(0.1)
    
    return times


def benchmark_aiohttp(port=10004, iterations=5):
    """Benchmark aiohttp WebSocket server."""
    
    script = f'''
from aiohttp import web

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    async for msg in ws:
        pass
    return ws

app = web.Application()
app.router.add_get('/', websocket_handler)
web.run_app(app, host='127.0.0.1', port={port}, print=None)
'''
    
    times = []
    for i in range(iterations):
        result = run_server_test(script, port, timeout=15.0)
        if result:
            times.append(result)
        time.sleep(0.1)
    
    return times


def benchmark_fastapi(port=10005, iterations=5):
    """Benchmark FastAPI with WebSocket."""
    
    script = f'''
from fastapi import FastAPI, WebSocket
import uvicorn

app = FastAPI()

@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.receive_text()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port={port}, log_level="critical")
'''
    
    times = []
    for i in range(iterations):
        result = run_server_test(script, port, timeout=15.0)
        if result:
            times.append(result)
        time.sleep(0.1)
    
    return times


def check_library_available(import_statement):
    """Check if a library is available."""
    try:
        subprocess.run(
            ['python3', '-c', import_statement],
            capture_output=True,
            timeout=2,
            check=True
        )
        return True
    except:
        return False


def print_results(name, times):
    """Print benchmark results for a server."""
    if not times:
        print(f"\n{name}:")
        print("  ✗ No successful measurements (may not be installed)")
        return None
    
    print(f"\n{name}:")
    print(f"  Successful runs: {len(times)}")
    print(f"  Average: {mean(times):7.2f} ms")
    print(f"  Median:  {median(times):7.2f} ms")
    print(f"  Min:     {min(times):7.2f} ms")
    print(f"  Max:     {max(times):7.2f} ms")
    if len(times) > 1:
        print(f"  Std Dev: {stdev(times):7.2f} ms")
    
    return mean(times)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Compare WebSocket server startup times'
    )
    parser.add_argument(
        '-n', '--iterations',
        type=int,
        default=5,
        help='Number of iterations per server (default: 5)'
    )
    parser.add_argument(
        '--skip',
        nargs='+',
        choices=['pocketsocket', 'websockets', 'tornado', 'aiohttp', 'fastapi'],
        help='Skip specific servers'
    )
    
    args = parser.parse_args()
    skip = set(args.skip or [])
    
    print("=" * 70)
    print("WebSocket Server Startup Time Comparison")
    print("=" * 70)
    print()
    print(f"Iterations per server: {args.iterations}")
    print(f"Method: Time from process start to accepting first connection")
    print()
    
    # Check which libraries are available
    print("Checking available libraries...")
    available = {}
    
    if 'pocketsocket' not in skip:
        available['pocketsocket'] = os.path.exists('python/pocketsocket/pocketsocket_server.cpython-312-x86_64-linux-gnu.so')
    
    if 'websockets' not in skip:
        available['websockets'] = check_library_available('import websockets')
    
    if 'tornado' not in skip:
        available['tornado'] = check_library_available('import tornado')
    
    if 'aiohttp' not in skip:
        available['aiohttp'] = check_library_available('import aiohttp')
    
    if 'fastapi' not in skip:
        available['fastapi'] = check_library_available('import fastapi; import uvicorn')
    
    for lib, avail in available.items():
        status = "✓" if avail else "✗"
        print(f"  {status} {lib}")
    
    print()
    print("Running benchmarks...")
    print("=" * 70)
    
    results = {}
    
    # Benchmark Pocketsocket
    if available.get('pocketsocket'):
        print("\n[1/5] Benchmarking Pocketsocket...")
        times = benchmark_pocketsocket_python(iterations=args.iterations)
        results['Pocketsocket'] = times
    
    # Benchmark websockets
    if available.get('websockets'):
        print("\n[2/5] Benchmarking websockets library...")
        times = benchmark_websockets(iterations=args.iterations)
        results['websockets'] = times
    
    # Benchmark Tornado
    if available.get('tornado'):
        print("\n[3/5] Benchmarking Tornado...")
        times = benchmark_tornado(iterations=args.iterations)
        results['Tornado'] = times
    
    # Benchmark aiohttp
    if available.get('aiohttp'):
        print("\n[4/5] Benchmarking aiohttp...")
        times = benchmark_aiohttp(iterations=args.iterations)
        results['aiohttp'] = times
    
    # Benchmark FastAPI
    if available.get('fastapi'):
        print("\n[5/5] Benchmarking FastAPI + uvicorn...")
        times = benchmark_fastapi(iterations=args.iterations)
        results['FastAPI'] = times
    
    # Print summary
    print()
    print("=" * 70)
    print("Results Summary")
    print("=" * 70)
    
    averages = {}
    for name, times in results.items():
        avg = print_results(name, times)
        if avg:
            averages[name] = avg
    
    # Comparison table
    if averages and 'Pocketsocket' in averages:
        print()
        print("=" * 70)
        print("Speed Comparison (relative to Pocketsocket)")
        print("=" * 70)
        print()
        
        pocketsocket_time = averages['Pocketsocket']
        
        # Sort by speed (fastest first)
        sorted_results = sorted(averages.items(), key=lambda x: x[1])
        
        print(f"{'Server':<20} {'Avg Time':>12} {'vs Pocketsocket':>15} {'Factor':>10}")
        print("-" * 70)
        
        for name, avg_time in sorted_results:
            if name == 'Pocketsocket':
                print(f"{name:<20} {avg_time:>10.2f}ms {'(baseline)':>15} {'1.0x':>10}")
            else:
                factor = avg_time / pocketsocket_time
                diff = avg_time - pocketsocket_time
                print(f"{name:<20} {avg_time:>10.2f}ms {f'+{diff:.2f}ms':>15} {f'{factor:.1f}x':>10}")
        
        print()
        print("=" * 70)
    
    # Visual comparison
    if len(averages) > 1:
        print()
        print("Visual Comparison:")
        print()
        
        max_time = max(averages.values())
        scale = 60 / max_time  # Scale to 60 characters max
        
        for name, avg_time in sorted(averages.items(), key=lambda x: x[1]):
            bar_length = int(avg_time * scale)
            bar = '▓' * bar_length
            print(f"{name:<20} {bar} {avg_time:.2f}ms")
        
        print()
        print("=" * 70)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
