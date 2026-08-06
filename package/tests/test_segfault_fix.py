#!/usr/bin/env python3
"""
Test script to verify the segfault fix works.

This will fail with SIGSEGV before the fix, and work after.
"""

import sys
import time
import asyncio
import subprocess
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[2] / 'package'
sys.path.insert(0, str(PACKAGE_DIR))

def test_module_import():
    """Test that module imports"""
    print("1. Testing module import...")
    try:
        import pocketsocket
        print("   ✓ Module imported successfully")
        return True
    except Exception as e:
        print(f"   ✗ Import failed: {e}")
        return False


def test_server_start():
    """Test that server starts without immediate crash"""
    print("\n2. Testing server startup...")
    
    server_code = """
import sys
sys.path.insert(0, __PACKAGE_DIR__)
import pocketsocket

def test_handler(uuid, etype, event):
    print(f'Handler called: etype={etype}', flush=True)
    if etype == 0:
        print('   Connection event received', flush=True)
        return
    # This line would cause segfault before the fix
    print(f'   Message: kind={event["kind"]}, data={event["data"]}', flush=True)
    pocketsocket.send(uuid, event['kind'], event['data'])

pocketsocket.hook(test_handler)
print('Server starting...', flush=True)
pocketsocket.run_blocking_server('127.0.0.1', 8091)
""".replace('__PACKAGE_DIR__', repr(str(PACKAGE_DIR)))
    
    proc = subprocess.Popen(
        [sys.executable, '-c', server_code],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Wait for startup
    time.sleep(2)
    
    if proc.poll() is not None:
        output = proc.stdout.read()
        print(f"   ✗ Server crashed immediately")
        print(f"   Output: {output}")
        return False
    
    print("   ✓ Server started without crash")
    proc.terminate()
    proc.wait(timeout=2)
    return True


def test_message_sending():
    """Test sending actual WebSocket messages"""
    print("\n3. Testing WebSocket message sending...")
    
    server_code = """
import sys
sys.path.insert(0, __PACKAGE_DIR__)
import pocketsocket

def echo_handler(uuid, etype, event):
    if etype == 0:
        return
    # Echo back - this would segfault before fix
    pocketsocket.send(uuid, event['kind'], event['data'])

pocketsocket.hook(echo_handler)
pocketsocket.run_blocking_server('127.0.0.1', 8091)
""".replace('__PACKAGE_DIR__', repr(str(PACKAGE_DIR)))
    
    proc = subprocess.Popen(
        [sys.executable, '-c', server_code],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    time.sleep(2)
    
    # Try to send a message
    client_code = """
import asyncio
import websockets

async def test():
    async with websockets.connect('ws://127.0.0.1:8091/ws/') as ws:
        await ws.recv()  # The server sends request headers after upgrading.
        await ws.send('Hello World')
        response = await ws.recv()
        print(f'Received: {response}')
        return response == 'Hello World'

result = asyncio.run(test())
exit(0 if result else 1)
"""
    
    try:
        result = subprocess.run(
            [sys.executable, '-c', client_code],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("   ✓ Message echo successful!")
            print(f"   {result.stdout.strip()}")
            success = True
        else:
            print("   ✗ Message echo failed")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
            success = False
            
    except subprocess.TimeoutExpired:
        print("   ✗ Test timed out (server likely crashed)")
        success = False
    except Exception as e:
        print(f"   ✗ Test failed: {e}")
        success = False
    finally:
        proc.terminate()
        proc.wait(timeout=2)
    
    return success


def main():
    print("="*70)
    print("POCKETSOCKET SEGFAULT FIX VERIFICATION")
    print("="*70)
    print("\nThis test verifies that the Message marshalling bug is fixed.")
    print("Before the fix: SIGSEGV when receiving WebSocket messages")
    print("After the fix:  Messages echo correctly\n")
    
    results = []
    
    # Test 1: Import
    results.append(("Import", test_module_import()))
    
    if not results[0][1]:
        print("\n❌ Cannot proceed - module not available")
        print("\nPlease build the module first:")
        print("  (cd server && nimble buildPyd)")
        return False
    
    # Test 2: Server start
    results.append(("Server Start", test_server_start()))
    
    # Test 3: Message sending
    results.append(("Message Echo", test_message_sending()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:20s} {status}")
        if not passed:
            all_passed = False
    
    print("="*70)
    
    if all_passed:
        print("\n🎉 All tests passed! The segfault bug is fixed.")
    else:
        print("\n❌ Some tests failed. The bug may still exist.")
        print("\nIf 'Message Echo' fails with SIGSEGV, the bug is not fixed.")
        print("Make sure you rebuilt after applying the hook.nim changes:")
        print("  (cd server && nimble buildPyd)")
    
    return all_passed


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
