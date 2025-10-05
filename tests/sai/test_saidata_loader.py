"""Tests for SaidataLoader functionality."""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
import yaml

from sai.core.saidata_loader import SaidataLoader, ValidationResult, SaidataNotFoundError, ValidationError
from sai.models.config import SaiConfig
from sai.models.saidata import SaiData


class TestSaidataLoader:
    """Test SaidataLoader functionality."""
    
    def test_initialization(self):
        """Test SaidataLoader initialization."""
        config = SaiConfig()
        loader = SaidataLoader(config)
        assert loader.config == config
        assert loader._schema_cache is None
        
        # Test with no config
        loader_no_config = SaidataLoader()
        assert isinstance(loader_no_config.config, SaiConfig)
    
    def test_get_search_paths(self):
        """Test search path resolution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config = SaiConfig(saidata_paths=[str(temp_path), "/nonexistent/path"])
            loader = SaidataLoader(config)
            
            search_paths = loader.get_search_paths()
            assert len(search_paths) == 1
            assert temp_path.resolve() in [p.resolve() for p in search_paths]
    
    def test_find_hierarchical_software(self):
        """Test finding software in hierarchical structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create hierarchical structure
            # software/ng/nginx/default.yaml
            nginx_dir = temp_path / "software" / "ng" / "nginx"
            nginx_dir.mkdir(parents=True)
            (nginx_dir / "default.yaml").write_text("version: '0.2'\nmetadata:\n  name: nginx")
            
            # software/ap/apache/default.yaml
            apache_dir = temp_path / "software" / "ap" / "apache"
            apache_dir.mkdir(parents=True)
            (apache_dir / "default.yaml").write_text("version: '0.2'\nmetadata:\n  name: apache")
            
            # software/my/mysql/default.yaml
            mysql_dir = temp_path / "software" / "my" / "mysql"
            mysql_dir.mkdir(parents=True)
            (mysql_dir / "default.yaml").write_text("version: '0.2'\nmetadata:\n  name: mysql")
            
            config = SaiConfig(saidata_paths=[str(temp_path)])
            loader = SaidataLoader(config)
            
            # Test finding all software in hierarchical structure
            software_list = loader.find_all_hierarchical_software(temp_path)
            assert "nginx" in software_list
            assert "apache" in software_list
            assert "mysql" in software_list
            assert len(software_list) == 3
            
            # Test expected paths
            nginx_path = loader.get_expected_hierarchical_path("nginx", temp_path)
            assert nginx_path.hierarchical_path == temp_path / "software" / "ng" / "nginx" / "default.yaml"
            
            apache_path = loader.get_expected_hierarchical_path("apache", temp_path)
            assert apache_path.hierarchical_path == temp_path / "software" / "ap" / "apache" / "default.yaml"
    
    def test_load_saidata_file_yaml(self):
        """Test loading YAML saidata files."""
        test_data = {
            "version": "0.2.0",
            "metadata": {"name": "test"}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            temp_path = Path(f.name)
        
        try:
            loader = SaidataLoader()
            loaded_data = loader._load_saidata_file(temp_path)
            assert loaded_data == test_data
        finally:
            temp_path.unlink()
    
    def test_load_saidata_file_json(self):
        """Test loading JSON saidata files."""
        test_data = {
            "version": "0.2.0",
            "metadata": {"name": "test"}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_path = Path(f.name)
        
        try:
            loader = SaidataLoader()
            loaded_data = loader._load_saidata_file(temp_path)
            assert loaded_data == test_data
        finally:
            temp_path.unlink()
    
    def test_load_saidata_file_invalid_format(self):
        """Test loading file with invalid format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("invalid content")
            temp_path = Path(f.name)
        
        try:
            loader = SaidataLoader()
            with pytest.raises(ValueError, match="Unsupported file format"):
                loader._load_saidata_file(temp_path)
        finally:
            temp_path.unlink()
    
    def test_deep_merge(self):
        """Test deep merging of dictionaries."""
        loader = SaidataLoader()
        
        base = {
            "metadata": {
                "name": "test",
                "description": "base description"
            },
            "packages": [{"name": "pkg1"}],
            "providers": {
                "apt": {"packages": [{"name": "apt-pkg1"}]}
            }
        }
        
        override = {
            "metadata": {
                "description": "override description",
                "tags": ["web"]
            },
            "packages": [{"name": "pkg2"}],
            "providers": {
                "apt": {"packages": [{"name": "apt-pkg2"}]},
                "brew": {"packages": [{"name": "brew-pkg1"}]}
            }
        }
        
        result = loader._deep_merge(base, override)
        
        # Check metadata merge
        assert result["metadata"]["name"] == "test"  # From base
        assert result["metadata"]["description"] == "override description"  # Overridden
        assert result["metadata"]["tags"] == ["web"]  # From override
        
        # Check list merge (packages)
        assert len(result["packages"]) == 2
        assert {"name": "pkg1"} in result["packages"]
        assert {"name": "pkg2"} in result["packages"]
        
        # Check nested dict merge (providers)
        assert "apt" in result["providers"]
        assert "brew" in result["providers"]
        assert len(result["providers"]["apt"]["packages"]) == 2
    
    def test_merge_saidata_files(self):
        """Test merging multiple saidata files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create base file
            base_data = {
                "version": "0.2.0",
                "metadata": {"name": "nginx", "description": "base"},
                "packages": [{"name": "nginx"}]
            }
            base_file = temp_path / "base.yaml"
            with open(base_file, 'w') as f:
                yaml.dump(base_data, f)
            
            # Create override file
            override_data = {
                "version": "0.2.0",
                "metadata": {"description": "override"},
                "packages": [{"name": "nginx-extras"}]
            }
            override_file = temp_path / "override.yaml"
            with open(override_file, 'w') as f:
                yaml.dump(override_data, f)
            
            loader = SaidataLoader()
            result = loader._merge_saidata_files([override_file, base_file])
            
            assert result["metadata"]["name"] == "nginx"
            assert result["metadata"]["description"] == "override"
            assert len(result["packages"]) == 2
    
    def test_validate_saidata_valid(self):
        """Test validation of valid saidata."""
        valid_data = {
            "version": "0.2.0",
            "metadata": {
                "name": "test-software",
                "description": "Test software"
            },
            "packages": [{"name": "test-package"}],
            "providers": {
                "apt": {"packages": [{"name": "test-package"}]}
            }
        }
        
        loader = SaidataLoader()
        result = loader.validate_saidata(valid_data)
        
        assert result.valid
        assert len(result.errors) == 0
    
    def test_validate_saidata_invalid(self):
        """Test validation of invalid saidata."""
        invalid_data = {
            "version": "0.2.0"
            # Missing required metadata
        }
        
        loader = SaidataLoader()
        result = loader.validate_saidata(invalid_data)
        
        assert not result.valid
        assert len(result.errors) > 0
        assert any("metadata" in error.lower() for error in result.errors)
    
    def test_validate_saidata_warnings(self):
        """Test validation warnings."""
        data_with_warnings = {
            "version": "0.2.0",
            "metadata": {
                "name": "test-software"
                # Missing description - should generate warning
            }
            # No packages - should generate warning
        }
        
        loader = SaidataLoader()
        result = loader.validate_saidata(data_with_warnings)
        
        assert result.valid  # Should still be valid
        assert result.has_warnings
        assert any("description" in warning.lower() for warning in result.warnings)
        assert any("packages" in warning.lower() for warning in result.warnings)
    
    def test_load_saidata_success(self):
        """Test successful saidata loading from hierarchical structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            test_data = {
                "version": "0.2.0",
                "metadata": {
                    "name": "nginx",
                    "description": "Web server"
                },
                "packages": [{"name": "nginx"}],
                "services": [{"name": "nginx", "type": "systemd"}]
            }
            
            # Create hierarchical structure: software/ng/nginx/default.yaml
            nginx_dir = temp_path / "software" / "ng" / "nginx"
            nginx_dir.mkdir(parents=True)
            saidata_file = nginx_dir / "default.yaml"
            with open(saidata_file, 'w') as f:
                yaml.dump(test_data, f)
            
            config = SaiConfig(saidata_paths=[str(temp_path)])
            loader = SaidataLoader(config)
            
            saidata = loader.load_saidata("nginx")
            
            assert isinstance(saidata, SaiData)
            assert saidata.metadata.name == "nginx"
            assert saidata.metadata.description == "Web server"
            assert len(saidata.packages) == 1
            assert saidata.packages[0].name == "nginx"
            assert len(saidata.services) == 1
            assert saidata.services[0].name == "nginx"
    
    def test_load_saidata_not_found(self):
        """Test loading non-existent saidata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = SaiConfig(saidata_paths=[temp_dir])
            loader = SaidataLoader(config)
            
            with pytest.raises(SaidataNotFoundError):
                loader.load_saidata("nonexistent")
    
    def test_load_saidata_validation_error(self):
        """Test loading invalid saidata from hierarchical structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            invalid_data = {
                "version": "0.2.0"
                # Missing required metadata
            }
            
            # Create hierarchical structure: software/in/invalid/default.yaml
            invalid_dir = temp_path / "software" / "in" / "invalid"
            invalid_dir.mkdir(parents=True)
            saidata_file = invalid_dir / "default.yaml"
            with open(saidata_file, 'w') as f:
                yaml.dump(invalid_data, f)
            
            config = SaiConfig(saidata_paths=[str(temp_path)])
            loader = SaidataLoader(config)
            
            with pytest.raises(ValidationError):
                loader.load_saidata("invalid")


class TestValidationResult:
    """Test ValidationResult functionality."""
    
    def test_validation_result_properties(self):
        """Test ValidationResult properties."""
        # Valid result
        valid_result = ValidationResult(valid=True, errors=[], warnings=[])
        assert valid_result.valid
        assert not valid_result.has_errors
        assert not valid_result.has_warnings
        
        # Result with errors
        error_result = ValidationResult(valid=False, errors=["error1"], warnings=[])
        assert not error_result.valid
        assert error_result.has_errors
        assert not error_result.has_warnings
        
        # Result with warnings
        warning_result = ValidationResult(valid=True, errors=[], warnings=["warning1"])
        assert warning_result.valid
        assert not warning_result.has_errors
        assert warning_result.has_warnings
        
        # Result with both
        mixed_result = ValidationResult(valid=False, errors=["error1"], warnings=["warning1"])
        assert not mixed_result.valid
        assert mixed_result.has_errors
        assert mixed_result.has_warnings