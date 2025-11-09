"""
Test the new loadHookModule approach.
"""
import sys
sys.path.insert(0, '/workspaces/pocketsocket-2/python')

import pocketsocket

print("Loading handler module...")
pocketsocket.loadHookModule("test_handler")
print("✓ Handler loaded, starting server...")

pocketsocket.run_blocking_server('127.0.0.1', 8091)
