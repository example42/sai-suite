"""Tests for path utilities including OS detection from saidata file paths."""

import pytest
from pathlib import Path

from saigen.utils.path_utils import extract_os_info, get_hierarchical_output_path


class TestExtractOsInfo:
    """Tests for extract_os_info function."""

    def test_ubuntu_path_pattern(self):
        """Test Ubuntu path patterns."""
        # Test Ubuntu 22.04
        result = extract_os_info(Path("ng/nginx/ubuntu/22.04.yaml"))
        assert result["os"] == "ubuntu"
        assert result["version"] == "22.04"
        assert result["is_default"] is False

        # Test Ubuntu 20.04
        result = extract_os_info(Path("ap/apache/ubuntu/20.04.yaml"))
        assert result["os"] == "ubuntu"
        assert result["version"] == "20.04"
        assert result["is_default"] is False

        # Test Ubuntu 24.04
        result = extract_os_info(Path("po/postgresql/ubuntu/24.04.yaml"))
        assert result["os"] == "ubuntu"
        assert result["version"] == "24.04"
        assert result["is_default"] is False

    def test_debian_path_pattern(self):
        """Test Debian path patterns."""
        # Test Debian 11
        result = extract_os_info(Path("ng/nginx/debian/11.yaml"))
        assert result["os"] == "debian"
        assert result["version"] == "11"
        assert result["is_default"] is False

        # Test Debian 12
        result = extract_os_info(Path("ap/apache/debian/12.yaml"))
        assert result["os"] == "debian"
        assert result["version"] == "12"
        assert result["is_default"] is False

        # Test Debian 10
        result = extract_os_info(Path("po/postgresql/debian/10.yaml"))
        assert result["os"] == "debian"
        assert result["version"] == "10"
        assert result["is_default"] is False

    def test_fedora_path_pattern(self):
        """Test Fedora path patterns."""
        result = extract_os_info(Path("ng/nginx/fedora/39.yaml"))
        assert result["os"] == "fedora"
        assert result["version"] == "39"
        assert result["is_default"] is False

        result = extract_os_info(Path("ap/apache/fedora/40.yaml"))
        assert result["os"] == "fedora"
        assert result["version"] == "40"
        assert result["is_default"] is False

    def test_rocky_path_pattern(self):
        """Test Rocky Linux path patterns."""
        result = extract_os_info(Path("ng/nginx/rocky/8.yaml"))
        assert result["os"] == "rocky"
        assert result["version"] == "8"
        assert result["is_default"] is False

        result = extract_os_info(Path("ap/apache/rocky/9.yaml"))
        assert result["os"] == "rocky"
        assert result["version"] == "9"
        assert result["is_default"] is False

    def test_default_yaml_handling(self):
        """Test default.yaml handling."""
        # Test default.yaml in various locations
        result = extract_os_info(Path("ng/nginx/default.yaml"))
        assert result["os"] is None
        assert result["version"] is None
        assert result["is_default"] is True

        result = extract_os_info(Path("ap/apache/default.yaml"))
        assert result["os"] is None
        assert result["version"] is None
        assert result["is_default"] is True

        # Test with absolute path
        result = extract_os_info(Path("/path/to/software/ng/nginx/default.yaml"))
        assert result["os"] is None
        assert result["version"] is None
        assert result["is_default"] is True

    def test_absolute_path_patterns(self):
        """Test with absolute paths."""
        # Test Ubuntu with absolute path
        result = extract_os_info(Path("/home/user/saidata/ng/nginx/ubuntu/22.04.yaml"))
        assert result["os"] == "ubuntu"
        assert result["version"] == "22.04"
        assert result["is_default"] is False

        # Test Debian with absolute path
        result = extract_os_info(Path("/var/lib/saidata/ap/apache/debian/11.yaml"))
        assert result["os"] == "debian"
        assert result["version"] == "11"
        assert result["is_default"] is False

    def test_string_path_input(self):
        """Test that string paths are handled correctly."""
        # Test with string input
        result = extract_os_info("ng/nginx/ubuntu/22.04.yaml")
        assert result["os"] == "ubuntu"
        assert result["version"] == "22.04"
        assert result["is_default"] is False

        result = extract_os_info("ng/nginx/default.yaml")
        assert result["os"] is None
        assert result["version"] is None
        assert result["is_default"] is True

    def test_invalid_path_patterns(self):
        """Test invalid path patterns."""
        # Too few path components
        result = extract_os_info(Path("nginx.yaml"))
        assert result["os"] is None
        assert result["version"] is None
        assert result["is_default"] is False

        # Not a yaml file
        result = extract_os_info(Path("ng/nginx/ubuntu/22.04.txt"))
        assert result["os"] is None
        assert result["version"] is None
        assert result["is_default"] is False

        # Missing version
        result = extract_os_info(Path("ng/nginx/ubuntu/"))
        assert result["os"] is None
        assert result["version"] is None
        assert result["is_default"] is False

    def test_edge_cases(self):
        """Test edge cases."""
        # Single digit version
        result = extract_os_info(Path("ng/nginx/debian/9.yaml"))
        assert result["os"] == "debian"
        assert result["version"] == "9"
        assert result["is_default"] is False

        # Version with multiple dots
        result = extract_os_info(Path("ng/nginx/ubuntu/22.04.1.yaml"))
        assert result["os"] == "ubuntu"
        assert result["version"] == "22.04.1"
        assert result["is_default"] is False

        # OS name with hyphen
        result = extract_os_info(Path("ng/nginx/centos-stream/9.yaml"))
        assert result["os"] == "centos-stream"
        assert result["version"] == "9"
        assert result["is_default"] is False

    def test_various_os_distributions(self):
        """Test various OS distributions."""
        # AlmaLinux
        result = extract_os_info(Path("ng/nginx/alma/8.yaml"))
        assert result["os"] == "alma"
        assert result["version"] == "8"
        assert result["is_default"] is False

        # RHEL
        result = extract_os_info(Path("ng/nginx/rhel/9.yaml"))
        assert result["os"] == "rhel"
        assert result["version"] == "9"
        assert result["is_default"] is False

        # SLES
        result = extract_os_info(Path("ng/nginx/sles/15.yaml"))
        assert result["os"] == "sles"
        assert result["version"] == "15"
        assert result["is_default"] is False

        # openSUSE
        result = extract_os_info(Path("ng/nginx/opensuse/15.yaml"))
        assert result["os"] == "opensuse"
        assert result["version"] == "15"
        assert result["is_default"] is False

        # Arch
        result = extract_os_info(Path("ng/nginx/arch/rolling.yaml"))
        assert result["os"] == "arch"
        assert result["version"] == "rolling"
        assert result["is_default"] is False


