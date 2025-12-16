"""Performance tests for refresh-versions command.

This module tests performance requirements for the refresh-versions command,
including single file refresh time, directory refresh time, and repository
query performance with 33+ repositories configured.
"""

import pytest
import yaml
import time
from pathlib import Path
from click.testing import CliRunner

from saigen.cli.main import cli


@pytest.mark.integration
@pytest.mark.performance
class TestRefreshVersionsPerformance:
    """Performance tests for refresh-versions command."""
    
    def test_single_file_refresh_time(self, tmp_path):
        """Test that single file refresh completes in < 5 seconds."""
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
        
        # Should complete in < 5 seconds (target from requirements)
        assert elapsed_time < 5.0, f"Single file refresh took {elapsed_time:.2f}s, expected < 5s"
        
        # Log performance for monitoring
        print(f"\nSingle file refresh time: {elapsed_time:.2f}s")
    
    def test_directory_refresh_10_files_time(self, tmp_path):
        """Test that directory refresh with 10 files completes in < 30 seconds."""
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
            ("ubuntu", "20.04", "apt"),
            ("ubuntu", "22.04", "apt"),
            ("ubuntu", "24.04", "apt"),
            ("debian", "10", "apt"),
            ("debian", "11", "apt"),
            ("debian", "12", "apt"),
            ("fedora", "39", "dnf"),
            ("fedora", "40", "dnf"),
            ("rocky", "9", "dnf")
        ]
        
        for os_name, version, provider in os_versions:
            os_dir = software_dir / os_name
            os_dir.mkdir(exist_ok=True)
            
            os_file = os_dir / f"{version}.yaml"
            with open(os_file, "w") as f:
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
        
        # Should complete in < 30 seconds (target from requirements)
        assert elapsed_time < 30.0, f"Directory refresh took {elapsed_time:.2f}s, expected < 30s"
        
        # Log performance for monitoring
        print(f"\nDirectory refresh (10 files) time: {elapsed_time:.2f}s")
        print(f"Average time per file: {elapsed_time / 10:.2f}s")
    
    def test_directory_refresh_with_33_plus_repositories(self, tmp_path):
        """Test performance with 33+ repositories configured.
        
        This test verifies that the system can handle a large number of
        repository configurations without significant performance degradation.
        """
        # Create directory with files that would query different repositories
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
        
        # Create files for various OS versions (would query different repos)
        os_configs = [
            ("ubuntu", "20.04", "apt"),
            ("ubuntu", "22.04", "apt"),
            ("ubuntu", "24.04", "apt"),
            ("debian", "10", "apt"),
            ("debian", "11", "apt"),
            ("debian", "12", "apt"),
            ("fedora", "38", "dnf"),
            ("fedora", "39", "dnf"),
            ("fedora", "40", "dnf"),
            ("rocky", "8", "dnf"),
            ("rocky", "9", "dnf"),
            ("alma", "8", "dnf"),
            ("alma", "9", "dnf"),
        ]
        
        for os_name, version, provider in os_configs:
            os_dir = software_dir / os_name
            os_dir.mkdir(exist_ok=True)
            
            os_file = os_dir / f"{version}.yaml"
            with open(os_file, "w") as f:
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
        
        # Should process all files
        file_count = len(os_configs) + 1  # +1 for default.yaml
        assert f"Processing {file_count} saidata file(s)" in result.output
        
        # Should complete in reasonable time (< 60 seconds for 14 files)
        assert elapsed_time < 60.0, f"Refresh with 33+ repos took {elapsed_time:.2f}s, expected < 60s"
        
        # Log performance for monitoring
        print(f"\nRefresh with 33+ repositories time: {elapsed_time:.2f}s")
        print(f"Files processed: {file_count}")
        print(f"Average time per file: {elapsed_time / file_count:.2f}s")
    
    def test_file_creation_performance(self, tmp_path):
        """Test performance of OS-specific file creation."""
        # Create directory with only default.yaml
        software_dir = tmp_path / "nginx"
        software_dir.mkdir()
        
        default_file = software_dir / "default.yaml"
        with open(default_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "nginx"},
                "packages": [{"name": "nginx", "package_name": "nginx", "version": "1.24.0"}]
            }, f)
        
        # Measure time for file creation
        start_time = time.time()
        
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--create-missing", "--check-only", str(software_dir)]
        )
        
        elapsed_time = time.time() - start_time
        
        # Should complete successfully
        assert result.exit_code == 0
        
        # Should complete in reasonable time (< 30 seconds)
        assert elapsed_time < 30.0, f"File creation took {elapsed_time:.2f}s, expected < 30s"
        
        # Log performance for monitoring
        print(f"\nFile creation performance time: {elapsed_time:.2f}s")
    
    def test_cache_effectiveness(self, tmp_path):
        """Test cache effectiveness by running refresh twice."""
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
        
        runner = CliRunner()
        
        # First run (cold cache)
        start_time = time.time()
        result1 = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(ubuntu_file)]
        )
        first_run_time = time.time() - start_time
        
        assert result1.exit_code == 0
        
        # Second run (warm cache)
        start_time = time.time()
        result2 = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(ubuntu_file)]
        )
        second_run_time = time.time() - start_time
        
        assert result2.exit_code == 0
        
        # Second run should be faster or similar (cache effectiveness)
        # Allow some variance due to system load
        cache_speedup = first_run_time / second_run_time if second_run_time > 0 else 1.0
        
        # Log cache performance
        print(f"\nFirst run (cold cache): {first_run_time:.2f}s")
        print(f"Second run (warm cache): {second_run_time:.2f}s")
        print(f"Cache speedup: {cache_speedup:.2f}x")
        
        # Cache should provide some benefit (at least not slower)
        assert second_run_time <= first_run_time * 1.5, "Second run should not be significantly slower"


