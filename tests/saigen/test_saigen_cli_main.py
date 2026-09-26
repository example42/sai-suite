"""Tests for saigen CLI main interface."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import yaml
from click.testing import CliRunner

from saigen.cli.main import cli, main
from saigen.models.generation import GenerationResult
from saigen.models.saidata import Metadata, SaiData


class TestSaigenCLIMain:
    """Test saigen CLI main interface."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def sample_config(self, temp_config_dir):
        """Create sample configuration file."""
        config_data = {
            "llm_providers": {
                "openai": {"provider": "openai", "api_key": "test-key", "model": "gpt-4o-mini"}
            },
            "generation": {"output_directory": str(temp_config_dir / "output")},
            "cache": {"directory": str(temp_config_dir / "cache")},
        }

        config_file = temp_config_dir / "saigen.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        return config_file

    def test_cli_version(self, runner):
        """Test CLI version command."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "saigen" in result.output

    def test_cli_help(self, runner):
        """Test CLI help command."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "generate" in result.output
        assert "validate" in result.output
        assert "test" in result.output
        assert "batch" in result.output

    def test_cli_global_options(self, runner, sample_config):
        """Test global CLI options."""
        with patch("saigen.core.generation_engine.GenerationEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine.generate_saidata = AsyncMock(
                return_value=GenerationResult(
                    success=True,
                    saidata=SaiData(version="0.2", metadata=Metadata(name="test")),
                    validation_errors=[],
                    warnings=[],
                    generation_time=1.0,
                    llm_provider_used="openai",
                    tokens_used=100,
                    cost_estimate=0.001,
                )
            )
            mock_engine.save_saidata = AsyncMock()
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                cli, ["--config", str(sample_config), "--verbose", "generate", "nginx"]
            )

            # Should not fail due to global options
            assert result.exit_code == 0

    def test_cli_invalid_config_file(self, runner):
        """Test CLI with invalid config file."""
        result = runner.invoke(cli, ["--config", "/nonexistent/config.yaml", "generate", "nginx"])

        # Should handle missing config gracefully
        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_cli_json_output(self, runner, tmp_path):
        """Test CLI JSON output format."""
        record = tmp_path / "nginx.yaml"
        record.write_text('version: "0.3"\nmetadata:\n  name: nginx\n')

        result = runner.invoke(cli, ["validate", str(record), "--format", "json"])

        assert result.exit_code == 0
        assert json.loads(result.output)["schema_version"] == "0.3"

    def test_cli_dry_run_mode(self, runner):
        """Test CLI dry-run mode."""
        with patch("saigen.core.generation_engine.GenerationEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine.generate_saidata = AsyncMock(
                return_value=GenerationResult(
                    success=True,
                    saidata=SaiData(version="0.2", metadata=Metadata(name="nginx")),
                    validation_errors=[],
                    warnings=[],
                    generation_time=1.0,
                    llm_provider_used="openai",
                    tokens_used=100,
                    cost_estimate=0.001,
                )
            )
            mock_engine.save_saidata = AsyncMock()
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(cli, ["--dry-run", "generate", "nginx"])

            assert result.exit_code == 0
            assert "DRY RUN" in result.output or "dry run" in result.output.lower()

    def test_main_function(self):
        """Test main function entry point."""
        with patch("saigen.cli.main.cli") as mock_cli:
            main()
            mock_cli.assert_called_once()

    def test_cli_error_handling(self, runner):
        """Test CLI error handling."""
        with patch("saigen.core.generation_engine.GenerationEngine") as mock_engine_class:
            mock_engine_class.side_effect = Exception("Test error")

            result = runner.invoke(cli, ["generate", "nginx"])

            assert result.exit_code != 0
            assert "error" in result.output.lower()

    def test_cli_keyboard_interrupt(self, runner):
        """Test CLI keyboard interrupt handling."""
        with patch("saigen.core.generation_engine.GenerationEngine") as mock_engine_class:
            mock_engine_class.side_effect = KeyboardInterrupt()

            result = runner.invoke(cli, ["generate", "nginx"])

            assert result.exit_code != 0
            assert "aborted" in result.output.lower()


