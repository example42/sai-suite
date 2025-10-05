"""Integration tests for hierarchical saidata path resolution."""

import pytest
import tempfile
import yaml
from pathlib import Path

from sai.core.saidata_loader import SaidataLoader
from sai.core.saidata_path import SaidataPath, HierarchicalPathResolver
from sai.models.config import SaiConfig


class TestHierarchicalIntegration:
    """Integration tests for hierarchical saidata functionality."""
    
    def create_test_saidata_structure(self, base_path: Path):
        """Create a complete hierarchical saidata structure for testing."""
        test_software = {
            "apache": {
                "version": "0.2",
                "metadata": {
                    "name": "apache",
                    "description": "Apache HTTP Server",
                    "category": "web-server"
                },
                "packages": [{"name": "apache2"}]
            },
            "nginx": {
                "version": "0.2", 
                "metadata": {
                    "name": "nginx",
                    "description": "Nginx Web Server",
                    "category": "web-server"
                },
                "packages": [{"name": "nginx"}]
            },
            "mysql": {
                "version": "0.2",
                "metadata": {
                    "name": "mysql",
                    "description": "MySQL Database Server",
                    "category": "database"
                },
                "packages": [{"name": "mysql-server"}]
            },
            "redis": {
                "version": "0.2",
                "metadata": {
                    "name": "redis",
                    "description": "Redis In-Memory Database",
                    "category": "database"
                },
                "packages": [{"name": "redis-server"}]
            }
        }
        
        created_files = []
        for software_name, content in test_software.items():
            saidata_path = SaidataPath.from_software_name(software_name, base_path)
            saidata_path.get_directory().mkdir(parents=True, exist_ok=True)
            
            with open(saidata_path.hierarchical_path, 'w') as f:
                yaml.dump(content, f)
            
            created_files.append(saidata_path.hierarchical_path)
        
        return created_files
    
    def test_end_to_end_hierarchical_loading(self):
        """Test complete end-to-end hierarchical saidata loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            # Create hierarchical structure
            created_files = self.create_test_saidata_structure(base_path)
            assert len(created_files) == 4
            
            # Configure loader with hierarchical path
            config = SaiConfig(saidata_paths=[str(base_path)])
            loader = SaidataLoader(config)
            
            # Test loading each software
            test_cases = [
                ("apache", "Apache HTTP Server", "apache2"),
                ("nginx", "Nginx Web Server", "nginx"),
                ("mysql", "MySQL Database Server", "mysql-server"),
                ("redis", "Redis In-Memory Database", "redis-server")
            ]
            
            for software_name, expected_desc, expected_package in test_cases:
                saidata = loader.load_saidata(software_name)
                
                assert saidata is not None
                assert saidata.metadata.name == software_name
                assert saidata.metadata.description == expected_desc
                assert len(saidata.packages) == 1
                assert saidata.packages[0].name == expected_package
    
    def test_hierarchical_path_generation_consistency(self):
        """Test that hierarchical path generation is consistent."""
        base_path = Path("/test/base")
        
        test_cases = [
            ("apache", "software/ap/apache/default.yaml"),
            ("nginx", "software/ng/nginx/default.yaml"),
            ("mysql", "software/my/mysql/default.yaml"),
            ("redis", "software/re/redis/default.yaml"),
            ("postgresql", "software/po/postgresql/default.yaml"),
            ("docker", "software/do/docker/default.yaml"),
            ("kubernetes", "software/ku/kubernetes/default.yaml"),
            ("a", "software/a/a/default.yaml"),  # Single character
            ("ab", "software/ab/ab/default.yaml"),  # Two characters
        ]
        
        for software_name, expected_path in test_cases:
            saidata_path = SaidataPath.from_software_name(software_name, base_path)
            actual_path = str(saidata_path.hierarchical_path.relative_to(base_path))
            
            assert actual_path == expected_path, f"For '{software_name}': expected '{expected_path}', got '{actual_path}'"
    
    def test_hierarchical_resolver_with_multiple_paths(self):
        """Test hierarchical resolver with multiple search paths."""
        with tempfile.TemporaryDirectory() as temp_dir1, tempfile.TemporaryDirectory() as temp_dir2:
            base_path1 = Path(temp_dir1)
            base_path2 = Path(temp_dir2)
            
            # Create different software in each path
            # Path 1: apache, nginx
            for software_name in ["apache", "nginx"]:
                saidata_path = SaidataPath.from_software_name(software_name, base_path1)
                saidata_path.get_directory().mkdir(parents=True, exist_ok=True)
                saidata_path.hierarchical_path.write_text("version: '0.2'\nmetadata:\n  name: " + software_name)
            
            # Path 2: mysql, redis
            for software_name in ["mysql", "redis"]:
                saidata_path = SaidataPath.from_software_name(software_name, base_path2)
                saidata_path.get_directory().mkdir(parents=True, exist_ok=True)
                saidata_path.hierarchical_path.write_text("version: '0.2'\nmetadata:\n  name: " + software_name)
            
            # Test resolver finds software in both paths
            resolver = HierarchicalPathResolver([base_path1, base_path2])
            
            # Should find apache and nginx in path1
            apache_files = resolver.find_saidata_files("apache")
            assert len(apache_files) == 1
            assert base_path1 in apache_files[0].parents
            
            nginx_files = resolver.find_saidata_files("nginx")
            assert len(nginx_files) == 1
            assert base_path1 in nginx_files[0].parents
            
            # Should find mysql and redis in path2
            mysql_files = resolver.find_saidata_files("mysql")
            assert len(mysql_files) == 1
            assert base_path2 in mysql_files[0].parents
            
            redis_files = resolver.find_saidata_files("redis")
            assert len(redis_files) == 1
            assert base_path2 in redis_files[0].parents
    
    def test_hierarchical_structure_validation(self):
        """Test validation of hierarchical directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            # Create valid hierarchical structure
            self.create_test_saidata_structure(base_path)
            
            config = SaiConfig()
            loader = SaidataLoader(config)
            
            # Validate structure
            errors = loader.validate_hierarchical_structure(base_path)
            assert errors == [], f"Valid structure should have no errors: {errors}"
            
            # Find all software
            software_list = loader.find_all_hierarchical_software(base_path)
            expected_software = ["apache", "mysql", "nginx", "redis"]
            assert sorted(software_list) == sorted(expected_software)
    
    def test_hierarchical_alternative_file_formats(self):
        """Test hierarchical structure with alternative file formats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            # Create software with different file extensions
            test_data = {
                "version": "0.2",
                "metadata": {
                    "name": "test-software",
                    "description": "Test Software"
                }
            }
            
            # Create with .yml extension
            saidata_path = SaidataPath.from_software_name("test-yml", base_path)
            saidata_path.get_directory().mkdir(parents=True, exist_ok=True)
            yml_file = saidata_path.get_directory() / "default.yml"
            with open(yml_file, 'w') as f:
                yaml.dump(test_data, f)
            
            # Create with .json extension
            saidata_path = SaidataPath.from_software_name("test-json", base_path)
            saidata_path.get_directory().mkdir(parents=True, exist_ok=True)
            json_file = saidata_path.get_directory() / "default.json"
            import json
            with open(json_file, 'w') as f:
                json.dump(test_data, f)
            
            # Test loading both formats
            config = SaiConfig(saidata_paths=[str(base_path)])
            loader = SaidataLoader(config)
            
            yml_saidata = loader.load_saidata("test-yml")
            assert yml_saidata.metadata.name == "test-software"
            
            json_saidata = loader.load_saidata("test-json")
            assert json_saidata.metadata.name == "test-software"
    
    def test_hierarchical_error_reporting(self):
        """Test error reporting for missing hierarchical saidata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            # Create empty hierarchical structure
            software_dir = base_path / "software"
            software_dir.mkdir()
            
            config = SaiConfig(saidata_paths=[str(base_path)])
            loader = SaidataLoader(config)
            
            # Try to load non-existent software
            with pytest.raises(Exception) as exc_info:  # SaidataNotFoundError
                loader.load_saidata("nonexistent")
            
            error_msg = str(exc_info.value)
            assert "No saidata found for software 'nonexistent'" in error_msg
            assert "hierarchical structure" in error_msg
            assert "software/no/nonexistent/default.yaml" in error_msg
    
    def test_hierarchical_path_precedence(self):
        """Test that hierarchical paths respect search path precedence."""
        with tempfile.TemporaryDirectory() as temp_dir1, tempfile.TemporaryDirectory() as temp_dir2:
            base_path1 = Path(temp_dir1)  # Higher precedence
            base_path2 = Path(temp_dir2)  # Lower precedence
            
            # Create same software in both paths with different content
            software_name = "apache"
            
            # Higher precedence version
            content1 = {
                "version": "0.2",
                "metadata": {
                    "name": "apache",
                    "description": "Apache from path 1"
                },
                "packages": [{"name": "apache2-high"}]
            }
            
            # Lower precedence version
            content2 = {
                "version": "0.2",
                "metadata": {
                    "name": "apache", 
                    "description": "Apache from path 2"
                },
                "packages": [{"name": "apache2-low"}]
            }
            
            # Create files in both paths
            for base_path, content in [(base_path1, content1), (base_path2, content2)]:
                saidata_path = SaidataPath.from_software_name(software_name, base_path)
                saidata_path.get_directory().mkdir(parents=True, exist_ok=True)
                with open(saidata_path.hierarchical_path, 'w') as f:
                    yaml.dump(content, f)
            
            # Configure loader with both paths (path1 has higher precedence)
            config = SaiConfig(saidata_paths=[str(base_path1), str(base_path2)])
            loader = SaidataLoader(config)
            
            # Load saidata - should get merged result with path1 taking precedence
            saidata = loader.load_saidata(software_name)
            
            # Should have description from higher precedence path
            assert saidata.metadata.description == "Apache from path 1"
            
            # Should have packages from both paths (merged)
            package_names = [pkg.name for pkg in saidata.packages]
            assert "apache2-high" in package_names
            assert "apache2-low" in package_names