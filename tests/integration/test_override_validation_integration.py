"""Integration tests for override validation functionality.

This module tests the override validation command and functionality,
including duplicate detection, automatic cleanup, and validation with
various OS-specific files.
"""

import pytest
import yaml
from pathlib import Path
from click.testing import CliRunner

from saigen.cli.main import cli


@pytest.mark.integration
class TestOverrideValidationIntegration:
    """Integration tests for override validation."""
    
    def test_duplicate_detection_in_os_specific_file(self, tmp_path):
        """Test detection of duplicate fields in OS-specific files."""
        # Create directory structure
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create default.yaml
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {
                    "name": "nginx",
                    "display_name": "NGINX",
                    "description": "HTTP server",
                    "version": "1.24.0"
                },
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ],
                "services": [
                    {"name": "nginx", "service_name": "nginx", "type": "systemd"}
                ]
            }, f)
        
        # Create ubuntu/22.04.yaml with duplicate fields
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},  # Duplicate
                "providers": {
                    "apt": {
                        "packages": [
                            {
                                "name": "nginx",
                                "package_name": "nginx",  # Duplicate (same as default)
                                "version": "1.20.0"  # Different (necessary override)
                            }
                        ]
                    }
                }
            }, f)
        
        # Run validate-overrides command
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-overrides", str(ubuntu_file)]
        )
        
        # Should detect duplicates
        assert result.exit_code == 0
        assert "identical" in result.output.lower() or "duplicate" in result.output.lower()
    
    def test_automatic_cleanup_of_duplicates(self, tmp_path):
        """Test automatic cleanup of duplicate fields."""
        # Create directory structure
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create default.yaml
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx", "version": "1.24.0"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }, f)
        
        # Create ubuntu/22.04.yaml with duplicates
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        original_content = {
            "version": "0.3",
            "metadata": {"name": "nginx"},  # Duplicate
            "providers": {
                "apt": {
                    "packages": [
                        {
                            "name": "nginx",
                            "package_name": "nginx",  # Duplicate
                            "version": "1.20.0"  # Different
                        }
                    ]
                }
            }
        }
        with open(ubuntu_file, "w") as f:
            yaml.dump(original_content, f)
        
        # Run validate-overrides with --remove-duplicates
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-overrides", "--remove-duplicates", str(ubuntu_file)]
        )
        
        # Should clean up duplicates
        assert result.exit_code == 0
        
        # Verify file was modified
        with open(ubuntu_file) as f:
            cleaned_content = yaml.safe_load(f)
        
        # package_name should be removed (duplicate)
        # version should remain (different)
        if "providers" in cleaned_content and "apt" in cleaned_content["providers"]:
            packages = cleaned_content["providers"]["apt"].get("packages", [])
            if packages:
                # package_name should not be present (was duplicate)
                assert "package_name" not in packages[0] or packages[0].get("package_name") != "nginx"
                # version should be present (was different)
                assert "version" in packages[0]
    
    def test_validation_with_multiple_os_files(self, tmp_path):
        """Test validation with multiple OS-specific files."""
        # Create directory structure
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create default.yaml
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx", "version": "1.24.0"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }, f)
        
        # Create ubuntu/22.04.yaml
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_2204 = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_2204, "w") as f:
            yaml.dump({
                "version": "0.3",
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx", "version": "1.20.0"}
                        ]
                    }
                }
            }, f)
        
        # Create ubuntu/20.04.yaml
        ubuntu_2004 = ubuntu_dir / "20.04.yaml"
        with open(ubuntu_2004, "w") as f:
            yaml.dump({
                "version": "0.3",
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx", "version": "1.18.0"}
                        ]
                    }
                }
            }, f)
        
        # Create debian/11.yaml
        debian_dir = software_dir / "debian"
        debian_dir.mkdir()
        debian_11 = debian_dir / "11.yaml"
        with open(debian_11, "w") as f:
            yaml.dump({
                "version": "0.3",
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx-full", "version": "1.18.0"}
                        ]
                    }
                }
            }, f)
        
        # Run validation on directory
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-overrides", str(software_dir)]
        )
        
        # Should validate all OS-specific files
        assert result.exit_code == 0
    
    def test_validation_identifies_necessary_overrides(self, tmp_path):
        """Test that validation correctly identifies necessary overrides."""
        # Create directory structure
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create default.yaml
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx", "version": "1.24.0"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }, f)
        
        # Create ubuntu/22.04.yaml with necessary overrides
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "providers": {
                    "apt": {
                        "packages": [
                            {
                                "name": "nginx",
                                "package_name": "nginx-full",  # Different (necessary)
                                "version": "1.20.0"  # Different (necessary)
                            }
                        ]
                    }
                }
            }, f)
        
        # Run validation
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-overrides", str(ubuntu_file)]
        )
        
        # Should identify these as necessary overrides
        assert result.exit_code == 0
        assert "different" in result.output.lower() or "override" in result.output.lower()
    
    def test_validation_with_complex_nested_structures(self, tmp_path):
        """Test validation with complex nested structures."""
        # Create directory structure
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create default.yaml with complex structure
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {
                    "name": "nginx",
                    "version": "1.24.0",
                    "tags": ["web", "server", "proxy"]
                },
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ],
                "services": [
                    {
                        "name": "nginx",
                        "service_name": "nginx",
                        "type": "systemd",
                        "enabled": True
                    }
                ],
                "ports": [
                    {"port": 80, "protocol": "tcp", "service": "http"},
                    {"port": 443, "protocol": "tcp", "service": "https"}
                ]
            }, f)
        
        # Create ubuntu/22.04.yaml with some duplicates and some overrides
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {
                    "name": "nginx",  # Duplicate
                    "tags": ["web", "server", "proxy"]  # Duplicate
                },
                "providers": {
                    "apt": {
                        "packages": [
                            {
                                "name": "nginx",
                                "package_name": "nginx-full",  # Different
                                "version": "1.20.0"  # Different
                            }
                        ]
                    }
                },
                "services": [
                    {
                        "name": "nginx",
                        "service_name": "nginx",  # Duplicate
                        "type": "systemd",  # Duplicate
                        "enabled": True  # Duplicate
                    }
                ]
            }, f)
        
        # Run validation
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-overrides", str(ubuntu_file)]
        )
        
        # Should detect both duplicates and necessary overrides
        assert result.exit_code == 0


