"""Tests for hierarchical path resolution edge cases and validation."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from sai.core.saidata_path import HierarchicalPathResolver, SaidataPath


class TestSaidataPathEdgeCases:
    """Test edge cases for SaidataPath."""

    @pytest.fixture
    def temp_dir(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_software_name_normalization_edge_cases(self, temp_dir):
        """Test software name normalization edge cases."""
        base_path = temp_dir

        # Test various whitespace scenarios
        test_cases = [
            ("  apache  ", "apache"),
            ("\tapache\t", "apache"),
            ("\napache\n", "apache"),
            ("  NGINX  ", "nginx"),
            ("MySQL", "mysql"),
        ]

        for input_name, expected_name in test_cases:
            path = SaidataPath.from_software_name(input_name, base_path)
            assert path.software_name == expected_name
            assert expected_name in str(path.hierarchical_path)

    def test_software_name_special_characters(self, temp_dir):
        """Test software names with special characters."""
        base_path = temp_dir

        valid_names = [
            "node-js",
            "python_3",
            "mysql5.7",
            "gcc-9",
            "lib32z1",
            "x11-apps",
            "python3.9-dev",
        ]

        for name in valid_names:
            path = SaidataPath.from_software_name(name, base_path)
            assert path.software_name == name
            assert name in str(path.hierarchical_path)

    def test_software_name_invalid_characters(self, temp_dir):
        """Test software names with invalid characters."""
        base_path = temp_dir

        invalid_names = [
            "apache@server",
            "nginx/proxy",
            "mysql\\server",
            "node:js",
            "python|3",
            "gcc<9>",
            "lib*32*z1",
            "x11?apps",
            "python3&dev",
        ]

        for name in invalid_names:
            with pytest.raises(ValueError, match="Invalid software name"):
                SaidataPath.from_software_name(name, base_path)

    def test_prefix_generation_edge_cases(self, temp_dir):
        """Test prefix generation for edge cases."""
        base_path = temp_dir

        test_cases = [
            ("a", "a"),  # Single character
            ("ab", "ab"),  # Two characters
            ("abc", "ab"),  # Three characters - should use first two
            ("1password", "1p"),  # Starting with number
            ("2fa", "2f"),  # Starting with number
            ("_private", "_p"),  # Starting with underscore
            ("-dash", "-d"),  # Starting with dash
        ]

        for software_name, expected_prefix in test_cases:
            path = SaidataPath.from_software_name(software_name, base_path)
            assert expected_prefix in str(path.hierarchical_path)
            expected_path = (
                base_path / "software" / expected_prefix / software_name / "default.yaml"
            )
            assert path.hierarchical_path == expected_path

    def test_path_validation_comprehensive(self, temp_dir):
        """Test comprehensive path validation."""
        base_path = temp_dir

        # Valid path
        valid_path = SaidataPath.from_software_name("nginx", base_path)
        errors = valid_path.validate_path()
        assert errors == []

        # Invalid path - wrong structure
        invalid_path = SaidataPath("nginx", base_path / "wrong" / "structure" / "nginx.yaml")
        errors = invalid_path.validate_path()
        assert len(errors) > 0
        assert any("software" in error for error in errors)

        # Invalid path - wrong prefix
        wrong_prefix_path = SaidataPath(
            "nginx", base_path / "software" / "ap" / "nginx" / "default.yaml"
        )
        errors = wrong_prefix_path.validate_path()
        assert len(errors) > 0
        assert any(
            "Prefix directory 'ap' does not match expected 'ng'" in error for error in errors
        )

        # Invalid path - wrong software directory
        wrong_software_path = SaidataPath(
            "nginx", base_path / "software" / "ng" / "apache" / "default.yaml"
        )
        errors = wrong_software_path.validate_path()
        assert len(errors) > 0
        assert any(
            "Software directory 'apache' does not match software name 'nginx'" in error
            for error in errors
        )

    def test_alternative_file_detection(self, temp_dir):
        """Test detection of alternative saidata files."""
        base_path = temp_dir

        # Create hierarchical structure with multiple file types
        software_dir = base_path / "software" / "ng" / "nginx"
        software_dir.mkdir(parents=True)

        # Create various alternative files
        files_to_create = [
            "default.yaml",
            "default.yml",
            "default.json",
            "saidata.yaml",
            "saidata.yml",
            "saidata.json",
            "nginx.yaml",  # Should not be detected as alternative
            "config.yaml",  # Should not be detected as alternative
        ]

        for filename in files_to_create:
            (software_dir / filename).write_text(f"content of {filename}")

        path = SaidataPath.from_software_name("nginx", base_path)
        alternatives = path.get_alternative_files()

        # Should find valid alternatives but not nginx.yaml or config.yaml
        alternative_names = [f.name for f in alternatives]

        expected_alternatives = [
            "default.yaml",
            "default.yml",
            "default.json",
            "saidata.yaml",
            "saidata.yml",
            "saidata.json",
        ]

        for expected in expected_alternatives:
            assert expected in alternative_names

        assert "nginx.yaml" not in alternative_names
        assert "config.yaml" not in alternative_names

    def test_file_existence_with_symlinks(self, temp_dir):
        """Test file existence detection with symbolic links."""
        base_path = temp_dir

        # Create actual file
        actual_dir = base_path / "actual" / "software" / "ap" / "apache"
        actual_dir.mkdir(parents=True)
        actual_file = actual_dir / "default.yaml"
        actual_file.write_text("apache config")

        # Create symlink structure
        symlink_dir = base_path / "software" / "ap" / "apache"
        symlink_dir.mkdir(parents=True)
        symlink_file = symlink_dir / "default.yaml"
        symlink_file.symlink_to(actual_file)

        path = SaidataPath.from_software_name("apache", base_path)

        # Should detect file through symlink
        assert path.exists() is True

        found_file = path.find_existing_file()
        assert found_file == symlink_file
        assert found_file.exists()
        assert found_file.read_text() == "apache config"

    def test_broken_symlink_handling(self, temp_dir):
        """Test handling of broken symbolic links."""
        base_path = temp_dir

        # Create symlink to non-existent file
        software_dir = base_path / "software" / "ap" / "apache"
        software_dir.mkdir(parents=True)
        broken_symlink = software_dir / "default.yaml"
        broken_symlink.symlink_to("/nonexistent/file.yaml")

        path = SaidataPath.from_software_name("apache", base_path)

        # Should handle broken symlink gracefully
        assert path.exists() is False

        found_file = path.find_existing_file()
        assert found_file is None

    def test_case_insensitive_filesystem_handling(self, temp_dir):
        """Test handling on case-insensitive filesystems."""
        base_path = temp_dir

        # Create directory with mixed case
        software_dir = base_path / "software" / "ng" / "NGINX"  # Uppercase
        software_dir.mkdir(parents=True)
        (software_dir / "default.yaml").write_text("nginx config")

        # Search for lowercase
        path = SaidataPath.from_software_name("nginx", base_path)

        # On case-insensitive filesystems, this might find the file
        # On case-sensitive filesystems, it won't
        # The behavior should be consistent and not crash
        exists = path.exists()
        assert isinstance(exists, bool)

        found_file = path.find_existing_file()
        assert found_file is None or found_file.exists()

    def test_very_long_software_names(self, temp_dir):
        """Test handling of very long software names."""
        base_path = temp_dir

        # Test reasonable long name (should work)
        long_name = "very-long-software-name-with-many-components-and-version-numbers-1.2.3"
        if len(long_name) <= 100:  # Assuming 100 char limit
            path = SaidataPath.from_software_name(long_name, base_path)
            assert path.software_name == long_name

        # Test extremely long name (should fail)
        extremely_long_name = "a" * 200
        with pytest.raises(ValueError):
            SaidataPath.from_software_name(extremely_long_name, base_path)

    def test_filesystem_encoding_issues(self, temp_dir):
        """Test handling of filesystem encoding issues."""
        base_path = temp_dir

        # Test with names that might cause encoding issues
        problematic_names = [
            "café",  # Unicode characters
            "naïve",  # Unicode characters
            "résumé",  # Unicode characters
        ]

        for name in problematic_names:
            try:
                # Should either work or fail gracefully
                path = SaidataPath.from_software_name(name, base_path)
                # If it works, the path should be valid
                assert isinstance(path.hierarchical_path, Path)
            except (ValueError, UnicodeError):
                # Acceptable to reject Unicode names
                pass


class TestHierarchicalPathResolverEdgeCases:
    """Test edge cases for HierarchicalPathResolver."""

    @pytest.fixture
    def temp_dir(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_empty_search_paths(self):
        """Test resolver with empty search paths."""
        resolver = HierarchicalPathResolver([])

        # Should handle empty search paths gracefully
        found_files = resolver.find_saidata_files("nginx")
        assert found_files == []

        # Should raise error when trying to get expected path
        with pytest.raises(ValueError, match="No search paths available"):
            resolver.get_expected_path("nginx")

    def test_nonexistent_search_paths(self):
        """Test resolver with non-existent search paths."""
        nonexistent_paths = [
            Path("/nonexistent/path1"),
            Path("/nonexistent/path2"),
            Path("/nonexistent/path3"),
        ]

        resolver = HierarchicalPathResolver(nonexistent_paths)

        # Should handle non-existent paths gracefully
        found_files = resolver.find_saidata_files("nginx")
        assert found_files == []

    def test_mixed_existing_nonexistent_paths(self, temp_dir):
        """Test resolver with mix of existing and non-existent paths."""
        existing_path = temp_dir / "existing"
        existing_path.mkdir()

        nonexistent_path = temp_dir / "nonexistent"

        resolver = HierarchicalPathResolver([existing_path, nonexistent_path])

        # Create saidata in existing path
        software_dir = existing_path / "software" / "ng" / "nginx"
        software_dir.mkdir(parents=True)
        (software_dir / "default.yaml").write_text("nginx config")

        found_files = resolver.find_saidata_files("nginx")

        # Should find file in existing path, ignore non-existent path
        assert len(found_files) == 1
        assert found_files[0].exists()

    def test_circular_symlinks_in_search_paths(self, temp_dir):
        """Test handling of circular symlinks in search paths."""
        # Create circular symlinks
        path1 = temp_dir / "path1"
        path2 = temp_dir / "path2"

        path1.mkdir()
        path2.mkdir()

        # Create circular symlinks
        (path1 / "link_to_path2").symlink_to(path2)
        (path2 / "link_to_path1").symlink_to(path1)

        resolver = HierarchicalPathResolver([path1, path2])

        # Should handle circular symlinks without infinite recursion
        found_files = resolver.find_saidata_files("nginx")
        assert isinstance(found_files, list)

    def test_permission_denied_in_search_paths(self, temp_dir):
        """Test handling of permission denied errors in search paths."""
        restricted_path = temp_dir / "restricted"
        restricted_path.mkdir()

        # Create saidata file
        software_dir = restricted_path / "software" / "ng" / "nginx"
        software_dir.mkdir(parents=True)
        (software_dir / "default.yaml").write_text("nginx config")

        # Restrict permissions
        restricted_path.chmod(0o000)

        try:
            resolver = HierarchicalPathResolver([restricted_path])

            # Should handle permission errors gracefully
            found_files = resolver.find_saidata_files("nginx")
            assert isinstance(found_files, list)
            # May or may not find files depending on system behavior
        finally:
            # Restore permissions for cleanup
            restricted_path.chmod(0o755)

    def test_deeply_nested_search_paths(self, temp_dir):
        """Test handling of deeply nested search paths."""
        # Create deeply nested structure
        deep_path = temp_dir
        for i in range(20):  # Create 20 levels deep
            deep_path = deep_path / f"level_{i}"
        deep_path.mkdir(parents=True)

        resolver = HierarchicalPathResolver([deep_path])

        # Should handle deep paths without issues
        found_files = resolver.find_saidata_files("nginx")
        assert isinstance(found_files, list)

    def test_search_path_with_special_characters(self, temp_dir):
        """Test search paths with special characters."""
        special_paths = [
            temp_dir / "path with spaces",
            temp_dir / "path-with-dashes",
            temp_dir / "path_with_underscores",
            temp_dir / "path.with.dots",
        ]

        for path in special_paths:
            path.mkdir(parents=True)

            # Create saidata file
            software_dir = path / "software" / "ng" / "nginx"
            software_dir.mkdir(parents=True)
            (software_dir / "default.yaml").write_text(f"nginx config in {path.name}")

        resolver = HierarchicalPathResolver(special_paths)
        found_files = resolver.find_saidata_files("nginx")

        # Should find files in all paths with special characters
        assert len(found_files) == len(special_paths)
        for file in found_files:
            assert file.exists()

    def test_concurrent_file_system_changes(self, temp_dir):
        """Test handling of concurrent file system changes."""
        resolver = HierarchicalPathResolver([temp_dir])

        # Create initial structure
        software_dir = temp_dir / "software" / "ng" / "nginx"
        software_dir.mkdir(parents=True)
        saidata_file = software_dir / "default.yaml"
        saidata_file.write_text("nginx config")

        # Simulate concurrent modification
        import threading
        import time

        def modify_filesystem():
            time.sleep(0.1)  # Small delay
            # Delete and recreate file
            if saidata_file.exists():
                saidata_file.unlink()
            time.sleep(0.1)
            saidata_file.write_text("modified nginx config")

        # Start modification in background
        modifier_thread = threading.Thread(target=modify_filesystem)
        modifier_thread.start()

        # Search for files while modification is happening
        found_files = resolver.find_saidata_files("nginx")

        modifier_thread.join()

        # Should handle concurrent changes gracefully
        assert isinstance(found_files, list)
        # File might or might not be found depending on timing

    def test_software_name_validation_comprehensive(self, temp_dir):
        """Test comprehensive software name validation."""
        resolver = HierarchicalPathResolver([temp_dir])

        # Valid names
        valid_names = [
            "nginx",
            "apache2",
            "mysql-server",
            "python3.9",
            "gcc-9",
            "lib32z1-dev",
            "x11-apps",
            "node-js",
            "python_3",
            "a",  # Single character
            "ab",  # Two characters
        ]

        for name in valid_names:
            errors = resolver.validate_software_name(name)
            assert errors == [], f"Valid name '{name}' should not have errors: {errors}"

        # Invalid names
        invalid_names = [
            "",  # Empty
            "   ",  # Whitespace only
            "a" * 101,  # Too long
            "nginx@server",  # Invalid character @
            "mysql/server",  # Invalid character /
            "python\\3",  # Invalid character \
            "node:js",  # Invalid character :
            "gcc|9",  # Invalid character |
            "lib*32*z1",  # Invalid character *
            "x11?apps",  # Invalid character ?
            "python<3>",  # Invalid characters < >
            "test&dev",  # Invalid character &
        ]

        for name in invalid_names:
            errors = resolver.validate_software_name(name)
            assert len(errors) > 0, f"Invalid name '{name}' should have errors"

    def test_path_resolution_with_relative_paths(self, temp_dir):
        """Test path resolution with relative search paths."""
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Create relative path structure
            relative_path = Path("relative_saidata")
            relative_path.mkdir()

            software_dir = relative_path / "software" / "ng" / "nginx"
            software_dir.mkdir(parents=True)
            (software_dir / "default.yaml").write_text("nginx config")

            resolver = HierarchicalPathResolver([relative_path])
            found_files = resolver.find_saidata_files("nginx")

            # Should resolve relative paths correctly
            assert len(found_files) == 1
            assert found_files[0].exists()
        finally:
            os.chdir(original_cwd)

    def test_search_performance_with_large_directories(self, temp_dir):
        """Test search performance with large directories."""
        # Create large directory structure
        software_base = temp_dir / "software"

        # Create many software packages
        for i in range(100):
            for prefix in ["aa", "bb", "cc"]:
                software_dir = software_base / prefix / f"software_{i:03d}"
                software_dir.mkdir(parents=True)
                (software_dir / "default.yaml").write_text(f"config for software_{i:03d}")

        resolver = HierarchicalPathResolver([temp_dir])

        # Search should complete in reasonable time
        import time

        start_time = time.time()

        found_files = resolver.find_saidata_files("software_050")

        end_time = time.time()
        search_time = end_time - start_time

        # Should find the file
        assert len(found_files) == 1

        # Should complete within reasonable time (adjust threshold as needed)
        assert search_time < 5.0, f"Search took too long: {search_time} seconds"
