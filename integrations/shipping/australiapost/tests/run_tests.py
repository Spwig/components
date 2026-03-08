"""
Test Runner for Australia Post Provider v2.0.0

Runs all unit tests and provides summary report.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py -v           # Verbose output
    python run_tests.py <module>     # Run specific module tests

Author: Spwig
Version: 2.0.0
"""
import sys
import unittest
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_all_tests(verbosity=2):
    """Run all unit tests."""
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(start_dir, pattern='test_*.py')

    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    return result.wasSuccessful()


def run_specific_test(module_name, verbosity=2):
    """Run tests for a specific module."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(f'test_{module_name}')

    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] != '-v':
        # Run specific test module
        module = sys.argv[1]
        success = run_specific_test(module, verbosity=2)
    else:
        # Run all tests
        verbosity = 2 if '-v' in sys.argv else 1
        success = run_all_tests(verbosity=verbosity)

    sys.exit(0 if success else 1)
