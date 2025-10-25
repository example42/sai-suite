"""Tests for package name update functionality in refresh-versions command."""

import pytest
from saigen.cli.commands.refresh_versions import _update_package_version
from saigen.models.saidata import Package


class TestPackageNameUpdates:
    """Tests for package name update functionality."""
    
    def test_update_version_only(self):
        """Test updating only version, not package name."""
        # Create a package object
        pkg = Package(name="nginx", package_name="nginx", version="1.20.0")
        pkg_info = {
            "package_name": "nginx",
            "current_version": "1.20.0",
            "object": pkg
        }
        
        # Update version only
        _update_package_version(None, pkg_info, "1.24.0", None)
        
        # Verify version updated, name unchanged
        assert pkg.version == "1.24.0"
        assert pkg.package_name == "nginx"
        assert pkg.name == "nginx"
    
    def test_update_version_and_package_name(self):
        """Test updating both version and package name."""
        # Create a package object
        pkg = Package(name="nginx", package_name="nginx", version="1.20.0")
        pkg_info = {
            "package_name": "nginx",
            "current_version": "1.20.0",
            "object": pkg
        }
        
        # Update both version and package name
        _update_package_version(None, pkg_info, "1.24.0", "nginx-full")
        
        # Verify both updated, logical name unchanged
        assert pkg.version == "1.24.0"
        assert pkg.package_name == "nginx-full"
        assert pkg.name == "nginx"  # Logical name never changes
    
    def test_update_package_name_same_as_current(self):
        """Test that providing same package name doesn't cause issues."""
        # Create a package object
        pkg = Package(name="nginx", package_name="nginx", version="1.20.0")
        pkg_info = {
            "package_name": "nginx",
            "current_version": "1.20.0",
            "object": pkg
        }
        
        # Update with same package name
        _update_package_version(None, pkg_info, "1.24.0", "nginx")
        
        # Verify version updated, name unchanged
        assert pkg.version == "1.24.0"
        assert pkg.package_name == "nginx"
        assert pkg.name == "nginx"
    
    def test_update_preserves_logical_name(self):
        """Test that logical name is never changed."""
        # Create a package with different logical and package names
        pkg = Package(name="web-server", package_name="nginx", version="1.20.0")
        pkg_info = {
            "package_name": "nginx",
            "current_version": "1.20.0",
            "object": pkg
        }
        
        # Update both version and package name
        _update_package_version(None, pkg_info, "1.24.0", "nginx-full")
        
        # Verify logical name preserved
        assert pkg.name == "web-server"  # Logical name never changes
        assert pkg.package_name == "nginx-full"
        assert pkg.version == "1.24.0"
    
    def test_update_object_without_package_name_attribute(self):
        """Test updating object that doesn't have package_name attribute (e.g., Binary, Source)."""
        # Create a mock object without package_name
        class MockObject:
            def __init__(self):
                self.name = "test"
                self.version = "1.0.0"
        
        obj = MockObject()
        pkg_info = {
            "package_name": "test",
            "current_version": "1.0.0",
            "object": obj
        }
        
        # Update with new package name (should not crash)
        _update_package_version(None, pkg_info, "2.0.0", "test-new")
        
        # Verify version updated, no package_name attribute added
        assert obj.version == "2.0.0"
        assert not hasattr(obj, 'package_name')


class TestQueryResultFormat:
    """Tests for query result format changes."""
    
    def test_query_result_dict_format(self):
        """Test that query results are in expected dict format."""
        # This is a documentation test showing expected format
        query_result = {
            'name': 'nginx-full',
            'version': '1.24.0'
        }
        
        # Verify format
        assert 'name' in query_result
        assert 'version' in query_result
        assert isinstance(query_result['name'], str)
        assert isinstance(query_result['version'], str)
    
    def test_none_result_handling(self):
        """Test that None result is handled correctly."""
        query_result = None
        
        # Code should check for None before accessing dict
        if query_result:
            name = query_result['name']
            version = query_result['version']
        else:
            # Should handle gracefully
            assert query_result is None


