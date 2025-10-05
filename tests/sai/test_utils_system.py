"""Tests for system utilities."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from sai.utils.system import (
    is_executable_available,
    get_executable_path,
    get_executable_version,
    check_executable_functionality,
    is_platform_supported,
    get_platform,
    get_system_info
)


class TestExecutableUtils:
    """Test executable-related utilities."""
    
    @patch('sai.utils.system.shutil.which')
    def test_is_executable_available_found(self, mock_which):
        """Test executable availability check when found."""
        mock_which.return_value = "/usr/bin/test-cmd"
        
        result = is_executable_available("test-cmd")
        
        assert result is True
        mock_which.assert_called_once_with("test-cmd")
    
    @patch('sai.utils.system.shutil.which')
    def test_is_executable_available_not_found(self, mock_which):
        """Test executable availability check when not found."""
        mock_which.return_value = None
        
        result = is_executable_available("nonexistent-cmd")
        
        assert result is False
        mock_which.assert_called_once_with("nonexistent-cmd")
    
    @patch('sai.utils.system.shutil.which')
    def test_get_executable_path_found(self, mock_which):
        """Test getting executable path when found."""
        expected_path = "/usr/bin/test-cmd"
        mock_which.return_value = expected_path
        
        result = get_executable_path("test-cmd")
        
        assert result == expected_path
        mock_which.assert_called_once_with("test-cmd")
    
    @patch('sai.utils.system.shutil.which')
    def test_get_executable_path_not_found(self, mock_which):
        """Test getting executable path when not found."""
        mock_which.return_value = None
        
        result = get_executable_path("nonexistent-cmd")
        
        assert result is None
        mock_which.assert_called_once_with("nonexistent-cmd")
    
    @patch('sai.utils.system.subprocess.run')
    def test_get_executable_version_success(self, mock_run):
        """Test getting executable version successfully."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test-cmd version 1.2.3\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        # Mock is_executable_available to return True
        with patch('sai.utils.system.is_executable_available', return_value=True):
            result = get_executable_version("test-cmd", ["--version"])
        
        assert result == "test-cmd version 1.2.3"
        mock_run.assert_called_once_with(
            ["test-cmd", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False
        )
    
    @patch('sai.utils.system.subprocess.run')
    def test_get_executable_version_failure(self, mock_run):
        """Test getting executable version when command fails."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Command not found"
        mock_run.return_value = mock_result
        
        result = get_executable_version("test-cmd", ["--version"])
        
        assert result is None
    
    @patch('sai.utils.system.subprocess.run')
    def test_get_executable_version_timeout(self, mock_run):
        """Test getting executable version with timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(["test-cmd"], 10)
        
        result = get_executable_version("test-cmd", ["--version"])
        
        assert result is None
    
    @patch('sai.utils.system.subprocess.run')
    def test_check_executable_functionality_success(self, mock_run):
        """Test checking executable functionality successfully."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "OK"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        # Mock is_executable_available to return True
        with patch('sai.utils.system.is_executable_available', return_value=True):
            result = check_executable_functionality("test-cmd", ["test-cmd", "--help"])
        
        assert result is True
        # Check that subprocess.run was called with the expected command
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["test-cmd", "--help"]
        assert call_args[1]['capture_output'] is True
        assert call_args[1]['text'] is True
        assert call_args[1]['timeout'] == 30
    
    @patch('sai.utils.system.subprocess.run')
    def test_check_executable_functionality_failure(self, mock_run):
        """Test checking executable functionality when it fails."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        
        result = check_executable_functionality("test-cmd", ["--help"])
        
        assert result is False
    
    @patch('sai.utils.system.subprocess.run')
    def test_check_executable_functionality_exception(self, mock_run):
        """Test checking executable functionality with exception."""
        mock_run.side_effect = FileNotFoundError("Command not found")
        
        result = check_executable_functionality("test-cmd", ["--help"])
        
        assert result is False


class TestPlatformUtils:
    """Test platform-related utilities."""
    
    @patch('sai.utils.system.platform.system')
    def test_get_platform_linux(self, mock_system):
        """Test getting current platform on Linux."""
        mock_system.return_value = "Linux"
        
        result = get_platform()
        
        assert result == "linux"
    
    @patch('sai.utils.system.platform.system')
    def test_get_platform_darwin(self, mock_system):
        """Test getting current platform on macOS."""
        mock_system.return_value = "Darwin"
        
        result = get_platform()
        
        assert result == "darwin"
    
    @patch('sai.utils.system.platform.system')
    def test_get_platform_windows(self, mock_system):
        """Test getting current platform on Windows."""
        mock_system.return_value = "Windows"
        
        result = get_platform()
        
        assert result == "windows"
    
    @patch('sai.utils.system.platform.system')
    def test_get_platform_unknown(self, mock_system):
        """Test getting current platform for unknown system."""
        mock_system.return_value = "UnknownOS"
        
        result = get_platform()
        
        assert result == "unknownos"
    
    @patch('sai.utils.system.get_platform')
    def test_is_platform_supported_single_match(self, mock_get_platform):
        """Test platform support check with single matching platform."""
        mock_get_platform.return_value = "linux"
        
        result = is_platform_supported(["linux", "darwin"])
        
        assert result is True
    
    @patch('sai.utils.system.get_platform')
    def test_is_platform_supported_no_match(self, mock_get_platform):
        """Test platform support check with no matching platform."""
        mock_get_platform.return_value = "windows"
        
        result = is_platform_supported(["linux", "darwin"])
        
        assert result is False
    
    @patch('sai.utils.system.get_platform')
    def test_is_platform_supported_empty_list(self, mock_get_platform):
        """Test platform support check with empty platform list."""
        mock_get_platform.return_value = "linux"
        
        result = is_platform_supported([])
        
        # Empty list should mean all platforms are supported
        assert result is True
    
    @patch('sai.utils.system.get_platform')
    def test_is_platform_supported_none(self, mock_get_platform):
        """Test platform support check with None platform list."""
        mock_get_platform.return_value = "linux"
        
        result = is_platform_supported(None)
        
        # None should mean all platforms are supported
        assert result is True


class TestSystemInfo:
    """Test system information utilities."""
    
    @patch('sai.utils.system.platform.system')
    @patch('sai.utils.system.platform.release')
    @patch('sai.utils.system.platform.machine')
    def test_get_system_info(self, mock_machine, mock_release, mock_system):
        """Test getting system information."""
        mock_system.return_value = "Linux"
        mock_release.return_value = "5.4.0"
        mock_machine.return_value = "x86_64"
        
        result = get_system_info()
        
        assert result['platform'] == "linux"
        assert result['system'] == "Linux"
        assert result['release'] == "5.4.0"
        assert result['machine'] == "x86_64"
    



class TestSystemUtilsIntegration:
    """Integration tests for system utilities."""
    
    def test_real_executable_check(self):
        """Test with real system executables."""
        # Test with a command that should exist on most systems
        common_commands = ['ls', 'echo', 'cat'] if not Path('/').exists() else ['dir', 'echo']
        
        for cmd in common_commands:
            if is_executable_available(cmd):
                path = get_executable_path(cmd)
                assert path is not None
                assert Path(path).exists()
                break
    
    def test_platform_detection(self):
        """Test actual platform detection."""
        platform = get_platform()
        
        # Should be one of the known platforms
        assert platform in ['linux', 'darwin', 'windows'] or len(platform) > 0
    
    def test_system_info_structure(self):
        """Test system info returns expected structure."""
        info = get_system_info()
        
        required_keys = ['platform', 'system', 'release', 'machine']
        for key in required_keys:
            assert key in info
            assert info[key] is not None


if __name__ == "__main__":
    pytest.main([__file__])