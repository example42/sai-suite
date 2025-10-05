"""Tests for SaidataLoader with hierarchical path resolution."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from sai.core.saidata_loader import SaidataLoader, SaidataNotFoundError
from sai.core.saidata_path import SaidataPath
from sai.models.config import SaiConfig
from sai.models.saidata import SaiData


class TestSaidataLoaderHierarchical:
    """Test cases for SaidataLoader with hierarchical path resolution."""

    def create_test_saidata_content(self):
        """Create valid test saidata content."""
        return {
            "version": "0.2",
            "metadata": {
                "name": "apache",
                "description": "Apache HTTP Server",
                "category": "web-server",
            },
            "packages": [{"name": "apache2"}],
        }

    def create_hierarchical_structure(self, base_path: Path, software_name: str, content: dict):
        """Create hierarchical saidata structure with test content."""
        saidata_path = SaidataPath.from_software_name(software_name, base_path)
        saidata_path.get_directory().mkdir(parents=True, exist_ok=True)

        # Write as YAML
        import yaml

        with open(saidata_path.hierarchical_path, "w") as f:
            yaml.dump(content, f)

        return saidata_path.hierarchical_path

    def test_init_with_hierarchical_resolver(self):
        """Test SaidataLoader initialization creates hierarchical path resolver."""
        config = SaiConfig()
        loader = SaidataLoader(config)

        assert hasattr(loader, "_path_resolver")
        assert loader._path_resolver is not None
        assert len(loader._path_resolver.search_paths) > 0

    def test_load_saidata_hierarchical_success(self):
        """Test successful loading of hierarchical saidata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create hierarchical structure
            content = self.create_test_saidata_content()
            self.create_hierarchical_structure(base_path, "apache", content)

            # Configure loader with test path
            config = SaiConfig(saidata_paths=[str(base_path)])
            loader = SaidataLoader(config)

            # Load saidata
            saidata = loader.load_saidata("apache")

            assert saidata is not None
            assert isinstance(saidata, SaiData)
            assert saidata.metadata.name == "apache"
            assert saidata.metadata.description == "Apache HTTP Server"

    def test_load_saidata_hierarchical_not_found(self):
        """Test SaidataNotFoundError when hierarchical saidata not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Configure loader with empty test path
            config = SaiConfig(saidata_paths=[str(base_path)])
            loader = SaidataLoader(config)

            # Try to load non-existent saidata
            with pytest.raises(SaidataNotFoundError) as exc_info:
                loader.load_saidata("nonexistent")

            error = exc_info.value
            assert error.software_name == "nonexistent"
            assert len(error.expected_paths) > 0
            assert "No saidata found for software 'nonexistent'" in str(error)
            assert "hierarchical structure" in str(error)

    def test_load_saidata_invalid_software_name(self):
        """Test ValueError for invalid software name."""
        config = SaiConfig()
        loader = SaidataLoader(config)

        with pytest.raises(ValueError, match="Invalid software name"):
            loader.load_saidata("invalid@name")

    def test_load_saidata_multiple_search_paths(self):
        """Test loading saidata from multiple hierarchical search paths."""
        with tempfile.TemporaryDirectory() as temp_dir1, tempfile.TemporaryDirectory() as temp_dir2:
            base_path1 = Path(temp_dir1)
            base_path2 = Path(temp_dir2)

            # Create saidata in second path only
            content = self.create_test_saidata_content()
            self.create_hierarchical_structure(base_path2, "apache", content)

            # Configure loader with both paths (first path has precedence)
            config = SaiConfig(saidata_paths=[str(base_path1), str(base_path2)])
            loader = SaidataLoader(config)

            # Should find saidata in second path
            saidata = loader.load_saidata("apache")
            assert saidata.metadata.name == "apache"

    def test_load_saidata_precedence_order(self):
        """Test that saidata files are loaded in correct precedence order."""
        with tempfile.TemporaryDirectory() as temp_dir1, tempfile.TemporaryDirectory() as temp_dir2:
            base_path1 = Path(temp_dir1)
            base_path2 = Path(temp_dir2)

            # Create different saidata in both paths
            content1 = self.create_test_saidata_content()
            content1["metadata"]["description"] = "Apache from path 1"

            content2 = self.create_test_saidata_content()
            content2["metadata"]["description"] = "Apache from path 2"

            self.create_hierarchical_structure(base_path1, "apache", content1)
            self.create_hierarchical_structure(base_path2, "apache", content2)

            # Configure loader with both paths (first path has precedence)
            config = SaiConfig(saidata_paths=[str(base_path1), str(base_path2)])
            loader = SaidataLoader(config)

            # Should use saidata from first path (higher precedence)
            saidata = loader.load_saidata("apache")
            assert saidata.metadata.description == "Apache from path 1"

    def test_load_saidata_alternative_extensions(self):
        """Test loading saidata with alternative file extensions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create hierarchical structure with .yml extension
            content = self.create_test_saidata_content()
            saidata_path = SaidataPath.from_software_name("nginx", base_path)
            saidata_path.get_directory().mkdir(parents=True, exist_ok=True)

            # Write as .yml instead of .yaml
            yml_file = saidata_path.get_directory() / "default.yml"
            import yaml

            with open(yml_file, "w") as f:
                yaml.dump(content, f)

            # Configure loader
            config = SaiConfig(saidata_paths=[str(base_path)])
            loader = SaidataLoader(config)

            # Should find and load .yml file
            saidata = loader.load_saidata("nginx")
            assert saidata.metadata.name == "apache"  # Content has apache name

    def test_load_saidata_json_format(self):
        """Test loading saidata in JSON format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create hierarchical structure with JSON file
            content = self.create_test_saidata_content()
            saidata_path = SaidataPath.from_software_name("mysql", base_path)
            saidata_path.get_directory().mkdir(parents=True, exist_ok=True)

            # Write as JSON
            json_file = saidata_path.get_directory() / "default.json"
            with open(json_file, "w") as f:
                json.dump(content, f)

            # Configure loader
            config = SaiConfig(saidata_paths=[str(base_path)])
            loader = SaidataLoader(config)

            # Should find and load JSON file
            saidata = loader.load_saidata("mysql")
            assert saidata.metadata.name == "apache"  # Content has apache name

    def test_get_expected_hierarchical_path(self):
        """Test get_expected_hierarchical_path method."""
        config = SaiConfig()
        loader = SaidataLoader(config)

        expected_path = loader.get_expected_hierarchical_path("apache")

        assert expected_path.software_name == "apache"
        assert "software/ap/apache/default.yaml" in str(expected_path.hierarchical_path)

    def test_get_expected_hierarchical_path_custom_base(self):
        """Test get_expected_hierarchical_path with custom base path."""
        config = SaiConfig()
        loader = SaidataLoader(config)

        custom_base = Path("/custom/base")
        expected_path = loader.get_expected_hierarchical_path("nginx", custom_base)

        assert expected_path.software_name == "nginx"
        assert (
            expected_path.hierarchical_path
            == custom_base / "software" / "ng" / "nginx" / "default.yaml"
        )

    def test_validate_hierarchical_structure_valid(self):
        """Test validate_hierarchical_structure with valid structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create valid hierarchical structure
            software_dir = base_path / "software"
            software_dir.mkdir()
            (software_dir / "ap").mkdir()
            (software_dir / "ng").mkdir()

            config = SaiConfig()
            loader = SaidataLoader(config)

            errors = loader.validate_hierarchical_structure(base_path)
            assert errors == []

    def test_validate_hierarchical_structure_missing_software_dir(self):
        """Test validate_hierarchical_structure with missing software directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            config = SaiConfig()
            loader = SaidataLoader(config)

            errors = loader.validate_hierarchical_structure(base_path)
            assert len(errors) > 0
            assert any("Missing 'software' directory" in error for error in errors)

    def test_validate_hierarchical_structure_nonexistent_path(self):
        """Test validate_hierarchical_structure with nonexistent path."""
        base_path = Path("/nonexistent/path")

        config = SaiConfig()
        loader = SaidataLoader(config)

        errors = loader.validate_hierarchical_structure(base_path)
        assert len(errors) > 0
        assert any("Base path does not exist" in error for error in errors)

    def test_validate_hierarchical_structure_invalid_prefix_dirs(self):
        """Test validate_hierarchical_structure with invalid prefix directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create structure with invalid prefix directory
            software_dir = base_path / "software"
            software_dir.mkdir()
            (software_dir / "toolong").mkdir()  # Invalid: more than 2 characters

            config = SaiConfig()
            loader = SaidataLoader(config)

            errors = loader.validate_hierarchical_structure(base_path)
            assert len(errors) > 0
            assert any("Invalid prefix directory name" in error for error in errors)

    def test_find_all_hierarchical_software(self):
        """Test find_all_hierarchical_software method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create hierarchical structure with multiple software
            content = self.create_test_saidata_content()

            self.create_hierarchical_structure(base_path, "apache", content)
            self.create_hierarchical_structure(base_path, "nginx", content)
            self.create_hierarchical_structure(base_path, "mysql", content)

            config = SaiConfig()
            loader = SaidataLoader(config)

            software_list = loader.find_all_hierarchical_software(base_path)

            assert len(software_list) == 3
            assert "apache" in software_list
            assert "nginx" in software_list
            assert "mysql" in software_list
            assert software_list == sorted(software_list)  # Should be sorted

    def test_find_all_hierarchical_software_empty_structure(self):
        """Test find_all_hierarchical_software with empty structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            config = SaiConfig()
            loader = SaidataLoader(config)

            software_list = loader.find_all_hierarchical_software(base_path)
            assert software_list == []

    def test_find_all_hierarchical_software_no_software_dir(self):
        """Test find_all_hierarchical_software with no software directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            config = SaiConfig()
            loader = SaidataLoader(config)

            software_list = loader.find_all_hierarchical_software(base_path)
            assert software_list == []

    @patch("sai.core.saidata_loader.logger")
    def test_load_saidata_logs_debug_info(self, mock_logger):
        """Test that load_saidata logs appropriate debug information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create hierarchical structure
            content = self.create_test_saidata_content()
            self.create_hierarchical_structure(base_path, "apache", content)

            # Configure loader
            config = SaiConfig(saidata_paths=[str(base_path)])
            loader = SaidataLoader(config)

            # Load saidata
            loader.load_saidata("apache")

            # Verify debug logging was called
            mock_logger.debug.assert_called()
            mock_logger.info.assert_called()

    def test_load_saidata_validation_errors(self):
        """Test load_saidata with validation errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create invalid saidata (missing required fields)
            invalid_content = {
                "version": "0.2"
                # Missing metadata section
            }
            self.create_hierarchical_structure(base_path, "invalid", invalid_content)

            # Configure loader
            config = SaiConfig(saidata_paths=[str(base_path)])
            loader = SaidataLoader(config)

            # Should raise ValidationError
            with pytest.raises(Exception):  # ValidationError or similar
                loader.load_saidata("invalid")

    def test_load_saidata_with_caching_disabled(self):
        """Test load_saidata with caching disabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create hierarchical structure
            content = self.create_test_saidata_content()
            self.create_hierarchical_structure(base_path, "apache", content)

            # Configure loader with caching disabled
            config = SaiConfig(saidata_paths=[str(base_path)], cache_enabled=False)
            loader = SaidataLoader(config)

            # Load saidata
            saidata = loader.load_saidata("apache")
            assert saidata.metadata.name == "apache"

    def test_load_saidata_merging_multiple_files(self):
        """Test load_saidata merging multiple hierarchical files."""
        with tempfile.TemporaryDirectory() as temp_dir1, tempfile.TemporaryDirectory() as temp_dir2:
            base_path1 = Path(temp_dir1)
            base_path2 = Path(temp_dir2)

            # Create base saidata in second path
            base_content = {
                "version": "0.2",
                "metadata": {"name": "apache", "description": "Base Apache"},
                "packages": [{"name": "apache2"}],
            }

            # Create override saidata in first path (higher precedence)
            override_content = {
                "version": "0.2",
                "metadata": {"name": "apache", "description": "Override Apache"},
                "services": [{"name": "apache2"}],
            }

            self.create_hierarchical_structure(base_path1, "apache", override_content)
            self.create_hierarchical_structure(base_path2, "apache", base_content)

            # Configure loader with both paths
            config = SaiConfig(saidata_paths=[str(base_path1), str(base_path2)])
            loader = SaidataLoader(config)

            # Load merged saidata
            saidata = loader.load_saidata("apache")

            # Should have description from override (first path)
            assert saidata.metadata.description == "Override Apache"

            # Should have packages from base (second path) and services from override
            assert len(saidata.packages) == 1
            assert saidata.packages[0].name == "apache2"
            assert len(saidata.services) == 1
            assert saidata.services[0].name == "apache2"
