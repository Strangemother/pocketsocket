"""Tests for loading a Python handler module."""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'package'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

@unittest.skip("Handler module API test is being rewritten")
class TestModuleLoading(unittest.TestCase):
	def test_load_handler_module(self):
		import pocketsocket

		pocketsocket.loadHookModule("test_handler")
		pocketsocket.run_blocking_server("127.0.0.1", 8091)
