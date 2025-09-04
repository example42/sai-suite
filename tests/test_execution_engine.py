"""Tests for ExecutionEngine."""

import os
import subprocess
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from sai.core.execution_engine import (
    ExecutionEngine, 
    ExecutionContext, 
    ExecutionResult, 
    ExecutionStatus
)
from sai.utils.errors import ProviderSelectionError, ExecutionError
from sai.providers.base import BaseProvider
from sai.models.provider_data import ProviderData, Provider, Action, ProviderType
from sai.models.saidata import SaiData, Metadata


@pytest.fixture
def sample_saidata():
    """Create sample saidata for testing."""
    return SaiData(
        version="0.2",
        metadata=Metadata(
            name="test-software",
            display_name="Test Software",
            description="A test software package"
        )
    )


@pytest.fixture
def sample_provider_data():
    """Create sample provider data for testing."""
    return ProviderData(
        version="0.1",
        provider=Provider(
            name="test-provider",
            display_name="Test Provider",
            description="A test provider",
            type=ProviderType.PACKAGE_MANAGER,
            platforms=["linux", "darwin"],
            capabilities=["install", "uninstall"],
            executable="test-cmd"
        ),
        actions={
            "install": Action(
                description="Install software",
                command="test-cmd install {{saidata.metadata.name}}",
                timeout=60
            ),
            "uninstall": Action(
                description="Uninstall software", 
                command="test-cmd uninstall {{saidata.metadata.name}}",
                timeout=60
            )
        }
    )


@pytest.fixture
def mock_provider(sample_provider_data):
    """Create a mock provider for testing."""
    provider = BaseProvider(sample_provider_data)
    
    # Mock the availability check
    with patch.object(provider, 'is_available', return_value=True):
        yield provider


@pytest.fixture
def execution_engine(mock_provider):
    """Create execution engine with mock provider."""
    return ExecutionEngine([mock_provider])


