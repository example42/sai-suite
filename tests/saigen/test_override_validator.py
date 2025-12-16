"""Tests for override validator."""

import pytest
import yaml
from pathlib import Path
from saigen.core.override_validator import OverrideValidator


@pytest.fixture
def temp_saidata_dir(tmp_path):
    """Create a temporary directory with saidata files for testing."""
    # Create directory structure
    software_dir = tmp_path / "software" / "ng" / "nginx"
    software_dir.mkdir(parents=True)

    # Create default.yaml
    default_data = {
        "version": "0.3",
        "metadata": {"name": "nginx", "version": "1.24.0"},
        "packages": [{"name": "nginx", "package_name": "nginx", "version": "1.24.0"}],
        "providers": {
            "apt": {
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }
        },
    }

    default_file = software_dir / "default.yaml"
    with open(default_file, "w") as f:
        yaml.dump(default_data, f)

    # Create OS-specific directory
    ubuntu_dir = software_dir / "ubuntu"
    ubuntu_dir.mkdir()

    return software_dir


@pytest.fixture
def validator():
    """Create an OverrideValidator instance."""
    return OverrideValidator()


def test_compare_identical_files(temp_saidata_dir, validator):
    """Test comparison when OS-specific file is identical to default."""
    # Create OS-specific file identical to default
    os_data = {
        "version": "0.3",
        "providers": {
            "apt": {
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.24.0"}
                ]
            }
        },
    }

    os_file = temp_saidata_dir / "ubuntu" / "22.04.yaml"
    with open(os_file, "w") as f:
        yaml.dump(os_data, f)

    default_file = temp_saidata_dir / "default.yaml"

    # Compare
    result = validator.compare_saidata_files(os_file, default_file)

    # All fields should be identical
    assert len(result["identical_fields"]) > 0
    assert "providers.apt.packages[0].package_name" in result["identical_fields"]
    assert "providers.apt.packages[0].version" in result["identical_fields"]
    assert len(result["different_fields"]) == 0


def test_compare_different_version(temp_saidata_dir, validator):
    """Test comparison when version differs."""
    # Create OS-specific file with different version
    os_data = {
        "version": "0.3",
        "providers": {
            "apt": {
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.18.0"}
                ]
            }
        },
    }

    os_file = temp_saidata_dir / "ubuntu" / "22.04.yaml"
    with open(os_file, "w") as f:
        yaml.dump(os_data, f)

    default_file = temp_saidata_dir / "default.yaml"

    # Compare
    result = validator.compare_saidata_files(os_file, default_file)

    # Version should be different, package_name identical
    assert "providers.apt.packages[0].version" in result["different_fields"]
    assert "providers.apt.packages[0].package_name" in result["identical_fields"]


def test_compare_different_package_name(temp_saidata_dir, validator):
    """Test comparison when package name differs."""
    # Create OS-specific file with different package name
    os_data = {
        "version": "0.3",
        "providers": {
            "apt": {
                "packages": [
                    {
                        "name": "nginx",
                        "package_name": "nginx-full",
                        "version": "1.18.0",
                    }
                ]
            }
        },
    }

    os_file = temp_saidata_dir / "ubuntu" / "22.04.yaml"
    with open(os_file, "w") as f:
        yaml.dump(os_data, f)

    default_file = temp_saidata_dir / "default.yaml"

    # Compare
    result = validator.compare_saidata_files(os_file, default_file)

    # Both should be different
    assert "providers.apt.packages[0].package_name" in result["different_fields"]
    assert "providers.apt.packages[0].version" in result["different_fields"]


def test_compare_os_only_fields(temp_saidata_dir, validator):
    """Test comparison when OS-specific file has additional fields."""
    # Create OS-specific file with additional repository
    os_data = {
        "version": "0.3",
        "providers": {
            "apt": {
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.18.0"}
                ],
                "repositories": [{"name": "nginx-stable", "url": "http://nginx.org"}],
            }
        },
    }

    os_file = temp_saidata_dir / "ubuntu" / "22.04.yaml"
    with open(os_file, "w") as f:
        yaml.dump(os_data, f)

    default_file = temp_saidata_dir / "default.yaml"

    # Compare
    result = validator.compare_saidata_files(os_file, default_file)

    # Repository should be OS-only
    assert any("repositories" in field for field in result["os_only_fields"])


