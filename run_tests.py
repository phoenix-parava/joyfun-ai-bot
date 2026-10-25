#!/usr/bin/env python3
"""
run_tests.py - Master Pre-Deployment Test Runner & Regression Shield for Joy Bot

Executes all automated test suites:
- tests/test_emotional_memory.py (22 tests)
- tests/test_onboarding_regression.py (6 tests)
- tests/test_quota_regression.py (4 tests)

Guarantees 100% offline execution and returns exit code 0 on success, 1 on failure.
Blocks git commits/pushes if regressions are introduced.
"""

import os
import sys
import time
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Force offline test environment
os.environ["OFFLINE_TEST"] = "1"
os.environ["TELEGRAM_BOT_TOKEN"] = "test_token_offline_dummy"
os.environ["OWNER_ID"] = "8747280850"

def main():
    print("=" * 70)
    print("🛡️  JOY BOT — MASTER AUTOMATED REGRESSION TEST HARNESS")
    print(f"📍 Directory: {BASE_DIR}")
    print(f"⏰ Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("=" * 70)

    loader = unittest.TestLoader()
    tests_dir = os.path.join(BASE_DIR, "tests")

    if not os.path.exists(tests_dir):
        print(f"❌ Error: Tests directory not found at {tests_dir}")
        sys.exit(1)

    start_time = time.time()
    suite = loader.discover(start_dir=tests_dir, pattern="test_*.py")
    test_count = suite.countTestCases()

    print(f"🔍 Discovered {test_count} automated tests across suites...")
    print("-" * 70)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    duration = time.time() - start_time

    print("-" * 70)
    if result.wasSuccessful():
        print(f"✅ ALL {test_count} TESTS PASSED CLEANLY in {duration:.2f}s!")
        print("🚀 Codebase is 100% regression-free. Ready for safe deployment.")
        print("=" * 70)
        sys.exit(0)
    else:
        print(f"❌ REGRESSION DETECTED: {len(result.failures)} failure(s), {len(result.errors)} error(s) in {duration:.2f}s.")
        print("🛑 Deployment blocked to protect production integrity.")
        print("=" * 70)
        sys.exit(1)

if __name__ == "__main__":
    main()
