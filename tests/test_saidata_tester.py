"""Tests for saidata testing functionality."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import yaml

from saigen.core.tester import (
    SaidataTester, SaidataTestResult, SaidataTestSuite, SaidataTestType, SaidataTestSeverity,
    MCPServerClient
)
from saigen.models.saidata import SaiData, Metadata, ProviderConfig, Package
from saigen.models.config import SaigenConfig


@pytest.fixture
def sample_saidata():
    """Create a sample SaiData object for testing."""
    return SaiData(
        version="0.2",
        metadata=Metadata(
            name="test-software",
            display_name="Test Software",
            description="A test software package"
        ),
        providers={
            "apt": ProviderConfig(
                packages=[
                    Package(name="test-package", version="1.0.0")
                ]
            ),
            "brew": ProviderConfig(
                packages=[
                    Package(name="test-formula")
                ]
            )
        }
    )


@pytest.fixture
def sample_saidata_file(sample_saidata, tmp_path):
    """Create a temporary saidata YAML file."""
    file_path = tmp_path / "test-software.yaml"
    
    # Convert to dict and write to file
    data = sample_saidata.model_dump(exclude_none=True)
    
    with open(file_path, 'w') as f:
        yaml.dump(data, f)
    
    return file_path


@pytest.fixture
def tester():
    """Create a SaidataTester instance."""
    config = SaigenConfig()
    return SaidataTester(config)


class TestMCPServerClient:
    """Test MCP server client functionality."""
    
    def test_init(self):
        """Test MCP client initialization."""
        client = MCPServerClient()
        assert client.server_config == {}
        
        config = {"enabled": True, "url": "http://localhost:8080"}
        client = MCPServerClient(config)
        assert client.server_config == config
    
    @pytest.mark.asyncio
    async def test_is_available_disabled(self):
        """Test MCP server availability check when disabled."""
        client = MCPServerClient({"enabled": False})
        assert not await client.is_available()
    
    @pytest.mark.asyncio
    async def test_is_available_enabled(self):
        """Test MCP server availability check when enabled."""
        client = MCPServerClient({"enabled": True})
        assert await client.is_available()
    
    @pytest.mark.asyncio
    async def test_test_saidata_unavailable(self, sample_saidata):
        """Test saidata testing when MCP server is unavailable."""
        client = MCPServerClient({"enabled": False})
        results = await client.test_saidata(sample_saidata, ["apt"])
        
        assert len(results) == 1
        assert results[0].test_type == SaidataTestType.MCP_SERVER
        assert results[0].severity == SaidataTestSeverity.SKIP
        assert "not available" in results[0].message
    
    @pytest.mark.asyncio
    async def test_test_saidata_available(self, sample_saidata):
        """Test saidata testing when MCP server is available."""
        client = MCPServerClient({"enabled": True})
        results = await client.test_saidata(sample_saidata, ["apt", "dnf"])
        
        # Should have results for apt (exists) and dnf (doesn't exist)
        assert len(results) == 2
        
        apt_result = next(r for r in results if r.provider == "apt")
        assert apt_result.severity == SaidataTestSeverity.PASS
        
        dnf_result = next(r for r in results if r.provider == "dnf")
        assert dnf_result.severity == SaidataTestSeverity.SKIP


class TestSaidataTester:
    """Test SaidataTester functionality."""
    
    def test_init(self):
        """Test tester initialization."""
        tester = SaidataTester()
        assert tester.config is None
        assert tester.validator is not None
        assert tester.mcp_client is not None
        
        config = SaigenConfig()
        tester = SaidataTester(config)
        assert tester.config == config
    
    @pytest.mark.asyncio
    async def test_test_file_success(self, tester, sample_saidata_file):
        """Test successful file testing."""
        with patch.object(tester, '_test_dry_run', new_callable=AsyncMock) as mock_dry_run:
            mock_dry_run.return_value = [
                SaidataTestResult(
                    test_type=SaidataTestType.DRY_RUN,
                    severity=SaidataTestSeverity.PASS,
                    message="Test passed"
                )
            ]
            
            with patch.object(tester, '_test_provider_compatibility', new_callable=AsyncMock) as mock_compat:
                mock_compat.return_value = [
                    SaidataTestResult(
                        test_type=SaidataTestType.PROVIDER_COMPATIBILITY,
                        severity=SaidataTestSeverity.PASS,
                        message="Compatible"
                    )
                ]
                
                result = await tester.test_file(sample_saidata_file, providers=["apt"])
                
                assert isinstance(result, SaidataTestSuite)
                assert result.total_tests >= 2
                assert result.passed >= 2
                assert result.failed == 0
                assert not result.has_failures
    
    @pytest.mark.asyncio
    async def test_test_file_invalid_yaml(self, tester, tmp_path):
        """Test file testing with invalid YAML."""
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: content: [")
        
        result = await tester.test_file(invalid_file)
        
        assert isinstance(result, SaidataTestSuite)
        assert result.total_tests == 1
        assert result.failed == 1
        assert result.has_failures
    
    @pytest.mark.asyncio
    async def test_test_package_dry_run_success(self, tester):
        """Test successful package dry-run."""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock successful process
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"Package available", b""))
            mock_subprocess.return_value = mock_process
            
            result = await tester._test_package_dry_run("apt", "test-package")
            
            assert result.test_type == SaidataTestType.DRY_RUN
            assert result.severity == SaidataTestSeverity.PASS
            assert "test-package" in result.message
    
    @pytest.mark.asyncio
    async def test_test_package_dry_run_failure(self, tester):
        """Test failed package dry-run."""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock failed process
            mock_process = Mock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(b"", b"Package not found"))
            mock_subprocess.return_value = mock_process
            
            result = await tester._test_package_dry_run("apt", "nonexistent-package")
            
            assert result.test_type == SaidataTestType.DRY_RUN
            assert result.severity == SaidataTestSeverity.FAIL
            assert "nonexistent-package" in result.message
            assert result.suggestions is not None
    
    @pytest.mark.asyncio
    async def test_test_package_dry_run_unsupported_provider(self, tester):
        """Test package dry-run with unsupported provider."""
        result = await tester._test_package_dry_run("unsupported", "test-package")
        
        assert result.test_type == SaidataTestType.DRY_RUN
        assert result.severity == SaidataTestSeverity.SKIP
        assert "not supported" in result.message
    
    @pytest.mark.asyncio
    async def test_test_package_dry_run_timeout(self, tester):
        """Test package dry-run timeout."""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock process that times out
            mock_process = Mock()
            mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_subprocess.return_value = mock_process
            
            result = await tester._test_package_dry_run("apt", "test-package")
            
            assert result.test_type == SaidataTestType.DRY_RUN
            assert result.severity == SaidataTestSeverity.FAIL
            assert "timed out" in result.message
    
    @pytest.mark.asyncio
    async def test_test_package_dry_run_command_not_found(self, tester):
        """Test package dry-run when command is not found."""
        with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError()):
            result = await tester._test_package_dry_run("apt", "test-package")
            
            assert result.test_type == SaidataTestType.DRY_RUN
            assert result.severity == SaidataTestSeverity.SKIP
            assert "not available" in result.message
    
    def test_check_provider_platform_compatibility_compatible(self, tester):
        """Test provider platform compatibility check - compatible."""
        result = tester._check_provider_platform_compatibility("apt", "linux", "x86_64")
        
        assert result.test_type == SaidataTestType.PROVIDER_COMPATIBILITY
        assert result.severity == SaidataTestSeverity.PASS
        assert "compatible" in result.message
    
    def test_check_provider_platform_compatibility_incompatible(self, tester):
        """Test provider platform compatibility check - incompatible."""
        result = tester._check_provider_platform_compatibility("apt", "windows", "x86_64")
        
        assert result.test_type == SaidataTestType.PROVIDER_COMPATIBILITY
        assert result.severity == SaidataTestSeverity.FAIL
        assert "not compatible" in result.message
        assert result.suggestions is not None
    
    def test_check_provider_platform_compatibility_unknown(self, tester):
        """Test provider platform compatibility check - unknown provider."""
        result = tester._check_provider_platform_compatibility("unknown", "linux", "x86_64")
        
        assert result.test_type == SaidataTestType.PROVIDER_COMPATIBILITY
        assert result.severity == SaidataTestSeverity.WARNING
        assert "Unknown provider" in result.message
    
    @pytest.mark.asyncio
    async def test_check_command_availability_found(self, tester):
        """Test command availability check - command found."""
        with patch('shutil.which', return_value='/usr/bin/test-command'):
            result = await tester._check_command_availability("test-command", None)
            
            assert result.test_type == SaidataTestType.COMMAND_VALIDATION
            assert result.severity == SaidataTestSeverity.PASS
            assert "found at" in result.message
    
    @pytest.mark.asyncio
    async def test_check_command_availability_not_found(self, tester):
        """Test command availability check - command not found."""
        with patch('shutil.which', return_value=None):
            result = await tester._check_command_availability("nonexistent-command", None)
            
            assert result.test_type == SaidataTestType.COMMAND_VALIDATION
            assert result.severity == SaidataTestSeverity.FAIL
            assert "not found" in result.message
            assert result.suggestions is not None
    
    def test_format_test_report(self, tester):
        """Test test report formatting."""
        test_suite = SaidataTestSuite(
            file_path="test.yaml",
            total_tests=3,
            passed=2,
            failed=1,
            warnings=0,
            skipped=0,
            results=[
                SaidataTestResult(
                    test_type=SaidataTestType.DRY_RUN,
                    severity=SaidataTestSeverity.PASS,
                    message="Test passed",
                    provider="apt"
                ),
                SaidataTestResult(
                    test_type=SaidataTestType.DRY_RUN,
                    severity=SaidataTestSeverity.PASS,
                    message="Another test passed",
                    provider="brew"
                ),
                SaidataTestResult(
                    test_type=SaidataTestType.PROVIDER_COMPATIBILITY,
                    severity=SaidataTestSeverity.FAIL,
                    message="Test failed",
                    suggestions=["Fix this issue"]
                )
            ],
            duration=1.5
        )
        
        report = tester.format_test_report(test_suite)
        
        assert "Test Report: test.yaml" in report
        assert "FAILED" in report
        assert "2 passed, 1 failed" in report
        assert "1.50s" in report
        assert "66.7%" in report  # Success rate
        assert "Test passed [apt]" in report
        assert "Fix this issue" in report


class TestSaidataTestResult:
    """Test SaidataTestResult data class."""
    
    def test_creation(self):
        """Test SaidataTestResult creation."""
        result = SaidataTestResult(
            test_type=SaidataTestType.DRY_RUN,
            severity=SaidataTestSeverity.PASS,
            message="Test message"
        )
        
        assert result.test_type == SaidataTestType.DRY_RUN
        assert result.severity == SaidataTestSeverity.PASS
        assert result.message == "Test message"
        assert result.details is None
        assert result.provider is None
        assert result.duration is None
        assert result.suggestions is None


class TestSaidataTestSuite:
    """Test SaidataTestSuite data class."""
    
    def test_creation(self):
        """Test SaidataTestSuite creation."""
        results = [
            SaidataTestResult(SaidataTestType.DRY_RUN, SaidataTestSeverity.PASS, "Pass"),
            SaidataTestResult(SaidataTestType.DRY_RUN, SaidataTestSeverity.FAIL, "Fail"),
            SaidataTestResult(SaidataTestType.DRY_RUN, SaidataTestSeverity.WARNING, "Warning"),
            SaidataTestResult(SaidataTestType.DRY_RUN, SaidataTestSeverity.SKIP, "Skip")
        ]
        
        suite = SaidataTestSuite(
            file_path="test.yaml",
            total_tests=4,
            passed=1,
            failed=1,
            warnings=1,
            skipped=1,
            results=results,
            duration=2.0
        )
        
        assert suite.file_path == "test.yaml"
        assert suite.total_tests == 4
        assert suite.success_rate == 25.0  # 1/4 * 100
        assert suite.has_failures is True
        assert len(suite.results) == 4
    
    def test_success_rate_no_tests(self):
        """Test success rate calculation with no tests."""
        suite = SaidataTestSuite(
            file_path="test.yaml",
            total_tests=0,
            passed=0,
            failed=0,
            warnings=0,
            skipped=0,
            results=[],
            duration=0.0
        )
        
        assert suite.success_rate == 0.0
        assert suite.has_failures is False
    
    def test_success_rate_all_passed(self):
        """Test success rate calculation with all tests passed."""
        suite = SaidataTestSuite(
            file_path="test.yaml",
            total_tests=3,
            passed=3,
            failed=0,
            warnings=0,
            skipped=0,
            results=[],
            duration=1.0
        )
        
        assert suite.success_rate == 100.0
        assert suite.has_failures is False


if __name__ == '__main__':
    pytest.main([__file__])