class TestGetHierarchicalOutputPath:
    """Tests for get_hierarchical_output_path function."""

    def test_basic_software_names(self):
        """Test basic software name handling."""
        base_dir = Path("/output")

        result = get_hierarchical_output_path("nginx", base_dir)
        assert result == Path("/output/ng/nginx/default.yaml")

        result = get_hierarchical_output_path("apache", base_dir)
        assert result == Path("/output/ap/apache/default.yaml")

        result = get_hierarchical_output_path("postgresql", base_dir)
        assert result == Path("/output/po/postgresql/default.yaml")

    def test_single_character_names(self):
        """Test single character software names."""
        base_dir = Path("/output")

        result = get_hierarchical_output_path("x", base_dir)
        assert result == Path("/output/x/x/default.yaml")

    def test_case_normalization(self):
        """Test that names are normalized to lowercase."""
        base_dir = Path("/output")

        result = get_hierarchical_output_path("NGINX", base_dir)
        assert result == Path("/output/ng/nginx/default.yaml")

        result = get_hierarchical_output_path("Apache", base_dir)
        assert result == Path("/output/ap/apache/default.yaml")

    def test_whitespace_handling(self):
        """Test whitespace is stripped."""
        base_dir = Path("/output")

        result = get_hierarchical_output_path("  nginx  ", base_dir)
        assert result == Path("/output/ng/nginx/default.yaml")

    def test_invalid_software_names(self):
        """Test invalid software names raise errors."""
        base_dir = Path("/output")

        with pytest.raises(ValueError, match="cannot be empty"):
            get_hierarchical_output_path("", base_dir)

        with pytest.raises(ValueError, match="cannot be empty"):
            get_hierarchical_output_path("   ", base_dir)

        with pytest.raises(ValueError, match="Invalid software name"):
            get_hierarchical_output_path("nginx@123", base_dir)

        with pytest.raises(ValueError, match="Invalid software name"):
            get_hierarchical_output_path("nginx/apache", base_dir)

    def test_valid_special_characters(self):
        """Test that hyphens, underscores, and dots are allowed."""
        base_dir = Path("/output")

        result = get_hierarchical_output_path("nginx-full", base_dir)
        assert result == Path("/output/ng/nginx-full/default.yaml")

        result = get_hierarchical_output_path("my_app", base_dir)
        assert result == Path("/output/my/my_app/default.yaml")

        result = get_hierarchical_output_path("app.v2", base_dir)
        assert result == Path("/output/ap/app.v2/default.yaml")
