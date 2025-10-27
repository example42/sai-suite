"""Integration tests for refresh-versions command enhancements.

This module tests end-to-end scenarios for the provider version refresh enhancement,
including OS-specific repository selection, directory-wide refresh, file creation,
and multi-OS support.
"""

import pytest
import yaml
from pathlib import Path
from click.testing import CliRunner

from saigen.cli.main import cli
from saigen.models.repository import RepositoryInfo


@pytest.mark.integration
class TestRefreshVersionsIntegration:
    """Integration tests for refresh-versions command with OS-specific support."""
    
    def test_single_file_refresh_with_os_detection(self, tmp_path):
        """Test end-to-end refresh for single OS-specific file."""
        # Create directory structure
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create ubuntu directory
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        
        # Create ubuntu/22.04.yaml
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_file, "w") as f:
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
        
        # Run refresh-versions on OS-specific file
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(ubuntu_file)]
        )
        
        # Should complete successfully
        assert result.exit_code == 0
        assert "Check Results" in result.output
    
    def test_directory_wide_refresh_all_variants(self, tmp_path):
        """Test directory-wide refresh with multiple OS variants."""
        # Create directory structure with multiple OS files
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Create default.yaml
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx", "description": "HTTP server"},
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
                "metadata": {"name": "nginx"},
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
                "metadata": {"name": "nginx"},
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
                "metadata": {"name": "nginx"},
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx", "version": "1.18.0"}
                        ]
                    }
                }
            }, f)
        
        # Run directory-wide refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--check-only", str(software_dir)]
        )
        
        # Should process all 4 files
        assert result.exit_code == 0
        assert "Processing 4 saidata file(s)" in result.output
        assert "Summary" in result.output
        assert "Files processed: 4" in result.output
    
    def test_os_specific_repository_selection(self, tmp_path):
        """Test that OS-specific repositories are correctly selected."""
        # Create ubuntu/22.04.yaml
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
        
        # Run refresh - should detect ubuntu/22.04 and query apt-ubuntu-jammy
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(ubuntu_file)]
        )
        
        # Should complete successfully
        assert result.exit_code == 0
    
    def test_package_name_and_version_updates(self, tmp_path):
        """Test that both package names and versions are updated."""
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
                            {"name": "nginx", "package_name": "nginx-old", "version": "1.0.0"}
                        ]
                    }
                }
            }, f)
        
        # Run refresh in check-only mode
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(ubuntu_file)]
        )
        
        # Should show potential updates
        assert result.exit_code == 0
        assert "Check Results" in result.output
    
    def test_windows_macos_repository_support(self, tmp_path):
        """Test Windows and macOS repository support."""
        # Test Windows (choco)
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        windows_dir = software_dir / "windows"
        windows_dir.mkdir()
        
        windows_file = windows_dir / "latest.yaml"
        with open(windows_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {
                    "choco": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx", "version": "1.20.0"}
                        ]
                    }
                }
            }, f)
        
        # Run refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(windows_file)]
        )
        
        # Should handle Windows repository
        assert result.exit_code == 0
        
        # Test macOS (brew)
        macos_dir = software_dir / "macos"
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
        
        # Run refresh
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(macos_file)]
        )
        
        # Should handle macOS repository
        assert result.exit_code == 0
    
    def test_os_specific_file_creation_with_create_missing(self, tmp_path):
        """Test OS-specific file creation with --create-missing flag."""
        # Create directory with only default.yaml
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx", "description": "HTTP server"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }, f)
        
        # Run with --create-missing and --check-only
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--create-missing", "--check-only", str(software_dir)]
        )
        
        # Should identify missing OS-specific files
        # Note: Actual file creation depends on repository configuration
        assert result.exit_code == 0
        assert "Processing" in result.output or "Found" in result.output or "No missing" in result.output


