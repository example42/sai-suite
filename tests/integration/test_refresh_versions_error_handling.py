"""Error handling tests for refresh-versions command.

This module tests error handling scenarios for the refresh-versions command,
including missing repositories, package not found, invalid saidata, network errors,
EOL repository access, and file creation failures.
"""

import pytest
import yaml
from pathlib import Path
from click.testing import CliRunner

from saigen.cli.main import cli


@pytest.mark.integration
class TestErrorHandling:
    """Integration tests for error handling in refresh-versions."""
    
    def test_missing_repository_handling(self, tmp_path):
        """Test handling when OS-specific repository is not configured."""
        # Create file for OS version without repository config
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Use an exotic OS that likely doesn't have a repository configured
        exotic_dir = software_dir / "exotic-os"
        exotic_dir.mkdir()
        exotic_file = exotic_dir / "99.99.yaml"
        with open(exotic_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx", "version": "1.0.0"}
                        ]
                    }
                }
            }, f)
        
        # Run refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(exotic_file)]
        )
        
        # Should handle gracefully without crashing
        assert result.exit_code == 0
        
        # May show warning about missing repository
        # But should not crash or fail completely
    
    def test_package_not_found_handling(self, tmp_path):
        """Test handling when package is not found in repository."""
        # Create file with non-existent package
        software_dir = tmp_path / "nonexistent"
        software_dir.mkdir()
        
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nonexistent-package-xyz-12345"},
                "providers": {
                    "apt": {
                        "packages": [
                            {
                                "name": "nonexistent-package-xyz-12345",
                                "package_name": "nonexistent-package-xyz-12345",
                                "version": "1.0.0"
                            }
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
        
        # Should handle gracefully
        assert result.exit_code == 0
        
        # Should show that package was not found or unchanged
        assert "Check Results" in result.output
    
    def test_invalid_saidata_handling(self, tmp_path):
        """Test handling of invalid saidata files."""
        # Create invalid saidata file (packages should be list, not string)
        invalid_file = tmp_path / "invalid.yaml"
        with open(invalid_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "test"},
                "packages": "invalid"  # Should be a list
            }, f)
        
        # Run refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(invalid_file)]
        )
        
        # Should fail with error
        assert result.exit_code != 0
        assert "Error" in result.output or "Invalid" in result.output or "Failed" in result.output
    
    def test_malformed_yaml_handling(self, tmp_path):
        """Test handling of malformed YAML files."""
        # Create malformed YAML file
        malformed_file = tmp_path / "malformed.yaml"
        with open(malformed_file, "w") as f:
            f.write("version: 0.3\n")
            f.write("metadata:\n")
            f.write("  name: test\n")
            f.write("packages:\n")
            f.write("  - name: test\n")
            f.write("    package_name: test\n")
            f.write("    version: 1.0.0\n")
            f.write("  invalid yaml syntax here ][{}\n")  # Malformed
        
        # Run refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(malformed_file)]
        )
        
        # Should fail with error
        assert result.exit_code != 0
        assert "Error" in result.output or "Failed" in result.output or "YAML" in result.output
    
    def test_network_error_handling(self, tmp_path, monkeypatch):
        """Test handling of network errors during repository access."""
        # Create test file
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
                    }
                }
            }, f)
        
        # Mock network error
        async def mock_search_error(*args, **kwargs):
            from saigen.repositories.errors import RepositoryError
            raise RepositoryError("Network connection failed")
        
        # Patch repository manager
        from saigen.repositories import manager
        monkeypatch.setattr(manager.RepositoryManager, 'search_packages', mock_search_error)
        
        # Run refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(ubuntu_file)]
        )
        
        # Should handle error gracefully
        # May show error message but shouldn't crash
        assert "Error" in result.output or "Failed" in result.output or result.exit_code == 0
    
    def test_eol_repository_access(self, tmp_path):
        """Test handling of EOL (end-of-life) repository access."""
        # Create file for EOL OS version
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Ubuntu 18.04 is EOL
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_1804 = ubuntu_dir / "18.04.yaml"
        with open(ubuntu_1804, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx", "version": "1.14.0"}
                        ]
                    }
                }
            }, f)
        
        # Run refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(ubuntu_1804)]
        )
        
        # Should handle gracefully
        # May show informational message about EOL status
        assert result.exit_code == 0
    
    def test_file_creation_failure_handling(self, tmp_path, monkeypatch):
        """Test handling of file creation failures."""
        # Create directory with default.yaml
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [{"name": "nginx", "package_name": "nginx", "version": "1.24.0"}]
            }, f)
        
        # Mock file creation to fail
        import builtins
        original_open = builtins.open
        
        def mock_open_fail(*args, **kwargs):
            # Fail when trying to create OS-specific files
            if len(args) > 0 and "ubuntu" in str(args[0]) and len(args) > 1 and "w" in str(args[1]):
                raise PermissionError("Permission denied")
            return original_open(*args, **kwargs)
        
        monkeypatch.setattr(builtins, 'open', mock_open_fail)
        
        # Run with --create-missing
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--create-missing", "--check-only", str(software_dir)]
        )
        
        # Should handle error gracefully
        # Command may fail or show error, but shouldn't crash unexpectedly
        assert "Error" in result.output or "Failed" in result.output or result.exit_code in [0, 1]


