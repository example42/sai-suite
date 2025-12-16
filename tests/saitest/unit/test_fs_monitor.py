"""Unit tests for FilesystemMonitor."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from saitest.utils.fs_monitor import FilesystemMonitor, FileChange


@pytest.fixture
def mock_container():
    """Create a mock container for testing."""
    container = Mock()
    container.platform = "ubuntu:22.04"
    return container


class TestFileChange:
    """Tests for FileChange dataclass."""
    
    def test_file_change_creation(self):
        """Test creating a FileChange instance."""
        change = FileChange(
            path="/usr/bin/nginx",
            change_type="new",
            timestamp="2025-10-30T10:30:00Z",
            size=1024,
            permissions="755"
        )
        
        assert change.path == "/usr/bin/nginx"
        assert change.change_type == "new"
        assert change.timestamp == "2025-10-30T10:30:00Z"
        assert change.size == 1024
        assert change.permissions == "755"
    
    def test_file_change_with_different_types(self):
        """Test FileChange with different change types."""
        new_change = FileChange(
            path="/usr/bin/test",
            change_type="new",
            timestamp="2025-10-30T10:30:00Z",
            size=512,
            permissions="644"
        )
        assert new_change.change_type == "new"
        
        modified_change = FileChange(
            path="/etc/config",
            change_type="modified",
            timestamp="2025-10-30T10:31:00Z",
            size=2048,
            permissions="600"
        )
        assert modified_change.change_type == "modified"


class TestFilesystemMonitor:
    """Tests for FilesystemMonitor class."""
    
    def test_initialization(self, mock_container):
        """Test FilesystemMonitor initialization."""
        monitor = FilesystemMonitor(mock_container)
        
        assert monitor.container == mock_container
        assert monitor.baseline_files is None
    
    def test_capture_baseline_success(self, mock_container):
        """Test capturing filesystem baseline."""
        # Mock exec to return files from different directories
        def mock_exec(command):
            if "/usr/bin" in command:
                return {
                    "success": True,
                    "output": "/usr/bin/file1\n/usr/bin/file2\n"
                }
            elif "/usr/sbin" in command:
                return {
                    "success": True,
                    "output": "/usr/sbin/daemon1\n"
                }
            elif "/etc" in command:
                return {
                    "success": True,
                    "output": "/etc/config1.conf\n/etc/config2.conf\n"
                }
            else:
                return {"success": True, "output": ""}
        
        mock_container.exec = Mock(side_effect=mock_exec)
        
        monitor = FilesystemMonitor(mock_container)
        monitor.capture_baseline()
        
        assert monitor.baseline_files is not None
        assert len(monitor.baseline_files) > 0
        assert "/usr/bin/file1" in monitor.baseline_files
        assert "/usr/bin/file2" in monitor.baseline_files
        assert "/usr/sbin/daemon1" in monitor.baseline_files
        assert "/etc/config1.conf" in monitor.baseline_files
    
    def test_capture_baseline_empty_directories(self, mock_container):
        """Test capturing baseline with empty directories."""
        mock_container.exec = Mock(return_value={
            "success": True,
            "output": ""
        })
        
        monitor = FilesystemMonitor(mock_container)
        monitor.capture_baseline()
        
        assert monitor.baseline_files is not None
        assert len(monitor.baseline_files) == 0
    
    def test_capture_baseline_with_errors(self, mock_container):
        """Test capturing baseline with command errors."""
        # Some directories might not exist, which is fine
        def mock_exec(command):
            if "/usr/bin" in command:
                return {
                    "success": True,
                    "output": "/usr/bin/file1\n"
                }
            else:
                # Other directories return empty (as if they don't exist)
                return {"success": True, "output": ""}
        
        mock_container.exec = Mock(side_effect=mock_exec)
        
        monitor = FilesystemMonitor(mock_container)
        monitor.capture_baseline()
        
        assert monitor.baseline_files is not None
        assert "/usr/bin/file1" in monitor.baseline_files
    
    def test_capture_changes_without_baseline(self, mock_container):
        """Test that capture_changes raises error without baseline."""
        monitor = FilesystemMonitor(mock_container)
        
        with pytest.raises(RuntimeError, match="Baseline not captured"):
            monitor.capture_changes()
    
    def test_capture_changes_detects_new_files(self, mock_container):
        """Test detecting new files after installation."""
        call_count = [0]
        
        def mock_exec(command):
            call_count[0] += 1
            
            # Handle stat commands for file details
            if "stat" in command:
                return {"success": True, "output": "2048 755"}
            
            # First 12 calls are for baseline (12 monitored directories)
            # Subsequent calls are for change detection
            if call_count[0] <= 12:
                # Baseline: only existing files
                if "/usr/bin" in command:
                    return {
                        "success": True,
                        "output": "/usr/bin/existing1\n/usr/bin/existing2\n"
                    }
                else:
                    return {"success": True, "output": ""}
            else:
                # After installation: existing + new files
                if "/usr/bin" in command:
                    return {
                        "success": True,
                        "output": "/usr/bin/existing1\n/usr/bin/existing2\n/usr/bin/newfile\n"
                    }
                else:
                    return {"success": True, "output": ""}
        
        mock_container.exec = Mock(side_effect=mock_exec)
        
        monitor = FilesystemMonitor(mock_container)
        monitor.capture_baseline()
        
        changes = monitor.capture_changes()
        
        assert len(changes) > 0
        new_file_paths = [c.path for c in changes]
        assert "/usr/bin/newfile" in new_file_paths
        
        # Verify FileChange attributes
        new_file_change = next(c for c in changes if c.path == "/usr/bin/newfile")
        assert new_file_change.change_type == "new"
        assert new_file_change.size == 2048
        assert new_file_change.permissions == "755"
        assert new_file_change.timestamp.endswith("Z")
    
    def test_capture_changes_multiple_new_files(self, mock_container):
        """Test detecting multiple new files."""
        call_count = [0]
        
        def mock_exec(command):
            call_count[0] += 1
            
            if "stat" in command:
                return {"success": True, "output": "1024 644"}
            
            if call_count[0] <= 12:
                # Baseline
                return {"success": True, "output": ""}
            else:
                # After installation
                if "/usr/bin" in command:
                    return {
                        "success": True,
                        "output": "/usr/bin/new1\n/usr/bin/new2\n"
                    }
                elif "/etc" in command:
                    return {
                        "success": True,
                        "output": "/etc/new.conf\n"
                    }
                else:
                    return {"success": True, "output": ""}
        
        mock_container.exec = Mock(side_effect=mock_exec)
        
        monitor = FilesystemMonitor(mock_container)
        monitor.capture_baseline()
        
        changes = monitor.capture_changes()
        
        assert len(changes) == 3
        paths = [c.path for c in changes]
        assert "/usr/bin/new1" in paths
        assert "/usr/bin/new2" in paths
        assert "/etc/new.conf" in paths
    
    def test_capture_changes_no_new_files(self, mock_container):
        """Test when no new files are detected."""
        mock_container.exec = Mock(return_value={
            "success": True,
            "output": "/usr/bin/existing\n"
        })
        
        monitor = FilesystemMonitor(mock_container)
        monitor.capture_baseline()
        
        changes = monitor.capture_changes()
        
        assert len(changes) == 0
    
    def test_get_service_files(self, mock_container):
        """Test finding systemd service files."""
        def mock_exec(command):
            if "*.service" in command:
                return {
                    "success": True,
                    "output": "/lib/systemd/system/nginx.service\n/lib/systemd/system/apache2.service\n"
                }
            else:
                return {"success": True, "output": ""}
        
        mock_container.exec = Mock(side_effect=mock_exec)
        
        monitor = FilesystemMonitor(mock_container)
        service_files = monitor.get_service_files()
        
        assert len(service_files) == 2
        assert "/lib/systemd/system/nginx.service" in service_files
        assert "/lib/systemd/system/apache2.service" in service_files
    
    def test_get_service_files_with_baseline(self, mock_container):
        """Test that get_service_files filters out baseline files."""
        call_count = [0]
        
        def mock_exec(command):
            call_count[0] += 1
            
            if "*.service" in command:
                # Return both existing and new service files
                return {
                    "success": True,
                    "output": "/lib/systemd/system/existing.service\n/lib/systemd/system/new.service\n"
                }
            elif call_count[0] <= 12:
                # Baseline includes existing service
                if "/lib/systemd/system" in command or "/usr/lib/systemd/system" in command or "/etc/systemd/system" in command:
                    return {
                        "success": True,
                        "output": "/lib/systemd/system/existing.service\n"
                    }
                else:
                    return {"success": True, "output": ""}
            else:
                return {"success": True, "output": ""}
        
        mock_container.exec = Mock(side_effect=mock_exec)
        
        monitor = FilesystemMonitor(mock_container)
        monitor.capture_baseline()
        
        service_files = monitor.get_service_files()
        
        # Should only return the new service file
        assert len(service_files) == 1
        assert "/lib/systemd/system/new.service" in service_files
        assert "/lib/systemd/system/existing.service" not in service_files
    
    def test_get_service_files_no_services(self, mock_container):
        """Test when no service files are found."""
        mock_container.exec = Mock(return_value={
            "success": True,
            "output": ""
        })
        
        monitor = FilesystemMonitor(mock_container)
        service_files = monitor.get_service_files()
        
        assert service_files == []
    
    def test_get_binaries(self, mock_container):
        """Test finding executable binaries."""
        def mock_exec(command):
            if "executable" in command:
                if "/usr/bin" in command:
                    return {
                        "success": True,
                        "output": "/usr/bin/nginx\n/usr/bin/nginx-debug\n"
                    }
                elif "/usr/sbin" in command:
                    return {
                        "success": True,
                        "output": "/usr/sbin/nginx\n"
                    }
                else:
                    return {"success": True, "output": ""}
            else:
                return {"success": True, "output": ""}
        
        mock_container.exec = Mock(side_effect=mock_exec)
        
        monitor = FilesystemMonitor(mock_container)
        binaries = monitor.get_binaries()
        
        assert len(binaries) == 3
        assert "/usr/bin/nginx" in binaries
        assert "/usr/bin/nginx-debug" in binaries
        assert "/usr/sbin/nginx" in binaries
    
    def test_get_binaries_with_baseline(self, mock_container):
        """Test that get_binaries filters out baseline files."""
        call_count = [0]
        
        def mock_exec(command):
            call_count[0] += 1
            
            if "executable" in command:
                if "/usr/bin" in command:
                    # Return both existing and new binaries
                    return {
                        "success": True,
                        "output": "/usr/bin/existing\n/usr/bin/newbinary\n"
                    }
                else:
                    return {"success": True, "output": ""}
            elif call_count[0] <= 12:
                # Baseline includes existing binary
                if "/usr/bin" in command:
                    return {
                        "success": True,
                        "output": "/usr/bin/existing\n"
                    }
                else:
                    return {"success": True, "output": ""}
            else:
                return {"success": True, "output": ""}
        
        mock_container.exec = Mock(side_effect=mock_exec)
        
        monitor = FilesystemMonitor(mock_container)
        monitor.capture_baseline()
        
        binaries = monitor.get_binaries()
        
        # Should only return the new binary
        assert len(binaries) == 1
        assert "/usr/bin/newbinary" in binaries
        assert "/usr/bin/existing" not in binaries
    
    def test_get_binaries_no_binaries(self, mock_container):
        """Test when no binaries are found."""
        mock_container.exec = Mock(return_value={
            "success": True,
            "output": ""
        })
        
        monitor = FilesystemMonitor(mock_container)
        binaries = monitor.get_binaries()
        
        assert binaries == []
