"""Tests for provider loading system."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from sai.providers.loader import ProviderLoader, ProviderLoadError, ProviderValidationError
from sai.providers.base import BaseProvider, ProviderFactory


class TestProviderLoader:
    """Test cases for ProviderLoader."""
    
    def test_scan_provider_directory_success(self, tmp_path):
        """Test successful directory scanning."""
        # Create test YAML files
        (tmp_path / "apt.yaml").write_text("test: data")
        (tmp_path / "brew.yml").write_text("test: data")
        (tmp_path / "not_yaml.txt").write_text("ignored")
        
        # Create specialized subdirectory
        specialized_dir = tmp_path / "specialized"
        specialized_dir.mkdir()
        (specialized_dir / "docker.yaml").write_text("test: data")
        
        loader = ProviderLoader()
        files = loader.scan_provider_directory(tmp_path)
        
        assert len(files) == 3
        file_names = [f.name for f in files]
        assert "apt.yaml" in file_names
        assert "brew.yml" in file_names
        assert "docker.yaml" in file_names
        assert "not_yaml.txt" not in file_names
    
    def test_scan_provider_directory_not_found(self):
        """Test scanning non-existent directory."""
        loader = ProviderLoader()
        
        with pytest.raises(FileNotFoundError):
            loader.scan_provider_directory(Path("/nonexistent"))
    
    def test_load_provider_file_success(self, tmp_path):
        """Test successful provider file loading."""
        # Create a valid provider YAML
        provider_data = {
            "version": "1.0",
            "provider": {
                "name": "test-provider",
                "type": "package_manager"
            },
            "actions": {
                "install": {
                    "template": "test install {{saidata.metadata.name}}"
                }
            }
        }
        
        provider_file = tmp_path / "test.yaml"
        with open(provider_file, 'w') as f:
            yaml.dump(provider_data, f)
        
        # Mock schema loading to avoid dependency on schema file
        with patch.object(ProviderLoader, '_load_schema'):
            loader = ProviderLoader()
            loader._schema_validator = None  # Skip JSON schema validation
            
            result = loader.load_provider_file(provider_file)
            
            assert result.provider.name == "test-provider"
            assert result.provider.type == "package_manager"
            assert "install" in result.actions
    
    def test_load_provider_file_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML file."""
        provider_file = tmp_path / "invalid.yaml"
        provider_file.write_text("invalid: yaml: content: [")
        
        with patch.object(ProviderLoader, '_load_schema'):
            loader = ProviderLoader()
            
            with pytest.raises(ProviderLoadError) as exc_info:
                loader.load_provider_file(provider_file)
            
            assert "Failed to parse YAML" in str(exc_info.value)
    
    def test_load_provider_file_validation_error(self, tmp_path):
        """Test loading file that fails Pydantic validation."""
        # Create invalid provider data (missing required fields)
        provider_data = {
            "version": "1.0",
            "provider": {
                "name": "test-provider"
                # Missing required 'type' field
            },
            "actions": {}
        }
        
        provider_file = tmp_path / "invalid.yaml"
        with open(provider_file, 'w') as f:
            yaml.dump(provider_data, f)
        
        with patch.object(ProviderLoader, '_load_schema'):
            loader = ProviderLoader()
            loader._schema_validator = None  # Skip JSON schema validation
            
            with pytest.raises(ProviderValidationError) as exc_info:
                loader.load_provider_file(provider_file)
            
            assert "Pydantic model validation failed" in str(exc_info.value)
    
    def test_load_providers_from_directory(self, tmp_path):
        """Test loading multiple providers from directory."""
        # Create valid provider files
        providers_data = [
            {
                "version": "1.0",
                "provider": {"name": "apt", "type": "package_manager"},
                "actions": {"install": {"template": "apt install {{saidata.metadata.name}}"}}
            },
            {
                "version": "1.0", 
                "provider": {"name": "brew", "type": "package_manager"},
                "actions": {"install": {"template": "brew install {{saidata.metadata.name}}"}}
            }
        ]
        
        for i, data in enumerate(providers_data):
            provider_file = tmp_path / f"provider{i}.yaml"
            with open(provider_file, 'w') as f:
                yaml.dump(data, f)
        
        # Create one invalid file
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: [")
        
        with patch.object(ProviderLoader, '_load_schema'):
            loader = ProviderLoader()
            loader._schema_validator = None
            
            providers = loader.load_providers_from_directory(tmp_path)
            
            # Should load valid providers and skip invalid ones
            assert len(providers) == 2
            assert "apt" in providers
            assert "brew" in providers


class TestBaseProvider:
    """Test cases for BaseProvider."""
    
    def test_provider_initialization(self):
        """Test provider initialization with ProviderData."""
        from sai.models.provider_data import ProviderData, Provider, Action
        
        provider_data = ProviderData(
            version="1.0",
            provider=Provider(
                name="test-provider",
                display_name="Test Provider",
                description="A test provider",
                type="package_manager",
                platforms=["linux"],
                capabilities=["install", "uninstall"]
            ),
            actions={
                "install": Action(template="test install {{saidata.metadata.name}}")
            }
        )
        
        provider = BaseProvider(provider_data)
        
        assert provider.name == "test-provider"
        assert provider.display_name == "Test Provider"
        assert provider.description == "A test provider"
        assert provider.type == "package_manager"
        assert provider.platforms == ["linux"]
        assert provider.capabilities == ["install", "uninstall"]
        assert provider.get_supported_actions() == ["install"]
        assert provider.has_action("install") is True
        assert provider.has_action("uninstall") is False


class TestProviderFactory:
    """Test cases for ProviderFactory."""
    
    def test_create_providers(self, tmp_path):
        """Test provider creation through factory."""
        # Create a valid provider YAML
        provider_data = {
            "version": "1.0",
            "provider": {
                "name": "test-provider",
                "type": "package_manager"
            },
            "actions": {
                "install": {
                    "template": "test install {{saidata.metadata.name}}"
                }
            }
        }
        
        provider_file = tmp_path / "test.yaml"
        with open(provider_file, 'w') as f:
            yaml.dump(provider_data, f)
        
        # Mock the loader to return our test directory
        with patch.object(ProviderLoader, '_load_schema'):
            with patch.object(ProviderLoader, 'get_default_provider_directories', return_value=[tmp_path]):
                factory = ProviderFactory.create_default_factory()
                providers = factory.create_providers()
                
                assert len(providers) == 1
                assert providers[0].name == "test-provider"
                assert isinstance(providers[0], BaseProvider)