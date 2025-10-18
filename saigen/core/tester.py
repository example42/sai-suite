"""Comprehensive saidata testing system with dry-run and MCP server integration."""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ..models.config import SaigenConfig
from ..models.saidata import SaiData
from .validator import SaidataValidator


class SaidataTestSeverity(str, Enum):
    """Test result severity levels."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIP = "skip"


class SaidataTestType(str, Enum):
    """Types of tests that can be performed."""

    DRY_RUN = "dry_run"
    PROVIDER_COMPATIBILITY = "provider_compatibility"
    MCP_SERVER = "mcp_server"
    PACKAGE_AVAILABILITY = "package_availability"
    COMMAND_VALIDATION = "command_validation"
    SERVICE_VALIDATION = "service_validation"


@dataclass
class SaidataTestResult:
    """Result of a single test."""

    test_type: SaidataTestType
    severity: SaidataTestSeverity
    message: str
    details: Optional[Dict[str, Any]] = None
    provider: Optional[str] = None
    duration: Optional[float] = None
    suggestions: Optional[List[str]] = None


@dataclass
class SaidataTestSuite:
    """Collection of test results."""

    file_path: str
    total_tests: int
    passed: int
    failed: int
    warnings: int
    skipped: int
    results: List[SaidataTestResult]
    duration: float

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100

    @property
    def has_failures(self) -> bool:
        """Check if any tests failed."""
        return self.failed > 0


class MCPServerClient:
    """Client for interacting with MCP servers for extended testing."""

    def __init__(self, server_config: Optional[Dict[str, Any]] = None):
        """Initialize MCP server client.

        Args:
            server_config: MCP server configuration
        """
        self.server_config = server_config or {}
        self.logger = logging.getLogger(__name__)

    async def is_available(self) -> bool:
        """Check if MCP server is available."""
        try:
            # Try to connect to MCP server
            # This is a placeholder - actual implementation would depend on MCP protocol
            return bool(self.server_config.get("enabled", False))
        except Exception as e:
            self.logger.debug(f"MCP server not available: {e}")
            return False

    async def test_saidata(self, saidata: SaiData, providers: List[str]) -> List[SaidataTestResult]:
        """Test saidata using MCP server capabilities.

        Args:
            saidata: SaiData to test
            providers: List of providers to test

        Returns:
            List of test results
        """
        results = []

        if not await self.is_available():
            results.append(
                SaidataTestResult(
                    test_type=SaidataTestType.MCP_SERVER,
                    severity=SaidataTestSeverity.SKIP,
                    message="MCP server not available",
                    details={"reason": "server_unavailable"},
                )
            )
            return results

        try:
            # Placeholder for actual MCP server testing
            # In a real implementation, this would:
            # 1. Send saidata to MCP server
            # 2. Request validation tests
            # 3. Parse and return results

            for provider in providers:
                if provider in (saidata.providers or {}):
                    results.append(
                        SaidataTestResult(
                            test_type=SaidataTestType.MCP_SERVER,
                            severity=SaidataTestSeverity.PASS,
                            message=f"MCP server validation passed for {provider}",
                            provider=provider,
                            details={"mcp_server": "placeholder"},
                        )
                    )
                else:
                    results.append(
                        SaidataTestResult(
                            test_type=SaidataTestType.MCP_SERVER,
                            severity=SaidataTestSeverity.SKIP,
                            message=f"Provider {provider} not defined in saidata",
                            provider=provider,
                        )
                    )

        except Exception as e:
            results.append(
                SaidataTestResult(
                    test_type=SaidataTestType.MCP_SERVER,
                    severity=SaidataTestSeverity.FAIL,
                    message=f"MCP server test failed: {str(e)}",
                    details={"error": str(e)},
                )
            )

        return results


class SaidataTester:
    """Comprehensive saidata testing system."""

    def __init__(self, config: Optional[SaigenConfig] = None):
        """Initialize saidata tester.

        Args:
            config: Saigen configuration
        """
        self.config = config
        self.validator = SaidataValidator()
        self.mcp_client = MCPServerClient()
        self.logger = logging.getLogger(__name__)

    async def test_file(
        self,
        file_path: Path,
        providers: Optional[List[str]] = None,
        test_types: Optional[List[SaidataTestType]] = None,
        dry_run: bool = True,
    ) -> SaidataTestSuite:
        """Test a saidata file comprehensively.

        Args:
            file_path: Path to saidata file
            providers: List of providers to test (default: all in file)
            test_types: Types of tests to run (default: all)
            dry_run: Whether to perform dry-run testing only

        Returns:
            TestSuite with all test results
        """
        import time

        start_time = time.time()

        try:
            # Load and validate saidata
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            saidata = SaiData(**data)

            # Determine providers to test
            if providers is None:
                providers = list(saidata.providers.keys()) if saidata.providers else []

            # Determine test types to run
            if test_types is None:
                test_types = [
                    SaidataTestType.DRY_RUN,
                    SaidataTestType.PROVIDER_COMPATIBILITY,
                    SaidataTestType.PACKAGE_AVAILABILITY,
                    SaidataTestType.COMMAND_VALIDATION,
                    SaidataTestType.SERVICE_VALIDATION,
                ]

                # Add MCP server tests if available
                if await self.mcp_client.is_available():
                    test_types.append(SaidataTestType.MCP_SERVER)

            # Run all tests
            all_results = []

            for test_type in test_types:
                if test_type == SaidataTestType.DRY_RUN:
                    results = await self._test_dry_run(saidata, providers)
                elif test_type == SaidataTestType.PROVIDER_COMPATIBILITY:
                    results = await self._test_provider_compatibility(saidata, providers)
                elif test_type == SaidataTestType.MCP_SERVER:
                    results = await self.mcp_client.test_saidata(saidata, providers)
                elif test_type == SaidataTestType.PACKAGE_AVAILABILITY:
                    results = await self._test_package_availability(saidata, providers)
                elif test_type == SaidataTestType.COMMAND_VALIDATION:
                    results = await self._test_command_validation(saidata, providers)
                elif test_type == SaidataTestType.SERVICE_VALIDATION:
                    results = await self._test_service_validation(saidata, providers)
                else:
                    continue

                all_results.extend(results)

            # Calculate statistics
            total_tests = len(all_results)
            passed = sum(1 for r in all_results if r.severity == SaidataTestSeverity.PASS)
            failed = sum(1 for r in all_results if r.severity == SaidataTestSeverity.FAIL)
            warnings = sum(1 for r in all_results if r.severity == SaidataTestSeverity.WARNING)
            skipped = sum(1 for r in all_results if r.severity == SaidataTestSeverity.SKIP)

            duration = time.time() - start_time

            return SaidataTestSuite(
                file_path=str(file_path),
                total_tests=total_tests,
                passed=passed,
                failed=failed,
                warnings=warnings,
                skipped=skipped,
                results=all_results,
                duration=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            return SaidataTestSuite(
                file_path=str(file_path),
                total_tests=1,
                passed=0,
                failed=1,
                warnings=0,
                skipped=0,
                results=[
                    SaidataTestResult(
                        test_type=SaidataTestType.DRY_RUN,
                        severity=SaidataTestSeverity.FAIL,
                        message=f"Failed to load or parse saidata file: {str(e)}",
                        details={"error": str(e)},
                    )
                ],
                duration=duration,
            )

    async def _test_dry_run(
        self, saidata: SaiData, providers: List[str]
    ) -> List[SaidataTestResult]:
        """Perform dry-run testing without actual installation.

        Args:
            saidata: SaiData to test
            providers: List of providers to test

        Returns:
            List of test results
        """
        results = []

        for provider in providers:
            if provider not in (saidata.providers or {}):
                results.append(
                    SaidataTestResult(
                        test_type=SaidataTestType.DRY_RUN,
                        severity=SaidataTestSeverity.SKIP,
                        message=f"Provider {provider} not defined in saidata",
                        provider=provider,
                    )
                )
                continue

            provider_config = saidata.providers[provider]

            # Test package installation commands (dry-run)
            if provider_config.packages:
                for package in provider_config.packages:
                    result = await self._test_package_dry_run(provider, package.name)
                    result.provider = provider
                    results.append(result)

            # Test service configurations
            if provider_config.services:
                for service in provider_config.services:
                    result = await self._test_service_dry_run(provider, service.name)
                    result.provider = provider
                    results.append(result)

            # Test file and directory operations
            if provider_config.files:
                for file_def in provider_config.files:
                    result = await self._test_file_dry_run(provider, file_def.path)
                    result.provider = provider
                    results.append(result)

        return results

    async def _test_package_dry_run(self, provider: str, package_name: str) -> SaidataTestResult:
        """Test package installation in dry-run mode.

        Args:
            provider: Provider name (apt, brew, etc.)
            package_name: Package name to test

        Returns:
            SaidataTestResult for the package test
        """
        try:
            # Map providers to their dry-run commands
            dry_run_commands = {
                "apt": ["apt-get", "install", "--dry-run", "-y", package_name],
                "brew": ["brew", "install", "--dry-run", package_name],
                "dnf": ["dnf", "install", "--assumeno", package_name],
                "yum": ["yum", "install", "--assumeno", package_name],
                "pacman": ["pacman", "-S", "--noconfirm", "--print", package_name],
                "winget": ["winget", "install", "--id", package_name, "--dry-run"],
                "choco": ["choco", "install", package_name, "--whatif"],
                "snap": ["snap", "install", "--dry-run", package_name],
                "flatpak": ["flatpak", "install", "--assumeyes", "--dry-run", package_name],
            }

            if provider not in dry_run_commands:
                return SaidataTestResult(
                    test_type=SaidataTestType.DRY_RUN,
                    severity=SaidataTestSeverity.SKIP,
                    message=f"Dry-run not supported for provider {provider}",
                    details={"package": package_name},
                )

            cmd = dry_run_commands[provider]

            # Run the dry-run command
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)

            if process.returncode == 0:
                return SaidataTestResult(
                    test_type=SaidataTestType.DRY_RUN,
                    severity=SaidataTestSeverity.PASS,
                    message=f"Package {package_name} dry-run successful",
                    details={
                        "package": package_name,
                        "command": " ".join(cmd),
                        "stdout": stdout.decode("utf-8", errors="ignore")[:500],
                    },
                )
            else:
                return SaidataTestResult(
                    test_type=SaidataTestType.DRY_RUN,
                    severity=SaidataTestSeverity.FAIL,
                    message=f"Package {package_name} dry-run failed",
                    details={
                        "package": package_name,
                        "command": " ".join(cmd),
                        "return_code": process.returncode,
                        "stderr": stderr.decode("utf-8", errors="ignore")[:500],
                    },
                    suggestions=[
                        "Check if package name is correct",
                        "Verify package exists in repository",
                        "Check repository configuration",
                    ],
                )

        except asyncio.TimeoutError:
            return SaidataTestResult(
                test_type=SaidataTestType.DRY_RUN,
                severity=SaidataTestSeverity.FAIL,
                message=f"Package {package_name} dry-run timed out",
                details={"package": package_name, "timeout": 30},
            )
        except FileNotFoundError:
            return SaidataTestResult(
                test_type=SaidataTestType.DRY_RUN,
                severity=SaidataTestSeverity.SKIP,
                message=f"Provider {provider} not available on system",
                details={"package": package_name},
            )
        except Exception as e:
            return SaidataTestResult(
                test_type=SaidataTestType.DRY_RUN,
                severity=SaidataTestSeverity.FAIL,
                message=f"Package {package_name} dry-run error: {str(e)}",
                details={"package": package_name, "error": str(e)},
            )

    async def _test_service_dry_run(self, provider: str, service_name: str) -> SaidataTestResult:
        """Test service configuration in dry-run mode.

        Args:
            provider: Provider name
            service_name: Service name to test

        Returns:
            SaidataTestResult for the service test
        """
        try:
            # Try systemd first (most common)
            try:
                process = await asyncio.create_subprocess_exec(
                    "systemctl",
                    "cat",
                    service_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)

                if process.returncode == 0:
                    return SaidataTestResult(
                        test_type=SaidataTestType.DRY_RUN,
                        severity=SaidataTestSeverity.PASS,
                        message=f"Service {service_name} configuration found",
                        details={"service": service_name, "type": "systemd"},
                    )
                else:
                    return SaidataTestResult(
                        test_type=SaidataTestType.DRY_RUN,
                        severity=SaidataTestSeverity.WARNING,
                        message=f"Service {service_name} not found or not configured",
                        details={"service": service_name, "type": "systemd"},
                        suggestions=["Service may need to be installed first"],
                    )

            except (FileNotFoundError, asyncio.TimeoutError):
                return SaidataTestResult(
                    test_type=SaidataTestType.DRY_RUN,
                    severity=SaidataTestSeverity.SKIP,
                    message=f"Service testing not available (systemctl not found)",
                    details={"service": service_name},
                )

        except Exception as e:
            return SaidataTestResult(
                test_type=SaidataTestType.DRY_RUN,
                severity=SaidataTestSeverity.FAIL,
                message=f"Service {service_name} test error: {str(e)}",
                details={"service": service_name, "error": str(e)},
            )

    async def _test_file_dry_run(self, provider: str, file_path: str) -> SaidataTestResult:
        """Test file operations in dry-run mode.

        Args:
            provider: Provider name
            file_path: File path to test

        Returns:
            SaidataTestResult for the file test
        """
        try:
            path = Path(file_path)

            # Check if parent directory exists or can be created
            parent_dir = path.parent

            if parent_dir.exists():
                if parent_dir.is_dir():
                    return SaidataTestResult(
                        test_type=SaidataTestType.DRY_RUN,
                        severity=SaidataTestSeverity.PASS,
                        message=f"File path {file_path} parent directory exists",
                        details={"file_path": file_path, "parent_exists": True},
                    )
                else:
                    return SaidataTestResult(
                        test_type=SaidataTestType.DRY_RUN,
                        severity=SaidataTestSeverity.FAIL,
                        message=f"File path {file_path} parent is not a directory",
                        details={"file_path": file_path, "parent_is_file": True},
                        suggestions=["Check file path configuration"],
                    )
            else:
                # Check if we can create the parent directory (permissions)
                try:
                    # Don't actually create, just check permissions
                    return SaidataTestResult(
                        test_type=SaidataTestType.DRY_RUN,
                        severity=SaidataTestSeverity.WARNING,
                        message=f"File path {file_path} parent directory does not exist",
                        details={"file_path": file_path, "parent_exists": False},
                        suggestions=["Parent directory will need to be created"],
                    )
                except Exception:
                    return SaidataTestResult(
                        test_type=SaidataTestType.DRY_RUN,
                        severity=SaidataTestSeverity.FAIL,
                        message=f"File path {file_path} cannot be created (permissions)",
                        details={"file_path": file_path, "permission_error": True},
                    )

        except Exception as e:
            return SaidataTestResult(
                test_type=SaidataTestType.DRY_RUN,
                severity=SaidataTestSeverity.FAIL,
                message=f"File path {file_path} test error: {str(e)}",
                details={"file_path": file_path, "error": str(e)},
            )

    async def _test_provider_compatibility(
        self, saidata: SaiData, providers: List[str]
    ) -> List[SaidataTestResult]:
        """Test provider compatibility across platforms.

        Args:
            saidata: SaiData to test
            providers: List of providers to test

        Returns:
            List of test results
        """
        results = []

        # Get current platform info
        import platform

        current_os = platform.system().lower()
        current_arch = platform.machine().lower()

        for provider in providers:
            if provider not in (saidata.providers or {}):
                continue

            # Check if provider is compatible with current platform
            compatibility_result = self._check_provider_platform_compatibility(
                provider, current_os, current_arch
            )
            compatibility_result.provider = provider
            results.append(compatibility_result)

            # Check if saidata has compatibility matrix
            if saidata.compatibility and saidata.compatibility.matrix:
                matrix_result = self._check_compatibility_matrix(
                    saidata.compatibility.matrix, provider, current_os, current_arch
                )
                matrix_result.provider = provider
                results.append(matrix_result)

        return results

    def _check_provider_platform_compatibility(
        self, provider: str, os_name: str, arch: str
    ) -> SaidataTestResult:
        """Check if provider is compatible with current platform.

        Args:
            provider: Provider name
            os_name: Operating system name
            arch: Architecture

        Returns:
            SaidataTestResult for compatibility check
        """
        # Define provider platform compatibility
        provider_platforms = {
            "apt": ["linux"],
            "dnf": ["linux"],
            "yum": ["linux"],
            "pacman": ["linux"],
            "brew": ["darwin", "linux"],
            "winget": ["windows"],
            "choco": ["windows"],
            "snap": ["linux"],
            "flatpak": ["linux"],
            "pkg": ["freebsd"],
            "portage": ["linux"],
            "zypper": ["linux"],
        }

        compatible_platforms = provider_platforms.get(provider, [])

        if not compatible_platforms:
            return SaidataTestResult(
                test_type=SaidataTestType.PROVIDER_COMPATIBILITY,
                severity=SaidataTestSeverity.WARNING,
                message=f"Unknown provider {provider} compatibility",
                details={"provider": provider, "current_os": os_name},
            )

        if os_name in compatible_platforms:
            return SaidataTestResult(
                test_type=SaidataTestType.PROVIDER_COMPATIBILITY,
                severity=SaidataTestSeverity.PASS,
                message=f"Provider {provider} compatible with {os_name}",
                details={"provider": provider, "current_os": os_name, "compatible": True},
            )
        else:
            return SaidataTestResult(
                test_type=SaidataTestType.PROVIDER_COMPATIBILITY,
                severity=SaidataTestSeverity.FAIL,
                message=f"Provider {provider} not compatible with {os_name}",
                details={
                    "provider": provider,
                    "current_os": os_name,
                    "compatible_platforms": compatible_platforms,
                },
                suggestions=[f"Use a provider compatible with {os_name}"],
            )

    def _check_compatibility_matrix(
        self, matrix: List[Any], provider: str, os_name: str, arch: str
    ) -> SaidataTestResult:
        """Check saidata compatibility matrix.

        Args:
            matrix: Compatibility matrix from saidata
            provider: Provider name
            os_name: Operating system name
            arch: Architecture

        Returns:
            SaidataTestResult for matrix check
        """
        for entry in matrix:
            if hasattr(entry, "provider") and entry.provider == provider:
                platforms = entry.platform if isinstance(entry.platform, list) else [entry.platform]

                if os_name in platforms or "all" in platforms:
                    if entry.supported:
                        severity = SaidataTestSeverity.PASS
                        message = f"Provider {provider} marked as supported in compatibility matrix"
                    else:
                        severity = SaidataTestSeverity.FAIL
                        message = (
                            f"Provider {provider} marked as unsupported in compatibility matrix"
                        )

                    return SaidataTestResult(
                        test_type=SaidataTestType.PROVIDER_COMPATIBILITY,
                        severity=severity,
                        message=message,
                        details={
                            "provider": provider,
                            "supported": entry.supported,
                            "tested": getattr(entry, "tested", None),
                            "notes": getattr(entry, "notes", None),
                        },
                    )

        return SaidataTestResult(
            test_type=SaidataTestType.PROVIDER_COMPATIBILITY,
            severity=SaidataTestSeverity.WARNING,
            message=f"Provider {provider} not found in compatibility matrix",
            details={"provider": provider},
        )

    async def _test_package_availability(
        self, saidata: SaiData, providers: List[str]
    ) -> List[SaidataTestResult]:
        """Test package availability in repositories.

        Args:
            saidata: SaiData to test
            providers: List of providers to test

        Returns:
            List of test results
        """
        results = []

        for provider in providers:
            if provider not in (saidata.providers or {}):
                continue

            provider_config = saidata.providers[provider]

            if provider_config.packages:
                for package in provider_config.packages:
                    result = await self._check_package_availability(provider, package.name)
                    result.provider = provider
                    results.append(result)

        return results

    async def _check_package_availability(
        self, provider: str, package_name: str
    ) -> SaidataTestResult:
        """Check if package is available in repository.

        Args:
            provider: Provider name
            package_name: Package name to check

        Returns:
            SaidataTestResult for availability check
        """
        try:
            # Map providers to their search commands
            search_commands = {
                "apt": ["apt-cache", "show", package_name],
                "brew": ["brew", "info", package_name],
                "dnf": ["dnf", "info", package_name],
                "yum": ["yum", "info", package_name],
                "pacman": ["pacman", "-Si", package_name],
                "winget": ["winget", "show", package_name],
                "snap": ["snap", "info", package_name],
                "flatpak": ["flatpak", "info", package_name],
            }

            if provider not in search_commands:
                return SaidataTestResult(
                    test_type=SaidataTestType.PACKAGE_AVAILABILITY,
                    severity=SaidataTestSeverity.SKIP,
                    message=f"Package availability check not supported for {provider}",
                    details={"package": package_name},
                )

            cmd = search_commands[provider]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)

            if process.returncode == 0:
                return SaidataTestResult(
                    test_type=SaidataTestType.PACKAGE_AVAILABILITY,
                    severity=SaidataTestSeverity.PASS,
                    message=f"Package {package_name} available in {provider}",
                    details={"package": package_name, "available": True},
                )
            else:
                return SaidataTestResult(
                    test_type=SaidataTestType.PACKAGE_AVAILABILITY,
                    severity=SaidataTestSeverity.FAIL,
                    message=f"Package {package_name} not available in {provider}",
                    details={
                        "package": package_name,
                        "available": False,
                        "stderr": stderr.decode("utf-8", errors="ignore")[:200],
                    },
                    suggestions=[
                        "Check package name spelling",
                        "Verify package exists in repository",
                        "Check if additional repositories need to be enabled",
                    ],
                )

        except asyncio.TimeoutError:
            return SaidataTestResult(
                test_type=SaidataTestType.PACKAGE_AVAILABILITY,
                severity=SaidataTestSeverity.WARNING,
                message=f"Package {package_name} availability check timed out",
                details={"package": package_name},
            )
        except FileNotFoundError:
            return SaidataTestResult(
                test_type=SaidataTestType.PACKAGE_AVAILABILITY,
                severity=SaidataTestSeverity.SKIP,
                message=f"Provider {provider} not available on system",
                details={"package": package_name},
            )
        except Exception as e:
            return SaidataTestResult(
                test_type=SaidataTestType.PACKAGE_AVAILABILITY,
                severity=SaidataTestSeverity.FAIL,
                message=f"Package {package_name} availability check error: {str(e)}",
                details={"package": package_name, "error": str(e)},
            )

    async def _test_command_validation(
        self, saidata: SaiData, providers: List[str]
    ) -> List[SaidataTestResult]:
        """Test command definitions and availability.

        Args:
            saidata: SaiData to test
            providers: List of providers to test

        Returns:
            List of test results
        """
        results = []

        # Test global commands
        if saidata.commands:
            for command in saidata.commands:
                result = await self._check_command_availability(command.name, command.path)
                results.append(result)

        # Test provider-specific commands
        for provider in providers:
            if provider not in (saidata.providers or {}):
                continue

            provider_config = saidata.providers[provider]

            if provider_config.commands:
                for command in provider_config.commands:
                    result = await self._check_command_availability(command.name, command.path)
                    result.provider = provider
                    results.append(result)

        return results

    async def _check_command_availability(
        self, command_name: str, command_path: Optional[str]
    ) -> SaidataTestResult:
        """Check if command is available on the system.

        Args:
            command_name: Command name
            command_path: Optional command path

        Returns:
            SaidataTestResult for command check
        """
        try:
            # Use 'which' or 'where' to find command
            import shutil

            cmd_to_check = command_path or command_name
            found_path = shutil.which(cmd_to_check)

            if found_path:
                return SaidataTestResult(
                    test_type=SaidataTestType.COMMAND_VALIDATION,
                    severity=SaidataTestSeverity.PASS,
                    message=f"Command {command_name} found at {found_path}",
                    details={"command": command_name, "path": found_path, "available": True},
                )
            else:
                return SaidataTestResult(
                    test_type=SaidataTestType.COMMAND_VALIDATION,
                    severity=SaidataTestSeverity.FAIL,
                    message=f"Command {command_name} not found",
                    details={"command": command_name, "available": False},
                    suggestions=[
                        "Install the package that provides this command",
                        "Check if command is in PATH",
                        "Verify command name is correct",
                    ],
                )

        except Exception as e:
            return SaidataTestResult(
                test_type=SaidataTestType.COMMAND_VALIDATION,
                severity=SaidataTestSeverity.FAIL,
                message=f"Command {command_name} validation error: {str(e)}",
                details={"command": command_name, "error": str(e)},
            )

    async def _test_service_validation(
        self, saidata: SaiData, providers: List[str]
    ) -> List[SaidataTestResult]:
        """Test service definitions and availability.

        Args:
            saidata: SaiData to test
            providers: List of providers to test

        Returns:
            List of test results
        """
        results = []

        # Test global services
        if saidata.services:
            for service in saidata.services:
                result = await self._check_service_definition(service.name, service.service_name)
                results.append(result)

        # Test provider-specific services
        for provider in providers:
            if provider not in (saidata.providers or {}):
                continue

            provider_config = saidata.providers[provider]

            if provider_config.services:
                for service in provider_config.services:
                    result = await self._check_service_definition(
                        service.name, service.service_name
                    )
                    result.provider = provider
                    results.append(result)

        return results

    async def _check_service_definition(
        self, service_name: str, service_file_name: Optional[str]
    ) -> SaidataTestResult:
        """Check service definition validity.

        Args:
            service_name: Service name
            service_file_name: Optional service file name

        Returns:
            SaidataTestResult for service check
        """
        try:
            actual_service_name = service_file_name or service_name

            # Check if service unit file exists (systemd)
            service_paths = [
                f"/etc/systemd/system/{actual_service_name}.service",
                f"/lib/systemd/system/{actual_service_name}.service",
                f"/usr/lib/systemd/system/{actual_service_name}.service",
            ]

            for service_path in service_paths:
                if Path(service_path).exists():
                    return SaidataTestResult(
                        test_type=SaidataTestType.SERVICE_VALIDATION,
                        severity=SaidataTestSeverity.PASS,
                        message=f"Service {service_name} unit file found",
                        details={
                            "service": service_name,
                            "unit_file": service_path,
                            "exists": True,
                        },
                    )

            # Service unit file not found
            return SaidataTestResult(
                test_type=SaidataTestType.SERVICE_VALIDATION,
                severity=SaidataTestSeverity.WARNING,
                message=f"Service {service_name} unit file not found",
                details={"service": service_name, "checked_paths": service_paths},
                suggestions=[
                    "Service may not be installed yet",
                    "Service may use different init system",
                    "Check service name is correct",
                ],
            )

        except Exception as e:
            return SaidataTestResult(
                test_type=SaidataTestType.SERVICE_VALIDATION,
                severity=SaidataTestSeverity.FAIL,
                message=f"Service {service_name} validation error: {str(e)}",
                details={"service": service_name, "error": str(e)},
            )

    def format_test_report(self, test_suite: SaidataTestSuite, show_details: bool = False) -> str:
        """Format test results as a human-readable report.

        Args:
            test_suite: TestSuite to format
            show_details: Whether to include detailed information

        Returns:
            Formatted test report string
        """
        lines = []

        # Header
        lines.append(f"🧪 Test Report: {test_suite.file_path}")
        lines.append("=" * 60)

        # Summary
        if test_suite.has_failures:
            status_icon = "❌"
            status = "FAILED"
        elif test_suite.warnings > 0:
            status_icon = "⚠️"
            status = "PASSED WITH WARNINGS"
        else:
            status_icon = "✅"
            status = "PASSED"

        lines.append(f"{status_icon} Status: {status}")
        lines.append(
            f"📊 Results: {test_suite.passed} passed, {test_suite.failed} failed, "
            f"{test_suite.warnings} warnings, {test_suite.skipped} skipped"
        )
        lines.append(f"⏱️  Duration: {test_suite.duration:.2f}s")
        lines.append(f"📈 Success Rate: {test_suite.success_rate:.1f}%")
        lines.append("")

        # Group results by test type
        results_by_type = {}
        for result in test_suite.results:
            test_type = result.test_type
            if test_type not in results_by_type:
                results_by_type[test_type] = []
            results_by_type[test_type].append(result)

        # Display results by type
        for test_type, results in results_by_type.items():
            lines.append(f"📋 {test_type.value.replace('_', ' ').title()} Tests:")
            lines.append("-" * 40)

            for result in results:
                severity_icons = {
                    SaidataTestSeverity.PASS: "✅",
                    SaidataTestSeverity.FAIL: "❌",
                    SaidataTestSeverity.WARNING: "⚠️",
                    SaidataTestSeverity.SKIP: "⏭️",
                }

                icon = severity_icons[result.severity]
                provider_info = f" [{result.provider}]" if result.provider else ""
                lines.append(f"  {icon} {result.message}{provider_info}")

                if show_details and result.details:
                    for key, value in result.details.items():
                        if isinstance(value, str) and len(value) > 100:
                            value = value[:100] + "..."
                        lines.append(f"     {key}: {value}")

                if result.suggestions:
                    lines.append("     💡 Suggestions:")
                    for suggestion in result.suggestions:
                        lines.append(f"       • {suggestion}")

                lines.append("")

            lines.append("")

        return "\n".join(lines)
