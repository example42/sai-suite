"""Tests for SAI data models with schema 0.3 support."""

import pytest
from pydantic import ValidationError

from sai.models.saidata import (
    Binary,
    BuildSystem,
    CustomCommands,
    Metadata,
    Package,
    ProviderConfig,
    SaiData,
    Script,
    Source,
)


class TestPackageModel03:
    """Test Package model with schema 0.3 fields."""

    def test_package_with_both_names(self):
        """Test package with both name and package_name."""
        package = Package(
            name="nginx",
            package_name="nginx-full",
            version="1.24.0"
        )
        assert package.name == "nginx"
        assert package.package_name == "nginx-full"
        assert package.version == "1.24.0"

    def test_package_name_required(self):
        """Test that package_name is required."""
        # Both name and package_name are required
        with pytest.raises(ValidationError):
            Package(name="nginx")  # Missing package_name

    def test_package_logical_name_required(self):
        """Test that name (logical name) is required."""
        with pytest.raises(ValidationError):
            Package(package_name="nginx")  # Missing name


class TestSourceModel03:
    """Test Source model for source builds."""

    def test_minimal_source(self):
        """Test minimal source configuration."""
        source = Source(
            name="main",
            url="https://example.com/app-1.0.0.tar.gz",
            build_system=BuildSystem.AUTOTOOLS
        )
        assert source.name == "main"
        assert source.url == "https://example.com/app-1.0.0.tar.gz"
        assert source.build_system == BuildSystem.AUTOTOOLS

    def test_complete_source(self):
        """Test complete source configuration."""
        source = Source(
            name="main",
            url="https://nginx.org/download/nginx-{{version}}.tar.gz",
            build_system=BuildSystem.AUTOTOOLS,
            version="1.24.0",
            build_dir="/tmp/build",
            source_dir="/tmp/build/nginx-1.24.0",
            install_prefix="/usr/local",
            configure_args=["--with-http_ssl_module", "--with-http_v2_module"],
            build_args=["-j4"],
            install_args=["install"],
            prerequisites=["build-essential", "libssl-dev"],
            environment={"CC": "gcc", "CFLAGS": "-O2"},
            checksum="sha256:abc123def456789abc123def456789abc123def456789abc123def456789abc12"
        )
        assert source.version == "1.24.0"
        assert len(source.configure_args) == 2
        assert source.prerequisites == ["build-essential", "libssl-dev"]
        assert source.environment["CC"] == "gcc"
        assert source.checksum.startswith("sha256:")

    def test_source_with_custom_commands(self):
        """Test source with custom commands."""
        custom_commands = CustomCommands(
            download="wget {{url}}",
            extract="tar xzf archive.tar.gz",
            configure="./configure --prefix={{install_prefix}}",
            build="make -j4",
            install="make install"
        )
        source = Source(
            name="main",
            url="https://example.com/app.tar.gz",
            build_system=BuildSystem.CUSTOM,
            custom_commands=custom_commands
        )
        assert source.custom_commands.download == "wget {{url}}"
        assert source.custom_commands.build == "make -j4"

    def test_build_system_enum(self):
        """Test BuildSystem enum values."""
        assert BuildSystem.AUTOTOOLS == "autotools"
        assert BuildSystem.CMAKE == "cmake"
        assert BuildSystem.MAKE == "make"
        assert BuildSystem.MESON == "meson"
        assert BuildSystem.NINJA == "ninja"
        assert BuildSystem.CUSTOM == "custom"


class TestBinaryModel03:
    """Test Binary model for binary downloads."""

    def test_minimal_binary(self):
        """Test minimal binary configuration."""
        binary = Binary(
            name="main",
            url="https://example.com/app-linux-amd64.tar.gz"
        )
        assert binary.name == "main"
        assert binary.url == "https://example.com/app-linux-amd64.tar.gz"

    def test_complete_binary(self):
        """Test complete binary configuration."""
        binary = Binary(
            name="main",
            url="https://releases.example.com/{{version}}/app_{{platform}}_{{architecture}}.tar.gz",
            version="1.5.0",
            architecture="amd64",
            platform="linux",
            checksum="sha256:def456789abc123def456789abc123def456789abc123def456789abc123def4",
            install_path="/usr/local/bin",
            executable="app",
            permissions="0755"
        )
        assert binary.version == "1.5.0"
        assert binary.architecture == "amd64"
        assert binary.platform == "linux"
        assert binary.install_path == "/usr/local/bin"
        assert binary.executable == "app"
        assert binary.permissions == "0755"
        assert binary.checksum.startswith("sha256:")

    def test_binary_with_archive_config(self):
        """Test binary with archive extraction configuration."""
        from sai.models.saidata import ArchiveConfig
        
        archive = ArchiveConfig(
            format="tar.gz",
            strip_prefix="app-1.5.0/",
            extract_path="bin/"
        )
        binary = Binary(
            name="main",
            url="https://example.com/app.tar.gz",
            archive=archive
        )
        assert binary.archive.format == "tar.gz"
        assert binary.archive.strip_prefix == "app-1.5.0/"
        assert binary.archive.extract_path == "bin/"


