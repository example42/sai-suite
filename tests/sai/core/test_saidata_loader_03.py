"""Tests for SaidataLoader with schema 0.3 support."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from sai.core.saidata_loader import SaidataLoader, ValidationError
from sai.models.config import SaiConfig
from sai.models.saidata import SaiData


class TestSaidataLoader03:
    """Test SaidataLoader with schema 0.3 files."""

    def test_load_schema_03(self):
        """Test that loader uses schema 0.3."""
        loader = SaidataLoader()
        loader._load_schema()
        
        # Verify schema is loaded
        assert loader._schema_cache is not None
        # Schema should have version property
        assert "properties" in loader._schema_cache
        assert "version" in loader._schema_cache["properties"]

    def test_validate_03_minimal(self):
        """Test validation of minimal schema 0.3 saidata."""
        data = {
            "version": "0.3",
            "metadata": {"name": "nginx"}
        }
        
        loader = SaidataLoader()
        result = loader.validate_saidata(data)
        
        assert result.valid
        assert len(result.errors) == 0

    def test_validate_03_with_packages(self):
        """Test validation of schema 0.3 with packages."""
        data = {
            "version": "0.3",
            "metadata": {"name": "nginx"},
            "packages": [
                {"name": "nginx", "package_name": "nginx-full", "version": "1.24.0"}
            ]
        }
        
        loader = SaidataLoader()
        result = loader.validate_saidata(data)
        
        assert result.valid
        assert len(result.errors) == 0

    def test_validate_03_missing_package_name(self):
        """Test validation error when package_name is missing."""
        data = {
            "version": "0.3",
            "metadata": {"name": "nginx"},
            "packages": [
                {"name": "nginx"}  # Missing package_name
            ]
        }
        
        loader = SaidataLoader()
        result = loader.validate_saidata(data)
        
        assert not result.valid
        assert len(result.errors) > 0
        assert any("package_name" in error.lower() for error in result.errors)

    def test_validate_03_with_sources(self):
        """Test validation of schema 0.3 with sources."""
        data = {
            "version": "0.3",
            "metadata": {"name": "nginx"},
            "sources": [
                {
                    "name": "main",
                    "url": "https://nginx.org/download/nginx-1.24.0.tar.gz",
                    "build_system": "autotools"
                }
            ]
        }
        
        loader = SaidataLoader()
        result = loader.validate_saidata(data)
        
        assert result.valid
        assert len(result.errors) == 0

    def test_validate_03_with_binaries(self):
        """Test validation of schema 0.3 with binaries."""
        data = {
            "version": "0.3",
            "metadata": {"name": "app"},
            "binaries": [
                {
                    "name": "main",
                    "url": "https://example.com/app-linux-amd64.tar.gz"
                }
            ]
        }
        
        loader = SaidataLoader()
        result = loader.validate_saidata(data)
        
        assert result.valid
        assert len(result.errors) == 0

    def test_validate_03_with_scripts(self):
        """Test validation of schema 0.3 with scripts."""
        data = {
            "version": "0.3",
            "metadata": {"name": "app"},
            "scripts": [
                {
                    "name": "official",
                    "url": "https://get.example.com/install.sh"
                }
            ]
        }
        
        loader = SaidataLoader()
        result = loader.validate_saidata(data)
        
        assert result.valid
        assert len(result.errors) == 0

    def test_validate_03_invalid_source(self):
        """Test validation error for invalid source."""
        data = {
            "version": "0.3",
            "metadata": {"name": "nginx"},
            "sources": [
                {
                    "name": "main"
                    # Missing required url and build_system
                }
            ]
        }
        
        loader = SaidataLoader()
        result = loader.validate_saidata(data)
        
        assert not result.valid
        assert len(result.errors) > 0

    def test_load_03_saidata_from_file(self):
        """Test loading schema 0.3 saidata from file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            test_data = {
                "version": "0.3",
                "metadata": {"name": "nginx", "description": "Web server"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx-full", "version": "1.24.0"}
                ],
                "sources": [
                    {
                        "name": "main",
                        "url": "https://nginx.org/download/nginx-1.24.0.tar.gz",
                        "build_system": "autotools"
                    }
                ]
            }
            
            # Create hierarchical structure
            nginx_dir = temp_path / "software" / "ng" / "nginx"
            nginx_dir.mkdir(parents=True)
            saidata_file = nginx_dir / "default.yaml"
            with open(saidata_file, "w") as f:
                yaml.dump(test_data, f)
            
            config = SaiConfig(saidata_paths=[str(temp_path)])
            loader = SaidataLoader(config)
            
            saidata = loader.load_saidata("nginx")
            
            assert isinstance(saidata, SaiData)
            assert saidata.version == "0.3"
            assert saidata.metadata.name == "nginx"
            assert len(saidata.packages) == 1
            assert saidata.packages[0].package_name == "nginx-full"
            assert len(saidata.sources) == 1
            assert saidata.sources[0].build_system == "autotools"

    def test_load_03_with_provider_overrides(self):
        """Test loading schema 0.3 with provider-specific overrides."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            test_data = {
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx"}
                ],
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx-full"}
                        ],
                        "sources": [
                            {
                                "name": "main",
                                "url": "https://nginx.org/download/nginx.tar.gz",
                                "build_system": "autotools"
                            }
                        ]
                    }
                }
            }
            
            nginx_dir = temp_path / "software" / "ng" / "nginx"
            nginx_dir.mkdir(parents=True)
            saidata_file = nginx_dir / "default.yaml"
            with open(saidata_file, "w") as f:
                yaml.dump(test_data, f)
            
            config = SaiConfig(saidata_paths=[str(temp_path)])
            loader = SaidataLoader(config)
            
            saidata = loader.load_saidata("nginx")
            
            assert saidata.providers["apt"].packages[0].package_name == "nginx-full"
            assert len(saidata.providers["apt"].sources) == 1

    def test_error_messages_for_03(self):
        """Test that error messages are clear for schema 0.3 validation."""
        data = {
            "version": "0.3",
            "metadata": {"name": "nginx"},
            "packages": [
                {"name": "nginx"}  # Missing package_name
            ]
        }
        
        loader = SaidataLoader()
        result = loader.validate_saidata(data)
        
        assert not result.valid
        # Error message should mention package_name requirement
        error_text = " ".join(result.errors).lower()
        assert "package" in error_text


class TestSaidataLoader03Fixtures:
    """Test loading schema 0.3 test fixtures."""

    def test_load_source_build_fixture(self):
        """Test loading test-source-build.yaml fixture."""
        fixture_path = Path("tests/fixtures/test-source-build.yaml")
        if not fixture_path.exists():
            pytest.skip("Fixture file not found")
        
        loader = SaidataLoader()
        data = loader._load_hierarchical_saidata_file(fixture_path)
        
        assert data["version"] == "0.3"
        assert "sources" in data
        assert len(data["sources"]) > 0
        assert data["sources"][0]["build_system"] == "autotools"

    def test_load_binary_download_fixture(self):
        """Test loading test-binary-download.yaml fixture."""
        fixture_path = Path("tests/fixtures/test-binary-download.yaml")
        if not fixture_path.exists():
            pytest.skip("Fixture file not found")
        
        loader = SaidataLoader()
        data = loader._load_hierarchical_saidata_file(fixture_path)
        
        assert data["version"] == "0.3"
        assert "binaries" in data
        assert len(data["binaries"]) > 0

    def test_load_script_install_fixture(self):
        """Test loading test-script-install.yaml fixture."""
        fixture_path = Path("tests/fixtures/test-script-install.yaml")
        if not fixture_path.exists():
            pytest.skip("Fixture file not found")
        
        loader = SaidataLoader()
        data = loader._load_hierarchical_saidata_file(fixture_path)
        
        assert data["version"] == "0.3"
        assert "scripts" in data
        assert len(data["scripts"]) > 0


if __name__ == "__main__":
    pytest.main([__file__])
