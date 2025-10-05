"""Test runner for executing saidata validation tests."""

import logging
from datetime import datetime
from pathlib import Path

from saigen.testing.models import TestSuite
from saigen.testing.validator import SaidataValidator

logger = logging.getLogger(__name__)


class TestRunner:
    """Runs validation tests on saidata files."""

    def __init__(
        self,
        dry_run: bool = True,
        verbose: bool = False,
        real_install: bool = False,
    ):
        """Initialize test runner.

        Args:
            dry_run: If True, don't actually install/modify system
            verbose: Enable verbose logging
            real_install: If True, perform actual installation tests
        """
        self.dry_run = dry_run and not real_install
        self.verbose = verbose
        self.validator = SaidataValidator(dry_run=self.dry_run, verbose=verbose)

    def run_tests(self, saidata_path: Path) -> TestSuite:
        """Run all validation tests on a saidata file.

        Args:
            saidata_path: Path to saidata YAML file

        Returns:
            TestSuite with all test results
        """
        suite = TestSuite(name=saidata_path.name)

        logger.info(f"Testing saidata: {saidata_path}")

        # Load saidata
        saidata = self.validator.load_saidata(saidata_path)
        if not saidata:
            suite.end_time = datetime.now()
            return suite

        # Run validation tests
        tests = [
            ("Package Existence", lambda: self.validator.validate_package_exists(saidata)),
            ("Installation", lambda: self.validator.validate_installation(saidata)),
            ("Services", lambda: self.validator.validate_services(saidata)),
            ("Files", lambda: self.validator.validate_files(saidata)),
        ]

        for test_name, test_func in tests:
            try:
                if self.verbose:
                    logger.info(f"Running test: {test_name}")
                result = test_func()
                suite.results.append(result)

                if self.verbose:
                    logger.info(f"  {result.status.value}: {result.message}")
            except Exception as e:
                logger.error(f"Test '{test_name}' raised exception: {e}")
                from saigen.testing.models import TestResult, TestStatus

                suite.results.append(
                    TestResult(
                        name=test_name.lower().replace(" ", "_"),
                        status=TestStatus.ERROR,
                        duration=0.0,
                        message=str(e),
                    )
                )

        suite.end_time = datetime.now()
        return suite

    def run_batch(self, saidata_dir: Path) -> list[TestSuite]:
        """Run tests on all saidata files in a directory.

        Args:
            saidata_dir: Directory containing saidata YAML files

        Returns:
            List of TestSuite results
        """
        results = []

        yaml_files = list(saidata_dir.glob("**/*.yaml")) + list(saidata_dir.glob("**/*.yml"))

        logger.info(f"Found {len(yaml_files)} saidata files to test")

        for yaml_file in yaml_files:
            suite = self.run_tests(yaml_file)
            results.append(suite)

        return results