def test_remove_duplicate_fields(temp_saidata_dir, validator):
    """Test removing duplicate fields."""
    # Create OS-specific file with duplicates
    os_data = {
        "version": "0.3",
        "providers": {
            "apt": {
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.18.0"}
                ]
            }
        },
    }

    os_file = temp_saidata_dir / "ubuntu" / "22.04.yaml"
    with open(os_file, "w") as f:
        yaml.dump(os_data, f)

    default_file = temp_saidata_dir / "default.yaml"

    # Compare to find duplicates
    result = validator.compare_saidata_files(os_file, default_file)

    # Remove duplicates (package_name is identical)
    identical_fields = [
        f for f in result["identical_fields"] if "package_name" in f
    ]

    cleaned_data, removed_fields = validator.remove_duplicate_fields(
        os_file, identical_fields, backup=False
    )

    # Verify package_name was removed
    assert len(removed_fields) > 0
    assert any("package_name" in f for f in removed_fields)

    # Verify version is still present (it's different)
    assert "providers" in cleaned_data
    assert "apt" in cleaned_data["providers"]
    assert "packages" in cleaned_data["providers"]["apt"]
    assert len(cleaned_data["providers"]["apt"]["packages"]) > 0
    assert "version" in cleaned_data["providers"]["apt"]["packages"][0]


def test_remove_duplicate_fields_with_backup(temp_saidata_dir, validator):
    """Test removing duplicate fields with backup creation."""
    # Create OS-specific file
    os_data = {
        "version": "0.3",
        "providers": {
            "apt": {
                "packages": [
                    {"name": "nginx", "package_name": "nginx", "version": "1.18.0"}
                ]
            }
        },
    }

    os_file = temp_saidata_dir / "ubuntu" / "22.04.yaml"
    with open(os_file, "w") as f:
        yaml.dump(os_data, f)

    # Remove duplicates with backup
    cleaned_data, removed_fields = validator.remove_duplicate_fields(
        os_file, ["providers.apt.packages[0].package_name"], backup=True
    )

    # Verify backup was created
    backup_files = list(temp_saidata_dir.glob("ubuntu/*.backup"))
    assert len(backup_files) > 0


def test_parse_field_path(validator):
    """Test field path parsing."""
    # Test simple path
    result = validator._parse_field_path("providers.apt.packages")
    assert result == ["providers", "apt", "packages"]

    # Test path with array index
    result = validator._parse_field_path("providers.apt.packages[0].version")
    assert result == ["providers", "apt", "packages", 0, "version"]

    # Test path with multiple array indices
    result = validator._parse_field_path("items[0].subitems[1].value")
    assert result == ["items", 0, "subitems", 1, "value"]


def test_save_cleaned_data(temp_saidata_dir, validator):
    """Test saving cleaned data."""
    cleaned_data = {
        "version": "0.3",
        "providers": {"apt": {"packages": [{"name": "nginx", "version": "1.18.0"}]}},
    }

    output_file = temp_saidata_dir / "ubuntu" / "cleaned.yaml"

    validator.save_cleaned_data(cleaned_data, output_file)

    # Verify file was created and contains correct data
    assert output_file.exists()

    with open(output_file, "r") as f:
        loaded_data = yaml.safe_load(f)

    assert loaded_data == cleaned_data


def test_compare_with_missing_default_file(temp_saidata_dir, validator):
    """Test comparison when default file doesn't exist."""
    os_file = temp_saidata_dir / "ubuntu" / "22.04.yaml"
    with open(os_file, "w") as f:
        yaml.dump({"version": "0.3"}, f)

    non_existent_default = temp_saidata_dir / "nonexistent.yaml"

    with pytest.raises(FileNotFoundError):
        validator.compare_saidata_files(os_file, non_existent_default)


def test_compare_with_missing_os_file(temp_saidata_dir, validator):
    """Test comparison when OS-specific file doesn't exist."""
    default_file = temp_saidata_dir / "default.yaml"
    non_existent_os = temp_saidata_dir / "ubuntu" / "nonexistent.yaml"

    with pytest.raises(FileNotFoundError):
        validator.compare_saidata_files(non_existent_os, default_file)
