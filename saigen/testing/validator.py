"""Validator for testing saidata files on real systems."""

import logging
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import yaml

from saigen.models.saidata import SaiData
from saigen.testing.models import TestResult, TestStatus

logger = logging.getLogger(__name__)


class SaidataValidator:
    """Validates saidata files by testing on real systems."""

    def __init__(self, dry_run: bool = True, verbose: bool = False):
        """Initialize validator.

        Args:
            dry_run: If True, don't actually install/modify system
            verbose: Enable verbose logging
        """
        self.dry_run = dry_run
        self.verbose = verbose
        self.system = platform.system().lower()

    def load_saidata(self, path: Path) -> Optional[SaiData]:
        """Load and parse saidata file."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
            return SaiData(**data)
        except Exception as e:
            logger.error(f"Failed to load saidata: {e}")
            return None

    def validate_package_exists(self, saidata: SaiData) -> TestResult:
        """Test if package exists in repositories."""
        start = self._now()

        if not saidata.packages:
            return TestResult(
                name="package_exists",
                status=TestStatus.SKIPPED,
                duration=self._elapsed(start),
                message="No packages defined",
            )

        for package in saidata.packages:
            pkg_mgr = package.name
            pkg_name = package.package_name

            if not self._is_package_manager_available(pkg_mgr):
                continue

            exists = self._check_package_exists(pkg_mgr, pkg_name)
            if not exists:
                return TestResult(
                    name="package_exists",
                    status=TestStatus.FAILED,
                    duration=self._elapsed(start),
                    message=f"Package '{pkg_name}' not found in {pkg_mgr}",
                    details={"package_manager": pkg_mgr, "package": pkg_name},
                )

        return TestResult(
            name="package_exists",
            status=TestStatus.PASSED,
            duration=self._elapsed(start),
            message="All packages exist in repositories",
        )

    def validate_installation(self, saidata: SaiData) -> TestResult:
        """Test package installation."""
        start = self._now()

        if self.dry_run:
            return TestResult(
                name="installation",
                status=TestStatus.SKIPPED,
                duration=self._elapsed(start),
                message="Skipped in dry-run mode",
            )

        if not saidata.packages:
            return TestResult(
                name="installation",
                status=TestStatus.SKIPPED,
                duration=self._elapsed(start),
                message="No packages defined",
            )

        # Try to install packages
        for package in saidata.packages:
            pkg_mgr = package.name
            pkg_name = package.package_name

            if not self._is_package_manager_available(pkg_mgr):
                continue

            success = self._install_package(pkg_mgr, pkg_name)
            if not success:
                return TestResult(
                    name="installation",
                    status=TestStatus.FAILED,
                    duration=self._elapsed(start),
                    message=f"Failed to install '{pkg_name}' via {pkg_mgr}",
                    details={"package_manager": pkg_mgr, "package": pkg_name},
                )

        return TestResult(
            name="installation",
            status=TestStatus.PASSED,
            duration=self._elapsed(start),
            message="Installation successful",
        )

    def validate_services(self, saidata: SaiData) -> TestResult:
        """Test service management."""
        start = self._now()

        if not saidata.services:
            return TestResult(
                name="services",
                status=TestStatus.SKIPPED,
                duration=self._elapsed(start),
                message="No services defined",
            )

        for service in saidata.services:
            service_name = service.service_name or service.name
            exists = self._check_service_exists(service_name)
            if not exists:
                return TestResult(
                    name="services",
                    status=TestStatus.FAILED,
                    duration=self._elapsed(start),
                    message=f"Service '{service_name}' not found",
                    details={"service": service_name},
                )

        return TestResult(
            name="services",
            status=TestStatus.PASSED,
            duration=self._elapsed(start),
            message="All services exist",
        )

    def validate_files(self, saidata: SaiData) -> TestResult:
        """Test file locations."""
        start = self._now()

        if not saidata.files:
            return TestResult(
                name="files",
                status=TestStatus.SKIPPED,
                duration=self._elapsed(start),
                message="No files defined",
            )

        missing_files = []
        for file_obj in saidata.files:
            file_path = file_obj.path
            if not Path(file_path).exists():
                missing_files.append(file_path)

        if missing_files:
            return TestResult(
                name="files",
                status=TestStatus.FAILED,
                duration=self._elapsed(start),
                message=f"Missing files: {', '.join(missing_files)}",
                details={"missing_files": missing_files},
            )

        return TestResult(
            name="files",
            status=TestStatus.PASSED,
            duration=self._elapsed(start),
            message="All files exist",
        )

    def _is_package_manager_available(self, pkg_mgr: str) -> bool:
        """Check if package manager is available on system."""
        return shutil.which(pkg_mgr) is not None

    def _check_package_exists(self, pkg_mgr: str, package: str) -> bool:
        """Check if package exists in repository."""
        commands = {
            "apt": ["apt-cache", "show", package],
            "dnf": ["dnf", "info", package],
            "yum": ["yum", "info", package],
            "brew": ["brew", "info", package],
            "winget": ["winget", "show", package],
            "pacman": ["pacman", "-Si", package],
        }

        cmd = commands.get(pkg_mgr)
        if not cmd:
            logger.warning(f"Unknown package manager: {pkg_mgr}")
            return False

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking package: {e}")
            return False

    def _install_package(self, pkg_mgr: str, package: str) -> bool:
        """Install package using package manager."""
        commands = {
            "apt": ["apt-get", "install", "-y", package],
            "dnf": ["dnf", "install", "-y", package],
            "yum": ["yum", "install", "-y", package],
            "brew": ["brew", "install", package],
            "winget": ["winget", "install", package],
            "pacman": ["pacman", "-S", "--noconfirm", package],
        }

        cmd = commands.get(pkg_mgr)
        if not cmd:
            return False

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error installing package: {e}")
            return False

    def _check_service_exists(self, service: str) -> bool:
        """Check if service exists on system."""
        if self.system == "linux":
            # Try systemctl
            try:
                result = subprocess.run(
                    ["systemctl", "list-unit-files", service],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                return result.returncode == 0
            except Exception:
                pass

        return False

    @staticmethod
    def _now() -> float:
        """Get current timestamp."""
        import time

        return time.time()

    @staticmethod
    def _elapsed(start: float) -> float:
        """Calculate elapsed time."""
        import time

        return time.time() - start
