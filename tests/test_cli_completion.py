"""Tests for CLI completion functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
import click

from sai.cli.completion import (
    complete_software_names,
    complete_provider_names,
    complete_action_names,
    complete_config_keys,
    complete_log_levels,
    complete_saidata_files
)
from sai.models.config import SaiConfig


class TestCLICompletion:
    """Test CLI completion functions."""
    
    def test_complete_software_names(self):
        """Test software name completion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test saidata files
            (temp_path / "nginx.yaml").touch()
            (temp_path / "apache.yml").touch()
            (temp_path / "mysql.yaml").touch()
            
            # Mock the SaidataLoader to return our test paths
            mock_loader = Mock()
            mock_loader.get_search_paths.return_value = [temp_path]
            
            with patch('sai.cli.completion.SaidataLoader', return_value=mock_loader):
                ctx = Mock()
                param = Mock()
                
                # Test completion with partial match
                result = complete_software_names(ctx, param, "ngi")
                assert "nginx" in result
                assert "apache" not in result
                assert "mysql" not in result
                
                # Test completion with no match
                result = complete_software_names(ctx, param, "xyz")
                assert len(result) == 0
                
                # Test completion with empty string (should return all)
                result = complete_software_names(ctx, param, "")
                assert "nginx" in result
                assert "apache" in result
                assert "mysql" in result
    
    def test_complete_software_names_error_handling(self):
        """Test software name completion error handling."""
        with patch('sai.cli.completion.get_config', side_effect=Exception("Config error")):
            ctx = Mock()
            param = Mock()
            
            result = complete_software_names(ctx, param, "test")
            assert result == []
    
    def test_complete_provider_names(self):
        """Test provider name completion."""
        mock_providers = {
            "apt": Mock(),
            "brew": Mock(),
            "yum": Mock(),
            "pacman": Mock()
        }
        
        with patch('sai.cli.completion.ProviderLoader') as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load_all_providers.return_value = mock_providers
            mock_loader_class.return_value = mock_loader
            
            ctx = Mock()
            param = Mock()
            
            # Test completion with partial match
            result = complete_provider_names(ctx, param, "a")
            assert "apt" in result
            assert "brew" not in result
            
            # Test completion with no match
            result = complete_provider_names(ctx, param, "xyz")
            assert len(result) == 0
            
            # Test completion with empty string
            result = complete_provider_names(ctx, param, "")
            assert len(result) == 4
            assert all(name in result for name in mock_providers.keys())
    
    def test_complete_provider_names_error_handling(self):
        """Test provider name completion error handling."""
        with patch('sai.cli.completion.ProviderLoader', side_effect=Exception("Loader error")):
            ctx = Mock()
            param = Mock()
            
            result = complete_provider_names(ctx, param, "test")
            assert result == []
    
    def test_complete_action_names(self):
        """Test action name completion."""
        # Mock provider with actions
        mock_provider = Mock()
        mock_provider.is_available.return_value = True
        mock_provider.get_supported_actions.return_value = ["install", "uninstall", "status", "info"]
        
        mock_providers = {"test-provider": Mock()}
        
        with patch('sai.cli.completion.ProviderLoader') as mock_loader_class, \
             patch('sai.providers.base.BaseProvider', return_value=mock_provider):
            
            mock_loader = Mock()
            mock_loader.load_all_providers.return_value = mock_providers
            mock_loader_class.return_value = mock_loader
            
            ctx = Mock()
            param = Mock()
            
            # Test completion with partial match
            result = complete_action_names(ctx, param, "in")
            assert "install" in result
            assert "info" in result
            assert "status" not in result
            
            # Test completion with no match
            result = complete_action_names(ctx, param, "xyz")
            assert len(result) == 0
    
    def test_complete_action_names_unavailable_provider(self):
        """Test action name completion with unavailable provider."""
        # Mock provider that's not available
        mock_provider = Mock()
        mock_provider.is_available.return_value = False
        
        mock_providers = {"test-provider": Mock()}
        
        with patch('sai.cli.completion.ProviderLoader') as mock_loader_class, \
             patch('sai.providers.base.BaseProvider', return_value=mock_provider):
            
            mock_loader = Mock()
            mock_loader.load_all_providers.return_value = mock_providers
            mock_loader_class.return_value = mock_loader
            
            ctx = Mock()
            param = Mock()
            
            result = complete_action_names(ctx, param, "in")
            assert len(result) == 0  # No actions from unavailable provider
    
    def test_complete_config_keys(self):
        """Test configuration key completion."""
        ctx = Mock()
        param = Mock()
        
        # Test completion with partial match
        result = complete_config_keys(ctx, param, "log")
        assert "log_level" in result
        
        # Test completion with no match
        result = complete_config_keys(ctx, param, "xyz")
        assert len(result) == 0
        
        # Test completion with empty string (should return all keys)
        result = complete_config_keys(ctx, param, "")
        assert len(result) > 0
        assert "log_level" in result
        assert "cache_enabled" in result
    
    def test_complete_config_keys_fallback(self):
        """Test configuration key completion fallback."""
        with patch('sai.models.config.SaiConfig', side_effect=Exception("Config error")):
            ctx = Mock()
            param = Mock()
            
            # Should fall back to hardcoded list
            result = complete_config_keys(ctx, param, "log")
            assert "log_level" in result
    
    def test_complete_log_levels(self):
        """Test log level completion."""
        ctx = Mock()
        param = Mock()
        
        # Test completion with partial match
        result = complete_log_levels(ctx, param, "d")
        assert "debug" in result
        assert "info" not in result
        
        # Test completion with no match
        result = complete_log_levels(ctx, param, "xyz")
        assert len(result) == 0
        
        # Test completion with empty string
        result = complete_log_levels(ctx, param, "")
        expected_levels = ['debug', 'info', 'warning', 'error']
        assert all(level in result for level in expected_levels)
    
    def test_complete_saidata_files(self):
        """Test saidata file completion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "nginx.yaml").touch()
            (temp_path / "apache.yml").touch()
            (temp_path / "config.json").touch()  # Should be ignored
            
            mock_config = Mock(spec=SaiConfig)
            mock_config.saidata_paths = [str(temp_path)]
            
            with patch('sai.cli.completion.get_config', return_value=mock_config):
                ctx = Mock()
                param = Mock()
                
                # Test completion with partial match
                result = complete_saidata_files(ctx, param, str(temp_path / "ng"))
                assert any("nginx.yaml" in path for path in result)
                
                # Test completion with directory path
                result = complete_saidata_files(ctx, param, str(temp_path))
                assert len(result) >= 2  # Should find yaml files
    
    def test_complete_saidata_files_error_handling(self):
        """Test saidata file completion error handling."""
        with patch('sai.cli.completion.get_config', side_effect=Exception("Config error")):
            ctx = Mock()
            param = Mock()
            
            result = complete_saidata_files(ctx, param, "test")
            # Should still find files in current directory even if config fails
            assert isinstance(result, list)
    
    def test_complete_saidata_files_current_directory(self):
        """Test saidata file completion in current directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)
                
                # Create test files in current directory
                Path("test.yaml").touch()
                Path("example.yml").touch()
                
                # Mock config to fail so it uses current directory
                with patch('sai.cli.completion.get_config', side_effect=Exception("Config error")):
                    ctx = Mock()
                    param = Mock()
                    
                    result = complete_saidata_files(ctx, param, "test")
                    assert any("test.yaml" in path for path in result)
            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    pytest.main([__file__])