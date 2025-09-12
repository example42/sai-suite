"""Test repository fixtures and setup utilities for integration tests."""

import tempfile
import shutil
import subprocess
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class TestRepositoryConfig:
    """Configuration for a test repository."""
    name: str
    url: str
    local_path: Optional[Path] = None
    requires_auth: bool = False
    auth_type: Optional[str] = None
    description: str = ""


class TestRepositoryManager:
    """Manages test repositories for integration testing."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize test repository manager."""
        self.base_dir = base_dir or Path(tempfile.mkdtemp())
        self.repositories: Dict[str, TestRepositoryConfig] = {}
        self.setup_test_repositories()
    
    def setup_test_repositories(self):
        """Set up predefined test repositories."""
        # Small public repository for basic testing
        self.repositories["small_public"] = TestRepositoryConfig(
            name="small_public",
            url="https://github.com/octocat/Hello-World.git",
            description="Small public repository for basic git operations"
        )
        
        # Non-existent repository for error testing
        self.repositories["nonexistent"] = TestRepositoryConfig(
            name="nonexistent",
            url="https://github.com/nonexistent-user/nonexistent-repo.git",
            description="Non-existent repository for error handling tests"
        )
        
        # Private repository for authentication testing
        self.repositories["private"] = TestRepositoryConfig(
            name="private",
            url="git@github.com:private-user/private-repo.git",
            requires_auth=True,
            auth_type="ssh",
            description="Private repository for authentication testing"
        )
    
    def create_local_test_repository(self, name: str, saidata_count: int = 10) -> TestRepositoryConfig:
        """Create a local test repository with saidata structure."""
        repo_path = self.base_dir / f"test_repo_{name}"
        repo_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize git repository
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], 
                      cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], 
                      cwd=repo_path, check=True, capture_output=True)
        
        # Create saidata structure
        self._create_saidata_structure(repo_path, saidata_count)
        
        # Add and commit files
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit with test saidata"], 
                      cwd=repo_path, check=True, capture_output=True)
        
        # Create test repository entry
        test_repo = TestRepositoryConfig(
            name=name,
            url=str(repo_path),
            local_path=repo_path,
            description=f"Local test repository with {saidata_count} saidata files"
        )
        
        self.repositories[name] = test_repo
        return test_repo
    
    def _create_saidata_structure(self, repo_path: Path, count: int):
        """Create hierarchical saidata structure in repository."""
        software_configs = [
            ("nginx", "ng", "Nginx Web Server"),
            ("apache", "ap", "Apache HTTP Server"),
            ("mysql", "my", "MySQL Database"),
            ("postgres", "po", "PostgreSQL Database"),
            ("redis", "re", "Redis Cache"),
            ("docker", "do", "Docker Container Platform"),
            ("kubernetes", "ku", "Kubernetes Orchestration"),
            ("jenkins", "je", "Jenkins CI/CD"),
            ("grafana", "gr", "Grafana Monitoring"),
            ("prometheus", "pr", "Prometheus Metrics")
        ]
        
        # Create repository metadata
        repo_metadata = {
            "version": "1.0",
            "description": "Test saidata repository",
            "software_count": min(count, len(software_configs)),
            "structure_version": "hierarchical",
            "created_by": "test_suite"
        }
        
        with open(repo_path / "repository.yaml", 'w') as f:
            yaml.dump(repo_metadata, f)
        
        # Create saidata files
        for i, (software_name, prefix, display_name) in enumerate(software_configs[:count]):
            software_dir = repo_path / "software" / prefix / software_name
            software_dir.mkdir(parents=True, exist_ok=True)
            
            saidata = {
                "version": "0.2",
                "metadata": {
                    "name": software_name,
                    "display_name": display_name,
                    "description": f"Test saidata for {display_name}",
                    "category": "test",
                    "tags": ["test", "integration"]
                },
                "packages": [{"name": software_name}],
                "services": [{"name": software_name, "type": "systemd"}] if i % 2 == 0 else [],
                "providers": {
                    "apt": {"packages": [{"name": f"{software_name}-apt"}]},
                    "brew": {"packages": [{"name": f"{software_name}-brew"}]},
                    "yum": {"packages": [{"name": f"{software_name}-yum"}]},
                    "dnf": {"packages": [{"name": f"{software_name}-dnf"}]}
                }
            }
            
            with open(software_dir / "default.yaml", 'w') as f:
                yaml.dump(saidata, f)
            
            # Create additional variant files for some software
            if i % 3 == 0:
                variant_saidata = saidata.copy()
                variant_saidata["metadata"]["variant"] = "enterprise"
                variant_saidata["metadata"]["display_name"] += " Enterprise"
                
                with open(software_dir / "enterprise.yaml", 'w') as f:
                    yaml.dump(variant_saidata, f)
    
    def create_large_test_repository(self, name: str, software_count: int = 1000) -> TestRepositoryConfig:
        """Create a large test repository for performance testing."""
        repo_path = self.base_dir / f"large_test_repo_{name}"
        repo_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize git repository
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], 
                      cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], 
                      cwd=repo_path, check=True, capture_output=True)
        
        # Create large saidata structure
        print(f"Creating large repository with {software_count} software packages...")
        
        for i in range(software_count):
            software_name = f"software_{i:04d}"
            prefix = software_name[:2]
            
            software_dir = repo_path / "software" / prefix / software_name
            software_dir.mkdir(parents=True, exist_ok=True)
            
            saidata = {
                "version": "0.2",
                "metadata": {
                    "name": software_name,
                    "display_name": f"Software Package {i}",
                    "description": f"Test software package number {i}",
                    "category": f"category_{i % 10}",
                    "tags": [f"tag_{i % 5}", "performance", "test"]
                },
                "packages": [{"name": software_name}],
                "providers": {
                    "apt": {"packages": [{"name": f"{software_name}-apt"}]},
                    "brew": {"packages": [{"name": f"{software_name}-brew"}]}
                }
            }
            
            with open(software_dir / "default.yaml", 'w') as f:
                yaml.dump(saidata, f)
            
            # Commit in batches to avoid huge commits
            if (i + 1) % 100 == 0:
                subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
                subprocess.run(["git", "commit", "-m", f"Add software packages {i-99:04d}-{i:04d}"], 
                              cwd=repo_path, check=True, capture_output=True)
                print(f"Committed packages {i-99:04d}-{i:04d}")
        
        # Final commit for remaining files
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Final commit"], 
                      cwd=repo_path, check=True, capture_output=True)
        
        test_repo = TestRepositoryConfig(
            name=name,
            url=str(repo_path),
            local_path=repo_path,
            description=f"Large test repository with {software_count} saidata files"
        )
        
        self.repositories[name] = test_repo
        return test_repo
    
    def create_malformed_repository(self, name: str) -> TestRepositoryConfig:
        """Create a repository with malformed saidata for error testing."""
        repo_path = self.base_dir / f"malformed_repo_{name}"
        repo_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize git repository
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], 
                      cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], 
                      cwd=repo_path, check=True, capture_output=True)
        
        # Create malformed saidata files
        malformed_configs = [
            # Missing required fields
            ("missing_metadata", {"version": "0.2", "packages": [{"name": "test"}]}),
            # Invalid version
            ("invalid_version", {"version": "999.0", "metadata": {"name": "test"}}),
            # Invalid YAML syntax
            ("invalid_yaml", "invalid: yaml: content: [unclosed"),
            # Empty file
            ("empty_file", ""),
            # Wrong structure
            ("wrong_structure", {"not_saidata": True})
        ]
        
        for config_name, content in malformed_configs:
            software_dir = repo_path / "software" / config_name[:2] / config_name
            software_dir.mkdir(parents=True, exist_ok=True)
            
            saidata_file = software_dir / "default.yaml"
            if isinstance(content, dict):
                with open(saidata_file, 'w') as f:
                    yaml.dump(content, f)
            else:
                saidata_file.write_text(content)
        
        # Add and commit
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add malformed saidata"], 
                      cwd=repo_path, check=True, capture_output=True)
        
        test_repo = TestRepositoryConfig(
            name=name,
            url=str(repo_path),
            local_path=repo_path,
            description="Repository with malformed saidata for error testing"
        )
        
        self.repositories[name] = test_repo
        return test_repo
    
    def get_repository(self, name: str) -> Optional[TestRepositoryConfig]:
        """Get a test repository by name."""
        return self.repositories.get(name)
    
    def list_repositories(self) -> List[TestRepositoryConfig]:
        """List all available test repositories."""
        return list(self.repositories.values())
    
    def cleanup(self):
        """Clean up all test repositories."""
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir, ignore_errors=True)


# Global test repository manager instance
_test_repo_manager = None


def get_test_repository_manager() -> TestRepositoryManager:
    """Get the global test repository manager instance."""
    global _test_repo_manager
    if _test_repo_manager is None:
        _test_repo_manager = TestRepositoryManager()
    return _test_repo_manager


def cleanup_test_repositories():
    """Clean up all test repositories."""
    global _test_repo_manager
    if _test_repo_manager is not None:
        _test_repo_manager.cleanup()
        _test_repo_manager = None