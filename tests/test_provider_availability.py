"""Tests for provider availability detection."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from sai.providers.base import BaseProvider, ProviderFactory
from sai.providers.loader import ProviderLoader
from sai.models.provider_data import ProviderData, Provider, Action, ProviderType
from sai.utils.system import (
    is_executable_available,
    get_executable_path,
    get_executable_version,
    check_executable_functionality,
    is_platform_supported
)


class TestSystemUtils:
    """Test system utility functions."""
    
    @patch('shutil.which')
    def test_is_executable_available_found(self, mock_which):
        """Test executable detection when executable is found."""
        mock_which.return_value = '/usr/bin/test-executable'
        
        result = is_executable_available('test-executable')
        
        assert result is True
        mock_which.assert_called_once_with('test-executable')
    
    @patch('shutil.which')
    def test_is_executable_available_not_found(self, mock_which):
        """Test executable detection when executable is not found."""
        mock_which.return_value = None
        
        result = is_executable_available('nonexistent-executable')
        
        assert result is False
        mock_which.assert_called_once_with('nonexistent-executable')
    
    @patch('shutil.which')
    def test_get_executable_path(self, mock_which):
        """Test getting executable path."""
        expected_path = '/usr/bin/test-executable'
        mock_which.return_value = expected_path
        
        result = get_executable_path('test-executable')
        
        assert result == expected_path
        mock_which.assert_called_once_with('test-executable')
    
    @patch('subprocess.run')
    @patch('sai.utils.system.is_executable_available')
    def test_get_executable_version(self, mock_is_available, mock_run):
        """Test getting executable version."""
        mock_is_available.return_value = True
        mock_result = Mock()
        mock_result.stdout = 'test-executable version 1.2.3\n'
        mock_result.stderr = ''
        mock_run.return_value = mock_result
        
        result = get_executable_version('test-executable')
        
        assert result == 'test-executable version 1.2.3'
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    @patch('sai.utils.system.is_executable_available')
    def test_check_executable_functionality_success(self, mock_is_available, mock_run):
        """Test executable functionality test success."""
        mock_is_available.return_value = True
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = check_executable_functionality('test-executable', ['test-executable', '--help'])
        
        assert result is True
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    @patch('sai.utils.system.is_executable_available')
    def test_check_executable_functionality_failure(self, mock_is_available, mock_run):
        """Test executable functionality test failure."""
        mock_is_available.return_value = True
        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        
        result = check_executable_functionality('test-executable', ['test-executable', '--help'])
        
        assert result is False
        mock_run.assert_called_once()
    
    @patch('sai.utils.system.get_platform')
    def test_is_platform_supported_exact_match(self, mock_get_platform):
        """Test platform support with exact match."""
        mock_get_platform.return_value = 'linux'
        
        result = is_platform_supported(['linux', 'darwin'])
        
        assert result is True
    
    @patch('sai.utils.system.get_platform')
    def test_is_platform_supported_alias_match(self, mock_get_platform):
        """Test platform support with alias match."""
        mock_get_platform.return_value = 'darwin'
        
        result = is_platform_supported(['macos', 'linux'])
        
        assert result is True
    
    @patch('sai.utils.system.get_platform')
    def test_is_platform_supported_no_match(self, mock_get_platform):
        """Test platform support with no match."""
        mock_get_platform.return_value = 'windows'
        
        result = is_platform_supported(['linux', 'darwin'])
        
        assert result is False


class TestBaseProviderAvailability:
    """Test BaseProvider availability detection."""
    
    def create_test_provider(self, name='test-provider', executable='test-exec'):
        """Create a test provider for testing."""
        provider_data = ProviderData(
            version='0.1',
            provider=Provider(
                name=name,
                display_name=f'Test {name}',
                description='Test provider',
                type=ProviderType.PACKAGE_MANAGER,
                platforms=['linux', 'darwin'],
                capabilities=['install', 'uninstall']
            ),
            actions={
                'install': Action(
                    description='Install packages',
                    command=f'{executable} install',
                    timeout=300
                )
            }
        )
        return BaseProvider(provider_data)
    
    @patch('sai.providers.base.is_platform_supported')
    @patch('sai.providers.base.is_executable_available')
    def test_is_available_success(self, mock_exec_available, mock_platform_supported):
        """Test provider availability when all checks pass."""
        mock_platform_supported.return_value = True
        mock_exec_available.return_value = True
        
        provider = self.create_test_provider()
        
        result = provider.is_available(use_cache=False)
        
        assert result is True
        mock_platform_supported.assert_called_once_with(['linux', 'darwin'])
        mock_exec_available.assert_called_once_with('test-exec')
    
    @patch('sai.providers.base.is_platform_supported')
    def test_is_available_platform_not_supported(self, mock_platform_supported):
        """Test provider availability when platform is not supported."""
        mock_platform_supported.return_value = False
        
        provider = self.create_test_provider()
        
        result = provider.is_available(use_cache=False)
        
        assert result is False
        mock_platform_supported.assert_called_once_with(['linux', 'darwin'])
    
    @patch('sai.providers.base.is_platform_supported')
    @patch('sai.providers.base.is_executable_available')
    def test_is_available_executable_not_found(self, mock_exec_available, mock_platform_supported):
        """Test provider availability when executable is not found."""
        mock_platform_supported.return_value = True
        mock_exec_available.return_value = False
        
        provider = self.create_test_provider()
        
        result = provider.is_available(use_cache=False)
        
        assert result is False
        mock_exec_available.assert_called_once_with('test-exec')
    
    @patch('sai.providers.base.get_executable_path')
    def test_get_executable_path(self, mock_get_path):
        """Test getting provider executable path."""
        expected_path = '/usr/bin/test-exec'
        mock_get_path.return_value = expected_path
        
        provider = self.create_test_provider()
        
        result = provider.get_executable_path()
        
        assert result == expected_path
        mock_get_path.assert_called_once_with('test-exec')
    
    @patch('sai.providers.base.get_executable_version')
    def test_get_version(self, mock_get_version):
        """Test getting provider version."""
        expected_version = 'test-exec version 1.0.0'
        mock_get_version.return_value = expected_version
        
        provider = self.create_test_provider()
        
        result = provider.get_version()
        
        assert result == expected_version
        mock_get_version.assert_called_once_with('test-exec')


class TestProviderFactory:
    """Test ProviderFactory availability detection."""
    
    @patch('sai.providers.base.ProviderFactory.create_providers')
    def test_create_available_providers(self, mock_create_providers):
        """Test creating only available providers."""
        # Create mock providers
        available_provider = Mock()
        available_provider.is_available.return_value = True
        available_provider.name = 'available-provider'
        
        unavailable_provider = Mock()
        unavailable_provider.is_available.return_value = False
        unavailable_provider.name = 'unavailable-provider'
        
        mock_create_providers.return_value = [available_provider, unavailable_provider]
        
        factory = ProviderFactory(Mock())
        result = factory.create_available_providers()
        
        assert len(result) == 1
        assert result[0] == available_provider
        available_provider.is_available.assert_called_once()
        unavailable_provider.is_available.assert_called_once()
    
    @patch('sai.providers.base.ProviderFactory.create_providers')
    def test_detect_providers(self, mock_create_providers):
        """Test provider detection with detailed information."""
        # Create mock provider
        mock_provider = Mock()
        mock_provider.name = 'test-provider'
        mock_provider.display_name = 'Test Provider'
        mock_provider.description = 'Test description'
        mock_provider.type = 'package_manager'
        mock_provider.platforms = ['linux']
        mock_provider.capabilities = ['install']
        mock_provider.get_supported_actions.return_value = ['install', 'uninstall']
        mock_provider.get_priority.return_value = 50
        mock_provider.is_available.return_value = True
        mock_provider.get_executable_path.return_value = '/usr/bin/test'
        mock_provider.get_version.return_value = 'test 1.0.0'
        
        mock_create_providers.return_value = [mock_provider]
        
        factory = ProviderFactory(Mock())
        result = factory.detect_providers()
        
        assert len(result) == 1
        assert 'test-provider' in result
        
        provider_info = result['test-provider']
        assert provider_info['name'] == 'test-provider'
        assert provider_info['display_name'] == 'Test Provider'
        assert provider_info['available'] is True
        assert provider_info['executable_path'] == '/usr/bin/test'
        assert provider_info['version'] == 'test 1.0.0'
        assert provider_info['supported_actions'] == ['install', 'uninstall']