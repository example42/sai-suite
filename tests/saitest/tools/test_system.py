"""Tests for system inspection tools."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from saitest.tools.system import (
    inspect_service,
    check_listening_ports,
    find_config_files,
    get_container_manager
)


class TestInspectService:
    """Test cases for inspect_service tool."""
    
    @patch('saitest.tools.system.get_container_manager')
    def test_active_enabled_service(self, mock_get_container_manager):
        """Test inspecting an active and enabled service."""
        # Setup mocks
        mock_container = Mock()
        mock_container.exec.side_effect = [
            {"success": True, "output": "● nginx.service - nginx\n   Active: active (running)", "exit_code": 0},
            {"success": True, "output": "active", "exit_code": 0},
            {"success": True, "output": "enabled", "exit_code": 0},
            {"success": True, "output": "[Unit]\nDescription=nginx", "exit_code": 0},
            {"success": True, "output": "FragmentPath=/lib/systemd/system/nginx.service", "exit_code": 0}
        ]
        
        mock_container_manager = Mock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_container
        mock_context_manager.__exit__.return_value = None
        mock_container_manager.spawn_container.return_value = mock_context_manager
        mock_get_container_manager.return_value = mock_container_manager
        
        # Execute
        result = inspect_service.invoke({
            "platform": "ubuntu:22.04",
            "service_name": "nginx"
        })
        
        # Verify
        assert result["success"] is True
        assert result["service_name"] == "nginx"
        assert result["active"] is True
        assert result["enabled"] is True
        assert "nginx.service" in result["status"]
        assert "[Unit]" in result["config"]
        assert result["unit_file_path"] == "/lib/systemd/system/nginx.service"
        assert len(result["errors"]) == 0
    
    @patch('saitest.tools.system.get_container_manager')
    def test_inactive_disabled_service(self, mock_get_container_manager):
        """Test inspecting an inactive and disabled service."""
        # Setup mocks
        mock_container = Mock()
        mock_container.exec.side_effect = [
            {"success": True, "output": "● nginx.service - nginx\n   Active: inactive (dead)", "exit_code": 3},
            {"success": False, "output": "inactive", "exit_code": 3},
            {"success": False, "output": "disabled", "exit_code": 1},
            {"success": True, "output": "[Unit]\nDescription=nginx", "exit_code": 0},
            {"success": True, "output": "FragmentPath=/lib/systemd/system/nginx.service", "exit_code": 0}
        ]
        
        mock_container_manager = Mock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_container
        mock_context_manager.__exit__.return_value = None
        mock_container_manager.spawn_container.return_value = mock_context_manager
        mock_get_container_manager.return_value = mock_container_manager
        
        # Execute
        result = inspect_service.invoke({
            "platform": "ubuntu:22.04",
            "service_name": "nginx"
        })
        
        # Verify
        assert result["success"] is True
        assert result["active"] is False
        assert result["enabled"] is False


class TestCheckListeningPorts:
    """Test cases for check_listening_ports tool."""
    
    @patch('saitest.tools.system.get_container_manager')
    def test_parse_listening_ports(self, mock_get_container_manager):
        """Test parsing listening ports from ss output."""
        # Setup mocks
        ss_output = """Netid State  Recv-Q Send-Q Local Address:Port Peer Address:Port Process
