"""Tests for configuration management."""

import json
import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from saigen.models.config import SaigenConfig, LLMConfig
from saigen.utils.config import ConfigManager


class TestConfigManager:
    """Test configuration manager functionality."""
    
    def test_create_default_config(self):
        """Test default configuration creation."""
        manager = ConfigManager()
        config = manager._create_default_config()
        
        assert isinstance(config, SaigenConfig)
        assert config.config_version == "0.1.0"
        assert len(config.llm_providers) >= 1  # Should have default OpenAI config
    
    def test_load_config_from_yaml(self):
        """Test loading configuration from YAML file."""
        config_data = {
            'config_version': '0.1.0',
            'log_level': 'debug',
            'llm_providers': {
                'openai': {
                    'provider': 'openai',
                    'model': 'gpt-4',
                    'max_tokens': 2000
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            manager = ConfigManager(temp_path)
            config = manager.load_config()
            
            assert config.log_level == 'debug'
            assert 'openai' in config.llm_providers
            assert config.llm_providers['openai'].model == 'gpt-4'
        finally:
            temp_path.unlink()
    
    def test_load_config_from_json(self):
        """Test loading configuration from JSON file."""
        config_data = {
            'config_version': '0.1.0',
            'log_level': 'info',
            'llm_providers': {
                'anthropic': {
                    'provider': 'anthropic',
                    'model': 'claude-3-sonnet-20240229'
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            manager = ConfigManager(temp_path)
            config = manager.load_config()
            
            assert config.log_level == 'info'
            assert 'anthropic' in config.llm_providers
        finally:
            temp_path.unlink()
    
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-openai-key',
        'ANTHROPIC_API_KEY': 'test-anthropic-key',
        'SAIGEN_LOG_LEVEL': 'debug'
    })
    def test_env_overrides(self):
        """Test environment variable overrides."""
        manager = ConfigManager()
        config = manager.load_config()
        
        assert 'openai' in config.llm_providers
        assert config.llm_providers['openai'].api_key.get_secret_value() == 'test-openai-key'
        assert 'anthropic' in config.llm_providers
        assert config.llm_providers['anthropic'].api_key.get_secret_value() == 'test-anthropic-key'
        assert config.log_level == 'debug'
    
    def test_invalid_config_file(self):
        """Test handling of invalid configuration files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)
        
        try:
            manager = ConfigManager(temp_path)
            with pytest.raises(ValueError, match="Invalid configuration file format"):
                manager.load_config()
        finally:
            temp_path.unlink()
    
    def test_config_validation(self):
        """Test configuration validation."""
        manager = ConfigManager()
        config = manager.load_config()
        
        issues = manager.validate_config()
        # Should have no critical issues with default config
        assert isinstance(issues, list)
    
    def test_masked_config_display(self):
        """Test that sensitive data is masked in config display."""
        config = SaigenConfig()
        config.llm_providers['openai'] = LLMConfig(
            provider='openai',
            api_key='secret-key-123'
        )
        
        masked = config.get_masked_config()
        assert masked['llm_providers']['openai']['api_key'] == '***masked***'


class TestSaigenConfig:
    """Test SaigenConfig model."""
    
    def test_default_config_creation(self):
        """Test creating default configuration."""
        config = SaigenConfig()
        
        assert config.config_version == "0.1.0"
        assert config.log_level == "info"
        assert len(config.llm_providers) >= 1
        assert config.cache.directory == Path.home() / ".saigen" / "cache"
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config_data = {
            'config_version': '0.1.0',
            'llm_providers': {
                'openai': {
                    'provider': 'openai',
                    'model': 'gpt-3.5-turbo'
                }
            }
        }
        config = SaigenConfig(**config_data)
        assert config.config_version == '0.1.0'
        
        # Invalid config version format
        with pytest.raises(ValidationError):
            SaigenConfig(config_version='invalid-version')


if __name__ == '__main__':
    pytest.main([__file__])