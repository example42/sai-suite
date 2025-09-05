"""Tests for saigen test CLI command."""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import yaml
from click.testing import CliRunner

from saigen.cli.commands.test import test
from saigen.core.tester import SaidataTestSuite, SaidataTestResult, SaidataTestType, SaidataTestSeverity
from saigen.models.saidata import SaiData, Metadata, ProviderConfig, Package


@pytest.fixture
def sample_saidata_file(tmp_path):
    """Create a temporary saidata YAML file."""
    saidata = {
        "version": "0.2",
        "metadata": {
            "name": "test-software",
            "display_name": "Test Software",
            "description": "A test software package"
        },
        "providers": {
            "apt": {
                "packages": [
                    {"name": "test-package", "version": "1.0.0"}
                ]
            }
        }
    }
    
    file_path = tmp_path / "test-software.yaml"
    with open(file_path, 'w') as f:
        yaml.dump(saidata, f)
    
    return file_path


@pytest.fixture
def mock_test_suite():
    """Create a mock test suite for testing."""
    return SaidataTestSuite(
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
                message="Package test-package dry-run successful",
                provider="apt",
                details={"package": "test-package"}
            ),
            SaidataTestResult(
                test_type=SaidataTestType.PROVIDER_COMPATIBILITY,
                severity=SaidataTestSeverity.PASS,
                message="Provider apt compatible with linux",
                provider="apt"
            ),
            SaidataTestResult(
                test_type=SaidataTestType.PACKAGE_AVAILABILITY,
                severity=SaidataTestSeverity.FAIL,
                message="Package test-package not available in apt",
                provider="apt",
                suggestions=["Check package name spelling"]
            )
        ],
        duration=1.5
    )