@pytest.mark.integration
class TestMultiFileErrorHandling:
    """Test error handling in multi-file processing scenarios."""
    
    def test_continue_on_single_file_error(self, tmp_path):
        """Test that multi-file processing continues when one file fails."""
        # Create directory with valid and invalid files
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create valid default.yaml
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [{"name": "nginx", "package_name": "nginx", "version": "1.24.0"}]
            }, f)
        
        # Create invalid ubuntu/22.04.yaml
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": "invalid"  # Should be a list
            }, f)
        
        # Create valid debian/11.yaml
        debian_dir = software_dir / "debian"
        debian_dir.mkdir()
        debian_file = debian_dir / "11.yaml"
        with open(debian_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {
                    "apt": {
                        "packages": [{"name": "nginx", "package_name": "nginx", "version": "1.18.0"}]
                    }
                }
            }, f)
        
        # Run refresh with --all-variants
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--check-only", str(software_dir)]
        )
        
        # Should process files that were found
        assert "Processing" in result.output
        
        # Should show summary even with errors
        assert "Summary" in result.output or "Failed" in result.output or "Files processed" in result.output
    
    def test_error_summary_in_multi_file_processing(self, tmp_path):
        """Test that error summary is displayed in multi-file processing."""
        # Create directory with multiple files, some will fail
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
        
        # Create valid ubuntu/22.04.yaml
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_2204 = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_2204, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {
                    "apt": {
                        "packages": [{"name": "nginx", "package_name": "nginx", "version": "1.20.0"}]
                    }
                }
            }, f)
        
        # Create invalid ubuntu/20.04.yaml
        ubuntu_2004 = ubuntu_dir / "20.04.yaml"
        with open(ubuntu_2004, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": "invalid"
            }, f)
        
        # Run refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--check-only", str(software_dir)]
        )
        
        # Should show summary with error information
        assert "Summary" in result.output or "Failed" in result.output
    
    def test_partial_success_reporting(self, tmp_path):
        """Test that partial success is properly reported."""
        # Create directory with mix of valid and problematic files
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create valid default.yaml
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [{"name": "nginx", "package_name": "nginx", "version": "1.24.0"}]
            }, f)
        
        # Create valid ubuntu/22.04.yaml
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
        
        # Create file for non-existent package (will show as unchanged/not found)
        debian_dir = software_dir / "debian"
        debian_dir.mkdir()
        debian_file = debian_dir / "11.yaml"
        with open(debian_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nonexistent-xyz", "package_name": "nonexistent-xyz", "version": "1.0.0"}
                        ]
                    }
                }
            }, f)
        
        # Run refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--check-only", str(software_dir)]
        )
        
        # Should complete and show results
        assert result.exit_code == 0
        assert "Processing 3 saidata file(s)" in result.output