class TestSaigenCLICommands:
    """Test individual saigen CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_generate_command_basic(self, runner):
        """Test basic generate command."""
        with patch("saigen.core.generation_engine.GenerationEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine.generate_saidata = AsyncMock(
                return_value=GenerationResult(
                    success=True,
                    saidata=SaiData(version="0.2", metadata=Metadata(name="nginx")),
                    validation_errors=[],
                    warnings=[],
                    generation_time=1.0,
                    llm_provider_used="openai",
                    tokens_used=100,
                    cost_estimate=0.001,
                )
            )
            mock_engine.save_saidata = AsyncMock()
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(cli, ["generate", "nginx"])

            assert result.exit_code == 0
            assert "nginx" in result.output

    def test_generate_command_with_providers(self, runner):
        """Test generate command with specific providers."""
        with patch("saigen.core.generation_engine.GenerationEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine.generate_saidata = AsyncMock(
                return_value=GenerationResult(
                    success=True,
                    saidata=SaiData(version="0.2", metadata=Metadata(name="nginx")),
                    validation_errors=[],
                    warnings=[],
                    generation_time=1.0,
                    llm_provider_used="openai",
                    tokens_used=100,
                    cost_estimate=0.001,
                )
            )
            mock_engine.save_saidata = AsyncMock()
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                cli,
                [
                    "--llm-provider",
                    "openai",
                    "generate",
                    "nginx",
                    "--providers",
                    "apt",
                    "--providers",
                    "brew",
                ],
            )

            assert result.exit_code == 0

    def test_validate_command(self, runner):
        """Test validate command."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {"version": "0.2", "metadata": {"name": "nginx", "description": "Web server"}}, f
            )
            temp_file = Path(f.name)

        try:
            with patch("saigen.core.validator.SaidataValidator") as mock_validator_class:
                mock_validator = Mock()
                mock_validator.validate_file = AsyncMock(
                    return_value=Mock(is_valid=True, errors=[], warnings=[])
                )
                mock_validator_class.return_value = mock_validator

                result = runner.invoke(cli, ["validate", str(temp_file)])

                assert result.exit_code == 0
                assert "valid" in result.output.lower()
        finally:
            temp_file.unlink()

    def test_test_command(self, runner):
        """Test test command."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "version": "0.2",
                    "metadata": {"name": "nginx", "description": "Web server"},
                    "providers": {
                        "apt": {"packages": [{"name": "nginx", "package_name": "nginx"}]}
                    },
                },
                f,
            )
            temp_file = Path(f.name)

        try:
            with patch("saigen.cli.commands.test.SaidataTester") as mock_tester_class:
                mock_tester = Mock()
                mock_tester.test_file = AsyncMock(return_value=Mock(has_failures=False, warnings=0))
                mock_tester.format_test_report.return_value = "5 tests passed"
                mock_tester_class.return_value = mock_tester

                result = runner.invoke(cli, ["test", str(temp_file)])

                assert result.exit_code == 0
                assert "test" in result.output.lower()
        finally:
            temp_file.unlink()

    def test_batch_command(self, runner):
        """Test batch command."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("nginx\napache2\nredis\n")
            temp_file = Path(f.name)

        try:
            result = runner.invoke(cli, ["batch", "--input-file", str(temp_file), "--preview"])

            assert result.exit_code == 0
            assert "Preview: Would process 3 software packages" in result.output
        finally:
            temp_file.unlink()

    def test_config_command_show(self, runner):
        """Test config show command."""
        with patch("saigen.utils.config.ConfigManager") as mock_config_class:
            mock_config = Mock()
            mock_config.get_config.return_value = {
                "llm_providers": {"openai": {"model": "gpt-4o-mini"}},
                "output_directory": "/tmp/saigen",
            }
            mock_config_class.return_value = mock_config

            result = runner.invoke(cli, ["config", "show"])

            assert result.exit_code == 0
            assert "llm_providers" in result.output

    def test_cache_command_status(self, runner):
        """Test cache status command."""
        with patch("saigen.repositories.manager.RepositoryManager") as mock_manager_class:
            mock_manager = Mock()
            mock_manager.get_cache_stats = AsyncMock(
                return_value={
                    "total_repositories": 5,
                    "cached_repositories": 3,
                    "cache_size": "10.5 MB",
                    "last_updated": "2024-01-01T00:00:00Z",
                }
            )
            mock_manager_class.return_value = mock_manager

            result = runner.invoke(cli, ["cache", "status"])

            assert result.exit_code == 0
            assert "cache" in result.output.lower()

    def test_index_command_status(self, runner):
        """Test index status command."""
        with patch("saigen.cli.commands.index.GenerationEngine") as mock_engine_class:
            mock_engine_class.return_value.is_rag_available.return_value = False

            result = runner.invoke(cli, ["index", "status"])

            assert result.exit_code == 0
            assert "RAG functionality is not available" in result.output
            mock_engine_class.return_value.is_rag_available.assert_called_once_with()
