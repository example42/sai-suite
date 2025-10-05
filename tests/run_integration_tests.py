#!/usr/bin/env python3
"""Integration test runner for repository operations.

This script runs comprehensive integration tests for the repository system,
including setup of test repositories and cleanup.
"""

from tests.fixtures.test_repositories import TestRepositoryManager, cleanup_test_repositories
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class IntegrationTestRunner:
    """Runner for integration tests with proper setup and cleanup."""

    def __init__(self, verbose: bool = True, network: bool = True):
        """Initialize the test runner."""
        self.verbose = verbose
        self.network = network
        self.test_repo_manager: Optional[TestRepositoryManager] = None
        self.temp_dir: Optional[Path] = None

    def setup_test_environment(self):
        """Set up the test environment."""
        print("🔧 Setting up integration test environment...")

        # Create temporary directory for test repositories
        self.temp_dir = Path(tempfile.mkdtemp(prefix="sai_integration_tests_"))
        print(f"   Test directory: {self.temp_dir}")

        # Initialize test repository manager
        self.test_repo_manager = TestRepositoryManager(self.temp_dir / "repositories")

        # Create test repositories
        print("   Creating test repositories...")
        self.test_repo_manager.create_local_test_repository("basic", saidata_count=10)
        self.test_repo_manager.create_local_test_repository("medium", saidata_count=50)

        # Create malformed repository for error testing
        self.test_repo_manager.create_malformed_repository("malformed")

        print("✅ Test environment setup complete")

    def cleanup_test_environment(self):
        """Clean up the test environment."""
        print("🧹 Cleaning up integration test environment...")

        if self.test_repo_manager:
            self.test_repo_manager.cleanup()

        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

        cleanup_test_repositories()
        print("✅ Test environment cleanup complete")

    def run_basic_integration_tests(self) -> int:
        """Run basic integration tests."""
        print("🧪 Running basic integration tests...")

        test_args = [
            sys.executable,
            "-m",
            "pytest",
            str(
                project_root
                / "tests"
                / "test_repository_integration_e2e.py::TestRepositoryIntegrationE2E"
            ),
            "-v" if self.verbose else "-q",
            "--tb=short",
            "-m",
            "integration and not slow and not performance",
        ]

        if not self.network:
            test_args.extend(["-m", "not network"])

        return subprocess.call(test_args)

    def run_offline_mode_tests(self) -> int:
        """Run offline mode and network failure tests."""
        print("📡 Running offline mode integration tests...")

        test_args = [
            sys.executable,
            "-m",
            "pytest",
            str(
                project_root
                / "tests"
                / "test_repository_integration_e2e.py::TestRepositoryOfflineModeIntegration"
            ),
            "-v" if self.verbose else "-q",
            "--tb=short",
            "-m",
            "integration",
        ]

        return subprocess.call(test_args)

    def run_authentication_tests(self) -> int:
        """Run authentication integration tests."""
        print("🔐 Running authentication integration tests...")

        test_args = [
            sys.executable,
            "-m",
            "pytest",
            str(
                project_root
                / "tests"
                / "test_repository_integration_e2e.py::TestRepositoryAuthenticationIntegration"
            ),
            "-v" if self.verbose else "-q",
            "--tb=short",
            "-m",
            "integration",
        ]

        return subprocess.call(test_args)

    def run_performance_tests(self) -> int:
        """Run performance integration tests."""
        print("⚡ Running performance integration tests...")

        # Create large repository for performance testing
        if self.test_repo_manager:
            print("   Creating large test repository (this may take a while)...")
            self.test_repo_manager.create_large_test_repository("performance", software_count=500)

        test_args = [
            sys.executable,
            "-m",
            "pytest",
            str(
                project_root
                / "tests"
                / "test_repository_integration_e2e.py::TestRepositoryPerformanceIntegration"
            ),
            "-v" if self.verbose else "-q",
            "--tb=short",
            "-m",
            "integration and performance",
            "--timeout=600",  # 10 minute timeout for performance tests
        ]

        return subprocess.call(test_args)

    def run_security_tests(self) -> int:
        """Run security integration tests."""
        print("🔒 Running security integration tests...")

        test_args = [
            sys.executable,
            "-m",
            "pytest",
            str(
                project_root
                / "tests"
                / "test_repository_integration_e2e.py::TestRepositorySecurityIntegration"
            ),
            "-v" if self.verbose else "-q",
            "--tb=short",
            "-m",
            "integration",
        ]

        return subprocess.call(test_args)

    def run_all_integration_tests(self) -> int:
        """Run all integration tests."""
        print("🚀 Running all integration tests...")

        test_args = [
            sys.executable,
            "-m",
            "pytest",
            str(project_root / "tests" / "test_repository_integration_e2e.py"),
            "-v" if self.verbose else "-q",
            "--tb=short",
            "-m",
            "integration",
        ]

        if not self.network:
            test_args.extend(["-m", "integration and not network"])

        return subprocess.call(test_args)

    def check_prerequisites(self) -> bool:
        """Check if prerequisites for integration tests are met."""
        print("🔍 Checking prerequisites...")

        # Check if git is available
        try:
            result = subprocess.run(["git", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ Git: {result.stdout.strip()}")
            else:
                print("   ❌ Git not available")
                return False
        except FileNotFoundError:
            print("   ❌ Git not found")
            return False

        # Check if pytest is available
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"   ✅ Pytest: {result.stdout.strip()}")
            else:
                print("   ❌ Pytest not available")
                return False
        except FileNotFoundError:
            print("   ❌ Pytest not found")
            return False

        # Check network connectivity (if network tests are enabled)
        if self.network:
            try:
                import socket

                socket.create_connection(("8.8.8.8", 53), timeout=3)
                print("   ✅ Network connectivity")
            except OSError:
                print("   ⚠️  Network not available (network tests will be skipped)")
                self.network = False

        print("✅ Prerequisites check complete")
        return True


def main():
    """Main entry point for integration test runner."""
    parser = argparse.ArgumentParser(description="Run SAI repository integration tests")

    parser.add_argument(
        "test_type",
        nargs="?",
        default="all",
        choices=["all", "basic", "offline", "auth", "performance", "security"],
        help="Type of integration tests to run",
    )

    parser.add_argument(
        "--no-network", action="store_true", help="Skip tests that require network access"
    )

    parser.add_argument("--quiet", "-q", action="store_true", help="Run tests in quiet mode")

    parser.add_argument(
        "--no-cleanup", action="store_true", help="Don't clean up test environment (for debugging)"
    )

    args = parser.parse_args()

    # Initialize test runner
    runner = IntegrationTestRunner(verbose=not args.quiet, network=not args.no_network)

    exit_code = 0

    try:
        # Check prerequisites
        if not runner.check_prerequisites():
            print("❌ Prerequisites not met")
            return 1

        # Set up test environment
        runner.setup_test_environment()

        # Run selected tests
        if args.test_type == "all":
            exit_code = runner.run_all_integration_tests()
        elif args.test_type == "basic":
            exit_code = runner.run_basic_integration_tests()
        elif args.test_type == "offline":
            exit_code = runner.run_offline_mode_tests()
        elif args.test_type == "auth":
            exit_code = runner.run_authentication_tests()
        elif args.test_type == "performance":
            exit_code = runner.run_performance_tests()
        elif args.test_type == "security":
            exit_code = runner.run_security_tests()

        if exit_code == 0:
            print("✅ All integration tests passed!")
        else:
            print("❌ Some integration tests failed")

    except KeyboardInterrupt:
        print("\n⚠️  Integration tests interrupted by user")
        exit_code = 130

    except Exception as e:
        print(f"❌ Error running integration tests: {e}")
        exit_code = 1

    finally:
        # Clean up test environment (unless --no-cleanup is specified)
        if not args.no_cleanup:
            runner.cleanup_test_environment()
        else:
            print(f"🔧 Test environment preserved at: {runner.temp_dir}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
