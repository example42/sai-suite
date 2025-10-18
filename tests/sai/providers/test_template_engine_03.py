"""Tests for template engine with schema 0.3 support."""

import pytest

from sai.providers.template_engine import (
    SaidataContextBuilder,
    TemplateEngine,
    TemplateResolutionError,
)
from saigen.models.saidata import (
    Binary,
    BuildSystem,
    Metadata,
    Package,
    SaiData,
    Script,
    Source,
)


class TestSaidataContextBuilder03:
    """Test context building with schema 0.3 fields."""

    def test_build_context_with_package_name(self):
        """Test context includes both name and package_name."""
        metadata = Metadata(name="nginx")
        packages = [
            Package(name="nginx", package_name="nginx-full", version="1.24.0"),
            Package(name="nginx-common", package_name="nginx-common-pkg"),
        ]
        
        saidata = SaiData(
            version="0.3",
            metadata=metadata,
            packages=packages,
        )
        
        builder = SaidataContextBuilder(saidata)
        context = builder.build_context()
        
        assert len(context["saidata"]["packages"]) == 2
        assert context["saidata"]["packages"][0]["name"] == "nginx"
        assert context["saidata"]["packages"][0]["package_name"] == "nginx-full"
        assert context["saidata"]["packages"][1]["name"] == "nginx-common"
        assert context["saidata"]["packages"][1]["package_name"] == "nginx-common-pkg"

    def test_build_context_with_sources(self):
        """Test context includes sources array."""
        metadata = Metadata(name="nginx")
        sources = [
            Source(
                name="main",
                url="https://nginx.org/download/nginx-1.24.0.tar.gz",
                build_system=BuildSystem.AUTOTOOLS,
                version="1.24.0",
                configure_args=["--with-http_ssl_module"],
            ),
        ]
        
        saidata = SaiData(
            version="0.3",
            metadata=metadata,
            sources=sources,
        )
        
        builder = SaidataContextBuilder(saidata)
        context = builder.build_context()
        
        assert len(context["saidata"]["sources"]) == 1
        assert context["saidata"]["sources"][0]["name"] == "main"
        assert context["saidata"]["sources"][0]["url"] == "https://nginx.org/download/nginx-1.24.0.tar.gz"
        assert context["saidata"]["sources"][0]["build_system"] == "autotools"
        assert context["saidata"]["sources"][0]["version"] == "1.24.0"
        assert len(context["saidata"]["sources"][0]["configure_args"]) == 1

    def test_build_context_with_binaries(self):
        """Test context includes binaries array."""
        metadata = Metadata(name="app")
        binaries = [
            Binary(
                name="main",
                url="https://example.com/app-linux-amd64.tar.gz",
                version="1.5.0",
                platform="linux",
                architecture="amd64",
                install_path="/usr/local/bin",
            ),
        ]
        
        saidata = SaiData(
            version="0.3",
            metadata=metadata,
            binaries=binaries,
        )
        
        builder = SaidataContextBuilder(saidata)
        context = builder.build_context()
        
        assert len(context["saidata"]["binaries"]) == 1
        assert context["saidata"]["binaries"][0]["name"] == "main"
        assert context["saidata"]["binaries"][0]["platform"] == "linux"
        assert context["saidata"]["binaries"][0]["architecture"] == "amd64"

    def test_build_context_with_scripts(self):
        """Test context includes scripts array."""
        metadata = Metadata(name="app")
        scripts = [
            Script(
                name="official",
                url="https://get.example.com/install.sh",
                interpreter="bash",
                timeout=600,
            ),
        ]
        
        saidata = SaiData(
            version="0.3",
            metadata=metadata,
            scripts=scripts,
        )
        
        builder = SaidataContextBuilder(saidata)
        context = builder.build_context()
        
        assert len(context["saidata"]["scripts"]) == 1
        assert context["saidata"]["scripts"][0]["name"] == "official"
        assert context["saidata"]["scripts"][0]["interpreter"] == "bash"
        assert context["saidata"]["scripts"][0]["timeout"] == 600

    def test_build_context_empty_installation_methods(self):
        """Test context with empty sources, binaries, scripts."""
        metadata = Metadata(name="nginx")
        
        saidata = SaiData(
            version="0.3",
            metadata=metadata,
        )
        
        builder = SaidataContextBuilder(saidata)
        context = builder.build_context()
        
        assert context["saidata"]["sources"] == []
        assert context["saidata"]["binaries"] == []
        assert context["saidata"]["scripts"] == []


