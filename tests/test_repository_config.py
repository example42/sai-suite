"""Tests for repository configuration management."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from saigen.repositories.config import (
    RepositoryConfig, RepositoryConfigManager, 
    create_default_configs, validate_repository_config,
    load_provider_configs_from_yaml
)
from saigen.utils.errors import ConfigurationError


class TestRepositoryConfig:
    """Test RepositoryConfig model."""
    
    def test_repository_config_creation(self):
        """Test creating a repository configuration."""
        config = RepositoryConfig(
            name="test-repo",
            type="apt",
            platform="linux",
            url="https://example.com/repo",
            enabled=True,
            priority=10
        )
        
        assert config.name == "test-repo"
        assert config.type == "apt"
        assert config.platform == "linux"
        assert config.url == "https://example.com/repo"
        assert config.enabled is True
        assert config.priority == 10
        assert config.cache_ttl_hours == 24  # default
    
    def test_repository_config_defaults(self):
        """Test repository configuration with defaults."""
        config = RepositoryConfig(
            name="minimal-repo",
            type="brew",
            platform="macos"
        )
        
        assert config.url is None
        assert config.enabled is True
        assert config.priority == 1
        assert config.cache_ttl_hours == 24
        assert config.timeout == 300
        assert config.architecture is None
        assert config.parsing == {}
        assert config.credentials == {}
        assert config.metadata == {}
    
    def test_to_repository_info(self):
        """Test conversion to RepositoryInfo."""
        config = RepositoryConfig(
            name="test-repo",
            type="apt",
            platform="linux",
            url="https://example.com/repo",
            architecture=["amd64", "arm64"],
            metadata={"description": "Test repo", "maintainer": "Test"}
        )
        
        repo_info = config.to_repository_info()
        
        assert repo_info.name == "test-repo"
        assert repo_info.type == "apt"
        assert repo_info.platform == "linux"
        assert repo_info.url == "https://example.com/repo"
        assert repo_info.architecture == ["amd64", "arm64"]
        assert repo_info.description == "Test repo"
        assert repo_info.maintainer == "Test"


class TestRepositoryConfigManager:
    """Test RepositoryConfigManager."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sample_config_data(self):
        """Sample configuration data."""
        return {
            'repositories': [
                {
                    'name': 'ubuntu-main',
                    'type': 'apt',
                    'platform': 'linux',
                    'url': 'http://archive.ubuntu.com/ubuntu/',
                    'enabled': True,
                    'priority': 10
                },
                {
                    'name': 'homebrew-core',
                    'type': 'brew',
                    'platform': 'macos',
                    'enabled': True,
                    'priority': 8
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_load_configs_empty_directory(self, temp_config_dir):
        """Test loading configs from empty directory."""
        manager = RepositoryConfigManager(temp_config_dir)
        await manager.load_configs()
        
        assert manager._loaded is True
        assert len(manager.get_all_configs()) == 0
    
    @pytest.mark.asyncio
    async def test_load_configs_with_yaml_file(self, temp_config_dir, sample_config_data):
        """Test loading configs from YAML file."""
        config_file = temp_config_dir / "test.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        manager = RepositoryConfigManager(temp_config_dir)
        await manager.load_configs()
        
        configs = manager.get_all_configs()
        assert len(configs) == 2
        
        ubuntu_config = manager.get_config('ubuntu-main')
        assert ubuntu_config is not None
        assert ubuntu_config.type == 'apt'
        assert ubuntu_config.platform == 'linux'
        
        brew_config = manager.get_config('homebrew-core')
        assert brew_config is not None
        assert brew_config.type == 'brew'
        assert brew_config.platform == 'macos'
    
    @pytest.mark.asyncio
    async def test_load_configs_single_repository(self, temp_config_dir):
        """Test loading single repository config."""
        single_config = {
            'name': 'single-repo',
            'type': 'generic',
            'platform': 'linux',
            'url': 'https://example.com/api'
        }
        
        config_file = temp_config_dir / "single.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(single_config, f)
        
        manager = RepositoryConfigManager(temp_config_dir)
        await manager.load_configs()
        
        configs = manager.get_all_configs()
        assert len(configs) == 1
        assert configs[0].name == 'single-repo'
    
    @pytest.mark.asyncio
    async def test_load_configs_invalid_yaml(self, temp_config_dir):
        """Test handling invalid YAML file."""
        config_file = temp_config_dir / "invalid.yaml"
        with open(config_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        manager = RepositoryConfigManager(temp_config_dir)
        # Should not raise exception, just log warning
        await manager.load_configs()
        
        assert len(manager.get_all_configs()) == 0
    
    @pytest.mark.asyncio
    async def test_load_configs_missing_required_fields(self, temp_config_dir):
        """Test handling config with missing required fields."""
        invalid_config = {
            'repositories': [
                {
                    'name': 'incomplete-repo',
                    # Missing 'type' and 'platform'
                    'url': 'https://example.com'
                }
            ]
        }
        
        config_file = temp_config_dir / "incomplete.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(invalid_config, f)
        
        manager = RepositoryConfigManager(temp_config_dir)
        # Should not raise exception, just log warning
        await manager.load_configs()
        
        assert len(manager.get_all_configs()) == 0
    
    def test_get_configs_by_type(self, temp_config_dir):
        """Test filtering configs by type."""
        manager = RepositoryConfigManager(temp_config_dir)
        
        # Add test configs
        manager._configs = {
            'apt1': RepositoryConfig(name='apt1', type='apt', platform='linux'),
            'apt2': RepositoryConfig(name='apt2', type='apt', platform='linux'),
            'brew1': RepositoryConfig(name='brew1', type='brew', platform='macos')
        }
        
        apt_configs = manager.get_configs_by_type('apt')
        assert len(apt_configs) == 2
        assert all(config.type == 'apt' for config in apt_configs)
        
        brew_configs = manager.get_configs_by_type('brew')
        assert len(brew_configs) == 1
        assert brew_configs[0].type == 'brew'
    
    def test_get_configs_by_platform(self, temp_config_dir):
        """Test filtering configs by platform."""
        manager = RepositoryConfigManager(temp_config_dir)
        
        # Add test configs
        manager._configs = {
            'linux1': RepositoryConfig(name='linux1', type='apt', platform='linux'),
            'linux2': RepositoryConfig(name='linux2', type='dnf', platform='linux'),
            'macos1': RepositoryConfig(name='macos1', type='brew', platform='macos')
        }
        
        linux_configs = manager.get_configs_by_platform('linux')
        assert len(linux_configs) == 2
        assert all(config.platform == 'linux' for config in linux_configs)
        
        macos_configs = manager.get_configs_by_platform('macos')
        assert len(macos_configs) == 1
        assert macos_configs[0].platform == 'macos'
    
    def test_get_enabled_configs(self, temp_config_dir):
        """Test filtering enabled configs."""
        manager = RepositoryConfigManager(temp_config_dir)
        
        # Add test configs
        manager._configs = {
            'enabled1': RepositoryConfig(name='enabled1', type='apt', platform='linux', enabled=True),
            'enabled2': RepositoryConfig(name='enabled2', type='brew', platform='macos', enabled=True),
            'disabled1': RepositoryConfig(name='disabled1', type='winget', platform='windows', enabled=False)
        }
        
        enabled_configs = manager.get_enabled_configs()
        assert len(enabled_configs) == 2
        assert all(config.enabled for config in enabled_configs)
    
    def test_get_sorted_configs(self, temp_config_dir):
        """Test getting configs sorted by priority."""
        manager = RepositoryConfigManager(temp_config_dir)
        
        # Add test configs with different priorities
        manager._configs = {
            'low': RepositoryConfig(name='low', type='apt', platform='linux', priority=1, enabled=True),
            'high': RepositoryConfig(name='high', type='brew', platform='linux', priority=10, enabled=True),
            'medium': RepositoryConfig(name='medium', type='dnf', platform='linux', priority=5, enabled=True),
            'disabled': RepositoryConfig(name='disabled', type='winget', platform='linux', priority=20, enabled=False)
        }
        
        sorted_configs = manager.get_sorted_configs('linux')
        assert len(sorted_configs) == 3  # Only enabled configs
        assert sorted_configs[0].name == 'high'  # Highest priority first
        assert sorted_configs[1].name == 'medium'
        assert sorted_configs[2].name == 'low'


class TestRepositoryConfigValidation:
    """Test repository configuration validation."""
    
    def test_validate_valid_config(self):
        """Test validation of valid config."""
        config = RepositoryConfig(
            name="valid-repo",
            type="apt",
            platform="linux",
            url="https://example.com/repo",
            priority=10,
            cache_ttl_hours=24
        )
        
        errors = validate_repository_config(config)
        assert len(errors) == 0
    
    def test_validate_missing_name(self):
        """Test validation with missing name."""
        config = RepositoryConfig(
            name="",
            type="apt",
            platform="linux"
        )
        
        errors = validate_repository_config(config)
        assert len(errors) > 0
        assert any("name is required" in error for error in errors)
    
    def test_validate_invalid_platform(self):
        """Test validation with invalid platform."""
        config = RepositoryConfig(
            name="test-repo",
            type="apt",
            platform="invalid-platform"
        )
        
        errors = validate_repository_config(config)
        assert len(errors) > 0
        assert any("Invalid platform" in error for error in errors)
    
    def test_validate_invalid_type(self):
        """Test validation with invalid repository type."""
        config = RepositoryConfig(
            name="test-repo",
            type="invalid-type",
            platform="linux"
        )
        
        errors = validate_repository_config(config)
        assert len(errors) > 0
        assert any("Invalid repository type" in error for error in errors)
    
    def test_validate_invalid_priority(self):
        """Test validation with invalid priority."""
        config = RepositoryConfig(
            name="test-repo",
            type="apt",
            platform="linux",
            priority=150  # Out of range
        )
        
        errors = validate_repository_config(config)
        assert len(errors) > 0
        assert any("Priority must be between" in error for error in errors)
    
    def test_validate_invalid_cache_ttl(self):
        """Test validation with invalid cache TTL."""
        config = RepositoryConfig(
            name="test-repo",
            type="apt",
            platform="linux",
            cache_ttl_hours=0  # Too low
        )
        
        errors = validate_repository_config(config)
        assert len(errors) > 0
        assert any("Cache TTL must be at least" in error for error in errors)


class TestRepositoryConfigUtilities:
    """Test utility functions."""
    
    def test_create_default_configs(self):
        """Test creating default configurations."""
        defaults = create_default_configs()
        
        assert len(defaults) > 0
        assert isinstance(defaults, list)
        
        # Check that all configs have required fields
        for config_data in defaults:
            assert 'name' in config_data
            assert 'type' in config_data
            assert 'platform' in config_data
    
    def test_load_provider_configs_from_yaml_multiple(self):
        """Test loading multiple configs from YAML."""
        yaml_content = """
repositories:
  - name: repo1
    type: apt
    platform: linux
  - name: repo2
    type: brew
    platform: macos
"""
        
        configs = load_provider_configs_from_yaml(yaml_content)
        assert len(configs) == 2
        assert configs[0].name == 'repo1'
        assert configs[1].name == 'repo2'
    
    def test_load_provider_configs_from_yaml_single(self):
        """Test loading single config from YAML."""
        yaml_content = """
name: single-repo
type: generic
platform: linux
url: https://example.com
"""
        
        configs = load_provider_configs_from_yaml(yaml_content)
        assert len(configs) == 1
        assert configs[0].name == 'single-repo'
    
    def test_load_provider_configs_invalid_yaml(self):
        """Test handling invalid YAML."""
        yaml_content = "invalid: yaml: [content"
        
        with pytest.raises(ConfigurationError):
            load_provider_configs_from_yaml(yaml_content)
    
    @pytest.mark.asyncio
    async def test_save_default_configs(self):
        """Test saving default configurations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            from saigen.repositories.config import save_default_configs
            await save_default_configs(config_dir)
            
            # Check that files were created
            config_files = list(config_dir.glob("*.yaml"))
            assert len(config_files) > 0
            
            # Check that files contain valid YAML
            for config_file in config_files:
                with open(config_file, 'r') as f:
                    data = yaml.safe_load(f)
                    assert 'repositories' in data
                    assert isinstance(data['repositories'], list)