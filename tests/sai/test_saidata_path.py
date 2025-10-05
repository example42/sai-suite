"""Tests for hierarchical saidata path resolution."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from sai.core.saidata_path import HierarchicalPathResolver, SaidataPath


class TestSaidataPath:
    """Test cases for SaidataPath class."""

    def test_from_software_name_basic(self):
        """Test basic path generation from software name."""
        base_path = Path("/test/base")
        saidata_path = SaidataPath.from_software_name("apache", base_path)

        assert saidata_path.software_name == "apache"
        assert (
            saidata_path.hierarchical_path
            == base_path / "software" / "ap" / "apache" / "default.yaml"
        )

    def test_from_software_name_single_character(self):
        """Test path generation for single character software name."""
        base_path = Path("/test/base")
        saidata_path = SaidataPath.from_software_name("r", base_path)

        assert saidata_path.software_name == "r"
        assert saidata_path.hierarchical_path == base_path / "software" / "r" / "r" / "default.yaml"

    def test_from_software_name_normalization(self):
        """Test software name normalization (lowercase, strip)."""
        base_path = Path("/test/base")
        saidata_path = SaidataPath.from_software_name("  NGINX  ", base_path)

        assert saidata_path.software_name == "nginx"
        assert (
            saidata_path.hierarchical_path
            == base_path / "software" / "ng" / "nginx" / "default.yaml"
        )

    def test_from_software_name_with_special_chars(self):
        """Test software name with valid special characters."""
        base_path = Path("/test/base")
        saidata_path = SaidataPath.from_software_name("node-js_v2.0", base_path)

        assert saidata_path.software_name == "node-js_v2.0"
        assert (
            saidata_path.hierarchical_path
            == base_path / "software" / "no" / "node-js_v2.0" / "default.yaml"
        )

    def test_from_software_name_empty_raises_error(self):
        """Test that empty software name raises ValueError."""
        base_path = Path("/test/base")

        with pytest.raises(ValueError, match="Software name cannot be empty"):
            SaidataPath.from_software_name("", base_path)

        with pytest.raises(ValueError, match="Software name cannot be empty"):
            SaidataPath.from_software_name("   ", base_path)

    def test_from_software_name_invalid_chars_raises_error(self):
        """Test that invalid characters in software name raise ValueError."""
        base_path = Path("/test/base")

        with pytest.raises(ValueError, match="Invalid software name"):
            SaidataPath.from_software_name("apache@server", base_path)

        with pytest.raises(ValueError, match="Invalid software name"):
            SaidataPath.from_software_name("nginx/proxy", base_path)

    def test_exists_file_present(self):
        """Test exists() method when file is present."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create hierarchical structure
            software_dir = base_path / "software" / "ap" / "apache"
            software_dir.mkdir(parents=True)
            saidata_file = software_dir / "default.yaml"
            saidata_file.write_text("version: '0.2'\nmetadata:\n  name: apache")

            saidata_path = SaidataPath.from_software_name("apache", base_path)
            assert saidata_path.exists() is True

    def test_exists_file_missing(self):
        """Test exists() method when file is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            saidata_path = SaidataPath.from_software_name("apache", base_path)
            assert saidata_path.exists() is False

    def test_exists_permission_error(self):
        """Test exists() method handles permission errors gracefully."""
        saidata_path = SaidataPath("test", Path("/root/restricted/software/te/test/default.yaml"))

        # Should return False instead of raising exception
        assert saidata_path.exists() is False

    def test_get_directory(self):
        """Test get_directory() method."""
        base_path = Path("/test/base")
        saidata_path = SaidataPath.from_software_name("nginx", base_path)

        expected_dir = base_path / "software" / "ng" / "nginx"
        assert saidata_path.get_directory() == expected_dir

    def test_get_alternative_files(self):
        """Test get_alternative_files() method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create hierarchical structure with alternative files
            software_dir = base_path / "software" / "ng" / "nginx"
            software_dir.mkdir(parents=True)

            # Create alternative files
            (software_dir / "default.yml").write_text("test")
            (software_dir / "default.json").write_text("test")
            (software_dir / "saidata.yaml").write_text("test")
            (software_dir / "other.yaml").write_text("test")  # Should not be included

            saidata_path = SaidataPath.from_software_name("nginx", base_path)
            alternatives = saidata_path.get_alternative_files()

            # Should find 3 alternative files (excluding other.yaml)
            assert len(alternatives) == 3
            alternative_names = [f.name for f in alternatives]
            assert "default.yml" in alternative_names
            assert "default.json" in alternative_names
            assert "saidata.yaml" in alternative_names
            assert "other.yaml" not in alternative_names

    def test_get_alternative_files_directory_missing(self):
        """Test get_alternative_files() when directory doesn't exist."""
        base_path = Path("/nonexistent")
        saidata_path = SaidataPath.from_software_name("nginx", base_path)
        alternatives = saidata_path.get_alternative_files()

        assert alternatives == []

    def test_find_existing_file_primary(self):
        """Test find_existing_file() finds primary file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create hierarchical structure with primary file
            software_dir = base_path / "software" / "ap" / "apache"
            software_dir.mkdir(parents=True)
            (software_dir / "default.yaml").write_text("test")

            saidata_path = SaidataPath.from_software_name("apache", base_path)
            found_file = saidata_path.find_existing_file()

            assert found_file == software_dir / "default.yaml"

    def test_find_existing_file_alternative(self):
        """Test find_existing_file() finds alternative file when primary missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create hierarchical structure with only alternative file
            software_dir = base_path / "software" / "ap" / "apache"
            software_dir.mkdir(parents=True)
            (software_dir / "default.yml").write_text("test")

            saidata_path = SaidataPath.from_software_name("apache", base_path)
            found_file = saidata_path.find_existing_file()

            assert found_file == software_dir / "default.yml"

    def test_find_existing_file_none(self):
        """Test find_existing_file() returns None when no files exist."""
        base_path = Path("/nonexistent")
        saidata_path = SaidataPath.from_software_name("apache", base_path)
        found_file = saidata_path.find_existing_file()

        assert found_file is None

    def test_validate_path_valid(self):
        """Test validate_path() with valid path."""
        base_path = Path("/test/base")
        saidata_path = SaidataPath.from_software_name("apache", base_path)
        errors = saidata_path.validate_path()

        assert errors == []

    def test_validate_path_empty_software_name(self):
        """Test validate_path() with empty software name."""
        saidata_path = SaidataPath("", Path("/test/software/ap/apache/default.yaml"))
        errors = saidata_path.validate_path()

        assert "Software name is empty" in errors

    def test_validate_path_invalid_structure(self):
        """Test validate_path() with invalid path structure."""
        saidata_path = SaidataPath("apache", Path("/test/invalid/path.yaml"))
        errors = saidata_path.validate_path()

        assert len(errors) > 0
        # The actual error message should be about missing 'software' directory
        assert any("software" in error for error in errors)

    def test_validate_path_wrong_prefix(self):
        """Test validate_path() with wrong prefix directory."""
        saidata_path = SaidataPath("apache", Path("/test/software/ng/apache/default.yaml"))
        errors = saidata_path.validate_path()

        assert any(
            "Prefix directory 'ng' does not match expected 'ap'" in error for error in errors
        )

    def test_validate_path_wrong_software_directory(self):
        """Test validate_path() with wrong software directory name."""
        saidata_path = SaidataPath("apache", Path("/test/software/ap/nginx/default.yaml"))
        errors = saidata_path.validate_path()

        assert any(
            "Software directory 'nginx' does not match software name 'apache'" in error
            for error in errors
        )

    def test_validate_path_wrong_filename(self):
        """Test validate_path() with wrong filename."""
        saidata_path = SaidataPath("apache", Path("/test/software/ap/apache/saidata.yaml"))
        errors = saidata_path.validate_path()

        assert any("File name 'saidata.yaml' should be 'default.yaml'" in error for error in errors)

    def test_str_representation(self):
        """Test string representation of SaidataPath."""
        base_path = Path("/test/base")
        saidata_path = SaidataPath.from_software_name("apache", base_path)

        assert str(saidata_path) == str(saidata_path.hierarchical_path)

    def test_repr_representation(self):
        """Test detailed string representation of SaidataPath."""
        base_path = Path("/test/base")
        saidata_path = SaidataPath.from_software_name("apache", base_path)

        repr_str = repr(saidata_path)
        assert "SaidataPath" in repr_str
        assert "software_name='apache'" in repr_str
        assert "hierarchical_path=" in repr_str