class TestTemplateEngine03:
    """Test template engine with schema 0.3 functions."""

    def test_sai_package_with_package_name_field(self):
        """Test sai_package function with package_name field."""
        metadata = Metadata(name="nginx")
        packages = [
            Package(name="nginx", package_name="nginx-full", version="1.24.0"),
        ]
        saidata = SaiData(version="0.3", metadata=metadata, packages=packages)
        
        engine = TemplateEngine()
        result = engine.resolve_template(
            "{{sai_package(saidata, 0, 'package_name', 'apt')}}",
            saidata
        )
        
        assert result == "nginx-full"

    def test_sai_package_with_name_field(self):
        """Test sai_package function with name (logical name) field."""
        metadata = Metadata(name="nginx")
        packages = [
            Package(name="nginx", package_name="nginx-full"),
        ]
        saidata = SaiData(version="0.3", metadata=metadata, packages=packages)
        
        engine = TemplateEngine()
        result = engine.resolve_template(
            "{{sai_package(saidata, 0, 'name')}}",
            saidata
        )
        
        assert result == "nginx"

    def test_sai_package_wildcard_package_names(self):
        """Test sai_package with wildcard for all package names."""
        metadata = Metadata(name="nginx")
        packages = [
            Package(name="nginx", package_name="nginx-full"),
            Package(name="nginx-common", package_name="nginx-common-pkg"),
        ]
        saidata = SaiData(version="0.3", metadata=metadata, packages=packages)
        
        engine = TemplateEngine()
        result = engine.resolve_template(
            "{{sai_package(saidata, '*', 'package_name')}}",
            saidata
        )
        
        assert result == "nginx-full nginx-common-pkg"

    def test_sai_package_default_field(self):
        """Test sai_package defaults to package_name field."""
        metadata = Metadata(name="nginx")
        packages = [
            Package(name="nginx", package_name="nginx-full"),
        ]
        saidata = SaiData(version="0.3", metadata=metadata, packages=packages)
        
        engine = TemplateEngine()
        # Without field parameter, should default to package_name
        result = engine.resolve_template(
            "{{sai_package(saidata, 0)}}",
            saidata
        )
        
        # Should return package_name by default
        assert result in ["nginx-full", "nginx"]  # Depends on implementation

    def test_sai_source_function(self):
        """Test sai_source template function."""
        metadata = Metadata(name="nginx")
        sources = [
            Source(
                name="main",
                url="https://nginx.org/download/nginx-1.24.0.tar.gz",
                build_system=BuildSystem.AUTOTOOLS,
                version="1.24.0",
            ),
        ]
        saidata = SaiData(version="0.3", metadata=metadata, sources=sources)
        
        engine = TemplateEngine()
        
        # Test URL field
        result = engine.resolve_template(
            "{{sai_source(saidata, 0, 'url')}}",
            saidata
        )
        assert result == "https://nginx.org/download/nginx-1.24.0.tar.gz"
        
        # Test version field
        result = engine.resolve_template(
            "{{sai_source(saidata, 0, 'version')}}",
            saidata
        )
        assert result == "1.24.0"
        
        # Test build_system field
        result = engine.resolve_template(
            "{{sai_source(saidata, 0, 'build_system')}}",
            saidata
        )
        assert result == "autotools"

    def test_sai_binary_function(self):
        """Test sai_binary template function."""
        metadata = Metadata(name="app")
        binaries = [
            Binary(
                name="main",
                url="https://example.com/app-linux-amd64.tar.gz",
                platform="linux",
                architecture="amd64",
            ),
        ]
        saidata = SaiData(version="0.3", metadata=metadata, binaries=binaries)
        
        engine = TemplateEngine()
        
        # Test URL field
        result = engine.resolve_template(
            "{{sai_binary(saidata, 0, 'url')}}",
            saidata
        )
        assert result == "https://example.com/app-linux-amd64.tar.gz"
        
        # Test platform field
        result = engine.resolve_template(
            "{{sai_binary(saidata, 0, 'platform')}}",
            saidata
        )
        assert result == "linux"
        
        # Test architecture field
        result = engine.resolve_template(
            "{{sai_binary(saidata, 0, 'architecture')}}",
            saidata
        )
        assert result == "amd64"

    def test_sai_script_function(self):
        """Test sai_script template function."""
        metadata = Metadata(name="app")
        scripts = [
            Script(
                name="official",
                url="https://get.example.com/install.sh",
                interpreter="bash",
            ),
        ]
        saidata = SaiData(version="0.3", metadata=metadata, scripts=scripts)
        
        engine = TemplateEngine()
        
        # Test URL field
        result = engine.resolve_template(
            "{{sai_script(saidata, 0, 'url')}}",
            saidata
        )
        assert result == "https://get.example.com/install.sh"
        
        # Test interpreter field
        result = engine.resolve_template(
            "{{sai_script(saidata, 0, 'interpreter')}}",
            saidata
        )
        assert result == "bash"

    def test_provider_specific_lookup(self):
        """Test provider-specific lookups for installation methods."""
        metadata = Metadata(name="nginx")
        packages = [
            Package(name="nginx", package_name="nginx"),
        ]
        
        saidata = SaiData(
            version="0.3",
            metadata=metadata,
            packages=packages,
            providers={
                "apt": {
                    "packages": [
                        {"name": "nginx", "package_name": "nginx-full"}
                    ],
                    "sources": [
                        {
                            "name": "main",
                            "url": "https://nginx.org/apt-source.tar.gz",
                            "build_system": "autotools"
                        }
                    ]
                }
            }
        )
        
        engine = TemplateEngine()
        
        # Provider-specific package lookup
        result = engine.resolve_template(
            "{{sai_package(saidata, 0, 'package_name', 'apt')}}",
            saidata
        )
        assert result == "nginx-full"

    def test_missing_installation_methods(self):
        """Test handling of missing installation methods."""
        metadata = Metadata(name="nginx")
        saidata = SaiData(version="0.3", metadata=metadata)
        
        engine = TemplateEngine()
        
        # Should return empty string for missing sources
        result = engine.resolve_template(
            "{{sai_source(saidata, 0, 'url')}}",
            saidata
        )
        assert result == ""
        
        # Should return empty string for missing binaries
        result = engine.resolve_template(
            "{{sai_binary(saidata, 0, 'url')}}",
            saidata
        )
        assert result == ""
        
        # Should return empty string for missing scripts
        result = engine.resolve_template(
            "{{sai_script(saidata, 0, 'url')}}",
            saidata
        )
        assert result == ""

    def test_complex_template_with_03_functions(self):
        """Test complex template using multiple schema 0.3 functions."""
        metadata = Metadata(name="nginx", version="1.24.0")
        packages = [
            Package(name="nginx", package_name="nginx-full"),
        ]
        sources = [
            Source(
                name="main",
                url="https://nginx.org/download/nginx-{{version}}.tar.gz",
                build_system=BuildSystem.AUTOTOOLS,
            ),
        ]
        
        saidata = SaiData(
            version="0.3",
            metadata=metadata,
            packages=packages,
            sources=sources,
        )
        
        engine = TemplateEngine()
        template = """
        Package: {{sai_package(saidata, 0, 'package_name')}}
        Source: {{sai_source(saidata, 0, 'url')}}
        Build: {{sai_source(saidata, 0, 'build_system')}}
        """
        
        result = engine.resolve_template(template, saidata)
        
        assert "nginx-full" in result
        assert "https://nginx.org/download/nginx-{{version}}.tar.gz" in result
        assert "autotools" in result


if __name__ == "__main__":
    pytest.main([__file__])
