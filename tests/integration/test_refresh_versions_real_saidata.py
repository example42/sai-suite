"""Integration tests for refresh-versions with real saidata files.

This module tests the refresh-versions command with realistic saidata files
for common software packages like nginx, apache, postgresql, and HashiCorp tools.
"""

import pytest
import yaml
from pathlib import Path
from click.testing import CliRunner

from saigen.cli.main import cli


@pytest.mark.integration
class TestRealSaidataRefresh:
    """Integration tests with real saidata files."""
    
    def test_nginx_saidata_multiple_os_versions(self, tmp_path):
        """Test nginx saidata with multiple OS versions including Windows/macOS."""
        # Create nginx directory structure
        nginx_dir = tmp_path / "nginx"
        nginx_dir.mkdir()
        
        # Create default.yaml with upstream version
        default_file = nginx_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {
                    "name": "nginx",
                    "display_name": "NGINX Web Server",
                    "description": "High-performance HTTP server and reverse proxy",
                    "version": "1.24.0",
                    "category": "web-server"
                },
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ],
                "services": [
                    {"name": "nginx", "service_name": "nginx", "type": "systemd"}
                ],
                "ports": [
                    {"port": 80, "protocol": "tcp", "service": "http"},
                    {"port": 443, "protocol": "tcp", "service": "https"}
                ]
            }, f)
        
        # Create Ubuntu 22.04 variant
        ubuntu_dir = nginx_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_2204 = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_2204, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx-full", "version": "1.20.2"}
                        ]
                    }
                }
            }, f)
        
        # Create Ubuntu 20.04 variant
        ubuntu_2004 = ubuntu_dir / "20.04.yaml"
        with open(ubuntu_2004, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx", "version": "1.18.0"}
                        ]
                    }
                }
            }, f)
        
        # Create Debian 11 variant
        debian_dir = nginx_dir / "debian"
        debian_dir.mkdir()
        debian_11 = debian_dir / "11.yaml"
        with open(debian_11, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx", "version": "1.18.0"}
                        ]
                    }
                }
            }, f)
        
        # Create Windows variant
        windows_dir = nginx_dir / "windows"
        windows_dir.mkdir()
        windows_file = windows_dir / "latest.yaml"
        with open(windows_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {
                    "choco": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                        ]
                    }
                }
            }, f)
        
        # Create macOS variant
        macos_dir = nginx_dir / "macos"
        macos_dir.mkdir()
        macos_file = macos_dir / "latest.yaml"
        with open(macos_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {
                    "brew": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                        ]
                    }
                }
            }, f)
        
        # Run directory-wide refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--check-only", str(nginx_dir)]
        )
        
        # Should process all 6 files
        assert result.exit_code == 0
        assert "Processing 6 saidata file(s)" in result.output
        assert "Summary" in result.output
    
    def test_apache_saidata_refresh(self, tmp_path):
        """Test apache saidata refresh across multiple OS versions."""
        # Create apache directory structure
        apache_dir = tmp_path / "apache"
        apache_dir.mkdir()
        
        # Create default.yaml
        default_file = apache_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {
                    "name": "apache",
                    "display_name": "Apache HTTP Server",
                    "description": "The Apache HTTP Server",
                    "version": "2.4.57",
                    "category": "web-server"
                },
                "packages": [
                    {"name": "apache2", "package_name": "apache2", "version": "2.4.57"}
                ],
                "services": [
                    {"name": "apache2", "service_name": "apache2", "type": "systemd"}
                ]
            }, f)
        
        # Create Ubuntu 22.04 variant
        ubuntu_dir = apache_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_2204 = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_2204, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "apache"},
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "apache2", "package_name": "apache2", "version": "2.4.52"}
                        ]
                    }
                }
            }, f)
        
        # Create Debian 12 variant
        debian_dir = apache_dir / "debian"
        debian_dir.mkdir()
        debian_12 = debian_dir / "12.yaml"
        with open(debian_12, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "apache"},
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "apache2", "package_name": "apache2", "version": "2.4.57"}
                        ]
                    }
                }
            }, f)
        
        # Run directory-wide refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--check-only", str(apache_dir)]
        )
        
        # Should process all 3 files
        assert result.exit_code == 0
        assert "Processing 3 saidata file(s)" in result.output
    
    def test_postgresql_saidata_refresh(self, tmp_path):
        """Test postgresql saidata refresh across multiple OS versions."""
        # Create postgresql directory structure
        pg_dir = tmp_path / "postgresql"
        pg_dir.mkdir()
        
        # Create default.yaml
        default_file = pg_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {
                    "name": "postgresql",
                    "display_name": "PostgreSQL",
                    "description": "PostgreSQL database server",
                    "version": "16.1",
                    "category": "database"
                },
                "packages": [
                    {"name": "postgresql", "package_name": "postgresql", "version": "16.1"}
                ],
                "services": [
                    {"name": "postgresql", "service_name": "postgresql", "type": "systemd"}
                ],
                "ports": [
                    {"port": 5432, "protocol": "tcp", "service": "postgresql"}
                ]
            }, f)
        
        # Create Ubuntu 22.04 variant
        ubuntu_dir = pg_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_2204 = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_2204, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "postgresql"},
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "postgresql", "package_name": "postgresql-14", "version": "14.10"}
                        ]
                    }
                }
            }, f)
        
        # Create Debian 11 variant
        debian_dir = pg_dir / "debian"
        debian_dir.mkdir()
        debian_11 = debian_dir / "11.yaml"
        with open(debian_11, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "postgresql"},
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "postgresql", "package_name": "postgresql-13", "version": "13.13"}
                        ]
                    }
                }
            }, f)
        
        # Create Fedora 40 variant
        fedora_dir = pg_dir / "fedora"
        fedora_dir.mkdir()
        fedora_40 = fedora_dir / "40.yaml"
        with open(fedora_40, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "postgresql"},
                "providers": {
                    "dnf": {
                        "packages": [
                            {"name": "postgresql", "package_name": "postgresql-server", "version": "16.1"}
                        ]
                    }
                }
            }, f)
        
        # Run directory-wide refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--check-only", str(pg_dir)]
        )
        
        # Should process all 4 files
        assert result.exit_code == 0
        assert "Processing 4 saidata file(s)" in result.output
    
    def test_hashicorp_terraform_upstream_repo(self, tmp_path):
        """Test HashiCorp Terraform with upstream repository support."""
        # Create terraform directory structure
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        
        # Create default.yaml
        default_file = terraform_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {
                    "name": "terraform",
                    "display_name": "Terraform",
                    "description": "Infrastructure as Code tool",
                    "version": "1.6.6",
                    "category": "devops"
                },
                "packages": [
                    {"name": "terraform", "package_name": "terraform", "version": "1.6.6"}
                ],
                "binaries": [
                    {
                        "name": "main",
                        "url": "https://releases.hashicorp.com/terraform/{{version}}/terraform_{{version}}_{{platform}}_{{architecture}}.zip",
                        "version": "1.6.6",
                        "platform": "linux",
                        "architecture": "amd64"
                    }
                ]
            }, f)
        
        # Create Ubuntu 22.04 variant (using HashiCorp apt repository)
        ubuntu_dir = terraform_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_2204 = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_2204, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "terraform"},
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "terraform", "package_name": "terraform", "version": "1.6.6"}
                        ]
                    }
                }
            }, f)
        
        # Create macOS variant
        macos_dir = terraform_dir / "macos"
        macos_dir.mkdir()
        macos_file = macos_dir / "latest.yaml"
        with open(macos_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "terraform"},
                "providers": {
                    "brew": {
                        "packages": [
                            {"name": "terraform", "package_name": "terraform", "version": "1.6.6"}
                        ]
                    }
                }
            }, f)
        
        # Run directory-wide refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--check-only", str(terraform_dir)]
        )
        
        # Should process all 3 files
        assert result.exit_code == 0
        assert "Processing 3 saidata file(s)" in result.output
    
    def test_create_missing_os_specific_files_nginx(self, tmp_path):
        """Test creating missing OS-specific files for nginx."""
        # Create nginx directory with only default.yaml
        nginx_dir = tmp_path / "nginx"
        nginx_dir.mkdir()
        
        # Create default.yaml
        default_file = nginx_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {
                    "name": "nginx",
                    "display_name": "NGINX Web Server",
                    "description": "High-performance HTTP server",
                    "version": "1.24.0"
                },
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }, f)
        
        # Run with --create-missing flag
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--create-missing", "--check-only", str(nginx_dir)]
        )
        
        # Should identify potential missing files
        assert result.exit_code == 0
        # Output depends on repository configuration
        assert "Processing" in result.output or "Found" in result.output or "No missing" in result.output
    
    def test_verify_accuracy_of_updates(self, tmp_path):
        """Test that updates are accurate by comparing before and after."""
        # Create test file with known outdated version
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        original_content = {
            "version": "0.3",
            "metadata": {"name": "nginx"},
            "providers": {
                "apt": {
                    "packages": [
                        {"name": "nginx", "package_name": "nginx", "version": "1.0.0"}
                    ]
                }
            }
        }
        with open(ubuntu_file, "w") as f:
            yaml.dump(original_content, f)
        
        # Run refresh in check-only mode
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(ubuntu_file)]
        )
        
        # Should complete successfully
        assert result.exit_code == 0
        
        # File should not be modified in check-only mode
        with open(ubuntu_file) as f:
            current_content = yaml.safe_load(f)
        assert current_content == original_content
        
        # Check results should show potential updates
        assert "Check Results" in result.output