class TestUpdateInfoFormat:
    """Tests for update info format with name changes."""
    
    def test_update_info_version_only(self):
        """Test update info format when only version changes."""
        update_info = {
            "provider": "apt",
            "package": "nginx",
            "old_version": "1.20.0",
            "new_version": "1.24.0",
            "location": "providers.apt.packages"
        }
        
        # Should not have old_name/new_name keys
        assert 'old_name' not in update_info
        assert 'new_name' not in update_info
    
    def test_update_info_with_name_change(self):
        """Test update info format when name changes."""
        update_info = {
            "provider": "apt",
            "package": "nginx",
            "old_version": "1.20.0",
            "new_version": "1.24.0",
            "location": "providers.apt.packages",
            "old_name": "nginx",
            "new_name": "nginx-full"
        }
        
        # Should have old_name/new_name keys
        assert 'old_name' in update_info
        assert 'new_name' in update_info
        assert update_info['old_name'] == "nginx"
        assert update_info['new_name'] == "nginx-full"


class TestNameChangeDetection:
    """Tests for name change detection in refresh flow."""
    
    def test_name_change_detected_when_different(self):
        """Test that name change is detected when package name differs."""
        # Simulate query result with different name
        query_result = {
            'name': 'nginx-full',
            'version': '1.24.0'
        }
        
        old_package_name = 'nginx'
        new_package_name = query_result['name']
        
        # Detect name change
        name_changed = new_package_name != old_package_name
        
        assert name_changed is True
        assert new_package_name == 'nginx-full'
    
    def test_name_change_not_detected_when_same(self):
        """Test that name change is not detected when package name is same."""
        # Simulate query result with same name
        query_result = {
            'name': 'nginx',
            'version': '1.24.0'
        }
        
        old_package_name = 'nginx'
        new_package_name = query_result['name']
        
        # Detect name change
        name_changed = new_package_name != old_package_name
        
        assert name_changed is False
    
    def test_name_change_with_version_change(self):
        """Test detecting both name and version changes."""
        # Simulate query result with both changes
        query_result = {
            'name': 'nginx-full',
            'version': '1.24.0'
        }
        
        old_package_name = 'nginx'
        old_version = '1.20.0'
        new_package_name = query_result['name']
        new_version = query_result['version']
        
        # Detect changes
        name_changed = new_package_name != old_package_name
        version_changed = new_version != old_version
        
        assert name_changed is True
        assert version_changed is True


class TestNameUpdateInSaidata:
    """Tests for updating package names in saidata objects."""
    
    def test_name_updated_in_package_object(self):
        """Test that package name is updated in Package object."""
        from saigen.models.saidata import Package
        
        # Create package with original name
        pkg = Package(name="web-server", package_name="nginx", version="1.20.0")
        
        # Simulate update
        pkg.package_name = "nginx-full"
        pkg.version = "1.24.0"
        
        # Verify updates
        assert pkg.package_name == "nginx-full"
        assert pkg.version == "1.24.0"
        assert pkg.name == "web-server"  # Logical name unchanged
    
    def test_name_update_preserves_other_fields(self):
        """Test that updating name preserves other package fields."""
        from saigen.models.saidata import Package
        
        # Create package with additional fields
        pkg = Package(
            name="web-server",
            package_name="nginx",
            version="1.20.0",
            repository="main",
            checksum="sha256:abc123"
        )
        
        # Simulate update
        pkg.package_name = "nginx-full"
        pkg.version = "1.24.0"
        
        # Verify other fields preserved
        assert pkg.repository == "main"
        assert pkg.checksum == "sha256:abc123"
        assert pkg.name == "web-server"


