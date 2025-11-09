#!/bin/bash
# Quick test runner for PocketSocket
# Usage: ./quick_tests.sh

export PATH=/home/codespace/.nimble/bin:$PATH
cd "$(dirname "$0")"
nimble test