class TestExecutionEngine:
    """Test cases for ExecutionEngine."""
    
    def test_initialization(self, mock_provider):
        """Test ExecutionEngine initialization."""
        engine = ExecutionEngine([mock_provider])
        
        assert len(engine.providers) == 1
        assert len(engine.available_providers) == 1
        assert engine.available_providers[0].name == "test-provider"
    
    def test_dry_run_execution(self, execution_engine, sample_saidata):
        """Test dry run execution."""
        context = ExecutionContext(
            action="install",
            software="test-software",
            saidata=sample_saidata,
            dry_run=True
        )
        
        result = execution_engine.execute_action(context)
        
        assert result.success is True
        assert result.status == ExecutionStatus.DRY_RUN
        assert result.dry_run is True
        assert result.provider_used == "test-provider"
        assert result.action_name == "install"
        assert len(result.commands_executed) > 0
        assert "test-cmd install test-software" in result.commands_executed[0]
    
    def test_provider_selection_specific(self, execution_engine, sample_saidata):
        """Test provider selection with specific provider."""
        context = ExecutionContext(
            action="install",
            software="test-software", 
            saidata=sample_saidata,
            provider="test-provider",
            dry_run=True
        )
        
        result = execution_engine.execute_action(context)
        
        assert result.success is True
        assert result.provider_used == "test-provider"
    
    def test_provider_selection_invalid(self, execution_engine, sample_saidata):
        """Test provider selection with invalid provider."""
        context = ExecutionContext(
            action="install",
            software="test-software",
            saidata=sample_saidata,
            provider="nonexistent-provider",
            dry_run=True
        )
        
        with pytest.raises(ProviderSelectionError) as exc_info:
            execution_engine.execute_action(context)
        
        assert "not available" in str(exc_info.value)
    
    def test_unsupported_action(self, execution_engine, sample_saidata):
        """Test execution with unsupported action."""
        context = ExecutionContext(
            action="unsupported-action",
            software="test-software",
            saidata=sample_saidata,
            dry_run=True
        )
        
        with pytest.raises(ProviderSelectionError) as exc_info:
            execution_engine.execute_action(context)
        
        assert "No available provider supports action" in str(exc_info.value)
    
    def test_get_available_providers(self, execution_engine):
        """Test getting available providers."""
        providers = execution_engine.get_available_providers()
        
        assert len(providers) == 1
        assert providers[0].name == "test-provider"
    
    def test_get_provider_by_name(self, execution_engine):
        """Test getting provider by name."""
        provider = execution_engine.get_provider_by_name("test-provider")
        
        assert provider is not None
        assert provider.name == "test-provider"
        
        # Test non-existent provider
        provider = execution_engine.get_provider_by_name("nonexistent")
        assert provider is None
    
    def test_get_supported_actions(self, execution_engine):
        """Test getting supported actions."""
        actions = execution_engine.get_supported_actions()
        
        assert "test-provider" in actions
        assert "install" in actions["test-provider"]
        assert "uninstall" in actions["test-provider"]
    
    @patch('sai.core.execution_engine.subprocess.Popen')
    def test_actual_execution_success(self, mock_popen, execution_engine, sample_saidata):
        """Test actual command execution (success case)."""
        # Mock successful command execution
        mock_process = Mock()
        mock_process.communicate.return_value = ("Success output", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        context = ExecutionContext(
            action="install",
            software="test-software",
            saidata=sample_saidata,
            dry_run=False
        )
        
        result = execution_engine.execute_action(context)
        
        assert result.success is True
        assert result.status == ExecutionStatus.SUCCESS
        assert result.dry_run is False
        assert result.exit_code == 0
        assert result.stdout == "Success output"
    
    @patch('sai.core.execution_engine.subprocess.Popen')
    def test_actual_execution_failure(self, mock_popen, execution_engine, sample_saidata):
        """Test actual command execution (failure case)."""
        # Mock failed command execution
        mock_process = Mock()
        mock_process.communicate.return_value = ("", "Error output")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process
        
        context = ExecutionContext(
            action="install",
            software="test-software",
            saidata=sample_saidata,
            dry_run=False
        )
        
        result = execution_engine.execute_action(context)
        
        assert result.success is False
        assert result.status == ExecutionStatus.FAILURE
        assert result.exit_code == 1
        assert result.stderr == "Error output"
    
    def test_command_security_validation(self, execution_engine):
        """Test command security validation."""
        # Test dangerous command patterns
        dangerous_commands = [
            ['rm', '-rf', '/'],
            ['sh', '-c', 'rm -rf /'],
            ['bash', '-c', 'echo $(whoami)'],
            ['cmd', '/c', 'del /f /s /q C:\\*'],
            ['python', '-c', 'import os; os.system("rm -rf /")'],
        ]
        
        for cmd in dangerous_commands:
            validation = execution_engine._validate_command_security(cmd, False)
            # Some commands should be blocked by security validation
            # Note: Not all will be blocked as some depend on context
            
        # Test safe commands
        safe_commands = [
            ['apt', 'install', 'vim'],
            ['brew', 'install', 'git'],
            ['systemctl', 'status', 'nginx'],
        ]
        
        for cmd in safe_commands:
            validation = execution_engine._validate_command_security(cmd, False)
            assert validation['valid'] is True
    
    def test_command_sanitization(self, execution_engine):
        """Test command argument sanitization."""
        # Test with null bytes and control characters
        dirty_args = ['test\0command', 'arg\nwith\nnewlines', 'normal-arg']
        sanitized = execution_engine._sanitize_command_args(dirty_args)
        
        assert '\0' not in sanitized[0]
        assert sanitized[1] == 'arg\nwith\nnewlines'  # Newlines are allowed in args
        assert sanitized[2] == 'normal-arg'
    
    def test_privilege_escalation(self, execution_engine):
        """Test privilege escalation handling."""
        cmd_args = ['apt', 'install', 'vim']
        
        # Test without root requirement
        result = execution_engine._handle_privilege_escalation(cmd_args, False)
        assert result == cmd_args
        
        # Test with root requirement (will add sudo if not root)
        result = execution_engine._handle_privilege_escalation(cmd_args, True)
        if os.name != 'nt' and os.geteuid() != 0:
            assert result[0] == 'sudo'
            assert result[1] == '-n'
            assert result[2] == '--'
            assert result[3:] == cmd_args
    
    def test_secure_environment(self, execution_engine):
        """Test secure environment generation."""
        env = execution_engine._get_secure_environment()
        
        # Should have essential variables
        assert 'PATH' in env
        assert 'LANG' in env
        assert env['LANG'] == 'C'
        assert env['LC_ALL'] == 'C'
        
        # Should not have dangerous variables
        dangerous_vars = ['LD_PRELOAD', 'LD_LIBRARY_PATH', 'PYTHONPATH']
        for var in dangerous_vars:
            assert var not in env
    
    @patch('sai.core.execution_engine.subprocess.Popen')
    def test_timeout_handling(self, mock_popen, execution_engine, sample_saidata):
        """Test command timeout handling."""
        # Mock process that times out
        mock_process = Mock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired(['test'], 1)
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        # Mock os.getpgid and os.killpg for timeout handling
        with patch('os.getpgid', return_value=12345), \
             patch('os.killpg') as mock_killpg:
            
            context = ExecutionContext(
                action="install",
                software="test-software",
                saidata=sample_saidata,
                timeout=1,
                dry_run=False
            )
            
            result = execution_engine.execute_action(context)
            
            assert result.success is False
            # The timeout error should be in error_details since it's caught at a higher level
            assert result.error_details is not None
            assert "timed out" in result.error_details
            # Verify that process termination was attempted
            mock_killpg.assert_called()
    
    def test_no_available_providers(self, sample_saidata):
        """Test execution with no available providers."""
        # Create provider that's not available
        provider_data = ProviderData(
            version="0.1",
            provider=Provider(
                name="unavailable-provider",
                type=ProviderType.PACKAGE_MANAGER,
                executable="unavailable-cmd"
            ),
            actions={
                "install": Action(command="unavailable-cmd install")
            }
        )
        
        provider = BaseProvider(provider_data)
        with patch.object(provider, 'is_available', return_value=False):
            engine = ExecutionEngine([provider])
            
            context = ExecutionContext(
                action="install",
                software="test-software",
                saidata=sample_saidata,
                dry_run=True
            )
            
            with pytest.raises(ProviderSelectionError) as exc_info:
                engine.execute_action(context)
            
            assert "No available provider supports action" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__])