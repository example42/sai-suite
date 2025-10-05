"""Test result reporting and formatting."""

import json
import logging
from pathlib import Path
from typing import Optional

from saigen.testing.models import TestStatus, TestSuite

logger = logging.getLogger(__name__)


class TestReporter:
    """Formats and reports test results."""

    def __init__(self, output_format: str = "text"):
        """Initialize reporter.

        Args:
            output_format: Output format (text, json, junit)
        """
        self.output_format = output_format

    def report(self, suite: TestSuite, output_file: Optional[Path] = None) -> str:
        """Generate test report.

        Args:
            suite: Test suite results
            output_file: Optional file to write report to

        Returns:
            Formatted report string
        """
        if self.output_format == "json":
            report = self._format_json(suite)
        elif self.output_format == "junit":
            report = self._format_junit(suite)
        else:
            report = self._format_text(suite)

        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(report)
            logger.info(f"Report written to: {output_file}")

        return report

    def report_batch(self, suites: list[TestSuite], output_file: Optional[Path] = None) -> str:
        """Generate batch test report.

        Args:
            suites: List of test suite results
            output_file: Optional file to write report to

        Returns:
            Formatted report string
        """
        if self.output_format == "json":
            report = self._format_batch_json(suites)
        else:
            report = self._format_batch_text(suites)

        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(report)
            logger.info(f"Batch report written to: {output_file}")

        return report

    def _format_text(self, suite: TestSuite) -> str:
        """Format as human-readable text."""
        lines = []
        lines.append(f"\n{'=' * 60}")
        lines.append(f"Test Suite: {suite.name}")
        lines.append(f"{'=' * 60}")
        lines.append(f"Duration: {suite.duration:.2f}s")
        lines.append(
            f"Total: {
                suite.total} | Passed: {
                suite.passed} | Failed: {
                suite.failed} | Skipped: {
                    suite.skipped} | Errors: {
                        suite.errors}")
        lines.append(f"{'-' * 60}")

        for result in suite.results:
            status_symbol = {
                TestStatus.PASSED: "✓",
                TestStatus.FAILED: "✗",
                TestStatus.SKIPPED: "○",
                TestStatus.ERROR: "⚠",
            }[result.status]

            lines.append(f"{status_symbol} {result.name} ({result.duration:.2f}s)")
            if result.message:
                lines.append(f"  {result.message}")
            if result.details:
                for key, value in result.details.items():
                    lines.append(f"    {key}: {value}")

        lines.append(f"{'=' * 60}\n")
        return "\n".join(lines)

    def _format_json(self, suite: TestSuite) -> str:
        """Format as JSON."""
        return json.dumps(suite.to_dict(), indent=2)

    def _format_junit(self, suite: TestSuite) -> str:
        """Format as JUnit XML."""
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append(
            f'<testsuite name="{suite.name}" tests="{suite.total}" '
            f'failures="{suite.failed}" errors="{suite.errors}" '
            f'skipped="{suite.skipped}" time="{suite.duration:.3f}">'
        )

        for result in suite.results:
            lines.append(f'  <testcase name="{result.name}" time="{result.duration:.3f}">')

            if result.status == TestStatus.FAILED:
                lines.append(f'    <failure message="{result.message or "Test failed"}"/>')
            elif result.status == TestStatus.ERROR:
                lines.append(f'    <error message="{result.message or "Test error"}"/>')
            elif result.status == TestStatus.SKIPPED:
                lines.append(f'    <skipped message="{result.message or "Test skipped"}"/>')

            lines.append("  </testcase>")

        lines.append("</testsuite>")
        return "\n".join(lines)

    def _format_batch_text(self, suites: list[TestSuite]) -> str:
        """Format batch results as text."""
        lines = []
        lines.append(f"\n{'=' * 60}")
        lines.append(f"Batch Test Results")
        lines.append(f"{'=' * 60}")

        total_tests = sum(s.total for s in suites)
        total_passed = sum(s.passed for s in suites)
        total_failed = sum(s.failed for s in suites)
        total_skipped = sum(s.skipped for s in suites)
        total_errors = sum(s.errors for s in suites)
        total_duration = sum(s.duration for s in suites)

        lines.append(f"Total Suites: {len(suites)}")
        lines.append(f"Total Tests: {total_tests}")
        lines.append(
            f"Passed: {total_passed} | Failed: {total_failed} | Skipped: {total_skipped} | Errors: {total_errors}"
        )
        lines.append(f"Total Duration: {total_duration:.2f}s")
        lines.append(f"{'-' * 60}")

        for suite in suites:
            status = "✓" if suite.failed == 0 and suite.errors == 0 else "✗"
            lines.append(
                f"{status} {suite.name}: {suite.passed}/{suite.total} passed ({suite.duration:.2f}s)"
            )

        lines.append(f"{'=' * 60}\n")
        return "\n".join(lines)

    def _format_batch_json(self, suites: list[TestSuite]) -> str:
        """Format batch results as JSON."""
        return json.dumps(
            {
                "suites": [s.to_dict() for s in suites],
                "summary": {
                    "total_suites": len(suites),
                    "total_tests": sum(s.total for s in suites),
                    "total_passed": sum(s.passed for s in suites),
                    "total_failed": sum(s.failed for s in suites),
                    "total_skipped": sum(s.skipped for s in suites),
                    "total_errors": sum(s.errors for s in suites),
                    "total_duration": sum(s.duration for s in suites),
                },
            },
            indent=2,
        )
