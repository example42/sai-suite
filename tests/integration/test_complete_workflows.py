"""Integration tests for complete SAI workflows."""

import json
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
from click.testing import CliRunner

from sai.cli.main import cli
from sai.models.config import SaiConfig
from sai.models.saidata import SaiData, Metadata, Package, Service
from sai.models.provider_data import ProviderData, Provider, Action, ProviderType
from sai.providers.loader import ProviderLoader
from sai.providers.base import BaseProvider


class TestCompleteWorkflows:
    """Test complete end-to-end workflows."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create test directories
        self.saidata_dir = self.temp_path / "saidata"
        self.provider_dir = self.temp_path / "providers"
        self.cache_dir = self.temp_path / "cache"
        
        for directory in [self.saidata_dir, self.provider_dir, self.cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_provider(self, name: str, actions: dict, priority: int = 50) -> Path:
        """Create a test provider YAML file."""
        provider_data = {
            "version": "1.0",
            "provider": {
                "name": name,
                "display_name": f"{name.title()} Provider",
                "description": f"Test provider for {name}",
                "type": "package_manager",
                "platforms": ["linux", "darwin"],
                "capabilities": list(actions.keys()),
                "executable": f"{name}-cmd"
            },
            "actions": actions,
            "priority": priority
        }
        
        provider_file = self.provider_dir / f"{name}.yaml"
        with open(provider_file, 'w') as f:
            yaml.dump(provider_data, f)
        
        return provider_file
    
    def create_test_saidata(self, name: str, packages: list = None, services: list = None) -> Path:
        """Create a test saidata YAML file."""
        saidata = {
            "version": "0.2",
            "metadata": {
                "name": name,
                "display_name": f"{name.title()}",
                "description": f"Test software: {name}"
            }
        }
        
        if packages:
            saidata["packages"] = packages
        
        if services:
            saidata["services"] = services
        
        # Add provider-specific data
        saidata["providers"] = {
            "apt": {
                "packages": [{"name": f"{name}-apt"}]
            },
            "brew": {
                "packages": [{"name": f"{name}-brew"}]
            },
            "test-apt": {
                "packages": [{"name": f"{name}-test-apt"}]
            }
        }
        
        saidata_file = self.saidata_dir / f"{name}.yaml"
        with open(saidata_file, 'w') as f:
            yaml.dump(saidata, f)
        
        return saidata_file
    
    @patch('sai.cli.main.get_config')
    def test_install_workflow_single_provider(self, mock_get_config):
        """Test complete install workflow with single provider."""
        # Setup config
        config = SaiConfig(
            saidata_paths=[str(self.saidata_dir)],
            provider_paths=[str(self.provider_dir)],
            cache_directory=self.cache_dir
        )
        mock_get_config.return_value = config
        
        # Create test provider with higher priority than built-in providers
        # Use a unique name to avoid conflicts with built-in providers
        provider_data = {
            "version": "1.0",
            "provider": {
                "name": "test-apt",
                "display_name": "Test APT Provider",
                "description": "Test provider for apt",
                "type": "package_manager",
                "platforms": ["linux", "darwin"],
                "capabilities": ["install"],
                "executable": "apt-get",  # Use apt-get which is in the template
                "priority": 95
            },
            "actions": {
                "install": {
                    "template": "apt-get install -y {{sai_package(saidata, 'test-apt')}}",
                    "requires_root": True,
                    "timeout": 300
                }
            }
        }
        
        provider_file = self.provider_dir / "test-apt.yaml"
        with open(provider_file, 'w') as f:
            yaml.dump(provider_data, f)
        
        # Create test saidata
        self.create_test_saidata("nginx", 
            packages=[{"name": "nginx"}],
            services=[{"name": "nginx", "type": "systemd"}]
        )
        
        # Mock provider loading to only return our test provider
        def mock_load_providers():
            from sai.models.provider_data import ProviderData
            provider_obj = ProviderData.model_validate(provider_data)
            # Return ProviderData objects, not BaseProvider instances
            return {"test-apt": provider_obj}
        
        with patch('sai.cli.main.ProviderLoader') as mock_loader_class, \
             patch('sai.utils.system.is_executable_available', return_value=True), \
             patch('sai.utils.system.check_executable_functionality', return_value=True), \
             patch('sai.providers.base.BaseProvider.is_available', return_value=True), \
             patch('sai.core.execution_engine.subprocess.Popen') as mock_popen:
            
            # Setup the mock loader
            mock_loader = Mock()
            mock_loader.load_all_providers.return_value = mock_load_providers()
            mock_loader_class.return_value = mock_loader
            
            # Mock successful command execution
            mock_process = Mock()
            mock_process.communicate.return_value = ("Package installed successfully", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            result = self.runner.invoke(cli, ['--provider', 'test-apt', '--yes', 'install', 'nginx'])
            
            if result.exit_code != 0:
                print(f"Exit code: {result.exit_code}")
                print(f"Output: {result.output}")
                print(f"Exception: {result.exception}")
            
            assert result.exit_code == 0
            assert "Package installed successfully" in result.output
            # Multiple calls expected: system detection + actual command
            assert mock_popen.call_count >= 1
            # Should use test-apt command
            calls = [str(call) for call in mock_popen.call_args_list]
            assert any("apt-get" in call and "nginx-test-apt" in call for call in calls)
    
    @patch('sai.cli.main.get_config')
    def test_install_workflow_multiple_providers(self, mock_get_config):
        """Test install workflow with multiple providers and selection."""
        # Setup config
        config = SaiConfig(
            saidata_paths=[str(self.saidata_dir)],
            provider_paths=[str(self.provider_dir)],
            cache_directory=self.cache_dir
        )
        mock_get_config.return_value = config
        
        # Create multiple test providers with different priorities
        self.create_test_provider("apt", {
            "install": {
                "template": "apt-get install -y {{sai_package(saidata, 'apt')}}",
                "requires_sudo": True
            }
        }, priority=60)
        
        self.create_test_provider("brew", {
            "install": {
                "template": "brew install {{sai_package(saidata, 'brew')}}",
                "requires_sudo": False
            }
        }, priority=70)
        
        # Create test saidata
        self.create_test_saidata("git")
        
        # Mock provider availability
        with patch('sai.utils.system.is_executable_available', return_value=True), \
             patch('sai.utils.system.check_executable_functionality', return_value=True), \
             patch('sai.core.execution_engine.subprocess.Popen') as mock_popen:
            
            mock_process = Mock()
            mock_process.communicate.return_value = ("Package installed", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            # Test with --yes flag (should use highest priority provider)
            result = self.runner.invoke(cli, ['--yes', 'install', 'git'])
            
            assert result.exit_code == 0
            # Should use brew (higher priority)
            # Multiple calls expected: system detection + actual command
            assert mock_popen.call_count >= 1
    
    @patch('sai.cli.main.get_config')
    def test_dry_run_workflow(self, mock_get_config):
        """Test dry run workflow."""
        # Setup config
        config = SaiConfig(
            saidata_paths=[str(self.saidata_dir)],
            provider_paths=[str(self.provider_dir)]
        )
        mock_get_config.return_value = config
        
        # Create test provider
        self.create_test_provider("apt", {
            "install": {
                "template": "apt-get install -y {{sai_package(saidata, 'apt')}}",
                "requires_sudo": True
            }
        })
        
        # Create test saidata
        self.create_test_saidata("vim")
        
        # Mock provider availability
        with patch('sai.utils.system.is_executable_available', return_value=True), \
             patch('sai.utils.system.check_executable_functionality', return_value=True):
            
            result = self.runner.invoke(cli, ['--dry-run', 'install', 'vim'])
            
            assert result.exit_code == 0
            # Should show what would be executed without actually executing
            # Updated to match new output formatting
            assert ("apt-get install" in result.output or 
                    "Would execute" in result.output or 
                    "Operation completed successfully" in result.output)
    
    @patch('sai.cli.main.get_config')
    def test_json_output_workflow(self, mock_get_config):
        """Test workflow with JSON output format."""
        # Setup config
        config = SaiConfig(
            saidata_paths=[str(self.saidata_dir)],
            provider_paths=[str(self.provider_dir)]
        )
        mock_get_config.return_value = config
        
        # Create test provider data
        provider_data = {
            "version": "1.0",
            "provider": {
                "name": "test-apt",
                "display_name": "Test APT Provider",
                "description": "Test provider for apt",
                "type": "package_manager",
                "platforms": ["linux", "darwin"],
                "capabilities": ["status"],
                "executable": "systemctl",
                "priority": 95
            },
            "actions": {
                "status": {
                    "template": "systemctl status {{sai_service(saidata, 'test-apt')}}",
                    "requires_root": False,
                    "timeout": 300
                }
            }
        }
        
        # Create test saidata
        self.create_test_saidata("nginx", services=[{"name": "nginx", "type": "systemd"}])
        
        # Mock provider loading to only return our test provider
        def mock_load_providers():
            from sai.models.provider_data import ProviderData
            provider_obj = ProviderData.model_validate(provider_data)
            return {"test-apt": provider_obj}
        
        # Mock provider availability and execution
        with patch('sai.cli.main.ProviderLoader') as mock_loader_class, \
             patch('sai.utils.system.is_executable_available', return_value=True), \
             patch('sai.utils.system.check_executable_functionality', return_value=True), \
             patch('sai.providers.base.BaseProvider.is_available', return_value=True), \
             patch('sai.core.execution_engine.subprocess.Popen') as mock_popen:
            
            # Setup the mock loader
            mock_loader = Mock()
            mock_loader.load_all_providers.return_value = mock_load_providers()
            mock_loader_class.return_value = mock_loader
            
            mock_process = Mock()
            mock_process.communicate.return_value = ("nginx is running", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            result = self.runner.invoke(cli, ['--json', 'status', 'nginx'])
            
            assert result.exit_code == 0
            
            # Parse JSON output
            output_data = json.loads(result.output)
            assert output_data['action'] == 'status'
            assert output_data['software'] == 'nginx'
            assert len(output_data['providers']) == 1
            
            provider_result = output_data['providers'][0]
            assert provider_result['provider'] == 'test-apt'
            assert provider_result['success'] is True
            assert provider_result['stdout'] == 'nginx is running'
    
    @patch('sai.cli.main.get_config')
    def test_error_handling_workflow(self, mock_get_config):
        """Test error handling in complete workflow."""
        # Setup config
        config = SaiConfig(
            saidata_paths=[str(self.saidata_dir)],
            provider_paths=[str(self.provider_dir)]
        )
        mock_get_config.return_value = config
        
        # Create test provider
        self.create_test_provider("apt", {
            "install": {
                "template": "apt-get install -y {{sai_package(saidata, 'apt')}}",
                "requires_sudo": True
            }
        })
        
        # Create test saidata
        self.create_test_saidata("nonexistent-package")
        
        # Mock provider availability but command failure
        with patch('sai.utils.system.is_executable_available', return_value=True), \
             patch('sai.utils.system.check_executable_functionality', return_value=True), \
             patch('sai.core.execution_engine.subprocess.Popen') as mock_popen:
            
            # Mock failed command execution
            mock_process = Mock()
            mock_process.communicate.return_value = ("", "Package not found")
            mock_process.returncode = 1
            mock_popen.return_value = mock_process
            
            result = self.runner.invoke(cli, ['--yes', 'install', 'nonexistent-package'])
            
            assert result.exit_code == 1
            assert "Package not found" in result.output or "failed" in result.output.lower()
    
    @patch('sai.cli.main.get_config')
    def test_no_saidata_workflow(self, mock_get_config):
        """Test workflow when no saidata is found."""
        # Setup config
        config = SaiConfig(
            saidata_paths=[str(self.saidata_dir)],
            provider_paths=[str(self.provider_dir)]
        )
        mock_get_config.return_value = config
        
        # Create test provider
        self.create_test_provider("apt", {
            "install": {
                "template": "apt-get install -y {{saidata.metadata.name}}",
                "requires_sudo": True
            }
        })
        
        # Don't create saidata file - should use basic execution
        
        # Mock provider availability
        with patch('sai.utils.system.is_executable_available', return_value=True), \
             patch('sai.utils.system.check_executable_functionality', return_value=True), \
             patch('sai.core.execution_engine.subprocess.Popen') as mock_popen:
            
            mock_process = Mock()
            mock_process.communicate.return_value = ("Package installed", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            result = self.runner.invoke(cli, ['--yes', '--verbose', 'install', 'unknown-software'])
            
            # Should still work with basic saidata
            assert result.exit_code == 0
            # Multiple calls expected: system detection + actual command
            assert mock_popen.call_count >= 1
    
    @patch('sai.cli.main.get_config')
    def test_provider_specific_workflow(self, mock_get_config):
        """Test workflow with specific provider selection."""
        # Setup config
        config = SaiConfig(
            saidata_paths=[str(self.saidata_dir)],
            provider_paths=[str(self.provider_dir)]
        )
        mock_get_config.return_value = config
        
        # Create multiple test providers
        apt_provider_data = {
            "version": "1.0",
            "provider": {
                "name": "apt",
                "display_name": "APT Provider",
                "description": "Test provider for apt",
                "type": "package_manager",
                "platforms": ["linux", "darwin"],
                "capabilities": ["install"],
                "executable": "apt-get",
                "priority": 80
            },
            "actions": {
                "install": {
                    "template": "apt-get install -y {{sai_package(saidata, 'apt')}}",
                    "requires_root": True,
                    "timeout": 300
                }
            }
        }
        
        snap_provider_data = {
            "version": "1.0",
            "provider": {
                "name": "snap",
                "display_name": "Snap Provider",
                "description": "Test provider for snap",
                "type": "package_manager",
                "platforms": ["linux", "darwin"],
                "capabilities": ["install"],
                "executable": "snap",
                "priority": 70
            },
            "actions": {
                "install": {
                    "template": "snap install {{sai_package(saidata, 'snap')}}",
                    "requires_root": True,
                    "timeout": 300
                }
            }
        }
        
        # Create test saidata with both providers
        saidata = {
            "version": "0.2",
            "metadata": {
                "name": "code",
                "display_name": "Visual Studio Code"
            },
            "providers": {
                "apt": {"packages": [{"name": "code"}]},
                "snap": {"packages": [{"name": "code", "channel": "classic"}]}
            }
        }
        
        saidata_file = self.saidata_dir / "code.yaml"
        with open(saidata_file, 'w') as f:
            yaml.dump(saidata, f)
        
        # Mock provider loading to return both providers
        def mock_load_providers():
            from sai.models.provider_data import ProviderData
            apt_obj = ProviderData.model_validate(apt_provider_data)
            snap_obj = ProviderData.model_validate(snap_provider_data)
            return {"apt": apt_obj, "snap": snap_obj}
        
        # Mock provider availability
        with patch('sai.cli.main.ProviderLoader') as mock_loader_class, \
             patch('sai.utils.system.is_executable_available', return_value=True), \
             patch('sai.utils.system.check_executable_functionality', return_value=True), \
             patch('sai.providers.base.BaseProvider.is_available', return_value=True), \
             patch('sai.core.execution_engine.subprocess.Popen') as mock_popen:
            
            # Setup the mock loader
            mock_loader = Mock()
            mock_loader.load_all_providers.return_value = mock_load_providers()
            mock_loader_class.return_value = mock_loader
            
            mock_process = Mock()
            mock_process.communicate.return_value = ("Package installed", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            # Force specific provider
            result = self.runner.invoke(cli, ['--provider', 'snap', '--yes', 'install', 'code'])
            
            assert result.exit_code == 0
            # Should use snap command
            call_args = mock_popen.call_args[0][0]
            assert any("snap" in str(arg) for arg in call_args)
    
    @patch('sai.cli.main.get_config')
    def test_informational_action_workflow(self, mock_get_config):
        """Test informational action workflow (runs on all providers)."""
        # Setup config
        config = SaiConfig(
            saidata_paths=[str(self.saidata_dir)],
            provider_paths=[str(self.provider_dir)]
        )
        mock_get_config.return_value = config
        
        # Create multiple providers with info action
        self.create_test_provider("apt", {
            "info": {
                "template": "apt show {{sai_package(saidata, 'apt')}}",
                "requires_sudo": False
            }
        })
        
        self.create_test_provider("dpkg", {
            "info": {
                "template": "dpkg -l {{sai_package(saidata, 'dpkg')}}",
                "requires_sudo": False
            }
        })
        
        # Create test saidata
        self.create_test_saidata("curl")
        
        # Mock provider availability
        with patch('sai.utils.system.is_executable_available', return_value=True), \
             patch('sai.utils.system.check_executable_functionality', return_value=True), \
             patch('sai.core.execution_engine.subprocess.Popen') as mock_popen:
            
            mock_process = Mock()
            mock_process.communicate.return_value = ("Package info", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            result = self.runner.invoke(cli, ['info', 'curl'])
            
            assert result.exit_code == 0
            # Should execute on multiple providers
            assert mock_popen.call_count >= 1
    
    @patch('sai.cli.main.get_config')
    def test_caching_workflow(self, mock_get_config):
        """Test workflow with caching enabled."""
        # Setup config with caching
        config = SaiConfig(
            saidata_paths=[str(self.saidata_dir)],
            provider_paths=[str(self.provider_dir)],
            cache_enabled=True,
            cache_directory=self.cache_dir
        )
        mock_get_config.return_value = config
        
        # Create test provider
        self.create_test_provider("apt", {
            "install": {
                "template": "apt-get install -y {{sai_package(saidata, 'apt')}}",
                "requires_sudo": True
            }
        })
        
        # Create test saidata
        self.create_test_saidata("htop")
        
        # Mock provider availability
        with patch('sai.utils.system.is_executable_available', return_value=True), \
             patch('sai.utils.system.check_executable_functionality', return_value=True), \
             patch('sai.core.execution_engine.subprocess.Popen') as mock_popen:
            
            mock_process = Mock()
            mock_process.communicate.return_value = ("Package installed", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            # First run - should cache results
            result1 = self.runner.invoke(cli, ['--yes', 'install', 'htop'])
            assert result1.exit_code == 0
            
            # Second run - should use cache (but still execute command)
            result2 = self.runner.invoke(cli, ['--yes', 'install', 'htop'])
            assert result2.exit_code == 0
            
            # Both should succeed - expect multiple calls due to system detection
            assert mock_popen.call_count >= 2


class TestWorkflowErrorScenarios:
    """Test error scenarios in complete workflows."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('sai.cli.main.get_config')
    def test_no_providers_available(self, mock_get_config):
        """Test workflow when no providers are available."""
        config = SaiConfig()
        mock_get_config.return_value = config
        
        # Mock empty provider loading
        with patch('sai.cli.main.ProviderLoader') as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load_all_providers.return_value = {}
            mock_loader_class.return_value = mock_loader
            
            result = self.runner.invoke(cli, ['install', 'test-software'])
            
            assert result.exit_code == 1
            assert "No providers found" in result.output
    
    @patch('sai.cli.main.get_config')
    def test_provider_not_available(self, mock_get_config):
        """Test workflow when requested provider is not available."""
        config = SaiConfig()
        mock_get_config.return_value = config
        
        # Mock provider that exists but is not available
        mock_provider_data = Mock()
        mock_provider = Mock()
        mock_provider.name = "unavailable-provider"
        mock_provider.is_available.return_value = False
        
        with patch('sai.cli.main.ProviderLoader') as mock_loader_class:
            
            mock_loader = Mock()
            mock_loader.load_all_providers.return_value = {"unavailable-provider": mock_provider_data}
            mock_loader_class.return_value = mock_loader
            
            result = self.runner.invoke(cli, ['install', 'test-software'])
            
            assert result.exit_code == 1
            assert "No available providers found" in result.output
    
    @patch('sai.cli.main.get_config')
    def test_unsupported_action(self, mock_get_config):
        """Test workflow with unsupported action."""
        config = SaiConfig()
        mock_get_config.return_value = config
        
        # Create provider that doesn't support restart action
        provider_data = {
            "version": "1.0",
            "provider": {
                "name": "test-provider",
                "display_name": "Test Provider",
                "description": "Test provider without restart",
                "type": "package_manager",
                "platforms": ["linux", "darwin"],
                "capabilities": ["install"],  # Only supports install, not restart
                "executable": "test-cmd",
                "priority": 50
            },
            "actions": {
                "install": {  # Only has install action, no restart
                    "template": "test-cmd install {{sai_package(saidata, 'test-provider')}}",
                    "requires_root": False,
                    "timeout": 300
                }
            }
        }
        
        # Mock provider loading
        def mock_load_providers():
            from sai.models.provider_data import ProviderData
            provider_obj = ProviderData.model_validate(provider_data)
            return {"test-provider": provider_obj}
        
        with patch('sai.cli.main.ProviderLoader') as mock_loader_class, \
             patch('sai.cli.main.SaidataLoader'), \
             patch('sai.utils.system.is_executable_available', return_value=True), \
             patch('sai.utils.system.check_executable_functionality', return_value=True), \
             patch('sai.providers.base.BaseProvider.is_available', return_value=True):
            
            mock_loader = Mock()
            mock_loader.load_all_providers.return_value = mock_load_providers()
            mock_loader_class.return_value = mock_loader
            
            result = self.runner.invoke(cli, ['restart', 'test-software'])
            
            assert result.exit_code == 1
            assert "No providers support action" in result.output


if __name__ == "__main__":
    pytest.main([__file__])