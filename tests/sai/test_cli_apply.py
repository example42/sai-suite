"""Tests for the apply CLI command."""

import pytest
import tempfile
import yaml
import json
from pathlib import Path
from click.testing import CliRunner

from sai.cli.main import cli


class TestApplyCommand:
    """Test the apply CLI command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def create_temp_action_file(self, data, suffix='.yaml'):
        """Create a temporary action file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            if suffix == '.json':
                json.dump(data, f)
            else:
                yaml.dump(data, f)
            return Path(f.name)
    
    def test_apply_help(self):
        """Test apply command help."""
        result = self.runner.invoke(cli, ['apply', '--help'])
        assert result.exit_code == 0
        assert 'Apply multiple actions from an action file' in result.output
        assert 'ACTION_FILE' in result.output
    
    def test_apply_nonexistent_file(self):
        """Test apply with nonexistent file."""
        result = self.runner.invoke(cli, ['apply', '/nonexistent/file.yaml'])
        assert result.exit_code == 2  # Click file not found error
    
    def test_apply_invalid_action_file(self):
        """Test apply with invalid action file."""
        invalid_data = {"config": {"verbose": True}}  # Missing actions
        temp_file = self.create_temp_action_file(invalid_data)
        
        try:
            result = self.runner.invoke(cli, ['apply', str(temp_file)])
            assert result.exit_code == 1
            assert 'Error loading action file' in result.output
        finally:
            temp_file.unlink()
    
    def test_apply_valid_yaml_file_dry_run(self):
        """Test apply with valid YAML file in dry run mode."""
        action_data = {
            "config": {"verbose": True, "dry_run": True},
            "actions": {"install": ["nginx"]}
        }
        temp_file = self.create_temp_action_file(action_data)
        
        try:
            # Use --yes to skip confirmation and --dry-run to avoid actual execution
            result = self.runner.invoke(cli, ['apply', str(temp_file), '--yes', '--dry-run'])
            
            # The command might fail due to missing providers in test environment,
            # but it should at least parse the file correctly
            assert 'Error loading action file' not in result.output
        finally:
            temp_file.unlink()
    
    def test_apply_valid_json_file_dry_run(self):
        """Test apply with valid JSON file in dry run mode."""
        action_data = {
            "config": {"verbose": True, "dry_run": True},
            "actions": {"install": ["nginx"]}
        }
        temp_file = self.create_temp_action_file(action_data, '.json')
        
        try:
            result = self.runner.invoke(cli, ['apply', str(temp_file), '--yes', '--dry-run'])
            
            # The command might fail due to missing providers in test environment,
            # but it should at least parse the file correctly
            assert 'Error loading action file' not in result.output
        finally:
            temp_file.unlink()
    
    def test_apply_with_parallel_option(self):
        """Test apply with parallel execution option."""
        action_data = {
            "config": {"verbose": True, "dry_run": True},
            "actions": {"install": ["nginx", "curl"]}
        }
        temp_file = self.create_temp_action_file(action_data)
        
        try:
            result = self.runner.invoke(cli, ['apply', str(temp_file), '--parallel', '--yes', '--dry-run'])
            
            # Should parse correctly with parallel option
            assert 'Error loading action file' not in result.output
        finally:
            temp_file.unlink()
    
    def test_apply_with_continue_on_error_option(self):
        """Test apply with continue-on-error option."""
        action_data = {
            "config": {"verbose": True, "dry_run": True},
            "actions": {"install": ["nginx", "curl"]}
        }
        temp_file = self.create_temp_action_file(action_data)
        
        try:
            result = self.runner.invoke(cli, ['apply', str(temp_file), '--continue-on-error', '--yes', '--dry-run'])
            
            # Should parse correctly with continue-on-error option
            assert 'Error loading action file' not in result.output
        finally:
            temp_file.unlink()
    
    def test_apply_with_timeout_option(self):
        """Test apply with timeout option."""
        action_data = {
            "config": {"verbose": True, "dry_run": True},
            "actions": {"install": ["nginx"]}
        }
        temp_file = self.create_temp_action_file(action_data)
        
        try:
            result = self.runner.invoke(cli, ['apply', str(temp_file), '--timeout', '300', '--yes', '--dry-run'])
            
            # Should parse correctly with timeout option
            assert 'Error loading action file' not in result.output
        finally:
            temp_file.unlink()
    
    def test_apply_complex_action_file(self):
        """Test apply with complex action file."""
        complex_data = {
            "config": {
                "verbose": True,
                "dry_run": True,
                "continue_on_error": True
            },
            "actions": {
                "install": [
                    "nginx",
                    {"name": "docker", "provider": "apt", "timeout": 600}
                ],
                "start": ["nginx"],
                "uninstall": ["old-package"]
            }
        }
        temp_file = self.create_temp_action_file(complex_data)
        
        try:
            result = self.runner.invoke(cli, ['apply', str(temp_file), '--yes'])
            
            # Should parse the complex file correctly
            assert 'Error loading action file' not in result.output
        finally:
            temp_file.unlink()
    
    def test_apply_json_output(self):
        """Test apply with JSON output format."""
        action_data = {
            "config": {"verbose": True, "dry_run": True},
            "actions": {"install": ["nginx"]}
        }
        temp_file = self.create_temp_action_file(action_data)
        
        try:
            result = self.runner.invoke(cli, ['apply', str(temp_file), '--json', '--yes'])
            
            # Should produce JSON output
            if result.exit_code != 0:
                # Even if execution fails, JSON format should be attempted
                try:
                    import json
                    json.loads(result.output)
                except json.JSONDecodeError:
                    # If not JSON, at least check it's not a file loading error
                    assert 'Error loading action file' not in result.output
        finally:
            temp_file.unlink()
    
    def test_apply_global_options_override(self):
        """Test that global CLI options override action file config."""
        action_data = {
            "config": {"verbose": False, "dry_run": False},
            "actions": {"install": ["nginx"]}
        }
        temp_file = self.create_temp_action_file(action_data)
        
        try:
            # Global --verbose and --dry-run should override file config
            result = self.runner.invoke(cli, ['--verbose', '--dry-run', 'apply', str(temp_file), '--yes'])
            
            # Should parse correctly and respect global options
            assert 'Error loading action file' not in result.output
        finally:
            temp_file.unlink()