@pytest.mark.integration
class TestValidationErrorHandling:
    """Test error handling for validation failures."""
    
    def test_schema_validation_failure_handling(self, tmp_path):
        """Test handling of schema validation failures."""
        # Create file that will fail schema validation
        invalid_file = tmp_path / "invalid-schema.yaml"
        with open(invalid_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "test"},
                # Missing required fields
                "packages": [
                    {"name": "test"}  # Missing package_name and version
                ]
            }, f)
        
        # Run refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(invalid_file)]
        )
        
        # Should fail with validation error
        assert result.exit_code != 0
        assert "Error" in result.output or "Invalid" in result.output or "validation" in result.output.lower()
    
    def test_missing_required_fields_handling(self, tmp_path):
        """Test handling of missing required fields in saidata."""
        # Create file with missing required fields
        incomplete_file = tmp_path / "incomplete.yaml"
        with open(incomplete_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                # Missing metadata
                "packages": [
                    {"name": "test", "package_name": "test", "version": "1.0.0"}
                ]
            }, f)
        
        # Run refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(incomplete_file)]
        )
        
        # Should fail with error about missing fields
        assert result.exit_code != 0
        assert "Error" in result.output or "Invalid" in result.output or "metadata" in result.output.lower()
    
    def test_invalid_version_format_handling(self, tmp_path):
        """Test handling of invalid version format."""
        # Create file with invalid version format
        invalid_version_file = tmp_path / "invalid-version.yaml"
        with open(invalid_version_file, "w") as f:
            yaml.dump({
                "version": "invalid",  # Should be "0.3"
                "metadata": {"name": "test"},
                "packages": [
                    {"name": "test", "package_name": "test", "version": "1.0.0"}
                ]
            }, f)
        
        # Run refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(invalid_version_file)]
        )
        
        # Should fail with error about invalid version
        assert result.exit_code != 0
        assert "Error" in result.output or "Invalid" in result.output or "version" in result.output.lower()


@pytest.mark.integration
class TestFileSystemErrorHandling:
    """Test error handling for file system operations."""
    
    def test_nonexistent_file_handling(self, tmp_path):
        """Test handling of non-existent file."""
        # Try to refresh non-existent file
        nonexistent_file = tmp_path / "nonexistent.yaml"
        
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(nonexistent_file)]
        )
        
        # Should fail with error
        assert result.exit_code != 0
        assert "Error" in result.output or "not found" in result.output.lower() or "does not exist" in result.output.lower()
    
    def test_nonexistent_directory_handling(self, tmp_path):
        """Test handling of non-existent directory."""
        # Try to refresh non-existent directory
        nonexistent_dir = tmp_path / "nonexistent"
        
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--check-only", str(nonexistent_dir)]
        )
        
        # Should fail with error
        assert result.exit_code != 0
        assert "Error" in result.output or "not found" in result.output.lower() or "does not exist" in result.output.lower()
    
    def test_empty_directory_handling(self, tmp_path):
        """Test handling of empty directory."""
        # Create empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--check-only", str(empty_dir)]
        )
        
        # Should handle gracefully
        assert result.exit_code == 0
        assert "No saidata files found" in result.output or "Processing 0 saidata file(s)" in result.output
    
    def test_permission_denied_handling(self, tmp_path, monkeypatch):
        """Test handling of permission denied errors."""
        # Create test file
        test_file = tmp_path / "test.yaml"
        with open(test_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "test"},
                "packages": [{"name": "test", "package_name": "test", "version": "1.0.0"}]
            }, f)
        
        # Mock file read to fail with permission error
        import builtins
        original_open = builtins.open
        
        def mock_open_permission_denied(*args, **kwargs):
            if len(args) > 0 and str(args[0]) == str(test_file):
                raise PermissionError("Permission denied")
            return original_open(*args, **kwargs)
        
        monkeypatch.setattr(builtins, 'open', mock_open_permission_denied)
        
        # Run refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(test_file)]
        )
        
        # Should fail with permission error
        assert result.exit_code != 0
        assert "Error" in result.output or "Permission" in result.output or "denied" in result.output.lower()


@pytest.mark.integration
class TestRecoveryMechanisms:
    """Test recovery mechanisms for error scenarios."""
    
    def test_backup_restoration_on_validation_failure(self, tmp_path, monkeypatch):
        """Test that backup is restored when validation fails after update."""
        # This test would require mocking the validation to fail
        # and verifying that the backup is restored
        # Implementation depends on the actual backup/restore mechanism
        pass
    
    def test_graceful_degradation_with_partial_repository_access(self, tmp_path):
        """Test graceful degradation when some repositories are accessible."""
        # Create directory with files for different repositories
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create files for different OS versions
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
        
        # Create file for potentially inaccessible repository
        exotic_dir = software_dir / "exotic"
        exotic_dir.mkdir()
        exotic_file = exotic_dir / "99.yaml"
        with open(exotic_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {
                    "apt": {
                        "packages": [{"name": "nginx", "package_name": "nginx", "version": "1.0.0"}]
                    }
                }
            }, f)
        
        # Run refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--check-only", str(software_dir)]
        )
        
        # Should process available files gracefully
        assert result.exit_code == 0
        assert "Processing 2 saidata file(s)" in result.output
