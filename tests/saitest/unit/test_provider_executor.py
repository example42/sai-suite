"""Unit tests for ProviderCommandExecutor."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from saitest.utils.provider_executor import (
    ProviderCommandExecutor,
    ProviderExecutorError
)
from sai.models.provider_data import ProviderData, Provider, Action


@pytest.fixture
def mock_providers_dir(tmp_path):
    """Create a temporary providers directory with test files."""
    providers_dir = tmp_path / "providers"
    providers_dir.mkdir()
    
    # Create a simple apt provider file
    apt_provider = providers_dir / "apt.yaml"
    apt_provider.write_text("""
version: "0.1"
provider:
  name: apt
  type: package_manager
  description: "APT package manager"
  platforms: ["ubuntu", "debian"]

actions:
  install:
    command: "apt-get install -y {{sai_package(0, 'package_name', 'apt')}}"
    requires_root: true
  
  status:
    command: "dpkg -l {{sai_package(0, 'package_name', 'apt')}}"
""")
    
    return providers_dir


@pytest.fixture
def mock_provider_data():
    """Create mock ProviderData for testing."""
    provider = Provider(
        name="apt",
        type="package_manager",
        description="APT package manager",
        platforms=["ubuntu", "debian"]
    )
    
    install_action = Action(
        command="apt-get install -y {{sai_package(0, 'package_name', 'apt')}}",
        requires_root=True
    )
    
    status_action = Action(
        command="dpkg -l {{sai_package(0, 'package_name', 'apt')}}"
    )
    
    provider_data = ProviderData(
        version="0.1",
        provider=provider,
        actions={"install": install_action, "status": status_action}
    )
    
    return provider_data


class TestProviderCommandExecutor:
    """Tests for ProviderCommandExecutor class."""
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_initialization_with_default_dir(self, mock_loader_class):
        """Test initialization with default providers directory."""
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {}
        mock_loader_class.return_value = mock_loader
        
        executor = ProviderCommandExecutor()
        
        assert executor.providers == {}
        assert executor.providers_dir.name == "providers"
        mock_loader.load_providers_from_directory.assert_called_once()
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_initialization_with_custom_dir(self, mock_loader_class, tmp_path):
        """Test initialization with custom providers directory."""
        custom_dir = tmp_path / "custom_providers"
        custom_dir.mkdir()
        
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {}
        mock_loader_class.return_value = mock_loader
        
        executor = ProviderCommandExecutor(providers_dir=custom_dir)
        
        assert executor.providers_dir == custom_dir
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_initialization_missing_directory(self, mock_loader_class, tmp_path):
        """Test initialization with non-existent directory."""
        missing_dir = tmp_path / "missing"
        
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {}
        mock_loader_class.return_value = mock_loader
        
        # Should not raise exception, just log warning
        executor = ProviderCommandExecutor(providers_dir=missing_dir)
        
        assert executor.providers == {}
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_load_providers_success(self, mock_loader_class, mock_provider_data):
        """Test successful provider loading."""
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {
            "apt": mock_provider_data
        }
        mock_loader_class.return_value = mock_loader
        
        executor = ProviderCommandExecutor()
        
        assert "apt" in executor.providers
        assert executor.providers["apt"] == mock_provider_data
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_validate_providers_removes_invalid(self, mock_loader_class):
        """Test that invalid providers are removed during validation."""
        # Create provider without install action
        invalid_provider = ProviderData(
            version="0.1",
            provider=Provider(name="invalid", type="package_manager"),
            actions={"status": Action(command="echo test")}
        )
        
        valid_provider = ProviderData(
            version="0.1",
            provider=Provider(name="valid", type="package_manager"),
            actions={"install": Action(command="echo install")}
        )
        
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {
            "invalid": invalid_provider,
            "valid": valid_provider
        }
        mock_loader_class.return_value = mock_loader
        
        executor = ProviderCommandExecutor()
        
        # Invalid provider should be removed
        assert "invalid" not in executor.providers
        assert "valid" in executor.providers
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_get_available_providers(self, mock_loader_class, mock_provider_data):
        """Test getting list of available providers."""
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {
            "apt": mock_provider_data,
            "dnf": mock_provider_data
        }
        mock_loader_class.return_value = mock_loader
        
        executor = ProviderCommandExecutor()
        providers = executor.get_available_providers()
        
        assert len(providers) == 2
        assert "apt" in providers
        assert "dnf" in providers
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_has_provider(self, mock_loader_class, mock_provider_data):
        """Test checking if provider exists."""
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {
            "apt": mock_provider_data
        }
        mock_loader_class.return_value = mock_loader
        
        executor = ProviderCommandExecutor()
        
        assert executor.has_provider("apt") is True
        assert executor.has_provider("dnf") is False
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_get_install_command_with_package_name(self, mock_loader_class, mock_provider_data):
        """Test getting install command with simple package name."""
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {
            "apt": mock_provider_data
        }
        mock_loader_class.return_value = mock_loader
        
        executor = ProviderCommandExecutor()
        command = executor.get_install_command("apt", package_name="nginx")
        
        # The command should contain the template or the substituted value
        # Since we're using simple substitution without full saidata, 
        # the template may not be fully resolved
        assert command is not None
        assert "apt-get install" in command
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_get_install_command_provider_not_found(self, mock_loader_class):
        """Test getting install command for non-existent provider."""
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {}
        mock_loader_class.return_value = mock_loader
        
        executor = ProviderCommandExecutor()
        
        with pytest.raises(ProviderExecutorError, match="Provider 'nonexistent' not found"):
            executor.get_install_command("nonexistent", package_name="nginx")
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_get_install_command_no_inputs(self, mock_loader_class, mock_provider_data):
        """Test getting install command without saidata or package_name."""
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {
            "apt": mock_provider_data
        }
        mock_loader_class.return_value = mock_loader
        
        executor = ProviderCommandExecutor()
        
        with pytest.raises(ProviderExecutorError, match="Either saidata or package_name must be provided"):
            executor.get_install_command("apt")
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_get_install_command_empty_provider_name(self, mock_loader_class):
        """Test getting install command with empty provider name."""
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {}
        mock_loader_class.return_value = mock_loader
        
        executor = ProviderCommandExecutor()
        
        with pytest.raises(ProviderExecutorError, match="Provider name cannot be empty"):
            executor.get_install_command("", package_name="nginx")
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_get_install_command_with_steps(self, mock_loader_class):
        """Test getting install command from provider with steps."""
        from sai.models.provider_data import Step
        
        # Create provider with multi-step install action
        provider = Provider(name="source", type="source")
        install_action = Action(
            steps=[
                Step(command="./configure"),
                Step(command="make"),
                Step(command="make install")
            ]
        )
        provider_data = ProviderData(
            version="0.1",
            provider=provider,
            actions={"install": install_action}
        )
        
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {
            "source": provider_data
        }
        mock_loader_class.return_value = mock_loader
        
        executor = ProviderCommandExecutor()
        command = executor.get_install_command("source", package_name="nginx")
        
        assert "./configure" in command
        assert "make" in command
        assert "make install" in command
        assert "&&" in command  # Steps should be combined with &&
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_get_test_command_success(self, mock_loader_class, mock_provider_data):
        """Test getting test command."""
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {
            "apt": mock_provider_data
        }
        mock_loader_class.return_value = mock_loader
        
        executor = ProviderCommandExecutor()
        command = executor.get_test_command("apt", package_name="nginx")
        
        # The command should contain the template or the substituted value
        # Since we're using simple substitution without full saidata,
        # the template may not be fully resolved
        assert command is not None
        assert "dpkg -l" in command
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_get_test_command_no_test_action(self, mock_loader_class):
        """Test getting test command when no test action exists."""
        # Create provider without test/status action
        provider = Provider(name="test", type="package_manager")
        provider_data = ProviderData(
            version="0.1",
            provider=provider,
            actions={"install": Action(command="echo install")}
        )
        
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {
            "test": provider_data
        }
        mock_loader_class.return_value = mock_loader
        
        executor = ProviderCommandExecutor()
        command = executor.get_test_command("test", package_name="nginx")
        
        assert command is None
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_get_test_command_provider_not_found(self, mock_loader_class):
        """Test getting test command for non-existent provider."""
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {}
        mock_loader_class.return_value = mock_loader
        
        executor = ProviderCommandExecutor()
        
        with pytest.raises(ProviderExecutorError, match="Provider 'nonexistent' not found"):
            executor.get_test_command("nonexistent", package_name="nginx")
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_get_provider_info(self, mock_loader_class, mock_provider_data):
        """Test getting provider information."""
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {
            "apt": mock_provider_data
        }
        mock_loader_class.return_value = mock_loader
        
        executor = ProviderCommandExecutor()
        info = executor.get_provider_info("apt")
        
        assert info is not None
        assert info["name"] == "apt"
        assert info["type"] == "package_manager"
        assert info["description"] == "APT package manager"
        assert "ubuntu" in info["platforms"]
        assert "debian" in info["platforms"]
        assert "install" in info["actions"]
        assert "status" in info["actions"]
    
    @patch('saitest.utils.provider_executor.ProviderLoader')
    def test_get_provider_info_not_found(self, mock_loader_class):
        """Test getting info for non-existent provider."""
        mock_loader = Mock()
        mock_loader.load_providers_from_directory.return_value = {}
        mock_loader_class.return_value = mock_loader
        
        executor = ProviderCommandExecutor()
        info = executor.get_provider_info("nonexistent")
        
        assert info is None


class TestProviderExecutorError:
    """Tests for ProviderExecutorError exception."""
    
    def test_provider_executor_error_creation(self):
        """Test creating ProviderExecutorError."""
        error = ProviderExecutorError("Test error message")
        
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_provider_executor_error_raise(self):
        """Test raising ProviderExecutorError."""
        with pytest.raises(ProviderExecutorError, match="Test error"):
            raise ProviderExecutorError("Test error")