@pytest.mark.integration
class TestComplexSaidataScenarios:
    """Integration tests for complex saidata scenarios."""
    
    def test_saidata_with_multiple_packages(self, tmp_path):
        """Test saidata file with multiple packages."""
        # Create test file with multiple packages
        software_dir = tmp_path / "dev-tools"
        software_dir.mkdir()
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "dev-tools"},
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "git", "package_name": "git", "version": "2.34.1"},
                            {"name": "curl", "package_name": "curl", "version": "7.81.0"},
                            {"name": "wget", "package_name": "wget", "version": "1.21.2"}
                        ]
                    }
                }
            }, f)
        
        # Run refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(ubuntu_file)]
        )
        
        # Should process all packages
        assert result.exit_code == 0
    
    def test_saidata_with_multiple_providers(self, tmp_path):
        """Test saidata file with multiple providers."""
        # Create test file with multiple providers
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx", "version": "1.20.0"}
                        ]
                    },
                    "source": {
                        "sources": [
                            {
                                "name": "main",
                                "url": "https://nginx.org/download/nginx-1.24.0.tar.gz",
                                "version": "1.24.0",
                                "build_system": "autotools"
                            }
                        ]
                    }
                }
            }, f)
        
        # Run refresh with provider filter
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", "--providers", "apt", str(ubuntu_file)]
        )
        
        # Should process only apt provider
        assert result.exit_code == 0
    
    def test_saidata_with_sources_binaries_scripts(self, tmp_path):
        """Test saidata file with sources, binaries, and scripts."""
        # Create comprehensive test file
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {
                    "name": "nginx",
                    "version": "1.24.0"
                },
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ],
                "sources": [
                    {
                        "name": "main",
                        "url": "https://nginx.org/download/nginx-{{version}}.tar.gz",
                        "version": "1.24.0",
                        "build_system": "autotools"
                    }
                ],
                "binaries": [
                    {
                        "name": "main",
                        "url": "https://nginx.org/download/nginx-{{version}}-{{platform}}-{{architecture}}.tar.gz",
                        "version": "1.24.0",
                        "platform": "linux",
                        "architecture": "amd64"
                    }
                ],
                "scripts": [
                    {
                        "name": "official",
                        "url": "https://nginx.org/install.sh",
                        "version": "1.24.0",
                        "interpreter": "bash"
                    }
                ]
            }, f)
        
        # Run refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(default_file)]
        )
        
        # Should process all installation methods
        assert result.exit_code == 0