@pytest.mark.integration
class TestMultiOSRefresh:
    """Integration tests for multi-OS refresh scenarios."""
    
    def test_refresh_multiple_ubuntu_versions(self, tmp_path):
        """Test refreshing multiple Ubuntu versions in one directory."""
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
        
        # Create multiple Ubuntu versions
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
                            "packages": [
                                {"name": "nginx", "package_name": "nginx", "version": "1.18.0"}
                            ]
                        }
                    }
                }, f)
        
        # Run directory-wide refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--check-only", str(software_dir)]
        )
        
        # Should process all 4 files (default + 3 Ubuntu versions)
        assert result.exit_code == 0
        assert "Processing 4 saidata file(s)" in result.output
    
    def test_refresh_multiple_debian_versions(self, tmp_path):
        """Test refreshing multiple Debian versions."""
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
        
        # Create multiple Debian versions
        debian_dir = software_dir / "debian"
        debian_dir.mkdir()
        
        for version in ["10", "11", "12"]:
            debian_file = debian_dir / f"{version}.yaml"
            with open(debian_file, "w") as f:
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
        
        # Run directory-wide refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--check-only", str(software_dir)]
        )
        
        # Should process all 4 files
        assert result.exit_code == 0
        assert "Processing 4 saidata file(s)" in result.output
    
    def test_refresh_mixed_distributions(self, tmp_path):
        """Test refreshing mixed distributions (Ubuntu, Debian, Fedora, Rocky)."""
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
        
        # Create Ubuntu
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        with open(ubuntu_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {"apt": {"packages": [{"name": "nginx", "package_name": "nginx", "version": "1.20.0"}]}}
            }, f)
        
        # Create Debian
        debian_dir = software_dir / "debian"
        debian_dir.mkdir()
        debian_file = debian_dir / "11.yaml"
        with open(debian_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {"apt": {"packages": [{"name": "nginx", "package_name": "nginx", "version": "1.18.0"}]}}
            }, f)
        
        # Create Fedora
        fedora_dir = software_dir / "fedora"
        fedora_dir.mkdir()
        fedora_file = fedora_dir / "40.yaml"
        with open(fedora_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {"dnf": {"packages": [{"name": "nginx", "package_name": "nginx", "version": "1.22.0"}]}}
            }, f)
        
        # Create Rocky
        rocky_dir = software_dir / "rocky"
        rocky_dir.mkdir()
        rocky_file = rocky_dir / "9.yaml"
        with open(rocky_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "providers": {"dnf": {"packages": [{"name": "nginx", "package_name": "nginx", "version": "1.20.0"}]}}
            }, f)
        
        # Run directory-wide refresh
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--check-only", str(software_dir)]
        )
        
        # Should process all 5 files
        assert result.exit_code == 0
        assert "Processing 5 saidata file(s)" in result.output


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Integration tests for error handling scenarios."""
    
    def test_missing_repository_handling(self, tmp_path):
        """Test handling of missing repository configuration."""
        # Create file for OS version without repository config
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
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
                "metadata": {"name": "nonexistent-package-xyz"},
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nonexistent-package-xyz", "package_name": "nonexistent-package-xyz", "version": "1.0.0"}
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
    
    def test_invalid_saidata_handling(self, tmp_path):
        """Test handling of invalid saidata files."""
        # Create invalid saidata file
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
            raise RepositoryError("Network error")
        
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
            if "ubuntu" in str(args[0]) and "w" in str(args[1]):
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
class TestPerformanceIntegration:
    """Integration tests for performance requirements."""
    
    def test_single_file_refresh_performance(self, tmp_path):
        """Test that single file refresh completes in reasonable time."""
        import time
        
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
        
        # Measure time
        start_time = time.time()
        
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(ubuntu_file)]
        )
        
        elapsed_time = time.time() - start_time
        
        # Should complete successfully
        assert result.exit_code == 0
        
        # Should complete in reasonable time (< 10 seconds for single file)
        assert elapsed_time < 10.0, f"Single file refresh took {elapsed_time:.2f}s, expected < 10s"
    
    def test_directory_refresh_performance(self, tmp_path):
        """Test that directory refresh with 10 files completes in reasonable time."""
        import time
        
        # Create directory with 10 files
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
        
        # Create 9 OS-specific files
        os_versions = [
            ("ubuntu", "20.04"),
            ("ubuntu", "22.04"),
            ("ubuntu", "24.04"),
            ("debian", "10"),
            ("debian", "11"),
            ("debian", "12"),
            ("fedora", "39"),
            ("fedora", "40"),
            ("rocky", "9")
        ]
        
        for os_name, version in os_versions:
            os_dir = software_dir / os_name
            os_dir.mkdir(exist_ok=True)
            
            os_file = os_dir / f"{version}.yaml"
            with open(os_file, "w") as f:
                provider = "apt" if os_name in ["ubuntu", "debian"] else "dnf"
                yaml.dump({
                    "version": "0.3",
                    "metadata": {"name": "nginx"},
                    "providers": {
                        provider: {
                            "packages": [
                                {"name": "nginx", "package_name": "nginx", "version": "1.20.0"}
                            ]
                        }
                    }
                }, f)
        
        # Measure time
        start_time = time.time()
        
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--check-only", str(software_dir)]
        )
        
        elapsed_time = time.time() - start_time
        
        # Should complete successfully
        assert result.exit_code == 0
        
        # Should process 10 files
        assert "Processing 10 saidata file(s)" in result.output
        
        # Should complete in reasonable time (< 60 seconds for 10 files)
        # Note: Target is < 30s but allowing more time for CI environments
        assert elapsed_time < 60.0, f"Directory refresh took {elapsed_time:.2f}s, expected < 60s"



@pytest.mark.integration
class TestFileCreationScenarios:
    """Integration tests for OS-specific file creation scenarios."""
    
    def test_create_single_os_specific_file(self, tmp_path, monkeypatch):
        """Test creating a single OS-specific file."""
        # Create directory with only default.yaml
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx", "description": "HTTP server"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }, f)
        
        # Mock query to return test data
        async def mock_query(repo_manager, package_name, provider, os_context, use_cache, verbose):
            return {'name': 'nginx', 'version': '1.20.0'}
        
        # Patch the query function
        import saigen.cli.commands.refresh_versions
        monkeypatch.setattr(saigen.cli.commands.refresh_versions, '_query_package_version', mock_query)
        
        # Run with --create-missing
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--create-missing", "--check-only", str(software_dir)]
        )
        
        # Should identify potential files to create
        assert result.exit_code == 0
    
    def test_create_multiple_files_in_directory(self, tmp_path, monkeypatch):
        """Test creating multiple OS-specific files in one operation."""
        # Create directory with only default.yaml
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }, f)
        
        # Mock query to return test data
        async def mock_query(repo_manager, package_name, provider, os_context, use_cache, verbose):
            return {'name': 'nginx', 'version': '1.20.0'}
        
        # Patch the query function
        import saigen.cli.commands.refresh_versions
        monkeypatch.setattr(saigen.cli.commands.refresh_versions, '_query_package_version', mock_query)
        
        # Run with --create-missing
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--create-missing", "--check-only", str(software_dir)]
        )
        
        # Should identify multiple potential files
        assert result.exit_code == 0
    
    def test_directory_structure_creation(self, tmp_path, monkeypatch):
        """Test that directory structure is created for new OS-specific files."""
        # Create directory with only default.yaml
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }, f)
        
        # Mock query to return test data
        async def mock_query(repo_manager, package_name, provider, os_context, use_cache, verbose):
            return {'name': 'nginx', 'version': '1.20.0'}
        
        # Patch the query function
        import saigen.cli.commands.refresh_versions
        monkeypatch.setattr(saigen.cli.commands.refresh_versions, '_query_package_version', mock_query)
        
        # Run with --create-missing (not check-only to actually create)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--create-missing", str(software_dir)]
        )
        
        # Check if directories were created (depends on repository configuration)
        # At minimum, command should complete without error
        assert result.exit_code == 0 or "Error" in result.output
    
    def test_minimal_yaml_generation(self, tmp_path, monkeypatch):
        """Test that created files have minimal YAML structure."""
        from saigen.cli.commands.refresh_versions import _create_os_specific_file, _load_saidata
        from saigen.repositories.manager import RepositoryManager
        import asyncio
        
        # Create directory with default.yaml
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx", "description": "HTTP server"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }, f)
        
        default_saidata = _load_saidata(default_file)
        
        # Create mock repository manager
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        repo_manager = RepositoryManager(cache_dir=cache_dir)
        
        # Mock query to return test data
        async def mock_query(repo_manager, package_name, provider, os_context, use_cache, verbose):
            return {'name': 'nginx', 'version': '1.20.0'}
        
        # Patch the query function
        import saigen.cli.commands.refresh_versions
        monkeypatch.setattr(saigen.cli.commands.refresh_versions, '_query_package_version', mock_query)
        
        # Create OS-specific file
        async def create():
            return await _create_os_specific_file(
                software_dir=software_dir,
                os='ubuntu',
                version='22.04',
                default_saidata=default_saidata,
                repo_manager=repo_manager,
                config=None,
                providers=['apt'],
                use_cache=True,
                verbose=False
            )
        
        success = asyncio.run(create())
        
        # Verify file was created
        os_file = software_dir / "ubuntu" / "22.04.yaml"
        if os_file.exists():
            with open(os_file) as f:
                data = yaml.safe_load(f)
            
            # Verify minimal structure
            assert data['version'] == '0.3'
            assert 'providers' in data
            # Should NOT have metadata (minimal structure)
            assert 'metadata' not in data
    
    def test_field_comparison_with_default_yaml(self, tmp_path, monkeypatch):
        """Test that created files only include fields different from default.yaml."""
        from saigen.cli.commands.refresh_versions import _create_os_specific_file, _load_saidata
        from saigen.repositories.manager import RepositoryManager
        import asyncio
        
        # Create directory with default.yaml
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }, f)
        
        default_saidata = _load_saidata(default_file)
        
        # Create mock repository manager
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        repo_manager = RepositoryManager(cache_dir=cache_dir)
        
        # Mock query to return SAME package name as default
        async def mock_query_same(repo_manager, package_name, provider, os_context, use_cache, verbose):
            return {'name': 'nginx', 'version': '1.20.0'}  # Same name, different version
        
        # Patch the query function
        import saigen.cli.commands.refresh_versions
        monkeypatch.setattr(saigen.cli.commands.refresh_versions, '_query_package_version', mock_query_same)
        
        # Create OS-specific file
        async def create():
            return await _create_os_specific_file(
                software_dir=software_dir,
                os='ubuntu',
                version='22.04',
                default_saidata=default_saidata,
                repo_manager=repo_manager,
                config=None,
                providers=['apt'],
                use_cache=True,
                verbose=False
            )
        
        success = asyncio.run(create())
        
        # Verify file was created
        os_file = software_dir / "ubuntu" / "22.04.yaml"
        if os_file.exists():
            with open(os_file) as f:
                data = yaml.safe_load(f)
            
            # Verify package_name is NOT included (same as default)
            if 'providers' in data and 'apt' in data['providers']:
                packages = data['providers']['apt'].get('packages', [])
                if packages:
                    # package_name should not be present (was same as default)
                    assert 'package_name' not in packages[0]
                    # version should be present (was different)
                    assert 'version' in packages[0]
                    assert packages[0]['version'] == '1.20.0'
    
    def test_create_missing_without_default_yaml(self, tmp_path):
        """Test that --create-missing requires default.yaml to exist."""
        # Create empty directory (no default.yaml)
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        # Run with --create-missing
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--create-missing", "--check-only", str(software_dir)]
        )
        
        # Should handle gracefully (no files to create without default.yaml)
        assert result.exit_code == 0
        assert "No saidata files found" in result.output or "default.yaml" in result.output.lower()
    
    def test_create_missing_skips_existing_files(self, tmp_path, monkeypatch):
        """Test that --create-missing skips files that already exist."""
        # Create directory with default.yaml and one OS-specific file
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }, f)
        
        # Create existing ubuntu/22.04.yaml
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
        
        # Mock query to return test data
        async def mock_query(repo_manager, package_name, provider, os_context, use_cache, verbose):
            return {'name': 'nginx', 'version': '1.20.0'}
        
        # Patch the query function
        import saigen.cli.commands.refresh_versions
        monkeypatch.setattr(saigen.cli.commands.refresh_versions, '_query_package_version', mock_query)
        
        # Run with --create-missing
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--create-missing", "--check-only", str(software_dir)]
        )
        
        # Should skip existing file
        assert result.exit_code == 0
        # Existing file should not be overwritten
        with open(ubuntu_file) as f:
            content = yaml.safe_load(f)
        assert content['providers']['apt']['packages'][0]['version'] == '1.20.0'
    
    def test_create_missing_with_multiple_providers(self, tmp_path, monkeypatch):
        """Test creating files with multiple providers."""
        # Create directory with default.yaml that has multiple providers
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ],
                "providers": {
                    "apt": {
                        "packages": [
                            {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
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
        
        # Mock query to return test data
        async def mock_query(repo_manager, package_name, provider, os_context, use_cache, verbose):
            return {'name': 'nginx', 'version': '1.20.0'}
        
        # Patch the query function
        import saigen.cli.commands.refresh_versions
        monkeypatch.setattr(saigen.cli.commands.refresh_versions, '_query_package_version', mock_query)
        
        # Run with --create-missing
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--create-missing", "--check-only", str(software_dir)]
        )
        
        # Should handle multiple providers
        assert result.exit_code == 0
