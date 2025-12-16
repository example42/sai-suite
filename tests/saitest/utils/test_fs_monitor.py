"""Tests for FilesystemMonitor."""

import pytest
from unittest.mock import Mock, MagicMock
from saitest.utils.fs_monitor import FilesystemMonitor, FileChange


@pytest.fixture
def mock_container():
    """Create a mock container for testing."""
    container = Mock()
    container.platform = "ubuntu:22.04"
    return container


def test_filesystem_monitor_initialization(mock_container):
    """Test FilesystemMonitor initialization."""
    monitor = FilesystemMonitor(mock_container)
    
    assert monitor.container == mock_container
    assert monitor.baseline_files is None


def test_capture_baseline(mock_container):
    """Test capturing filesystem baseline."""
    # Mock exec to return some files
    mock_container.exec = Mock(return_value={
        "success": True,
        "output": "/usr/bin/file1\n/usr/bin/file2\n/usr/sbin/file3\n"
    })
    
    monitor = FilesystemMonitor(mock_container)
    monitor.capture_baseline()
    
    assert monitor.baseline_files is not None
    assert len(monitor.baseline_files) > 0
    assert "/usr/bin/file1" in monitor.baseline_files
    assert "/usr/bin/file2" in monitor.baseline_files


def test_capture_changes_without_baseline(mock_container):
    """Test that capture_changes raises error without baseline."""
    monitor = FilesystemMonitor(mock_container)
    
    with pytest.raises(RuntimeError, match="Baseline not captured"):
        monitor.capture_changes()


def test_capture_changes_detects_new_files(mock_container):
    """Test detecting new files after installation."""
    # First call returns baseline files
    # Subsequent calls return baseline + new files
    call_count = [0]
    
    def mock_exec(command):
        call_count[0] += 1
        if "stat" in command:
            # Return file stats
            return {"success": True, "output": "1024 755"}
        elif call_count[0] <= 12:  # First set of calls for baseline
            return {
                "success": True,
                "output": "/usr/bin/existing1\n/usr/bin/existing2\n"
            }
        else:  # Second set of calls for changes
            return {
                "success": True,
                "output": "/usr/bin/existing1\n/usr/bin/existing2\n/usr/bin/newfile\n"
            }
    
    mock_container.exec = Mock(side_effect=mock_exec)
    
    monitor = FilesystemMonitor(mock_container)
    monitor.capture_baseline()
    
    changes = monitor.capture_changes()
    
    assert len(changes) > 0
    new_file_paths = [c.path for c in changes]
    assert "/usr/bin/newfile" in new_file_paths


def test_get_service_files(mock_container):
    """Test finding systemd service files."""
    mock_container.exec = Mock(return_value={
        "success": True,
        "output": "/lib/systemd/system/nginx.service\n/lib/systemd/system/apache2.service\n"
    })
    
    monitor = FilesystemMonitor(mock_container)
    service_files = monitor.get_service_files()
    
    assert len(service_files) == 2
    assert "/lib/systemd/system/nginx.service" in service_files
    assert "/lib/systemd/system/apache2.service" in service_files


def test_get_binaries(mock_container):
    """Test finding executable binaries."""
    mock_container.exec = Mock(return_value={
        "success": True,
        "output": "/usr/bin/nginx\n/usr/sbin/nginx\n"
    })
    
    monitor = FilesystemMonitor(mock_container)
    binaries = monitor.get_binaries()
    
    assert len(binaries) == 2
    assert "/usr/bin/nginx" in binaries
    assert "/usr/sbin/nginx" in binaries


def test_get_service_files_filters_baseline(mock_container):
    """Test that get_service_files filters out baseline files."""
    # Setup baseline with one service
    baseline_output = "/lib/systemd/system/existing.service\n"
    # After installation, two services exist
    current_output = "/lib/systemd/system/existing.service\n/lib/systemd/system/new.service\n"
    
    call_count = [0]
    
    def mock_exec(command):
        call_count[0] += 1
        if "*.service" in command:
            # Return current output for service queries
            return {"success": True, "output": current_output}
        else:
            # Return baseline for initial capture
            return {"success": True, "output": baseline_output}
    
    mock_container.exec = Mock(side_effect=mock_exec)
    
    monitor = FilesystemMonitor(mock_container)
    monitor.capture_baseline()
    
    service_files = monitor.get_service_files()
    
    # Should only return the new service file
    assert len(service_files) == 1
    assert "/lib/systemd/system/new.service" in service_files
    assert "/lib/systemd/system/existing.service" not in service_files


def test_file_change_dataclass():
    """Test FileChange dataclass."""
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