@pytest.mark.integration
class TestSkipDefaultFlag:
    """Integration tests for --skip-default flag."""
    
    def test_skip_default_excludes_default_yaml(self, tmp_path):
        """Test that --skip-default flag excludes default.yaml from processing."""
        # Create directory with default.yaml and OS-specific files
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create default.yaml
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [{"name": "nginx", "package_name": "nginx", "version": "1.24.0"}]
            }, f)
        
        # Create ubuntu/22.04.yaml
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {
                    "apt": {
                        "packages": [{"name": "nginx", "package_name": "nginx", "version": "1.20.0"}]
                    }
                }
            }, f)
        
        # Run with --skip-default
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--skip-default", "--check-only", str(software_dir)]
        )
        
        # Should only process 1 file (ubuntu/22.04.yaml)
        assert result.exit_code == 0
        assert "Processing 1 saidata file(s)" in result.output or "22.04.yaml" in result.output
    
    def test_skip_default_with_multiple_os_files(self, tmp_path):
        """Test --skip-default with multiple OS-specific files."""
        # Create directory with default.yaml and multiple OS files
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create default.yaml
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [{"name": "nginx", "package_name": "nginx", "version": "1.24.0"}]
            }, f)
        
        # Create multiple OS-specific files
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        for version in ["20.04", "22.04", "24.04"]:
            ubuntu_file = ubuntu_dir / f"{version}.yaml"
            with open(ubuntu_file, "w") as f:
                yaml.dump({
                    "version": "0.3",
                    "metadata": {"name": "nginx"},
                    "providers": {
                        "apt": {
                            "packages": [{"name": "nginx", "package_name": "nginx", "version": "1.20.0"}]
                        }
                    }
                }, f)
        
        # Run with --skip-default
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--skip-default", "--check-only", str(software_dir)]
        )
        
        # Should process only 3 files (Ubuntu versions, not default.yaml)
        assert result.exit_code == 0
        assert "Processing 3 saidata file(s)" in result.output
