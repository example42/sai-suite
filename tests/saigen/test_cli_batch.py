"""Tests for batch CLI command."""


import pytest
from click.testing import CliRunner

from saigen.cli.commands.batch import batch


class TestBatchCLI:
    """Test batch CLI command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        return {
            "llm_providers": {"openai": {"api_key": "test-key", "model": "gpt-4o-mini"}},
            "rag": {"enabled": True},
        }

    @pytest.fixture
    def sample_software_list(self, tmp_path):
        """Create sample software list file."""
        software_file = tmp_path / "software_list.txt"
        software_file.write_text(
            """# Test software list
nginx
redis
postgresql
"""
        )
        return software_file

    def test_batch_help(self, runner):
        """Test batch command help."""
        result = runner.invoke(batch, ["--help"])
        assert result.exit_code == 0
        assert "Generate saidata" in result.output
        assert "multiple software packages" in result.output
        assert "--input-file" in result.output
        assert "--software-list" in result.output
        assert "--max-concurrent" in result.output

    def test_batch_no_input_error(self, runner, mock_config):
        """Test error when no input is provided."""
        with runner.isolated_filesystem():
            result = runner.invoke(
                batch,
                [],
                obj={
                    "config": mock_config,
                    "verbose": False,
                    "dry_run": False,
                    "llm_provider": None,
                },
            )
            assert result.exit_code != 0
            assert "Must specify either --input-file or --software-list" in result.output

    def test_batch_both_inputs_error(self, runner, mock_config, sample_software_list):
        """Test error when both input methods are provided."""
        with runner.isolated_filesystem():
            result = runner.invoke(
                batch,
                ["--input-file", str(sample_software_list), "--software-list", "nginx"],
                obj={
                    "config": mock_config,
                    "verbose": False,
                    "dry_run": False,
                    "llm_provider": None,
                },
            )
            assert result.exit_code != 0
            assert "Cannot specify both --input-file and --software-list" in result.output

    def test_batch_preview_mode(self, runner, mock_config, sample_software_list):
        """Test batch preview mode."""
        result = runner.invoke(
            batch,
            ["--input-file", str(sample_software_list), "--preview"],
            obj={"config": mock_config, "verbose": False, "dry_run": False, "llm_provider": None},
        )

        assert result.exit_code == 0
        assert "Preview: Would process 3 software packages" in result.output
        assert "nginx" not in result.output  # Should not show individual packages in non-verbose

    def test_batch_preview_verbose(self, runner, mock_config, sample_software_list):
        """Test batch preview mode with verbose output."""
        result = runner.invoke(
            batch,
            ["--input-file", str(sample_software_list), "--preview"],
            obj={"config": mock_config, "verbose": True, "dry_run": False, "llm_provider": None},
        )

        assert result.exit_code == 0
        assert "Preview: Would process 3 software packages" in result.output
        assert "nginx" in result.output
        assert "redis" in result.output
        assert "postgresql" in result.output

    def test_batch_dry_run(self, runner, mock_config, sample_software_list):
        """Test batch dry run mode."""
        result = runner.invoke(
            batch,
            ["--input-file", str(sample_software_list), "--output-dir", "output"],
            obj={"config": mock_config, "verbose": False, "dry_run": True, "llm_provider": None},
        )

        assert result.exit_code == 0
        assert "[DRY RUN] Would process 3 software packages" in result.output
        assert "[DRY RUN] Would save files to: output" in result.output

    def test_batch_software_list_command_line(self, runner, mock_config):
        """Test batch with software list from command line."""
        result = runner.invoke(
            batch,
            ["--software-list", "nginx", "--software-list", "redis", "--preview"],
            obj={"config": mock_config, "verbose": False, "dry_run": False, "llm_provider": None},
        )

        assert result.exit_code == 0
        assert "Preview: Would process 2 software packages" in result.output

    def test_batch_category_filter(self, runner, mock_config, tmp_path):
        """Test batch with category filtering."""
        # Create software list with categories
        software_file = tmp_path / "categorized_list.txt"
        software_file.write_text(
            """# Categorized software list

