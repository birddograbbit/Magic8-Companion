#!/usr/bin/env python3
"""
Test script for running ML scheduler timezone test
Run this from the project root directory:
    python tests/run_scheduler_test.py
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now run the actual test
if __name__ == "__main__":
    import subprocess
    result = subprocess.run([
        sys.executable, 
        "-m", "pytest", 
        "tests/test_scheduler_start_timezone.py", 
        "-v"
    ])
    sys.exit(result.returncode)