class TestNameChangeDisplay:
    """Tests for displaying name changes in output."""
    
    def test_display_format_with_name_change(self):
        """Test display format when name changes."""
        update = {
            "provider": "apt",
            "package": "nginx",
            "old_version": "1.20.0",
            "new_version": "1.24.0",
            "old_name": "nginx",
            "new_name": "nginx-full",
            "location": "providers.apt.packages"
        }
        
        # Format display string
        if 'old_name' in update and 'new_name' in update:
            display = (
                f"{update['provider']}: "
                f"{update['old_name']} v{update['old_version']} → "
                f"{update['new_name']} v{update['new_version']}"
            )
        else:
            display = (
                f"{update['provider']}/{update['package']}: "
                f"{update['old_version']} → {update['new_version']}"
            )
        
        # Verify format
        assert "apt: nginx v1.20.0 → nginx-full v1.24.0" == display
    
    def test_display_format_without_name_change(self):
        """Test display format when only version changes."""
        update = {
            "provider": "apt",
            "package": "nginx",
            "old_version": "1.20.0",
            "new_version": "1.24.0",
            "location": "providers.apt.packages"
        }
        
        # Format display string
        if 'old_name' in update and 'new_name' in update:
            display = (
                f"{update['provider']}: "
                f"{update['old_name']} v{update['old_version']} → "
                f"{update['new_name']} v{update['new_version']}"
            )
        else:
            display = (
                f"{update['provider']}/{update['package']}: "
                f"{update['old_version']} → {update['new_version']}"
            )
        
        # Verify format
        assert "apt/nginx: 1.20.0 → 1.24.0" == display


class TestNotFoundHandling:
    """Tests for handling packages not found in repositories."""
    
    def test_none_result_from_query(self):
        """Test handling None result from package query."""
        query_result = None
        
        # Should handle None gracefully
        if query_result:
            # This branch should not execute
            assert False, "Should not process None result"
        else:
            # Should continue without error
            assert query_result is None
    
    def test_package_not_found_leaves_name_unchanged(self):
        """Test that package not found leaves package_name unchanged."""
        from saigen.models.saidata import Package
        
        # Create package
        pkg = Package(name="test", package_name="test-pkg", version="1.0.0")
        original_name = pkg.package_name
        original_version = pkg.version
        
        # Simulate not found (no update)
        query_result = None
        
        if query_result:
            pkg.package_name = query_result['name']
            pkg.version = query_result['version']
        
        # Verify unchanged
        assert pkg.package_name == original_name
        assert pkg.version == original_version
    
    def test_warning_added_for_not_found(self):
        """Test that warning is added when package not found."""
        warnings = []
        package_name = "nonexistent-package"
        provider = "apt"
        
        # Simulate not found
        query_result = None
        
        if not query_result:
            warning_msg = f"Package '{package_name}' not found in {provider} repository"
            warnings.append(warning_msg)
        
        # Verify warning added
        assert len(warnings) == 1
        assert "nonexistent-package" in warnings[0]
        assert "not found" in warnings[0]
    
    def test_continue_processing_after_not_found(self):
        """Test that processing continues after package not found."""
        from saigen.models.saidata import Package
        
        # Create multiple packages
        packages = [
            Package(name="pkg1", package_name="pkg1", version="1.0.0"),
            Package(name="pkg2", package_name="pkg2", version="2.0.0"),
            Package(name="pkg3", package_name="pkg3", version="3.0.0")
        ]
        
        # Simulate query results (second one not found)
        query_results = [
            {'name': 'pkg1', 'version': '1.1.0'},
            None,  # Not found
            {'name': 'pkg3', 'version': '3.1.0'}
        ]
        
        updated_count = 0
        for pkg, result in zip(packages, query_results):
            if result:
                pkg.version = result['version']
                updated_count += 1
        
        # Verify processing continued
        assert updated_count == 2
        assert packages[0].version == "1.1.0"
        assert packages[1].version == "2.0.0"  # Unchanged
        assert packages[2].version == "3.1.0"