class TestHierarchicalPathResolver:
    """Test cases for HierarchicalPathResolver class."""

    def test_init(self):
        """Test HierarchicalPathResolver initialization."""
        search_paths = [Path("/path1"), Path("/path2")]
        resolver = HierarchicalPathResolver(search_paths)

        assert resolver.search_paths == search_paths

    def test_find_saidata_files_single_path(self):
        """Test finding saidata files in single search path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create hierarchical structure
            software_dir = base_path / "software" / "ap" / "apache"
            software_dir.mkdir(parents=True)
            saidata_file = software_dir / "default.yaml"
            saidata_file.write_text("test")

            resolver = HierarchicalPathResolver([base_path])
            found_files = resolver.find_saidata_files("apache")

            assert len(found_files) == 1
            assert found_files[0] == saidata_file

    def test_find_saidata_files_multiple_paths(self):
        """Test finding saidata files across multiple search paths."""
        with tempfile.TemporaryDirectory() as temp_dir1, tempfile.TemporaryDirectory() as temp_dir2:
            base_path1 = Path(temp_dir1)
            base_path2 = Path(temp_dir2)

            # Create hierarchical structure in both paths
            for base_path in [base_path1, base_path2]:
                software_dir = base_path / "software" / "ap" / "apache"
                software_dir.mkdir(parents=True)
                saidata_file = software_dir / "default.yaml"
                saidata_file.write_text("test")

            resolver = HierarchicalPathResolver([base_path1, base_path2])
            found_files = resolver.find_saidata_files("apache")

            # Should find files in both paths, ordered by search path precedence
            assert len(found_files) == 2
            assert found_files[0].parent.parent.parent.parent == base_path1
            assert found_files[1].parent.parent.parent.parent == base_path2

    def test_find_saidata_files_nonexistent_path(self):
        """Test finding saidata files with nonexistent search path."""
        nonexistent_path = Path("/nonexistent/path")
        resolver = HierarchicalPathResolver([nonexistent_path])
        found_files = resolver.find_saidata_files("apache")

        assert found_files == []

    def test_find_saidata_files_invalid_software_name(self):
        """Test finding saidata files with invalid software name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            resolver = HierarchicalPathResolver([base_path])

            # Should handle invalid software name gracefully
            found_files = resolver.find_saidata_files("invalid@name")
            assert found_files == []

    def test_find_saidata_files_alternative_extensions(self):
        """Test finding saidata files with alternative extensions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create hierarchical structure with alternative file
            software_dir = base_path / "software" / "ng" / "nginx"
            software_dir.mkdir(parents=True)
            saidata_file = software_dir / "default.yml"  # Alternative extension
            saidata_file.write_text("test")

            resolver = HierarchicalPathResolver([base_path])
            found_files = resolver.find_saidata_files("nginx")

            assert len(found_files) == 1
            assert found_files[0] == saidata_file

    def test_get_expected_path_with_base_path(self):
        """Test get_expected_path() with explicit base path."""
        search_paths = [Path("/path1"), Path("/path2")]
        resolver = HierarchicalPathResolver(search_paths)

        custom_base = Path("/custom/base")
        expected_path = resolver.get_expected_path("apache", custom_base)

        assert expected_path.software_name == "apache"
        assert (
            expected_path.hierarchical_path
            == custom_base / "software" / "ap" / "apache" / "default.yaml"
        )

    def test_get_expected_path_default_base(self):
        """Test get_expected_path() with default base path (first search path)."""
        search_paths = [Path("/path1"), Path("/path2")]
        resolver = HierarchicalPathResolver(search_paths)

        expected_path = resolver.get_expected_path("apache")

        assert expected_path.software_name == "apache"
        assert (
            expected_path.hierarchical_path
            == search_paths[0] / "software" / "ap" / "apache" / "default.yaml"
        )

    def test_get_expected_path_no_search_paths(self):
        """Test get_expected_path() with no search paths raises error."""
        resolver = HierarchicalPathResolver([])

        with pytest.raises(ValueError, match="No search paths available"):
            resolver.get_expected_path("apache")

    def test_validate_software_name_valid(self):
        """Test validate_software_name() with valid names."""
        resolver = HierarchicalPathResolver([Path("/test")])

        valid_names = ["apache", "nginx", "node-js", "python_3", "mysql5.7"]
        for name in valid_names:
            errors = resolver.validate_software_name(name)
            assert errors == [], f"Valid name '{name}' should not have errors: {errors}"

    def test_validate_software_name_invalid(self):
        """Test validate_software_name() with invalid names."""
        resolver = HierarchicalPathResolver([Path("/test")])

        # Empty name
        errors = resolver.validate_software_name("")
        assert "Software name cannot be empty" in errors

        # Whitespace only
        errors = resolver.validate_software_name("   ")
        assert "Software name cannot be empty" in errors

        # Invalid characters
        errors = resolver.validate_software_name("apache@server")
        assert any("alphanumeric characters" in error for error in errors)

        # Too long
        long_name = "a" * 101
        errors = resolver.validate_software_name(long_name)
        assert any("cannot exceed 100 characters" in error for error in errors)

    @patch("sai.core.saidata_path.logger")
    def test_find_saidata_files_logs_debug_info(self, mock_logger):
        """Test that find_saidata_files() logs appropriate debug information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create hierarchical structure
            software_dir = base_path / "software" / "ap" / "apache"
            software_dir.mkdir(parents=True)
            saidata_file = software_dir / "default.yaml"
            saidata_file.write_text("test")

            resolver = HierarchicalPathResolver([base_path])
            resolver.find_saidata_files("apache")

            # Verify debug logging was called
            mock_logger.debug.assert_called()
            mock_logger.info.assert_called()

    def test_find_saidata_files_handles_exceptions(self):
        """Test that find_saidata_files() handles exceptions gracefully."""
        # Create resolver with path that will cause permission issues
        restricted_path = Path("/root/restricted")
        resolver = HierarchicalPathResolver([restricted_path])

        # Should not raise exception, just return empty list
        found_files = resolver.find_saidata_files("apache")
        assert found_files == []