class TestScriptModel03:
    """Test Script model for script installations."""

    def test_minimal_script(self):
        """Test minimal script configuration."""
        script = Script(
            name="official",
            url="https://get.example.com/install.sh"
        )
        assert script.name == "official"
        assert script.url == "https://get.example.com/install.sh"

    def test_complete_script(self):
        """Test complete script configuration."""
        script = Script(
            name="official",
            url="https://get.example.com/install.sh",
            version="1.2.0",
            interpreter="bash",
            checksum="sha256:abc123def456789abc123def456789abc123def456789abc123def456789abc12",
            arguments=["--yes", "--quiet"],
            environment={"INSTALL_DIR": "/usr/local", "CHANNEL": "stable"},
            working_dir="/tmp",
            timeout=600
        )
        assert script.version == "1.2.0"
        assert script.interpreter == "bash"
        assert script.checksum.startswith("sha256:")
        assert len(script.arguments) == 2
        assert script.environment["CHANNEL"] == "stable"
        assert script.timeout == 600

    def test_script_with_custom_commands(self):
        """Test script with custom commands."""
        custom_commands = CustomCommands(
            download="curl -o install.sh {{url}}",
            validation="bash -n install.sh",
            version="bash install.sh --version"
        )
        script = Script(
            name="official",
            url="https://get.example.com/install.sh",
            custom_commands=custom_commands
        )
        assert script.custom_commands.download == "curl -o install.sh {{url}}"
        assert script.custom_commands.validation == "bash -n install.sh"


class TestProviderConfig03:
    """Test ProviderConfig with schema 0.3 fields."""

    def test_provider_config_with_installation_methods(self):
        """Test provider config with sources, binaries, scripts."""
        config = ProviderConfig(
            packages=[Package(name="nginx", package_name="nginx-full")],
            sources=[Source(name="main", url="https://example.com/src.tar.gz", build_system=BuildSystem.AUTOTOOLS)],
            binaries=[Binary(name="main", url="https://example.com/bin.tar.gz")],
            scripts=[Script(name="official", url="https://example.com/install.sh")]
        )
        assert len(config.packages) == 1
        assert len(config.sources) == 1
        assert len(config.binaries) == 1
        assert len(config.scripts) == 1


class TestSaiData03:
    """Test SaiData model with schema 0.3 support."""

    def test_minimal_saidata_03(self):
        """Test minimal valid SaiData with schema 0.3."""
        data = {
            "version": "0.3",
            "metadata": {"name": "nginx"}
        }
        saidata = SaiData(**data)
        assert saidata.version == "0.3"
        assert saidata.metadata.name == "nginx"

    def test_saidata_with_packages_03(self):
        """Test SaiData with packages using schema 0.3."""
        data = {
            "version": "0.3",
            "metadata": {"name": "nginx"},
            "packages": [
                {"name": "nginx", "package_name": "nginx-full", "version": "1.24.0"}
            ]
        }
        saidata = SaiData(**data)
        assert len(saidata.packages) == 1
        assert saidata.packages[0].name == "nginx"
        assert saidata.packages[0].package_name == "nginx-full"

    def test_saidata_with_sources(self):
        """Test SaiData with sources array."""
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
        saidata = SaiData(**data)
        assert len(saidata.sources) == 1
        assert saidata.sources[0].name == "main"
        assert saidata.sources[0].build_system == BuildSystem.AUTOTOOLS

    def test_saidata_with_binaries(self):
        """Test SaiData with binaries array."""
        data = {
            "version": "0.3",
            "metadata": {"name": "app"},
            "binaries": [
                {
                    "name": "main",
                    "url": "https://example.com/app-linux-amd64.tar.gz",
                    "platform": "linux",
                    "architecture": "amd64"
                }
            ]
        }
        saidata = SaiData(**data)
        assert len(saidata.binaries) == 1
        assert saidata.binaries[0].platform == "linux"

    def test_saidata_with_scripts(self):
        """Test SaiData with scripts array."""
        data = {
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
        saidata = SaiData(**data)
        assert len(saidata.scripts) == 1
        assert saidata.scripts[0].interpreter == "bash"

    def test_saidata_with_provider_overrides_03(self):
        """Test SaiData with provider-specific overrides for schema 0.3."""
        data = {
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
        saidata = SaiData(**data)
        assert saidata.providers["apt"].packages[0].package_name == "nginx-full"
        assert len(saidata.providers["apt"].sources) == 1


if __name__ == "__main__":
    pytest.main([__file__])
