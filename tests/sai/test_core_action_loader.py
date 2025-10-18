"""Tests for action loader."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from sai.core.action_loader import (
    ActionFileNotFoundError,
    ActionFileValidationError,
    ActionLoader,
)
from sai.models.actions import ActionFile


class TestActionLoader:
    """Test ActionLoader class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.loader = ActionLoader()

    def test_load_valid_yaml_file(self):
        """Test loading a valid YAML action file."""
        action_data = {"config": {"verbose": True}, "actions": {"install": ["nginx", "curl"]}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(action_data, f)
            temp_path = Path(f.name)

        try:
            action_file = self.loader.load_action_file(temp_path)
            assert isinstance(action_file, ActionFile)
            assert action_file.config.verbose is True
            assert action_file.actions.install == ["nginx", "curl"]
        finally:
            temp_path.unlink()

    def test_load_valid_json_file(self):
        """Test loading a valid JSON action file."""
        action_data = {"config": {"verbose": True}, "actions": {"install": ["nginx", "curl"]}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(action_data, f)
            temp_path = Path(f.name)

        try:
            action_file = self.loader.load_action_file(temp_path)
            assert isinstance(action_file, ActionFile)
            assert action_file.config.verbose is True
            assert action_file.actions.install == ["nginx", "curl"]
        finally:
            temp_path.unlink()

    def test_load_file_without_extension(self):
        """Test loading file without extension (should try YAML first)."""
        action_data = {"config": {"verbose": True}, "actions": {"install": ["nginx"]}}

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            yaml.dump(action_data, f)
            temp_path = Path(f.name)

        try:
            action_file = self.loader.load_action_file(temp_path)
            assert isinstance(action_file, ActionFile)
            assert action_file.config.verbose is True
        finally:
            temp_path.unlink()

    def test_load_nonexistent_file(self):
        """Test loading a file that doesn't exist."""
        nonexistent_path = Path("/nonexistent/file.yaml")

        with pytest.raises(ActionFileNotFoundError):
            self.loader.load_action_file(nonexistent_path)

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML."""
        invalid_yaml = "invalid: yaml: content: ["

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(invalid_yaml)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ActionFileValidationError) as exc_info:
                self.loader.load_action_file(temp_path)
            assert "Invalid YAML" in str(exc_info.value)
        finally:
            temp_path.unlink()

    def test_load_invalid_json(self):
        """Test loading invalid JSON."""
        invalid_json = '{"invalid": json, "content"}'

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(invalid_json)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ActionFileValidationError) as exc_info:
                self.loader.load_action_file(temp_path)
            assert "Invalid JSON" in str(exc_info.value)
        finally:
            temp_path.unlink()

    def test_load_file_missing_required_fields(self):
        """Test loading file missing required fields."""
        invalid_data = {"config": {"verbose": True}}  # Missing actions

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(invalid_data, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ActionFileValidationError) as exc_info:
                self.loader.load_action_file(temp_path)
            assert "validation failed" in str(exc_info.value)
        finally:
            temp_path.unlink()

    def test_load_file_empty_actions(self):
        """Test loading file with empty actions."""
        invalid_data = {"config": {"verbose": True}, "actions": {}}  # Empty actions

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(invalid_data, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ActionFileValidationError):
                self.loader.load_action_file(temp_path)
        finally:
            temp_path.unlink()

    def test_validate_action_file_schema_valid(self):
        """Test schema validation for valid file."""
        action_data = {"config": {"verbose": True}, "actions": {"install": ["nginx"]}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(action_data, f)
            temp_path = Path(f.name)

        try:
            assert self.loader.validate_action_file_schema(temp_path) is True
        finally:
            temp_path.unlink()

    def test_validate_action_file_schema_invalid(self):
        """Test schema validation for invalid file."""
        invalid_data = {"config": {"verbose": True}}  # Missing actions

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(invalid_data, f)
            temp_path = Path(f.name)

        try:
            assert self.loader.validate_action_file_schema(temp_path) is False
        finally:
            temp_path.unlink()

    def test_load_complex_action_file(self):
        """Test loading a complex action file with all features."""
        complex_data = {
            "config": {
                "verbose": True,
                "dry_run": False,
                "timeout": 300,
                "parallel": True,
                "continue_on_error": True,
            },
            "actions": {
                "install": ["nginx", {"name": "docker", "provider": "apt", "timeout": 600}],
                "start": ["nginx", "docker"],
                "uninstall": ["old-package"],
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(complex_data, f)
            temp_path = Path(f.name)

        try:
            action_file = self.loader.load_action_file(temp_path)

            # Verify config
            assert action_file.config.verbose is True
            assert action_file.config.dry_run is False
            assert action_file.config.timeout == 300
            assert action_file.config.parallel is True
            assert action_file.config.continue_on_error is True

            # Verify actions
            assert len(action_file.actions.install) == 2
            assert action_file.actions.install[0] == "nginx"
            # Dict items remain as dicts in the flexible model
            assert isinstance(action_file.actions.install[1], dict)
            assert action_file.actions.install[1]["name"] == "docker"
            assert action_file.actions.install[1]["provider"] == "apt"
            assert action_file.actions.install[1]["timeout"] == 600

            assert action_file.actions.start == ["nginx", "docker"]
            assert action_file.actions.uninstall == ["old-package"]

        finally:
            temp_path.unlink()