tcp   LISTEN 0      128    0.0.0.0:80          0.0.0.0:*     users:(("nginx",pid=123,fd=4))
tcp   LISTEN 0      128    0.0.0.0:443         0.0.0.0:*     users:(("nginx",pid=123,fd=5))
tcp   LISTEN 0      128    127.0.0.1:3306      0.0.0.0:*     users:(("mysqld",pid=456,fd=10))
udp   UNCONN 0      0      0.0.0.0:53          0.0.0.0:*     users:(("systemd-resolve",pid=789,fd=12))
"""
        
        mock_container = Mock()
        mock_container.exec.return_value = {
            "success": True,
            "output": ss_output,
            "exit_code": 0
        }
        
        mock_container_manager = Mock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_container
        mock_context_manager.__exit__.return_value = None
        mock_container_manager.spawn_container.return_value = mock_context_manager
        mock_get_container_manager.return_value = mock_container_manager
        
        # Execute
        result = check_listening_ports.invoke({
            "platform": "ubuntu:22.04"
        })
        
        # Verify
        assert result["success"] is True
        assert len(result["ports"]) == 4
        
        # Check specific ports
        port_80 = next((p for p in result["ports"] if p["port"] == 80), None)
        assert port_80 is not None
        assert port_80["protocol"] == "tcp"
        assert port_80["address"] == "0.0.0.0"
        assert port_80["process"] == "nginx"
        
        port_3306 = next((p for p in result["ports"] if p["port"] == 3306), None)
        assert port_3306 is not None
        assert port_3306["address"] == "127.0.0.1"
    
    @patch('saitest.tools.system.get_container_manager')
    def test_no_listening_ports(self, mock_get_container_manager):
        """Test when no ports are listening."""
        # Setup mocks
        mock_container = Mock()
        mock_container.exec.return_value = {
            "success": True,
            "output": "",
            "exit_code": 0
        }
        
        mock_container_manager = Mock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_container
        mock_context_manager.__exit__.return_value = None
        mock_container_manager.spawn_container.return_value = mock_context_manager
        mock_get_container_manager.return_value = mock_container_manager
        
        # Execute
        result = check_listening_ports.invoke({
            "platform": "ubuntu:22.04"
        })
        
        # Verify
        assert result["success"] is True
        assert len(result["ports"]) == 0


class TestFindConfigFiles:
    """Test cases for find_config_files tool."""
    
    @patch('saitest.tools.system.get_container_manager')
    def test_find_config_directory(self, mock_get_container_manager):
        """Test finding config files in a directory."""
        # Setup mocks
        mock_container = Mock()
        
        # Create a default response for any exec call
        def exec_side_effect(cmd, **kwargs):
            if "test -e /etc/nginx" in cmd and "echo exists" in cmd:
                return {"success": True, "output": "exists", "exit_code": 0}
            elif "test -f /etc/nginx" in cmd or "test -d /etc/nginx" in cmd:
                return {"success": True, "output": "dir", "exit_code": 0}
            elif "find /etc/nginx" in cmd:
                return {"success": True, "output": "/etc/nginx/nginx.conf\n/etc/nginx/mime.types", "exit_code": 0}
            elif "test -e" in cmd:
                return {"success": True, "output": "notfound", "exit_code": 1}
            elif "find /etc" in cmd and "*.conf" in cmd:
                return {"success": True, "output": "/etc/nginx/nginx.conf", "exit_code": 0}
            else:
                return {"success": True, "output": "", "exit_code": 0}
        
        mock_container.exec.side_effect = exec_side_effect
        
        mock_container_manager = Mock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_container
        mock_context_manager.__exit__.return_value = None
        mock_container_manager.spawn_container.return_value = mock_context_manager
        mock_get_container_manager.return_value = mock_container_manager
        
        # Execute
        result = find_config_files.invoke({
            "platform": "ubuntu:22.04",
            "software": "nginx"
        })
        
        # Verify
        assert result["success"] is True
        assert len(result["config_files"]) >= 2
        assert "/etc/nginx/nginx.conf" in result["config_files"]
        assert "/etc/nginx/mime.types" in result["config_files"]
    
    @patch('saitest.tools.system.get_container_manager')
    def test_find_single_config_file(self, mock_get_container_manager):
        """Test finding a single config file."""
        # Setup mocks
        mock_container = Mock()
        
        def exec_side_effect(cmd, **kwargs):
            if "test -e /etc/software.conf" in cmd and "echo exists" in cmd:
                return {"success": True, "output": "exists", "exit_code": 0}
            elif "test -f /etc/software.conf" in cmd:
                return {"success": True, "output": "file", "exit_code": 0}
            elif "test -e" in cmd:
                return {"success": True, "output": "notfound", "exit_code": 1}
            elif "find /etc" in cmd:
                return {"success": True, "output": "", "exit_code": 0}
            else:
                return {"success": True, "output": "", "exit_code": 0}
        
        mock_container.exec.side_effect = exec_side_effect
        
        mock_container_manager = Mock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_container
        mock_context_manager.__exit__.return_value = None
        mock_container_manager.spawn_container.return_value = mock_context_manager
        mock_get_container_manager.return_value = mock_container_manager
        
        # Execute
        result = find_config_files.invoke({
            "platform": "ubuntu:22.04",
            "software": "software"
        })
        
        # Verify
        assert result["success"] is True
        assert "/etc/software.conf" in result["config_files"]
    
    @patch('saitest.tools.system.get_container_manager')
    def test_no_config_files_found(self, mock_get_container_manager):
        """Test when no config files are found."""
        # Setup mocks
        mock_container = Mock()
        
        def exec_side_effect(cmd, **kwargs):
            if "test -e" in cmd:
                return {"success": True, "output": "notfound", "exit_code": 1}
            elif "find" in cmd:
                return {"success": True, "output": "", "exit_code": 0}
            else:
                return {"success": True, "output": "", "exit_code": 0}
        
        mock_container.exec.side_effect = exec_side_effect
        
        mock_container_manager = Mock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_container
        mock_context_manager.__exit__.return_value = None
        mock_container_manager.spawn_container.return_value = mock_context_manager
        mock_get_container_manager.return_value = mock_container_manager
        
        # Execute
        result = find_config_files.invoke({
            "platform": "ubuntu:22.04",
            "software": "nonexistent"
        })
        
        # Verify
        assert result["success"] is True
        assert len(result["config_files"]) == 0


class TestGetContainerManager:
    """Test cases for get_container_manager function."""
    
    def test_singleton_behavior(self):
        """Test that get_container_manager returns the same instance."""
        # Reset global state
        import saitest.tools.system as system_module
        system_module._container_manager = None
        
        # Get manager twice
        with patch('saitest.tools.system.ContainerManager') as mock_cm_class:
            mock_instance = Mock()
            mock_cm_class.return_value = mock_instance
            
            from saitest.tools.system import get_container_manager
            manager1 = get_container_manager()
            manager2 = get_container_manager()
            
            # Should be the same instance
            assert manager1 is manager2
            
            # ContainerManager should only be instantiated once
            assert mock_cm_class.call_count == 1