class TestTestCommand:
    """Test the saigen test CLI command."""
    
    def test_test_command_success(self, sample_saidata_file, mock_test_suite):
        """Test successful test command execution."""
        runner = CliRunner()
        
        with patch('saigen.core.tester.SaidataTester') as mock_tester_class:
            mock_tester = Mock()
            mock_tester_class.return_value = mock_tester
            mock_tester.format_test_report = Mock(return_value="🧪 Test Report:\nStatus: FAILED")
            
            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.return_value = mock_test_suite
                
                result = runner.invoke(test, [str(sample_saidata_file)])
                
                assert result.exit_code == 1  # Has failures
                assert "🧪 Test Report:" in result.output
                assert "Status: FAILED" in result.output
    
    def test_test_command_with_providers(self, sample_saidata_file, mock_test_suite):
        """Test test command with specific providers."""
        runner = CliRunner()
        
        with patch('saigen.core.tester.SaidataTester') as mock_tester_class:
            mock_tester = Mock()
            mock_tester_class.return_value = mock_tester
            mock_tester.format_test_report = Mock(return_value="Test report")
            
            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.return_value = mock_test_suite
                
                result = runner.invoke(test, [
                    str(sample_saidata_file),
                    '--providers', 'apt',
                    '--providers', 'brew'
                ])
                
                assert result.exit_code == 1
                assert "Testing providers: apt, brew" in result.output
    
    def test_test_command_with_test_types(self, sample_saidata_file, mock_test_suite):
        """Test test command with specific test types."""
        runner = CliRunner()
        
        with patch('saigen.core.tester.SaidataTester') as mock_tester_class:
            mock_tester = Mock()
            mock_tester_class.return_value = mock_tester
            mock_tester.format_test_report = Mock(return_value="Test report")
            
            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.return_value = mock_test_suite
                
                result = runner.invoke(test, [
                    str(sample_saidata_file),
                    '--test-types', 'dry_run',
                    '--test-types', 'provider_compatibility'
                ])
                
                assert result.exit_code == 1
                assert "Running test types: dry_run, provider_compatibility" in result.output
    
    def test_test_command_json_output(self, sample_saidata_file, mock_test_suite):
        """Test test command with JSON output format."""
        runner = CliRunner()
        
        with patch('saigen.core.tester.SaidataTester') as mock_tester_class:
            mock_tester = Mock()
            mock_tester_class.return_value = mock_tester
            
            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.return_value = mock_test_suite
                
                result = runner.invoke(test, [
                    str(sample_saidata_file),
                    '--format', 'json'
                ])
                
                assert result.exit_code == 1
                
                # Parse JSON output
                output_data = json.loads(result.output)
                assert output_data['file_path'] == "test.yaml"
                assert output_data['summary']['total_tests'] == 3
                assert output_data['summary']['passed'] == 2
                assert output_data['summary']['failed'] == 1
                assert len(output_data['results']) == 3
    
    def test_test_command_show_details(self, sample_saidata_file, mock_test_suite):
        """Test test command with detailed output."""
        runner = CliRunner()
        
        with patch('saigen.core.tester.SaidataTester') as mock_tester_class:
            mock_tester = Mock()
            mock_tester_class.return_value = mock_tester
            mock_tester.format_test_report = Mock(return_value="Detailed test report")
            
            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.return_value = mock_test_suite
                
                result = runner.invoke(test, [
                    str(sample_saidata_file),
                    '--show-details'
                ])
                
                assert result.exit_code == 1
                # Just check that the command ran and produced output
                assert "Test Report:" in result.output
                # The detailed output should be present
                assert len(result.output) > 100
    
    def test_test_command_no_dry_run_with_confirmation(self, sample_saidata_file, mock_test_suite):
        """Test test command with dry-run disabled and user confirmation."""
        runner = CliRunner()
        
        with patch('saigen.core.tester.SaidataTester') as mock_tester_class:
            mock_tester = Mock()
            mock_tester_class.return_value = mock_tester
            mock_tester.format_test_report = Mock(return_value="Test report")
            
            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.return_value = mock_test_suite
                
                result = runner.invoke(test, [
                    str(sample_saidata_file),
                    '--no-dry-run'
                ], input='y\n')
                
                assert result.exit_code == 1
                assert "WARNING: Dry-run mode disabled" in result.output
                assert "Do you want to continue?" in result.output
    
    def test_test_command_no_dry_run_without_confirmation(self, sample_saidata_file):
        """Test test command with dry-run disabled and user declining."""
        runner = CliRunner()
        
        result = runner.invoke(test, [
            str(sample_saidata_file),
            '--no-dry-run'
        ], input='n\n', obj={})
        
        assert result.exit_code == 0
        assert "WARNING: Dry-run mode disabled" in result.output
        assert "Do you want to continue?" in result.output
    
    def test_test_command_timeout(self, sample_saidata_file):
        """Test test command with timeout."""
        runner = CliRunner()
        
        with patch('saigen.core.tester.SaidataTester') as mock_tester_class:
            mock_tester = Mock()
            mock_tester_class.return_value = mock_tester
            
            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.side_effect = TimeoutError("Test timed out")
                
                result = runner.invoke(test, [
                    str(sample_saidata_file),
                    '--timeout', '10'
                ])
                
                assert result.exit_code == 1
                assert "timed out" in result.output
    
    def test_test_command_file_not_found(self):
        """Test test command with non-existent file."""
        runner = CliRunner()
        
        result = runner.invoke(test, ['nonexistent.yaml'])
        
        assert result.exit_code == 2  # Click's exit code for bad parameter
    
    def test_test_command_warnings_only(self, sample_saidata_file):
        """Test test command with warnings only (no failures)."""
        runner = CliRunner()
        
        warning_suite = SaidataTestSuite(
            file_path="test.yaml",
            total_tests=2,
            passed=1,
            failed=0,
            warnings=1,
            skipped=0,
            results=[
                SaidataTestResult(
                    test_type=SaidataTestType.DRY_RUN,
                    severity=SaidataTestSeverity.PASS,
                    message="Test passed"
                ),
                SaidataTestResult(
                    test_type=SaidataTestType.PROVIDER_COMPATIBILITY,
                    severity=SaidataTestSeverity.WARNING,
                    message="Warning message"
                )
            ],
            duration=1.0
        )
        
        with patch('saigen.core.tester.SaidataTester') as mock_tester_class:
            mock_tester = Mock()
            mock_tester_class.return_value = mock_tester
            mock_tester.format_test_report = Mock(return_value="Test report")
            
            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.return_value = warning_suite
                
                result = runner.invoke(test, [str(sample_saidata_file)])
                
                assert result.exit_code == 2  # Exit code 2 for warnings
                assert "PASSED WITH WARNINGS" in result.output
    
    def test_test_command_all_passed(self, sample_saidata_file):
        """Test test command with all tests passing."""
        runner = CliRunner()
        
        success_suite = SaidataTestSuite(
            file_path="test.yaml",
            total_tests=2,
            passed=2,
            failed=0,
            warnings=0,
            skipped=0,
            results=[
                SaidataTestResult(
                    test_type=SaidataTestType.DRY_RUN,
                    severity=SaidataTestSeverity.PASS,
                    message="Test passed"
                ),
                SaidataTestResult(
                    test_type=SaidataTestType.PROVIDER_COMPATIBILITY,
                    severity=SaidataTestSeverity.PASS,
                    message="Compatible"
                )
            ],
            duration=1.0
        )
        
        with patch('saigen.core.tester.SaidataTester') as mock_tester_class:
            mock_tester = Mock()
            mock_tester_class.return_value = mock_tester
            mock_tester.format_test_report = Mock(return_value="Test report")
            
            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.return_value = success_suite
                
                result = runner.invoke(test, [str(sample_saidata_file)])
                
                assert result.exit_code == 0  # Success
    
    def test_test_command_verbose_error(self, sample_saidata_file):
        """Test test command with verbose error output."""
        runner = CliRunner()
        
        # Test with a non-existent file to trigger an error
        result = runner.invoke(test, ['nonexistent.yaml'], 
                             obj={'verbose': True})
        
        assert result.exit_code == 2  # Click's exit code for bad parameter
        # The command should handle the error gracefully
    
    def test_test_command_custom_timeout(self, sample_saidata_file, mock_test_suite):
        """Test test command with custom timeout."""
        runner = CliRunner()
        
        with patch('saigen.core.tester.SaidataTester') as mock_tester_class:
            mock_tester = Mock()
            mock_tester_class.return_value = mock_tester
            mock_tester.format_test_report = Mock(return_value="Test report")
            
            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.return_value = mock_test_suite
                
                result = runner.invoke(test, [
                    str(sample_saidata_file),
                    '--timeout', '60'
                ])
                
                assert result.exit_code == 1
                assert "Timeout: 60s" in result.output


if __name__ == '__main__':
    pytest.main([__file__])