"""Path utilities for hierarchical saidata structure."""

from pathlib import Path
from typing import Dict, Optional


def get_hierarchical_output_path(software_name: str, base_output_dir: Path) -> Path:
    """Get hierarchical output path for a software package.

    Creates a path following the structure:
    {first_two_letters}/{software_name}/default.yaml

    Examples:
        - sysdig -> sy/sysdig/default.yaml
        - nginx -> ng/nginx/default.yaml
        - apache -> ap/apache/default.yaml

    Args:
        software_name: Name of the software (will be normalized to lowercase)
        base_output_dir: Base output directory

    Returns:
        Full hierarchical path for the saidata file

    Raises:
        ValueError: If software_name is empty or invalid
    """
    if not software_name or not software_name.strip():
        raise ValueError("Software name cannot be empty")

    # Normalize software name (lowercase, strip whitespace)
    normalized_name = software_name.strip().lower()

    # Validate software name contains only valid characters
    if not normalized_name.replace("-", "").replace("_", "").replace(".", "").isalnum():
        raise ValueError(
            f"Invalid software name: {software_name}. "
            "Must contain only alphanumeric characters, hyphens, underscores, and dots."
        )

    # Generate prefix from first two characters
    prefix = normalized_name[:2] if len(normalized_name) >= 2 else normalized_name

    # Build hierarchical path: software/{prefix}/{software_name}/default.yaml
    hierarchical_path = base_output_dir / prefix / normalized_name / "default.yaml"

    return hierarchical_path


def extract_os_info(file_path: Path) -> Dict[str, Optional[str]]:
    """Extract OS information from saidata file path.

    Supports patterns:
    - {prefix}/{software}/{os}/{version}.yaml (e.g., ng/nginx/ubuntu/22.04.yaml)
    - {prefix}/{software}/default.yaml (e.g., ng/nginx/default.yaml)

    Args:
        file_path: Path to saidata file (can be absolute or relative)

    Returns:
        Dict with keys:
        - 'os': OS name (ubuntu, debian, fedora, etc.) or None
        - 'version': OS version (22.04, 11, 39, etc.) or None
        - 'is_default': True if default.yaml, False otherwise

    Examples:
        >>> extract_os_info(Path("ng/nginx/ubuntu/22.04.yaml"))
        {'os': 'ubuntu', 'version': '22.04', 'is_default': False}

        >>> extract_os_info(Path("ng/nginx/default.yaml"))
        {'os': None, 'version': None, 'is_default': True}

        >>> extract_os_info(Path("/path/to/ng/nginx/debian/11.yaml"))
        {'os': 'debian', 'version': '11', 'is_default': False}
    """
    # Convert to Path object if string
    if isinstance(file_path, str):
        file_path = Path(file_path)

    # Get the parts of the path
    parts = file_path.parts

    # Check if this is default.yaml
    if file_path.name == "default.yaml":
        return {"os": None, "version": None, "is_default": True}

    # Try to extract OS and version from path
    # Expected pattern: {prefix}/{software}/{os}/{version}.yaml
    # We need at least 4 parts: prefix, software, os, version.yaml
    if len(parts) >= 4:
        # The OS should be the second-to-last directory
        # The version should be the filename without .yaml extension
        os_name = parts[-2]
        version_with_ext = parts[-1]

        # Remove .yaml extension to get version
        if version_with_ext.endswith(".yaml"):
            version = version_with_ext[:-5]  # Remove .yaml
        else:
            # Not a .yaml file, treat as OS-agnostic
            return {"os": None, "version": None, "is_default": False}

        # Validate that we have both os and version
        if os_name and version:
            return {"os": os_name, "version": version, "is_default": False}

    # If we can't extract OS info, treat as OS-agnostic
    return {"os": None, "version": None, "is_default": False}