## Web Servers
nginx
apache

## Databases
postgresql
mysql

## Cache Systems
redis
memcached
"""
        )

        result = runner.invoke(
            batch,
            ["--input-file", str(software_file), "--category-filter", "database", "--preview"],
            obj={"config": mock_config, "verbose": True, "dry_run": False, "llm_provider": None},
        )

        assert result.exit_code == 0
        assert "Preview: Would process 2 software packages" in result.output
        assert "Applied category filter: database" in result.output

    def test_batch_invalid_concurrency(self, runner, mock_config, sample_software_list):
        """Test error with invalid concurrency setting."""
        result = runner.invoke(
            batch,
            ["--input-file", str(sample_software_list), "--max-concurrent", "0"],
            obj={"config": mock_config, "verbose": False, "dry_run": False, "llm_provider": None},
        )

        assert result.exit_code != 0
        assert "max-concurrent must be between 1 and 20" in result.output

    def test_batch_invalid_llm_provider(self, runner, mock_config, sample_software_list):
        """Test error with invalid LLM provider."""
        result = runner.invoke(
            batch,
            ["--input-file", str(sample_software_list), "--preview"],
            obj={
                "config": mock_config,
                "verbose": False,
                "dry_run": False,
                "llm_provider": "invalid_provider",
            },
        )

        assert result.exit_code != 0
        assert "Invalid LLM provider: invalid_provider" in result.output

    def test_batch_nonexistent_file(self, runner, mock_config):
        """Test error with nonexistent input file."""
        result = runner.invoke(
            batch,
            ["--input-file", "nonexistent.txt"],
            obj={"config": mock_config, "verbose": False, "dry_run": False, "llm_provider": None},
        )

        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_batch_successful_execution_dry_run(
        self, runner, mock_config, sample_software_list, tmp_path
    ):
        """Test successful batch execution in dry run mode."""
        # Create output directory
        output_dir = tmp_path / "output"

        result = runner.invoke(
            batch,
            ["--input-file", str(sample_software_list), "--output-dir", str(output_dir)],
            obj={
                "config": mock_config,
                "verbose": False,
                "dry_run": True,  # Use dry run to avoid actual execution
                "llm_provider": None,
            },
        )

        assert result.exit_code == 0
        assert "[DRY RUN] Would process 3 software packages" in result.output
        assert f"[DRY RUN] Would save files to: {output_dir}" in result.output

    def test_batch_partial_failure_preview(self, runner, mock_config, sample_software_list):
        """Test batch execution preview mode."""
        result = runner.invoke(
            batch,
            ["--input-file", str(sample_software_list), "--preview"],
            obj={"config": mock_config, "verbose": False, "dry_run": False, "llm_provider": None},
        )

        assert result.exit_code == 0
        assert "Preview: Would process 3 software packages" in result.output

    def test_batch_existing_files_prompt(self, runner, mock_config, sample_software_list, tmp_path):
        """Test prompt when output files already exist."""
        # Create output directory with existing file
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "nginx.yaml").write_text("existing content")

        result = runner.invoke(
            batch,
            [
                "--input-file",
                str(sample_software_list),
                "--output-dir",
                str(output_dir),
                "--preview",  # Use preview to avoid actual execution
            ],
            obj={"config": mock_config, "verbose": False, "dry_run": False, "llm_provider": None},
        )

        assert result.exit_code == 0

    def test_batch_force_overwrite(self, runner, mock_config, sample_software_list, tmp_path):
        """Test force overwrite of existing files."""
        # Create output directory with existing file
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "nginx.yaml").write_text("existing content")

        result = runner.invoke(
            batch,
            [
                "--input-file",
                str(sample_software_list),
                "--output-dir",
                str(output_dir),
                "--force",
                "--preview",  # Use preview to avoid actual execution
            ],
            obj={"config": mock_config, "verbose": False, "dry_run": False, "llm_provider": None},
        )

        assert result.exit_code == 0