@pytest.mark.integration
class TestOverrideValidationEdgeCases:
    """Integration tests for edge cases in override validation."""
    
    def test_validation_with_missing_default_file(self, tmp_path):
        """Test validation when default.yaml doesn't exist."""
        # Create OS-specific file without default.yaml
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx", "version": "1.20.0"}
                        ]
                    }
                }
            }, f)
        
        # Run validation
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-overrides", str(ubuntu_file)]
        )
        
        # Should handle gracefully (may show warning or error)
        assert "default.yaml" in result.output.lower() or "not found" in result.output.lower()
    
    def test_validation_with_empty_os_specific_file(self, tmp_path):
        """Test validation with empty OS-specific file."""
        # Create directory structure
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create default.yaml
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }, f)
        
        # Create empty ubuntu/22.04.yaml
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_file, "w") as f:
            yaml.dump({"version": "0.3"}, f)
        
        # Run validation
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-overrides", str(ubuntu_file)]
        )
        
        # Should handle gracefully
        assert result.exit_code == 0
    
    def test_validation_with_only_necessary_overrides(self, tmp_path):
        """Test validation when all fields are necessary overrides."""
        # Create directory structure
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create default.yaml
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx", "version": "1.24.0"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }, f)
        
        # Create ubuntu/22.04.yaml with all different values
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "providers": {
                    "apt": {
                        "packages": [
                            {
                                "name": "nginx",
                                "package_name": "nginx-full",  # Different
                                "version": "1.20.0"  # Different
                            }
                        ]
                    }
                }
            }, f)
        
        # Run validation
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-overrides", str(ubuntu_file)]
        )
        
        # Should show no duplicates
        assert result.exit_code == 0
        # Should indicate all overrides are necessary
    
    def test_validation_with_all_duplicates(self, tmp_path):
        """Test validation when all fields are duplicates."""
        # Create directory structure
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create default.yaml
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx", "version": "1.24.0"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ],
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                        ]
                    }
                }
            }, f)
        
        # Create ubuntu/22.04.yaml identical to default
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                        ]
                    }
                }
            }, f)
        
        # Run validation
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-overrides", str(ubuntu_file)]
        )
        
        # Should detect all as duplicates
        assert result.exit_code == 0
        assert "identical" in result.output.lower() or "duplicate" in result.output.lower()
    
    def test_validation_preserves_file_structure(self, tmp_path):
        """Test that validation preserves file structure and formatting."""
        # Create directory structure
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create default.yaml
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }, f)
        
        # Create ubuntu/22.04.yaml
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        original_content = {
            "version": "0.3",
            "providers": {
                "apt": {
                    "packages": [
                        {"name": "nginx", "package_name": "nginx", "version": "1.20.0"}
                    ]
                }
            }
        }
        with open(ubuntu_file, "w") as f:
            yaml.dump(original_content, f)
        
        # Run validation without --remove-duplicates
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-overrides", str(ubuntu_file)]
        )
        
        # File should not be modified
        with open(ubuntu_file) as f:
            current_content = yaml.safe_load(f)
        
        assert current_content == original_content


@pytest.mark.integration
class TestOverrideValidationBackup:
    """Integration tests for backup functionality in override validation."""
    
    def test_backup_creation_before_cleanup(self, tmp_path):
        """Test that backup is created before cleaning up duplicates."""
        # Create directory structure
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create default.yaml
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }, f)
        
        # Create ubuntu/22.04.yaml
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx", "version": "1.20.0"}
                        ]
                    }
                }
            }, f)
        
        # Run validation with --remove-duplicates
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-overrides", "--remove-duplicates", str(ubuntu_file)]
        )
        
        # Should create backup
        backup_files = list(ubuntu_dir.glob("*.backup.*.yaml"))
        assert len(backup_files) > 0
    
    def test_backup_contains_original_content(self, tmp_path):
        """Test that backup contains original content before cleanup."""
        # Create directory structure
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create default.yaml
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }, f)
        
        # Create ubuntu/22.04.yaml
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        original_content = {
            "version": "0.3",
            "providers": {
                "apt": {
                    "packages": [
                        {"name": "nginx", "package_name": "nginx", "version": "1.20.0"}
                    ]
                }
            }
        }
        with open(ubuntu_file, "w") as f:
            yaml.dump(original_content, f)
        
        # Run validation with --remove-duplicates
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-overrides", "--remove-duplicates", str(ubuntu_file)]
        )
        
        # Find backup file
        backup_files = list(ubuntu_dir.glob("*.backup.*.yaml"))
        assert len(backup_files) > 0
        
        # Verify backup contains original content
        with open(backup_files[0]) as f:
            backup_content = yaml.safe_load(f)
        
        assert backup_content == original_content
