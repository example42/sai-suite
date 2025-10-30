"""Tests for package installation tool."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from saitest.tools.package import install_package, get_container_manager
from saitest.models.observation import Observation
from saitest.utils.fs_monitor import FileChange


class TestInstallPackage:
    """Test cases for install_package tool."""
    
    @patch('saitest.tools.package.get_container_manager')
    @patch('saitest.tools.package.ProviderCommandExecutor')
    @patch('saitest.tools.package.FilesystemMonitor')
    def test_successful_installation(
        self,
        mock_fs_monitor_class,
        mock_executor_class,
        mock_get_container_manager
    ):
        """Test successful package installation."""
        # Setup mocks
        mock_executor = Mock()
        mock_executor.get_install_command.return_value = "apt-get install -y nginx"
        mock_executor.get_test_command.return_value = "dpkg -l nginx"
        mock_executor_class.return_value = mock_executor
        
        mock_container = Mock()
        mock_container.exec.side_effect = [
            {"success": True, "output": "Installation successful", "exit_code": 0},
            {"success": True, "output": "nginx installed", "exit_code": 0}
        ]
        
        mock_container_manager = Mock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_container
        mock_context_manager.__exit__.return_value = None
        mock_container_manager.spawn_container.return_value = mock_context_manager
        mock_get_container_manager.return_value = mock_container_manager
        
        mock_fs_monitor = Mock()
        mock_fs_monitor.capture_changes.return_value = [
            FileChange(
                path="/usr/bin/nginx",
                change_type="new",
                timestamp="2025-10-30T10:30:00Z",
                size=1024,
                permissions="755"
            )
        ]
        mock_fs_monitor.get_service_files.return_value = [
            "/lib/systemd/system/nginx.service"
        ]
        mock_fs_monitor.get_binaries.return_value = ["/usr/bin/nginx"]
        mock_fs_monitor_class.return_value = mock_fs_monitor
        
        # Execute
        result = install_package.invoke({
            "platform": "ubuntu:22.04",
            "provider": "apt",
            "package": "nginx"
        })
        
        # Verify
        assert result["success"] is True
        assert result["provider"] == "apt"
        assert result["platform"] == "ubuntu:22.04"
        assert len(result["files_created"]) == 1
        assert "/usr/bin/nginx" in result["files_created"]
        assert len(result["services_found"]) == 1
        assert len(result["binaries_found"]) == 1
        assert len(result["observations"]) == 4  # file + service + binary + package
        assert result["test_success"] is True
        
        # Verify executor was called correctly
        mock_executor.get_install_command.assert_called_once()
        mock_executor.get_test_command.assert_called_once()
        
        # Verify container operations
        mock_container_manager.spawn_container.assert_called_once_with("ubuntu:22.04")
        assert mock_container.exec.call_count == 2
    
    @patch('saitest.tools.package.get_container_manager')
    @patch('saitest.tools.package.ProviderCommandExecutor')
    def test_installation_failure(
        self,
        mock_executor_class,
        mock_get_container_manager
    ):
        """Test failed package installation."""
        # Setup mocks
        mock_executor = Mock()
        mock_executor.get_install_command.return_value = "apt-get install -y nonexistent"
        mock_executor_class.return_value = mock_executor
        
        mock_container = Mock()
        mock_container.exec.return_value = {
            "success": False,
            "output": "Package not found",
            "exit_code": 100
        }
        
        mock_container_manager = Mock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_container
        mock_context_manager.__exit__.return_value = None
        mock_container_manager.spawn_container.return_value = mock_context_manager
        mock_get_container_manager.return_value = mock_container_manager
        
        # Execute
        result = install_package.invoke({
            "platform": "ubuntu:22.04",
            "provider": "apt",
            "package": "nonexistent"
        })
        
        # Verify
        assert result["success"] is False
        assert len(result["errors"]) > 0
        assert "Installation failed" in result["errors"][0]
        assert result["output"] == "Package not found"
    
    @patch('saitest.tools.package.get_container_manager')
    @patch('saitest.tools.package.ProviderCommandExecutor')
    def test_provider_not_found(
        self,
        mock_executor_class,
        mock_get_container_manager
    ):
        """Test installation with non-existent provider."""
        # Setup mocks
        mock_executor = Mock()
        mock_executor.get_install_command.side_effect = Exception(
            "Provider 'invalid' not found"
        )
        mock_executor_class.return_value = mock_executor
        
        # Execute
        result = install_package.invoke({
            "platform": "ubuntu:22.04",
            "provider": "invalid",
            "package": "nginx"
        })
        
        # Verify
        assert result["success"] is False
        assert len(result["errors"]) > 0
        # The error could be either "Failed to get install command" or "Unexpected error"
        assert ("Failed to get install command" in result["errors"][0] or 
                "Unexpected error" in result["errors"][0])
    
    @patch('saitest.tools.package.get_container_manager')
    @patch('saitest.tools.package.ProviderCommandExecutor')
    @patch('saitest.tools.package.FilesystemMonitor')
    def test_installation_without_test_command(
        self,
        mock_fs_monitor_class,
        mock_executor_class,
        mock_get_container_manager
    ):
        """Test installation when provider has no test command."""
        # Setup mocks
        mock_executor = Mock()
        mock_executor.get_install_command.return_value = "pip install nginx"
        mock_executor.get_test_command.return_value = None  # No test command
        mock_executor_class.return_value = mock_executor
        
        mock_container = Mock()
        mock_container.exec.return_value = {
            "success": True,
            "output": "Successfully installed nginx",
            "exit_code": 0
        }
        
        mock_container_manager = Mock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_container
        mock_context_manager.__exit__.return_value = None
        mock_container_manager.spawn_container.return_value = mock_context_manager
        mock_get_container_manager.return_value = mock_container_manager
        
        mock_fs_monitor = Mock()
        mock_fs_monitor.capture_changes.return_value = []
        mock_fs_monitor.get_service_files.return_value = []
        mock_fs_monitor.get_binaries.return_value = []
        mock_fs_monitor_class.return_value = mock_fs_monitor
        
        # Execute
        result = install_package.invoke({
            "platform": "ubuntu:22.04",
            "provider": "pip",
            "package": "nginx"
        })
        
        # Verify
        assert result["success"] is True
        assert result["test_output"] is None
        assert result["test_success"] is None
        
        # Verify only install command was executed
        assert mock_container.exec.call_count == 1
    
    @patch('saitest.tools.package.get_container_manager')
    @patch('saitest.tools.package.ProviderCommandExecutor')
    @patch('saitest.tools.package.FilesystemMonitor')
    def test_observations_creation(
        self,
        mock_fs_monitor_class,
        mock_executor_class,
        mock_get_container_manager
    ):
        """Test that observations are created correctly."""
        # Setup mocks
        mock_executor = Mock()
        mock_executor.get_install_command.return_value = "apt-get install -y nginx"
        mock_executor.get_test_command.return_value = None
        mock_executor_class.return_value = mock_executor
        
        mock_container = Mock()
        mock_container.exec.return_value = {
            "success": True,
            "output": "Installation successful",
            "exit_code": 0
        }
        
        mock_container_manager = Mock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_container
        mock_context_manager.__exit__.return_value = None
        mock_container_manager.spawn_container.return_value = mock_context_manager
        mock_get_container_manager.return_value = mock_container_manager
        
        mock_fs_monitor = Mock()
        mock_fs_monitor.capture_changes.return_value = [
            FileChange("/usr/bin/nginx", "new", "2025-10-30T10:30:00Z", 1024, "755"),
            FileChange("/etc/nginx/nginx.conf", "new", "2025-10-30T10:30:00Z", 512, "644")
        ]
        mock_fs_monitor.get_service_files.return_value = [
            "/lib/systemd/system/nginx.service"
        ]
        mock_fs_monitor.get_binaries.return_value = ["/usr/bin/nginx"]
        mock_fs_monitor_class.return_value = mock_fs_monitor
        
        # Execute
        result = install_package.invoke({
            "platform": "ubuntu:22.04",
            "provider": "apt",
            "package": "nginx"
        })
        
        # Verify observations
        assert len(result["observations"]) == 5  # 2 files + 1 service + 1 binary + 1 package
        
        # Check observation types
        obs_types = [obs["type"] for obs in result["observations"]]
        assert obs_types.count("file") == 2
        assert obs_types.count("service") == 1
        assert obs_types.count("binary") == 1
        assert obs_types.count("package") == 1
        
        # Verify all observations have required fields
        for obs in result["observations"]:
            assert "type" in obs
            assert "platform" in obs
            assert "provider" in obs
            assert "timestamp" in obs
            assert "data" in obs
            assert "confidence" in obs
            assert obs["platform"] == "ubuntu:22.04"
            assert obs["provider"] == "apt"


class TestGetContainerManager:
    """Test cases for get_container_manager function."""
    
    def test_singleton_behavior(self):
        """Test that get_container_manager returns the same instance."""
        # Reset global state
        import saitest.tools.package as package_module
        package_module._container_manager = None
        
        # Get manager twice
        with patch('saitest.tools.package.ContainerManager') as mock_cm_class:
            mock_instance = Mock()
            mock_cm_class.return_value = mock_instance
            
            manager1 = get_container_manager()
            manager2 = get_container_manager()
            
            # Should be the same instance
            assert manager1 is manager2
            
            # ContainerManager should only be instantiated once
            assert mock_cm_class.call_count == 1
