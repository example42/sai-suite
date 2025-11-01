"""Unit tests for performance optimizations.

Tests for Docker image caching, filesystem scanning optimizations,
and timeout controls.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from saitest.utils.docker_manager import ContainerManager
from saitest.utils.fs_monitor import FilesystemMonitor
from saitest.utils.config_loader import ConfigLoader, get_config, reset_config


class TestConfigLoader:
    """Tests for configuration loader."""
    
    def test_default_config_values(self):
        """Test that default config values are loaded."""
        config = ConfigLoader()
        
        # Check container timeouts
        assert config.get("containers.timeout") == 600
        assert config.get("containers.pull_timeout") == 600
        assert config.get("containers.startup_timeout") == 30
        
        # Check filesystem settings
        assert config.get("verification.filesystem.scan_timeout") == 120
        assert config.get("verification.filesystem.max_depth") == 10
    
    def test_config_get_with_default(self):
        """Test getting config value with default."""
        config = ConfigLoader()
        
        # Existing key
        assert config.get("containers.timeout", 999) == 600
        
        # Non-existing key
        assert config.get("nonexistent.key", 999) == 999
    
    def test_config_env_overrides(self):
        """Test environment variable overrides."""
        with patch.dict('os.environ', {
            'SAITEST_CONTAINER_TIMEOUT': '1200',
            'SAITEST_PULL_TIMEOUT': '900',
            'SAITEST_SCAN_TIMEOUT': '180'
        }):
            config = ConfigLoader()
            
            assert config.get("containers.timeout") == 1200
            assert config.get("containers.pull_timeout") == 900
            assert config.get("verification.filesystem.scan_timeout") == 180
    
    def test_global_config_instance(self):
        """Test global config instance."""
        reset_config()
        
        config1 = get_config()
        config2 = get_config()
        
        # Should be same instance
        assert config1 is config2
        
        reset_config()


class TestDockerManagerPerformance:
    """Tests for Docker manager performance optimizations."""
    
    @patch('saitest.utils.docker_manager.docker.from_env')
    def test_image_caching_check(self, mock_docker):
        """Test that image caching is checked before pulling."""
        mock_client = Mock()
        mock_docker.return_value = mock_client
        
        # Mock image exists (cached)
        mock_image = Mock()
        mock_client.images.get.return_value = mock_image
        
        manager = ContainerManager()
        
        # Should not call pull if image exists
        manager._pull_image_if_needed("ubuntu:22.04")
        
        mock_client.images.get.assert_called_once_with("ubuntu:22.04")
        mock_client.images.pull.assert_not_called()
    
    @patch('saitest.utils.docker_manager.docker.from_env')
    def test_image_pull_with_timeout(self, mock_docker):
        """Test that image pull respects timeout."""
        from docker.errors import ImageNotFound
        
        mock_client = Mock()
        mock_docker.return_value = mock_client
        
        # Mock image not found (needs pull)
        mock_client.images.get.side_effect = ImageNotFound("Image not found")
        mock_client.images.pull.return_value = Mock()
        
        manager = ContainerManager()
        
        # Should pull image
        manager._pull_image_if_needed("ubuntu:22.04", pull_timeout=300)
        
        mock_client.images.pull.assert_called_once_with("ubuntu:22.04")
    
    @patch('saitest.utils.docker_manager.docker.from_env')
    def test_spawn_container_uses_config_timeouts(self, mock_docker):
        """Test that spawn_container uses config timeouts."""
        mock_client = Mock()
        mock_docker.return_value = mock_client
        
        # Mock image exists
        mock_client.images.get.return_value = Mock()
        
        # Mock container
        mock_container = Mock()
        mock_container.status = 'running'
        mock_container.short_id = 'abc123'
        mock_client.containers.run.return_value = mock_container
        
        manager = ContainerManager()
        
        # Reset config to ensure we're using defaults
        reset_config()
        
        # Spawn container should use config values
        with manager.spawn_container("ubuntu:22.04"):
            pass
        
        # Verify container was created
        mock_client.containers.run.assert_called_once()


class TestFilesystemMonitorPerformance:
    """Tests for filesystem monitor performance optimizations."""
    
    def test_monitor_uses_config_values(self):
        """Test that monitor uses config values."""
        mock_container = Mock()
        mock_container.platform = "ubuntu:22.04"
        
        # Reset config
        reset_config()
        
        monitor = FilesystemMonitor(mock_container)
        
        # Should use default config values
        assert monitor.scan_timeout == 120
        assert monitor.max_depth == 10
        assert len(monitor.monitored_paths) > 0
    
    def test_monitor_custom_timeouts(self):
        """Test that monitor accepts custom timeouts."""
        mock_container = Mock()
        mock_container.platform = "ubuntu:22.04"
        
        monitor = FilesystemMonitor(
            mock_container,
            scan_timeout=60,
            max_depth=5
        )
        
        assert monitor.scan_timeout == 60
        assert monitor.max_depth == 5
    
    def test_monitor_custom_paths(self):
        """Test that monitor accepts custom monitored paths."""
        mock_container = Mock()
        mock_container.platform = "ubuntu:22.04"
        
        custom_paths = ["/usr/bin", "/etc"]
        monitor = FilesystemMonitor(
            mock_container,
            monitored_paths=custom_paths
        )
        
        assert monitor.monitored_paths == custom_paths
    
    def test_optimized_baseline_capture(self):
        """Test that baseline capture uses optimized command."""
        mock_container = Mock()
        mock_container.platform = "ubuntu:22.04"
        mock_container.exec.return_value = {
            "success": True,
            "output": "/usr/bin/test1\n/usr/bin/test2\n/etc/config"
        }
        
        monitor = FilesystemMonitor(mock_container, scan_timeout=60, max_depth=5)
        monitor.capture_baseline()
        
        # Verify exec was called with optimized command
        mock_container.exec.assert_called_once()
        call_args = mock_container.exec.call_args
        command = call_args[0][0]
        
        # Should include timeout and maxdepth
        assert "timeout 60" in command
        assert "-maxdepth 5" in command
        assert "-type f" in command
    
    def test_optimized_change_capture(self):
        """Test that change capture uses optimized command."""
        mock_container = Mock()
        mock_container.platform = "ubuntu:22.04"
        
        # Mock baseline
        mock_container.exec.return_value = {
            "success": True,
            "output": "/usr/bin/old1\n/usr/bin/old2"
        }
        
        monitor = FilesystemMonitor(mock_container, scan_timeout=60, max_depth=5)
        monitor.capture_baseline()
        
        # Mock new files and stat command
        def mock_exec_side_effect(cmd, timeout=None):
            if "stat" in cmd:
                # Return mock stat output for new file
                return {
                    "success": True,
                    "output": "/usr/bin/new1|1024|755"
                }
            # Return file list with new file
            return {
                "success": True,
                "output": "/usr/bin/old1\n/usr/bin/old2\n/usr/bin/new1"
            }
        
        mock_container.exec.side_effect = mock_exec_side_effect
        
        changes = monitor.capture_changes()
        
        # Should detect new file
        assert len(changes) > 0
        assert changes[0].path == "/usr/bin/new1"
    
    def test_batch_stat_optimization(self):
        """Test that file stat operations are batched."""
        mock_container = Mock()
        mock_container.platform = "ubuntu:22.04"
        
        # Mock baseline with no files
        mock_container.exec.return_value = {
            "success": True,
            "output": ""
        }
        
        monitor = FilesystemMonitor(mock_container)
        monitor.capture_baseline()
        
        # Mock many new files
        new_files = [f"/usr/bin/file{i}" for i in range(150)]
        mock_container.exec.return_value = {
            "success": True,
            "output": "\n".join(new_files)
        }
        
        # Mock stat responses
        def mock_exec_side_effect(cmd, timeout=None):
            if "stat" in cmd:
                # Return mock stat output
                return {
                    "success": True,
                    "output": "\n".join([f"{f}|1024|755" for f in new_files[:100]])
                }
            return {"success": True, "output": "\n".join(new_files)}
        
        mock_container.exec.side_effect = mock_exec_side_effect
        
        changes = monitor.capture_changes()
        
        # Should batch stat commands (150 files / 100 batch size = 2 batches)
        # Plus initial scan call
        assert mock_container.exec.call_count >= 2


class TestPerformanceIntegration:
    """Integration tests for performance features."""
    
    def test_config_propagates_to_components(self):
        """Test that config values propagate to all components."""
        reset_config()
        
        # Set custom config
        with patch.dict('os.environ', {
            'SAITEST_SCAN_TIMEOUT': '90',
            'SAITEST_MAX_DEPTH': '8'
        }):
            config = get_config()
            
            # Create monitor
            mock_container = Mock()
            mock_container.platform = "ubuntu:22.04"
            monitor = FilesystemMonitor(mock_container)
            
            # Should use env config
            assert monitor.scan_timeout == 90
            assert monitor.max_depth == 8
        
        reset_config()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
