"""Comprehensive test runner for saigen components."""

import pytest
import sys
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import subprocess
import json


class SaigenTestRunner:
    """Comprehensive test runner for saigen components."""
    
    def __init__(self, test_dir: Path = None):
        """Initialize test runner."""
        self.test_dir = test_dir or Path(__file__).parent
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def run_unit_tests(self, verbose: bool = True, coverage: bool = True) -> Dict[str, Any]:
        """Run unit tests for saigen components."""
        print("🧪 Running saigen unit tests...")
        
        args = [
            "-m", "pytest",
            str(self.test_dir),
            "-v" if verbose else "-q",
            "-x",  # Stop on first failure
            "--tb=short",
            "-m", "not integration and not slow and not performance"
        ]
        
        if coverage:
            args.extend([
                "--cov=saigen",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov_saigen",
                "--cov-fail-under=80"
            ])
        
        # Filter to saigen-specific tests
        saigen_test_files = [
            "test_saigen_cli_main.py",
            "test_saigen_batch_engine.py", 
            "test_saigen_repository_manager.py",
            "test_generation_engine.py",
            "test_llm_providers.py",
            "test_rag_indexer.py",
            "test_saidata_validator.py",
            "test_saidata_tester.py",
            "test_advanced_validator.py",
            "test_batch_engine.py",
            "test_update_engine.py",
            "test_config.py",
            "test_models.py"
        ]
        
        # Add specific test files
        for test_file in saigen_test_files:
            test_path = self.test_dir / test_file
            if test_path.exists():
                args.append(str(test_path))
        
        result = subprocess.run(args, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    
    def run_integration_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run integration tests."""
        print("🔗 Running saigen integration tests...")
        
        args = [
            "-m", "pytest",
            str(self.test_dir / "test_saigen_integration.py"),
            "-v" if verbose else "-q",
            "--tb=short",
            "-m", "integration"
        ]
        
        result = subprocess.run(args, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    
    def run_performance_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run performance benchmarks."""
        print("⚡ Running saigen performance tests...")
        
        args = [
            "-m", "pytest",
            str(self.test_dir / "test_performance_benchmarks.py"),
            "-v" if verbose else "-q",
            "--tb=short",
            "-m", "performance",
            "-s"  # Don't capture output for performance metrics
        ]
        
        result = subprocess.run(args, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    
    def run_specific_component_tests(self, component: str, verbose: bool = True) -> Dict[str, Any]:
        """Run tests for a specific component."""
        print(f"🎯 Running tests for {component}...")
        
        component_test_map = {
            "cli": ["test_saigen_cli_main.py"],
            "generation": ["test_generation_engine.py"],
            "batch": ["test_saigen_batch_engine.py", "test_batch_engine.py"],
            "repository": ["test_saigen_repository_manager.py", "test_repository_cache.py"],
            "llm": ["test_llm_providers.py", "test_llm_providers_extended.py"],
            "validation": ["test_saidata_validator.py", "test_advanced_validator.py"],
            "testing": ["test_saidata_tester.py"],
            "rag": ["test_rag_indexer.py"],
            "models": ["test_models.py"],
            "config": ["test_config.py"]
        }
        
        if component not in component_test_map:
            return {
                "success": False,
                "error": f"Unknown component: {component}. Available: {list(component_test_map.keys())}"
            }
        
        test_files = component_test_map[component]
        args = ["-m", "pytest", "-v" if verbose else "-q", "--tb=short"]
        
        for test_file in test_files:
            test_path = self.test_dir / test_file
            if test_path.exists():
                args.append(str(test_path))
        
        result = subprocess.run(args, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    
    def run_fast_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run fast tests only (excluding slow and integration tests)."""
        print("🏃 Running fast tests...")
        
        args = [
            "-m", "pytest",
            str(self.test_dir),
            "-v" if verbose else "-q",
            "--tb=short",
            "-m", "not slow and not integration and not performance"
        ]
        
        result = subprocess.run(args, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    
    def run_all_tests(self, 
                     include_integration: bool = False,
                     include_performance: bool = False,
                     verbose: bool = True,
                     coverage: bool = True) -> Dict[str, Any]:
        """Run all tests with specified options."""
        print("🚀 Running comprehensive saigen test suite...")
        
        self.start_time = time.time()
        results = {}
        
        # Always run unit tests
        results["unit"] = self.run_unit_tests(verbose=verbose, coverage=coverage)
        
        # Optionally run integration tests
        if include_integration:
            results["integration"] = self.run_integration_tests(verbose=verbose)
        
        # Optionally run performance tests
        if include_performance:
            results["performance"] = self.run_performance_tests(verbose=verbose)
        
        self.end_time = time.time()
        
        # Calculate overall success
        overall_success = all(result.get("success", False) for result in results.values())
        
        results["summary"] = {
            "overall_success": overall_success,
            "total_time": self.end_time - self.start_time,
            "test_categories": list(results.keys())
        }
        
        self.results = results
        return results
    
    def generate_report(self, output_file: Optional[Path] = None) -> str:
        """Generate a comprehensive test report."""
        if not self.results:
            return "No test results available. Run tests first."
        
        report_lines = [
            "# Saigen Test Suite Report",
            f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        # Summary
        summary = self.results.get("summary", {})
        overall_success = summary.get("overall_success", False)
        total_time = summary.get("total_time", 0)
        
        report_lines.extend([
            "## Summary",
            f"Overall Status: {'✅ PASSED' if overall_success else '❌ FAILED'}",
            f"Total Time: {total_time:.2f} seconds",
            f"Test Categories: {', '.join(summary.get('test_categories', []))}",
            ""
        ])
        
        # Detailed results for each category
        for category, result in self.results.items():
            if category == "summary":
                continue
            
            status = "✅ PASSED" if result.get("success", False) else "❌ FAILED"
            report_lines.extend([
                f"## {category.title()} Tests",
                f"Status: {status}",
                f"Return Code: {result.get('returncode', 'N/A')}",
                ""
            ])
            
            if result.get("stdout"):
                report_lines.extend([
                    "### Output",
                    "```",
                    result["stdout"],
                    "```",
                    ""
                ])
            
            if result.get("stderr"):
                report_lines.extend([
                    "### Errors",
                    "```",
                    result["stderr"],
                    "```",
                    ""
                ])
        
        report = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            print(f"📄 Report saved to: {output_file}")
        
        return report
    
    def print_summary(self):
        """Print a summary of test results."""
        if not self.results:
            print("No test results available.")
            return
        
        summary = self.results.get("summary", {})
        overall_success = summary.get("overall_success", False)
        total_time = summary.get("total_time", 0)
        
        print("\n" + "="*60)
        print("🧪 SAIGEN TEST SUITE SUMMARY")
        print("="*60)
        print(f"Overall Status: {'✅ PASSED' if overall_success else '❌ FAILED'}")
        print(f"Total Time: {total_time:.2f} seconds")
        print()
        
        for category, result in self.results.items():
            if category == "summary":
                continue
            
            status = "✅ PASSED" if result.get("success", False) else "❌ FAILED"
            print(f"{category.title()} Tests: {status}")
        
        print("="*60)
        
        if not overall_success:
            print("\n❌ Some tests failed. Check the detailed output above.")
            return False
        else:
            print("\n✅ All tests passed!")
            return True


def main():
    """Main entry point for test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Saigen Test Runner")
    parser.add_argument("command", nargs="?", default="all", 
                       choices=["all", "unit", "integration", "performance", "fast", "component"],
                       help="Test category to run")
    parser.add_argument("--component", help="Specific component to test (for component command)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-coverage", action="store_true", help="Disable coverage reporting")
    parser.add_argument("--include-integration", action="store_true", 
                       help="Include integration tests (for 'all' command)")
    parser.add_argument("--include-performance", action="store_true",
                       help="Include performance tests (for 'all' command)")
    parser.add_argument("--report", help="Generate report to file")
    
    args = parser.parse_args()
    
    runner = SaigenTestRunner()
    
    try:
        if args.command == "all":
            results = runner.run_all_tests(
                include_integration=args.include_integration,
                include_performance=args.include_performance,
                verbose=args.verbose,
                coverage=not args.no_coverage
            )
        elif args.command == "unit":
            results = {"unit": runner.run_unit_tests(verbose=args.verbose, coverage=not args.no_coverage)}
        elif args.command == "integration":
            results = {"integration": runner.run_integration_tests(verbose=args.verbose)}
        elif args.command == "performance":
            results = {"performance": runner.run_performance_tests(verbose=args.verbose)}
        elif args.command == "fast":
            results = {"fast": runner.run_fast_tests(verbose=args.verbose)}
        elif args.command == "component":
            if not args.component:
                print("Error: --component required for component command")
                sys.exit(1)
            results = {"component": runner.run_specific_component_tests(args.component, verbose=args.verbose)}
        
        runner.results = results
        
        # Generate report if requested
        if args.report:
            runner.generate_report(Path(args.report))
        
        # Print summary
        success = runner.print_summary()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Test run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()