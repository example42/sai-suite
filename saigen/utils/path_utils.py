"""Path utilities for hierarchical saidata structure."""

from pathlib import Path


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