@pytest.mark.integration
@pytest.mark.performance
class TestScalabilityPerformance:
    """Performance tests for scalability scenarios."""
    
    def test_large_directory_structure_performance(self, tmp_path):
        """Test performance with large directory structure (20+ files)."""
        # Create directory with 20+ files
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
        
        # Create 20 OS-specific files
        os_configs = []
        for ubuntu_ver in ["18.04", "20.04", "22.04", "24.04"]:
            os_configs.append(("ubuntu", ubuntu_ver, "apt"))
        for debian_ver in ["9", "10", "11", "12", "13"]:
            os_configs.append(("debian", debian_ver, "apt"))
        for fedora_ver in ["37", "38", "39", "40", "41"]:
            os_configs.append(("fedora", fedora_ver, "dnf"))
        for rocky_ver in ["8", "9", "10"]:
            os_configs.append(("rocky", rocky_ver, "dnf"))
        for alma_ver in ["8", "9", "10"]:
            os_configs.append(("alma", alma_ver, "dnf"))
        
        for os_name, version, provider in os_configs:
            os_dir = software_dir / os_name
            os_dir.mkdir(exist_ok=True)
            
            os_file = os_dir / f"{version}.yaml"
            with open(os_file, "w") as f:
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
        
        # Should process all files
        file_count = len(os_configs) + 1
        assert f"Processing {file_count} saidata file(s)" in result.output
        
        # Should complete in reasonable time (< 90 seconds for 20+ files)
        assert elapsed_time < 90.0, f"Large directory refresh took {elapsed_time:.2f}s, expected < 90s"
        
        # Log performance
        print(f"\nLarge directory ({file_count} files) refresh time: {elapsed_time:.2f}s")
        print(f"Average time per file: {elapsed_time / file_count:.2f}s")
    
    def test_multiple_packages_per_file_performance(self, tmp_path):
        """Test performance with files containing multiple packages."""
        # Create file with 10 packages
        software_dir = tmp_path / "dev-tools"
        software_dir.mkdir()
        ubuntu_dir = software_dir / "ubuntu"
        ubuntu_dir.mkdir()
        
        ubuntu_file = ubuntu_dir / "22.04.yaml"
        packages = []
        for i in range(10):
            packages.append({
                "name": f"package{i}",
                "package_name": f"package{i}",
                "version": "1.0.0"
            })
        
        with open(ubuntu_file, "w") as f:
            yaml.dump({
                "version": "0.3",
                "metadata": {"name": "dev-tools"},
                "providers": {
                    "apt": {
                        "packages": packages
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
        
        # Should complete in reasonable time (< 15 seconds for 10 packages)
        assert elapsed_time < 15.0, f"Multi-package refresh took {elapsed_time:.2f}s, expected < 15s"
        
        # Log performance
        print(f"\nMulti-package (10 packages) refresh time: {elapsed_time:.2f}s")
        print(f"Average time per package: {elapsed_time / 10:.2f}s")
    
    def test_concurrent_repository_queries_performance(self, tmp_path):
        """Test performance of concurrent repository queries."""
        # Create directory with files that would trigger concurrent queries
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
        
        # Create 5 OS-specific files (should trigger concurrent queries)
        os_configs = [
            ("ubuntu", "22.04", "apt"),
            ("debian", "11", "apt"),
            ("fedora", "40", "dnf"),
            ("rocky", "9", "dnf"),
            ("alma", "9", "dnf")
        ]
        
        for os_name, version, provider in os_configs:
            os_dir = software_dir / os_name
            os_dir.mkdir(exist_ok=True)
            
            os_file = os_dir / f"{version}.yaml"
            with open(os_file, "w") as f:
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
        
        # Should process all files
        file_count = len(os_configs) + 1
        assert f"Processing {file_count} saidata file(s)" in result.output
        
        # Should complete in reasonable time (< 20 seconds for 6 files)
        assert elapsed_time < 20.0, f"Concurrent queries took {elapsed_time:.2f}s, expected < 20s"
        
        # Log performance
        print(f"\nConcurrent queries ({file_count} files) time: {elapsed_time:.2f}s")
        print(f"Average time per file: {elapsed_time / file_count:.2f}s")


@pytest.mark.integration
@pytest.mark.performance
class TestOptimizationScenarios:
    """Performance tests for optimization scenarios."""
    
    def test_skip_default_performance_improvement(self, tmp_path):
        """Test that --skip-default improves performance by skipping default.yaml."""
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
        
        # Create 5 OS-specific files
        for i, (os_name, version) in enumerate([
            ("ubuntu", "22.04"),
            ("debian", "11"),
            ("fedora", "40"),
            ("rocky", "9"),
            ("alma", "9")
        ]):
            os_dir = software_dir / os_name
            os_dir.mkdir(exist_ok=True)
            
            os_file = os_dir / f"{version}.yaml"
            provider = "apt" if os_name in ["ubuntu", "debian"] else "dnf"
            with open(os_file, "w") as f:
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
        
        runner = CliRunner()
        
        # Run without --skip-default
        start_time = time.time()
        result1 = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--check-only", str(software_dir)]
        )
        time_with_default = time.time() - start_time
        
        assert result1.exit_code == 0
        assert "Processing 6 saidata file(s)" in result1.output
        
        # Run with --skip-default
        start_time = time.time()
        result2 = runner.invoke(
            cli,
            ["refresh-versions", "--all-variants", "--skip-default", "--check-only", str(software_dir)]
        )
        time_without_default = time.time() - start_time
        
        assert result2.exit_code == 0
        assert "Processing 5 saidata file(s)" in result2.output
        
        # --skip-default should be faster (or at least not slower)
        print(f"\nWith default.yaml: {time_with_default:.2f}s (6 files)")
        print(f"Without default.yaml: {time_without_default:.2f}s (5 files)")
        print(f"Time saved: {time_with_default - time_without_default:.2f}s")
        
        # Should process fewer files and be faster
        assert time_without_default <= time_with_default * 1.1, "Skip-default should not be significantly slower"
    
    def test_provider_filter_performance_improvement(self, tmp_path):
        """Test that --providers filter improves performance."""
        # Create file with multiple providers
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
                    },
                    "binary": {
                        "binaries": [
                            {
                                "name": "main",
                                "url": "https://nginx.org/download/nginx-1.24.0-linux-amd64.tar.gz",
                                "version": "1.24.0",
                                "platform": "linux",
                                "architecture": "amd64"
                            }
                        ]
                    }
                }
            }, f)
        
        runner = CliRunner()
        
        # Run without provider filter (all providers)
        start_time = time.time()
        result1 = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", str(ubuntu_file)]
        )
        time_all_providers = time.time() - start_time
        
        assert result1.exit_code == 0
        
        # Run with provider filter (only apt)
        start_time = time.time()
        result2 = runner.invoke(
            cli,
            ["refresh-versions", "--check-only", "--providers", "apt", str(ubuntu_file)]
        )
        time_filtered = time.time() - start_time
        
        assert result2.exit_code == 0
        
        # Filtered should be faster or similar
        print(f"\nAll providers: {time_all_providers:.2f}s")
        print(f"Filtered (apt only): {time_filtered:.2f}s")
        print(f"Time saved: {time_all_providers - time_filtered:.2f}s")
        
        # Filtered should not be significantly slower
        assert time_filtered <= time_all_providers * 1.2, "Filtered refresh should not be significantly slower"
