"""Test runner for SAI CLI tool tests."""

import sys
import subprocess
from pathlib import Path
import pytest


def run_unit_tests():
    """Run unit tests."""
    print("Running unit tests...")
    
    unit_test_args = [
        "-v",
        "--tb=short",
        "--cov=sai",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "tests/",
        "--ignore=tests/integration/",
        "-m", "not integration and not slow"
    ]
    
    return pytest.main(unit_test_args)


def run_integration_tests():
    """Run integration tests."""
    print("Running integration tests...")
    
    integration_test_args = [
        "-v",
        "--tb=short",
        "tests/integration/",
        "-m", "integration"
    ]
    
    return pytest.main(integration_test_args)


def run_all_tests():
    """Run all tests."""
    print("Running all tests...")
    
    all_test_args = [
        "-v",
        "--tb=short",
        "--cov=sai",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "tests/"
    ]
    
    return pytest.main(all_test_args)


def run_specific_test(test_path):
    """Run a specific test file or test function."""
    print(f"Running specific test: {test_path}")
    
    specific_test_args = [
        "-v",
        "--tb=short",
        test_path
    ]
    
    return pytest.main(specific_test_args)


def run_tests_with_coverage():
    """Run tests with detailed coverage reporting."""
    print("Running tests with coverage...")
    
    coverage_args = [
        "-v",
        "--tb=short",
        "--cov=sai",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
        "--cov-branch",
        "tests/",
        "--ignore=tests/integration/"
    ]
    
    return pytest.main(coverage_args)


def run_fast_tests():
    """Run only fast tests (exclude slow and integration tests)."""
    print("Running fast tests...")
    
    fast_test_args = [
        "-v",
        "--tb=short",
        "tests/",
        "--ignore=tests/integration/",
        "-m", "not slow and not integration"
    ]
    
    return pytest.main(fast_test_args)


def main():
    """Main test runner function."""
    if len(sys.argv) < 2:
        print("Usage: python test_runner.py <command> [args]")
        print("Commands:")
        print("  unit        - Run unit tests only")
        print("  integration - Run integration tests only")
        print("  all         - Run all tests")
        print("  fast        - Run fast tests only")
        print("  coverage    - Run tests with detailed coverage")
        print("  specific    - Run specific test (requires test path)")
        return 1
    
    command = sys.argv[1]
    
    if command == "unit":
        return run_unit_tests()
    elif command == "integration":
        return run_integration_tests()
    elif command == "all":
        return run_all_tests()
    elif command == "fast":
        return run_fast_tests()
    elif command == "coverage":
        return run_tests_with_coverage()
    elif command == "specific":
        if len(sys.argv) < 3:
            print("Error: specific command requires test path")
            return 1
        return run_specific_test(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())