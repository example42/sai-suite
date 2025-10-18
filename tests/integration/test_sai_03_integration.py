"""Integration tests for SAI with schema 0.3 support."""

import tempfile
from pathlib import Path

import pytest
import yaml

from sai.core.saidata_loader import SaidataLoader
from sai.models.config import SaiConfig
from sai.models.saidata import SaiData
from sai.providers.template_engine import TemplateEngine


class TestSai03Integration:
    """Integration tests for schema 0.3 end-to-end workflows."""

    def test_load_and_resolve_package_template(self):
        """Test loading schema 0.3 saidata and resolving package templates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test saidata file
            test_data = {
                "version": "0.3",
                "metadata": {"name": "nginx", "version": "1.24.0"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx-full", "version": "1.24.0"}
                ]
            }
            
            nginx_dir = temp_path / "software" / "ng" / "nginx"
            nginx_dir.mkdir(parents=True)
            saidata_file = nginx_dir / "default.yaml"
            with open(saidata_file, "w") as f:
                yaml.dump(test_data, f)
            
            # Load saidata
            config = SaiConfig(saidata_paths=[str(temp_path)])
            loader = SaidataLoader(config)
            saidata = loader.load_saidata("nginx")
            
            # Resolve template
            engine = TemplateEngine()
            result = engine.resolve_template(
                "apt-get install -y {{sai_package(saidata, 0, 'package_name')}}",
                saidata
            )
            
            assert result == "apt-get install -y nginx-full"

    def test_load_and_resolve_source_template(self):
        """Test loading schema 0.3 with sources and resolving templates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            test_data = {
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "sources": [
                    {
                        "name": "main",
                        "url": "https://nginx.org/download/nginx-1.24.0.tar.gz",
                        "build_system": "autotools",
                        "configure_args": ["--with-http_ssl_module"]
                    }
                ]
            }
            
            nginx_dir = temp_path / "software" / "ng" / "nginx"
            nginx_dir.mkdir(parents=True)
            saidata_file = nginx_dir / "default.yaml"
            with open(saidata_file, "w") as f:
                yaml.dump(test_data, f)
            
            config = SaiConfig(saidata_paths=[str(temp_path)])
            loader = SaidataLoader(config)
            saidata = loader.load_saidata("nginx")
            
            engine = TemplateEngine()
            result = engine.resolve_template(
                "wget {{sai_source(saidata, 0, 'url')}}",
                saidata
            )
            
            assert result == "wget https://nginx.org/download/nginx-1.24.0.tar.gz"

    def test_load_and_resolve_binary_template(self):
        """Test loading schema 0.3 with binaries and resolving templates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            test_data = {
                "version": "0.3",
                "metadata": {"name": "app"},
                "binaries": [
                    {
                        "name": "main",
                        "url": "https://example.com/app-linux-amd64.tar.gz",
                        "platform": "linux",
                        "architecture": "amd64",
                        "install_path": "/usr/local/bin"
                    }
                ]
            }
            
            app_dir = temp_path / "software" / "ap" / "app"
            app_dir.mkdir(parents=True)
            saidata_file = app_dir / "default.yaml"
            with open(saidata_file, "w") as f:
                yaml.dump(test_data, f)
            
            config = SaiConfig(saidata_paths=[str(temp_path)])
            loader = SaidataLoader(config)
            saidata = loader.load_saidata("app")
            
            engine = TemplateEngine()
            result = engine.resolve_template(
                "curl -L {{sai_binary(saidata, 0, 'url')}} -o app.tar.gz",
                saidata
            )
            
            assert result == "curl -L https://example.com/app-linux-amd64.tar.gz -o app.tar.gz"

    def test_load_and_resolve_script_template(self):
        """Test loading schema 0.3 with scripts and resolving templates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            test_data = {
                "version": "0.3",
                "metadata": {"name": "app"},
                "scripts": [
                    {
                        "name": "official",
                        "url": "https://get.example.com/install.sh",
                        "interpreter": "bash"
                    }
                ]
            }
            
            app_dir = temp_path / "software" / "ap" / "app"
            app_dir.mkdir(parents=True)
            saidata_file = app_dir / "default.yaml"
            with open(saidata_file, "w") as f:
                yaml.dump(test_data, f)
            
            config = SaiConfig(saidata_paths=[str(temp_path)])
            loader = SaidataLoader(config)
            saidata = loader.load_saidata("app")
            
            engine = TemplateEngine()
            result = engine.resolve_template(
                "{{sai_script(saidata, 0, 'interpreter')}} {{sai_script(saidata, 0, 'url')}}",
                saidata
            )
            
            assert result == "bash https://get.example.com/install.sh"

    def test_provider_override_integration(self):
        """Test provider-specific overrides in integration workflow."""
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
                        ]
                    },
                    "brew": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx"}
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
            
            engine = TemplateEngine()
            
            # Test apt provider
            result_apt = engine.resolve_template(
                "apt-get install {{sai_package(saidata, 0, 'package_name', 'apt')}}",
                saidata
            )
            assert result_apt == "apt-get install nginx-full"
            
            # Test brew provider
            result_brew = engine.resolve_template(
                "brew install {{sai_package(saidata, 0, 'package_name', 'brew')}}",
                saidata
            )
            assert result_brew == "brew install nginx"

    def test_multiple_installation_methods(self):
        """Test saidata with multiple installation methods."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            test_data = {
                "version": "0.3",
                "metadata": {"name": "nginx", "version": "1.24.0"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx"}
                ],
                "sources": [
                    {
                        "name": "main",
                        "url": "https://nginx.org/download/nginx-1.24.0.tar.gz",
                        "build_system": "autotools"
                    }
                ],
                "binaries": [
                    {
                        "name": "main",
                        "url": "https://nginx.org/download/nginx-1.24.0-linux-amd64.tar.gz",
                        "platform": "linux"
                    }
                ],
                "scripts": [
                    {
                        "name": "official",
                        "url": "https://nginx.org/install.sh",
                        "interpreter": "bash"
                    }
                ]
            }
            
            nginx_dir = temp_path / "software" / "ng" / "nginx"
            nginx_dir.mkdir(parents=True)
            saidata_file = nginx_dir / "default.yaml"
            with open(saidata_file, "w") as f:
                yaml.dump(test_data, f)
            
            config = SaiConfig(saidata_paths=[str(temp_path)])
            loader = SaidataLoader(config)
            saidata = loader.load_saidata("nginx")
            
            # Verify all installation methods are loaded
            assert len(saidata.packages) == 1
            assert len(saidata.sources) == 1
            assert len(saidata.binaries) == 1
            assert len(saidata.scripts) == 1
            
            # Test template resolution for each method
            engine = TemplateEngine()
            
            pkg_result = engine.resolve_template(
                "{{sai_package(saidata, 0, 'package_name')}}",
                saidata
            )
            assert pkg_result == "nginx"
            
            src_result = engine.resolve_template(
                "{{sai_source(saidata, 0, 'url')}}",
                saidata
            )
            assert "nginx-1.24.0.tar.gz" in src_result
            
            bin_result = engine.resolve_template(
                "{{sai_binary(saidata, 0, 'url')}}",
                saidata
            )
            assert "nginx-1.24.0-linux-amd64.tar.gz" in bin_result
            
            scr_result = engine.resolve_template(
                "{{sai_script(saidata, 0, 'url')}}",
                saidata
            )
            assert "install.sh" in scr_result

    def test_validation_and_loading_workflow(self):
        """Test complete validation and loading workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Valid data
            valid_data = {
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx-full"}
                ]
            }
            
            nginx_dir = temp_path / "software" / "ng" / "nginx"
            nginx_dir.mkdir(parents=True)
            saidata_file = nginx_dir / "default.yaml"
            with open(saidata_file, "w") as f:
                yaml.dump(valid_data, f)
            
            config = SaiConfig(saidata_paths=[str(temp_path)])
            loader = SaidataLoader(config)
            
            # Validate before loading
            data = loader._load_hierarchical_saidata_file(saidata_file)
            validation_result = loader.validate_saidata(data)
            
            assert validation_result.valid
            assert len(validation_result.errors) == 0
            
            # Load saidata
            saidata = loader.load_saidata("nginx")
            assert isinstance(saidata, SaiData)
            assert saidata.version == "0.3"


class TestSai03ProviderIntegration:
    """Integration tests for provider workflows with schema 0.3."""

    def test_apt_provider_workflow(self):
        """Test apt provider workflow with schema 0.3."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            test_data = {
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx"},
                    {"name": "nginx-common", "package_name": "nginx-common"}
                ],
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx-full"},
                            {"name": "nginx-common", "package_name": "nginx-common"}
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
            
            engine = TemplateEngine()
            
            # Test install command with wildcard
            result = engine.resolve_template(
                "apt-get install -y {{sai_package(saidata, '*', 'package_name', 'apt')}}",
                saidata
            )
            
            assert "nginx-full" in result
            assert "nginx-common" in result


if __name__ == "__main__":
    pytest.main([__file__])
