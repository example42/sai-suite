"""Unit tests for ContainerManager."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from docker.errors import DockerException, ImageNotFound, APIError

from saitest.utils.docker_manager import (
    ContainerManager,
    ContainerWrapper,
    PLATFORM_IMAGE_MAP
)


@pytest.fixture
def mock_docker_client():
    """Create a mock Docker client."""
    client = Mock()
    client.images = Mock()
    client.containers = Mock()
    return client


@pytest.fixture
def mock_container():
    """Create a mock Docker container."""
    container = Mock()
    container.short_id = "abc123"
    container.exec_run = Mock(return_value=Mock(exit_code=0, output=b"test output"))
    container.stop = Mock()
    container.remove = Mock()
    return container


class TestContainerWrapper:
    """Tests for ContainerWrapper class."""
    
    def test_initialization(self, mock_container):
        """Test ContainerWrapper initialization."""
        wrapper = ContainerWrapper(mock_container, "ubuntu:22.04")
        
        assert wrapper.container == mock_container
        assert wrapper.platform == "ubuntu:22.04"
    
    def test_exec_success(self, mock_container):
        """Test successful command execution."""
        mock_container.exec_run.return_value = Mock(
            exit_code=0,
            output=b"command output"
        )
        
        wrapper = ContainerWrapper(mock_container, "ubuntu:22.04")
        result = wrapper.exec("echo test")
        
        assert result["success"] is True
        assert result["exit_code"] == 0
        assert result["output"] == "command output"
        
        # Verify exec_run was called with correct parameters
        mock_container.exec_run.assert_called_once()
        call_args = mock_container.exec_run.call_args
        assert call_args[1]["cmd"] == ["sh", "-c", "echo test"]
        assert call_args[1]["privileged"] is True
        assert call_args[1]["user"] == "root"
    
    def test_exec_failure(self, mock_container):
        """Test failed command execution."""
        mock_container.exec_run.return_value = Mock(
            exit_code=1,
            output=b"error message"
        )
        
        wrapper = ContainerWrapper(mock_container, "ubuntu:22.04")
        result = wrapper.exec("false")
        
        assert result["success"] is False
        assert result["exit_code"] == 1
        assert result["output"] == "error message"
    
    def test_exec_exception(self, mock_container):
        """Test command execution with exception."""
        mock_container.exec_run.side_effect = Exception("Container error")
        
        wrapper = ContainerWrapper(mock_container, "ubuntu:22.04")
        result = wrapper.exec("echo test")
        
        assert result["success"] is False
        assert result["exit_code"] == -1
        assert "Container error" in result["output"]
    
    def test_read_file_success(self, mock_container):
        """Test successful file reading."""
        mock_container.exec_run.return_value = Mock(
            exit_code=0,
            output=b"file contents"
        )
        
        wrapper = ContainerWrapper(mock_container, "ubuntu:22.04")
        content = wrapper.read_file("/etc/test.conf")
        
        assert content == "file contents"
    
    def test_read_file_not_found(self, mock_container):
        """Test reading non-existent file."""
        mock_container.exec_run.return_value = Mock(
            exit_code=1,
            output=b"cat: /etc/test.conf: No such file or directory"
        )
        
        wrapper = ContainerWrapper(mock_container, "ubuntu:22.04")
        content = wrapper.read_file("/etc/test.conf")
        
        assert content is None
    
    def test_list_files_success(self, mock_container):
        """Test successful file listing."""
        mock_container.exec_run.return_value = Mock(
            exit_code=0,
            output=b"/usr/bin/file1\n/usr/bin/file2\n/usr/bin/file3\n"
        )
        
        wrapper = ContainerWrapper(mock_container, "ubuntu:22.04")
        files = wrapper.list_files("/usr/bin", "*.conf")
        
        assert len(files) == 3
        assert "/usr/bin/file1" in files
        assert "/usr/bin/file2" in files
        assert "/usr/bin/file3" in files
    
    def test_list_files_empty(self, mock_container):
        """Test listing files with no results."""
        mock_container.exec_run.return_value = Mock(
            exit_code=0,
            output=b""
        )
        
        wrapper = ContainerWrapper(mock_container, "ubuntu:22.04")
        files = wrapper.list_files("/usr/bin", "*.conf")
        
        assert files == []


class TestContainerManager:
    """Tests for ContainerManager class."""
    
    @patch('saitest.utils.docker_manager.docker.from_env')
    def test_initialization_success(self, mock_from_env, mock_docker_client):
        """Test successful ContainerManager initialization."""
        mock_from_env.return_value = mock_docker_client
        
        manager = ContainerManager()
        
        assert manager.client == mock_docker_client
        assert manager.active_containers == {}
        mock_from_env.assert_called_once()
    
    @patch('saitest.utils.docker_manager.docker.from_env')
    def test_initialization_docker_not_available(self, mock_from_env):
        """Test initialization when Docker is not available."""
        mock_from_env.side_effect = DockerException("Docker not running")
        
        with pytest.raises(RuntimeError, match="Docker is not available"):
            ContainerManager()
    
    def test_get_image_for_platform_valid(self):
        """Test getting image for valid platform."""
        with patch('saitest.utils.docker_manager.docker.from_env'):
            manager = ContainerManager()
            
            image = manager.get_image_for_platform("ubuntu:22.04")
            assert image == "ubuntu:22.04"
            
            image = manager.get_image_for_platform("centos:9")
            assert image == "quay.io/centos/centos:stream9"
    
    def test_get_image_for_platform_invalid(self):
        """Test getting image for invalid platform."""
        with patch('saitest.utils.docker_manager.docker.from_env'):
            manager = ContainerManager()
            
            with pytest.raises(ValueError, match="Unsupported platform"):
                manager.get_image_for_platform("invalid:platform")
    
    @patch('saitest.utils.docker_manager.docker.from_env')
    def test_pull_image_if_needed_cached(self, mock_from_env, mock_docker_client):
        """Test pulling image when already cached."""
        mock_from_env.return_value = mock_docker_client
        mock_docker_client.images.get.return_value = Mock()  # Image exists
        
        manager = ContainerManager()
        manager._pull_image_if_needed("ubuntu:22.04")
        
        # Should check for image but not pull
        mock_docker_client.images.get.assert_called_once_with("ubuntu:22.04")
        mock_docker_client.images.pull.assert_not_called()
    
    @patch('saitest.utils.docker_manager.docker.from_env')
    def test_pull_image_if_needed_not_cached(self, mock_from_env, mock_docker_client):
        """Test pulling image when not cached."""
        mock_from_env.return_value = mock_docker_client
        mock_docker_client.images.get.side_effect = ImageNotFound("Image not found")
        
        manager = ContainerManager()
        manager._pull_image_if_needed("ubuntu:22.04")
        
        # Should check for image and then pull
        mock_docker_client.images.get.assert_called_once_with("ubuntu:22.04")
        mock_docker_client.images.pull.assert_called_once_with("ubuntu:22.04")
    
    @patch('saitest.utils.docker_manager.docker.from_env')
    def test_spawn_container_success(self, mock_from_env, mock_docker_client, mock_container):
        """Test successful container spawning."""
        mock_from_env.return_value = mock_docker_client
        mock_docker_client.images.get.return_value = Mock()  # Image exists
        mock_docker_client.containers.run.return_value = mock_container
        
        manager = ContainerManager()
        
        with manager.spawn_container("ubuntu:22.04") as wrapper:
            assert isinstance(wrapper, ContainerWrapper)
            assert wrapper.platform == "ubuntu:22.04"
            assert wrapper.container == mock_container
            assert "ubuntu:22.04" in manager.active_containers
        
        # After context exit, container should be cleaned up
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()
        assert "ubuntu:22.04" not in manager.active_containers
    
    @patch('saitest.utils.docker_manager.docker.from_env')
    def test_spawn_container_api_error(self, mock_from_env, mock_docker_client):
        """Test container spawning with API error."""
        mock_from_env.return_value = mock_docker_client
        mock_docker_client.images.get.return_value = Mock()
        mock_docker_client.containers.run.side_effect = APIError("API error")
        
        manager = ContainerManager()
        
        with pytest.raises(RuntimeError, match="Failed to create container"):
            with manager.spawn_container("ubuntu:22.04"):
                pass
    
    @patch('saitest.utils.docker_manager.docker.from_env')
    def test_spawn_container_cleanup_on_error(self, mock_from_env, mock_docker_client, mock_container):
        """Test container cleanup when error occurs during usage."""
        mock_from_env.return_value = mock_docker_client
        mock_docker_client.images.get.return_value = Mock()
        mock_docker_client.containers.run.return_value = mock_container
        
        manager = ContainerManager()
        
        try:
            with manager.spawn_container("ubuntu:22.04") as wrapper:
                # Simulate error during container usage
                raise Exception("Test error")
        except Exception:
            pass
        
        # Container should still be cleaned up
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()
        assert "ubuntu:22.04" not in manager.active_containers
    
    @patch('saitest.utils.docker_manager.docker.from_env')
    def test_cleanup_all(self, mock_from_env, mock_docker_client):
        """Test cleaning up all active containers."""
        mock_from_env.return_value = mock_docker_client
        
        # Create mock containers
        container1 = Mock()
        container1.stop = Mock()
        container1.remove = Mock()
        
        container2 = Mock()
        container2.stop = Mock()
        container2.remove = Mock()
        
        manager = ContainerManager()
        manager.active_containers = {
            "ubuntu:22.04": container1,
            "debian:12": container2
        }
        
        manager.cleanup_all()
        
        # Both containers should be stopped and removed
        container1.stop.assert_called_once()
        container1.remove.assert_called_once()
        container2.stop.assert_called_once()
        container2.remove.assert_called_once()
        
        # Active containers should be empty
        assert manager.active_containers == {}
    
    @patch('saitest.utils.docker_manager.docker.from_env')
    def test_cleanup_all_with_errors(self, mock_from_env, mock_docker_client):
        """Test cleanup_all handles errors gracefully."""
        mock_from_env.return_value = mock_docker_client
        
        # Create mock container that raises error on stop
        container = Mock()
        container.stop.side_effect = Exception("Stop failed")
        container.remove = Mock()
        
        manager = ContainerManager()
        manager.active_containers = {"ubuntu:22.04": container}
        
        # Should not raise exception
        manager.cleanup_all()
        
        # Container should still be removed from active_containers
        assert manager.active_containers == {}


class TestPlatformImageMap:
    """Tests for PLATFORM_IMAGE_MAP constant."""
    
    def test_platform_image_map_contains_common_platforms(self):
        """Test that PLATFORM_IMAGE_MAP contains common platforms."""
        assert "ubuntu:22.04" in PLATFORM_IMAGE_MAP
        assert "ubuntu:24.04" in PLATFORM_IMAGE_MAP
        assert "debian:12" in PLATFORM_IMAGE_MAP
        assert "fedora:40" in PLATFORM_IMAGE_MAP
        assert "centos:9" in PLATFORM_IMAGE_MAP
        assert "rocky:9" in PLATFORM_IMAGE_MAP
        assert "alpine:3.19" in PLATFORM_IMAGE_MAP
    
    def test_platform_image_map_centos_uses_quay(self):
        """Test that CentOS platforms use quay.io images."""
        assert PLATFORM_IMAGE_MAP["centos:9"] == "quay.io/centos/centos:stream9"
        assert PLATFORM_IMAGE_MAP["centos:8"] == "quay.io/centos/centos:stream8"
    
    def test_platform_image_map_rocky_uses_rockylinux(self):
        """Test that Rocky platforms use rockylinux images."""
        assert PLATFORM_IMAGE_MAP["rocky:9"] == "rockylinux:9"
        assert PLATFORM_IMAGE_MAP["rocky:8"] == "rockylinux:8"
