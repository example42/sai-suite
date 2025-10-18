"""Action file loader for SAI CLI tool."""

import json
from pathlib import Path

import yaml
from pydantic import ValidationError

from ..models.actions import ActionFile
from ..utils.errors import SaiError


class ActionFileError(SaiError):
    """Error loading or parsing action files."""


class ActionFileNotFoundError(ActionFileError):
    """Action file not found."""


class ActionFileValidationError(ActionFileError):
    """Action file validation failed."""


class ActionLoader:
    """Loads and validates action files."""

    def __init__(self):
        """Initialize the action loader."""

    def load_action_file(self, file_path: Path) -> ActionFile:
        """Load and validate an action file.

        Args:
            file_path: Path to the action file

        Returns:
            ActionFile: Validated action file object

        Raises:
            ActionFileNotFoundError: If file doesn't exist
            ActionFileValidationError: If file is invalid
        """
        if not file_path.exists():
            raise ActionFileNotFoundError(f"Action file not found: {file_path}")

        try:
            # Load file content
            content = file_path.read_text(encoding="utf-8")

            # Parse based on file extension
            if file_path.suffix.lower() in [".yaml", ".yml"]:
                data = yaml.safe_load(content)
            elif file_path.suffix.lower() == ".json":
                data = json.loads(content)
            else:
                # Try YAML first, then JSON
                try:
                    data = yaml.safe_load(content)
                except yaml.YAMLError:
                    data = json.loads(content)

            # Validate against schema
            return ActionFile(**data)

        except yaml.YAMLError as e:
            raise ActionFileValidationError(f"Invalid YAML in action file: {e}")
        except json.JSONDecodeError as e:
            raise ActionFileValidationError(f"Invalid JSON in action file: {e}")
        except ValidationError as e:
            error_details = []
            for error in e.errors():
                field = " -> ".join(str(x) for x in error["loc"])
                message = error["msg"]
                error_details.append(f"{field}: {message}")

            raise ActionFileValidationError(
                f"Action file validation failed:\n"
                + "\n".join(f"  • {detail}" for detail in error_details)
            )
        except Exception as e:
            raise ActionFileValidationError(f"Error loading action file: {e}")

    def validate_action_file_schema(self, file_path: Path) -> bool:
        """Validate an action file against the schema without loading.

        Args:
            file_path: Path to the action file

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            self.load_action_file(file_path)
            return True
        except ActionFileError:
            return False
