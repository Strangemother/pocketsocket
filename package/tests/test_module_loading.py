"""
Test the new loadHookModule approach.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'package'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pocketsocket

print("Loading handler module...")
pocketsocket.loadHookModule("test_handler")
print("✓ Handler loaded, starting server...")

pocketsocket.run_blocking_server('127.0.0.1', 8091)
