#!/usr/bin/env python3
"""
Quick test to verify pocketsocket throughput benchmark works

This script tests basic functionality before running full benchmarks.
"""

import subprocess
import sys
import time

def check_module():
    """Check if pocketsocket is available"""
    try:
        result = subprocess.run(
            [sys.executable, '-c', 'import pocketsocket; print("OK")'],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.returncode == 0
    except:
        return False

def check_websockets():
    """Check if websockets is available"""
    try:
        import websockets
        return True
    except ImportError:
        return False

def main():
    print("="*70)
    print("POCKETSOCKET THROUGHPUT BENCHMARK - DEPENDENCY CHECK")
    print("="*70)
    
    # Check pocketsocket
    print("\nChecking pocketsocket module... ", end='')
    if check_module():
        print("✓ OK")
    else:
        print("✗ NOT FOUND")
        print("\nTo build pocketsocket:")
        print("  1. Install Nim: https://nim-lang.org/install.html")
        print("  2. Build module: nimble buildPyd")
        print("  3. Install: pip install -e .")
        return False
    
    # Check websockets
    print("Checking websockets library... ", end='')
    if check_websockets():
        print("✓ OK")
    else:
        print("✗ NOT FOUND")
        print("\nTo install websockets:")
        print("  pip install websockets")
        return False
    
    print("\n" + "="*70)
    print("✓ All dependencies available!")
    print("="*70)
    print("\nYou can now run the throughput benchmark:")
    print("  python3 benchmarks/benchmark_throughput.py -n 5 -m 500")
    print("\nOr run a quick test:")
    print("  python3 benchmarks/benchmark_throughput.py --echo-only -n 3 -m 100")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
