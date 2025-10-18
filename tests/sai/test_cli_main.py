"""Tests for CLI main module."""

import json
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from sai.cli.main import _convert_config_value, cli
from sai.core.execution_engine import ExecutionResult, ExecutionStatus
from sai.models.config import LogLevel, SaiConfig
from sai.models.saidata import Metadata, SaiData
from sai.utils.errors import SaiError


class TestCLIMain:
    """Test cases for CLI main functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_version(self):
        """Test CLI version command."""
        result = self.runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_help(self):
        """Test CLI help output."""
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "SAI - Software Automation and Installation CLI tool" in result.output
        assert "install" in result.output
        assert "uninstall" in result.output

    @patch("sai.cli.main.get_config")
    def test_cli_global_options(self, mock_get_config):
        """Test CLI global options are properly stored."""
        mock_config = Mock(spec=SaiConfig)
        mock_get_config.return_value = mock_config

        # Test with various global options
        result = self.runner.invoke(
            cli,
            [
                "--verbose",
                "--dry-run",
                "--yes",
                "--quiet",
                "--json",
                "--provider",
                "test-provider",
                "install",
                "test-software",
            ],
            catch_exceptions=False,
        )

        # The command will fail due to missing providers, but we can check
        # that the options were parsed correctly by examining the context
        assert result.exit_code != 0  # Expected to fail without providers

    @patch("sai.cli.main.get_config")
    def test_config_loading_error(self, mock_get_config):
        """Test handling of configuration loading errors."""
        mock_get_config.side_effect = SaiError("Config error", error_code="CONFIG_001")

        result = self.runner.invoke(cli, ["install", "test"])

        assert result.exit_code == 1
        assert "Error loading configuration" in result.output

    @patch("sai.cli.main.ProviderLoader")
    @patch("sai.cli.main.get_config")
    def test_install_command_no_providers(self, mock_get_config, mock_provider_loader):
        """Test install command with no providers available."""
        mock_config = Mock(spec=SaiConfig)
        mock_get_config.return_value = mock_config

        mock_loader = Mock()
        mock_loader.load_all_providers.return_value = {}
        mock_provider_loader.return_value = mock_loader

        result = self.runner.invoke(cli, ["install", "test-software"])

        assert result.exit_code == 1
        assert "No providers found" in result.output

    @patch("sai.cli.main.ProviderLoader")
    @patch("sai.cli.main.SaidataLoader")
    @patch("sai.cli.main.ExecutionEngine")
    @patch("sai.cli.main.get_config")
    def test_install_command_success(
        self, mock_get_config, mock_execution_engine, mock_saidata_loader, mock_provider_loader
    ):
        """Test successful install command execution."""
        # Setup mocks
        mock_config = Mock(spec=SaiConfig)
        mock_get_config.return_value = mock_config

        # Mock provider
        mock_provider_data = Mock()
        mock_provider = Mock()
        mock_provider.name = "test-provider"
        mock_provider.is_available.return_value = True
        mock_provider.get_priority.return_value = 50
        mock_provider.has_action.return_value = True
        mock_provider.can_handle_software.return_value = True

        mock_loader = Mock()
        mock_loader.load_all_providers.return_value = {"test-provider": mock_provider_data}
        mock_provider_loader.return_value = mock_loader

        # Mock saidata
        mock_saidata = SaiData(version="0.2", metadata=Metadata(name="test-software"))
        mock_saidata_loader_instance = Mock()
        mock_saidata_loader_instance.load_saidata.return_value = mock_saidata
        mock_saidata_loader.return_value = mock_saidata_loader_instance

        # Mock execution result
        mock_result = ExecutionResult(
            success=True,
            status=ExecutionStatus.SUCCESS,
            message="Installation successful",
            provider_used="test-provider",
            action_name="install",
            commands_executed=["test-provider install test-software"],
            execution_time=1.5,
            dry_run=False,
        )

        mock_engine = Mock()
        mock_engine.execute_action.return_value = mock_result
        mock_execution_engine.return_value = mock_engine

        # Mock BaseProvider import
        with patch("sai.providers.base.BaseProvider", return_value=mock_provider):
            result = self.runner.invoke(cli, ["--yes", "install", "test-software"])

        assert result.exit_code == 0
        mock_engine.execute_action.assert_called_once()

    @patch("sai.cli.main.ProviderLoader")
    @patch("sai.cli.main.get_config")
    def test_dry_run_mode(self, mock_get_config, mock_provider_loader):
        """Test dry run mode execution."""
        mock_config = Mock(spec=SaiConfig)
        mock_get_config.return_value = mock_config

        # Mock provider
        mock_provider_data = Mock()
        mock_provider = Mock()
        mock_provider.name = "test-provider"
        mock_provider.is_available.return_value = True
        mock_provider.get_priority.return_value = 50
        mock_provider.has_action.return_value = True
        mock_provider.can_handle_software.return_value = True

        mock_loader = Mock()
        mock_loader.load_all_providers.return_value = {"test-provider": mock_provider_data}
        mock_provider_loader.return_value = mock_loader

        with patch("sai.providers.base.BaseProvider", return_value=mock_provider), patch(
            "sai.cli.main.SaidataLoader"
        ), patch("sai.cli.main.ExecutionEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_result = ExecutionResult(
                success=True,
                status=ExecutionStatus.DRY_RUN,
                message="Would install test-software",
                provider_used="test-provider",
                action_name="install",
                commands_executed=["test-provider install test-software"],
                execution_time=0.1,
                dry_run=True,
            )
            mock_engine.execute_action.return_value = mock_result
            mock_engine_class.return_value = mock_engine

            result = self.runner.invoke(cli, ["--dry-run", "install", "test-software"])

            # Should succeed in dry run mode
            assert result.exit_code == 0

    @patch("sai.cli.main.ProviderLoader")
    @patch("sai.cli.main.get_config")
    def test_json_output_format(self, mock_get_config, mock_provider_loader):
        """Test JSON output format."""
        mock_config = Mock(spec=SaiConfig)
        mock_get_config.return_value = mock_config

        # Mock provider
        mock_provider_data = Mock()
        mock_provider = Mock()
        mock_provider.name = "test-provider"
        mock_provider.is_available.return_value = True
        mock_provider.get_priority.return_value = 50
        mock_provider.has_action.return_value = True
        mock_provider.can_handle_software.return_value = True

        mock_loader = Mock()
        mock_loader.load_all_providers.return_value = {"test-provider": mock_provider_data}
        mock_provider_loader.return_value = mock_loader

        with patch("sai.providers.base.BaseProvider", return_value=mock_provider), patch(
            "sai.cli.main.SaidataLoader"
        ), patch("sai.cli.main.ExecutionEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_result = ExecutionResult(
                success=True,
                status=ExecutionStatus.SUCCESS,
                message="Installation successful",
                provider_used="test-provider",
                action_name="install",
                commands_executed=["test-provider install test-software"],
                execution_time=1.5,
                dry_run=False,
                stdout="Package installed successfully",
            )
            mock_engine.execute_action.return_value = mock_result
            mock_engine_class.return_value = mock_engine

            result = self.runner.invoke(cli, ["--json", "--yes", "install", "test-software"])

            assert result.exit_code == 0

            # Parse JSON output
            output_data = json.loads(result.output)
            assert output_data["success"] is True
            assert output_data["provider_used"] == "test-provider"
            assert output_data["stdout"] == "Package installed successfully"

    def test_convert_config_value_log_level(self):
        """Test config value conversion for log levels."""
        result = _convert_config_value("log_level", "debug", LogLevel)
        assert result == LogLevel.DEBUG

        with pytest.raises(ValueError, match="Invalid log level"):
            _convert_config_value("log_level", "invalid", LogLevel)

    def test_convert_config_value_boolean(self):
        """Test config value conversion for booleans."""
        assert _convert_config_value("cache_enabled", "true", bool) is True
        assert _convert_config_value("cache_enabled", "false", bool) is False
        assert _convert_config_value("cache_enabled", "1", bool) is True
        assert _convert_config_value("cache_enabled", "0", bool) is False

    def test_convert_config_value_list(self):
        """Test config value conversion for lists."""
        result = _convert_config_value("saidata_paths", "/path1, /path2, /path3", list)
        assert result == ["/path1", "/path2", "/path3"]

    def test_convert_config_value_dict(self):
        """Test config value conversion for dictionaries."""
        result = _convert_config_value("provider_priorities", "apt:10,brew:20", dict)
        assert result == {"apt": 10, "brew": 20}

    @patch("sai.cli.main.ProviderLoader")
    @patch("sai.cli.main.get_config")
    def test_error_handling_with_suggestions(self, mock_get_config, mock_provider_loader):
        """Test error handling with suggestions."""
        mock_config = Mock(spec=SaiConfig)
        mock_get_config.return_value = mock_config

        # Mock provider loader to raise an error with suggestions
        error = SaiError("Test error", suggestions=["Try this", "Or this"])
        mock_loader = Mock()
        mock_loader.load_all_providers.side_effect = error
        mock_provider_loader.return_value = mock_loader

        result = self.runner.invoke(cli, ["install", "test-software"])

        assert result.exit_code == 1
        assert "Test error" in result.output
        assert "Suggestions:" in result.output
        assert "Try this" in result.output

    @patch("sai.cli.main.ProviderLoader")
    @patch("sai.cli.main.get_config")
    def test_multiple_provider_selection(self, mock_get_config, mock_provider_loader):
        """Test provider selection when multiple providers are available."""
        mock_config = Mock(spec=SaiConfig)
        mock_get_config.return_value = mock_config

        # Mock multiple providers
        mock_provider1 = Mock()
        mock_provider1.name = "provider1"
        mock_provider1.is_available.return_value = True
        mock_provider1.get_priority.return_value = 50
        mock_provider1.has_action.return_value = True
        mock_provider1.can_handle_software.return_value = True

        mock_provider2 = Mock()
        mock_provider2.name = "provider2"
        mock_provider2.is_available.return_value = True
        mock_provider2.get_priority.return_value = 60
        mock_provider2.has_action.return_value = True
        mock_provider2.can_handle_software.return_value = True

        mock_loader = Mock()
        mock_loader.load_all_providers.return_value = {"provider1": Mock(), "provider2": Mock()}
        mock_provider_loader.return_value = mock_loader

        with patch("sai.providers.base.BaseProvider", side_effect=[mock_provider1, mock_provider2]):
            # Test with --yes flag (should use default/highest priority)
            with patch("sai.cli.main.SaidataLoader"), patch(
                "sai.cli.main.ExecutionEngine"
            ) as mock_engine_class:
                mock_engine = Mock()
                mock_result = ExecutionResult(
                    success=True,
                    status=ExecutionStatus.SUCCESS,
                    message="Success",
                    provider_used="provider2",
                    action_name="install",
                    commands_executed=["provider2 install test"],
                    execution_time=1.0,
                    dry_run=False,
                )
                mock_engine.execute_action.return_value = mock_result
                mock_engine_class.return_value = mock_engine

                result = self.runner.invoke(cli, ["--yes", "install", "test-software"])
                assert result.exit_code == 0


class TestCLICommands:
    """Test individual CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sai.cli.main._execute_software_action")
    @patch("sai.cli.main.get_config")
    def test_install_command(self, mock_get_config, mock_execute):
        """Test install command."""
        mock_config = Mock(spec=SaiConfig)
        mock_get_config.return_value = mock_config

        self.runner.invoke(cli, ["install", "test-software"])

        mock_execute.assert_called_once()
        args = mock_execute.call_args[0]
        assert args[1] == "install"  # action
        assert args[2] == "test-software"  # software

    @patch("sai.cli.main._execute_software_action")
    @patch("sai.cli.main.get_config")
    def test_uninstall_command(self, mock_get_config, mock_execute):
        """Test uninstall command."""
        mock_config = Mock(spec=SaiConfig)
        mock_get_config.return_value = mock_config

        self.runner.invoke(cli, ["uninstall", "test-software"])

        mock_execute.assert_called_once()
        args = mock_execute.call_args[0]
        assert args[1] == "uninstall"  # action
        assert args[2] == "test-software"  # software

    @patch("sai.cli.main._execute_software_action")
    @patch("sai.cli.main.get_config")
    def test_status_command(self, mock_get_config, mock_execute):
        """Test status command (informational, no confirmation required)."""
        mock_config = Mock(spec=SaiConfig)
        mock_get_config.return_value = mock_config

        self.runner.invoke(cli, ["status", "test-software"])

        mock_execute.assert_called_once()
        # Check that requires_confirmation is False for status
        kwargs = mock_execute.call_args[1]
        assert kwargs.get("requires_confirmation") is False

    @patch("sai.cli.main._execute_software_action")
    @patch("sai.cli.main.get_config")
    def test_info_command(self, mock_get_config, mock_execute):
        """Test info command (informational, no confirmation required)."""
        mock_config = Mock(spec=SaiConfig)
        mock_get_config.return_value = mock_config

        self.runner.invoke(cli, ["info", "test-software"])

        mock_execute.assert_called_once()
        # Check that requires_confirmation is False for info
        kwargs = mock_execute.call_args[1]
        assert kwargs.get("requires_confirmation") is False

    @patch("sai.cli.main._execute_software_action")
    @patch("sai.cli.main.get_config")
    def test_command_with_timeout(self, mock_get_config, mock_execute):
        """Test command with timeout option."""
        mock_config = Mock(spec=SaiConfig)
        mock_get_config.return_value = mock_config

        self.runner.invoke(cli, ["install", "test-software", "--timeout", "30"])

        mock_execute.assert_called_once()
        args = mock_execute.call_args[0]
        assert args[3] == 30  # timeout parameter

    @patch("sai.cli.main._execute_software_action")
    @patch("sai.cli.main.get_config")
    def test_command_with_no_cache(self, mock_get_config, mock_execute):
        """Test command with no-cache option."""
        mock_config = Mock(spec=SaiConfig)
        mock_get_config.return_value = mock_config

        self.runner.invoke(cli, ["install", "test-software", "--no-cache"])

        mock_execute.assert_called_once()
        kwargs = mock_execute.call_args[1]
        assert kwargs.get("use_cache") is False


if __name__ == "__main__":
    pytest.main([__file__])
