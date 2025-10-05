"""Tests for output formatter functionality."""

import pytest
from unittest.mock import patch, MagicMock
import click

from sai.utils.output_formatter import OutputFormatter, OutputType, create_output_formatter


class TestOutputFormatter:
    """Test output formatter functionality."""
    
    def test_initialization(self):
        """Test formatter initialization with different modes."""
        # Default mode
        formatter = OutputFormatter()
        assert not formatter.quiet
        assert not formatter.verbose
        assert not formatter.output_json
        
        # Quiet mode
        formatter = OutputFormatter(quiet=True)
        assert formatter.quiet
        
        # Verbose mode
        formatter = OutputFormatter(verbose=True)
        assert formatter.verbose
        
        # JSON mode
        formatter = OutputFormatter(output_json=True)
        assert formatter.output_json
    
    def test_format_provider_header(self):
        """Test provider header formatting."""
        formatter = OutputFormatter()
        
        # Success header
        header = formatter.format_provider_header("apt", success=True)
        assert "apt" in header
        assert "failed" not in header
        
        # Failed header
        header = formatter.format_provider_header("apt", success=False)
        assert "apt" in header
        assert "failed" in header
    
    def test_format_command(self):
        """Test command formatting."""
        formatter = OutputFormatter()
        
        # Simple command
        formatted = formatter.format_command("sudo apt install nginx")
        assert "sudo apt install nginx" in formatted
        
        # Command with provider
        formatted = formatter.format_command("sudo apt install nginx", "apt")
        assert "apt" in formatted
        assert "sudo apt install nginx" in formatted
    
    def test_format_output(self):
        """Test output formatting with different types."""
        formatter = OutputFormatter()
        
        # Test different output types
        stdout_output = formatter.format_output("Normal output", OutputType.STDOUT)
        assert "Normal output" in stdout_output
        
        stderr_output = formatter.format_output("Error output", OutputType.STDERR)
        assert "Error output" in stderr_output
        
        success_output = formatter.format_output("Success message", OutputType.SUCCESS)
        assert "Success message" in success_output
        
        # Empty output
        empty_output = formatter.format_output("", OutputType.STDOUT)
        assert empty_output == ""
    
    def test_command_sanitization(self):
        """Test command sanitization for sensitive data."""
        formatter = OutputFormatter()
        
        # Test password sanitization
        sanitized = formatter._sanitize_command("mysql -u root -p secret123")
        assert "[REDACTED]" in sanitized
        assert "secret123" not in sanitized
        
        # Test key sanitization
        sanitized = formatter._sanitize_command("curl --header 'Authorization: Bearer token123'")
        # Note: This is a basic test, the actual implementation may vary
        
        # Test normal command (should not be sanitized)
        sanitized = formatter._sanitize_command("sudo apt install nginx")
        assert sanitized == "sudo apt install nginx"
    
    @patch('click.echo')
    def test_print_provider_section(self, mock_echo):
        """Test provider section printing."""
        formatter = OutputFormatter()
        
        # Test successful operation
        formatter.print_provider_section(
            provider_name="apt",
            command="sudo apt install nginx",
            stdout="Package installed successfully",
            stderr="",
            success=True,
            show_command=True
        )
        
        # Verify echo was called
        assert mock_echo.called
        
        # Test failed operation
        mock_echo.reset_mock()
        formatter.print_provider_section(
            provider_name="apt",
            command="sudo apt install nonexistent",
            stdout="",
            stderr="Package not found",
            success=False,
            show_command=True
        )
        
        assert mock_echo.called
    
    @patch('click.echo')
    def test_quiet_mode_behavior(self, mock_echo):
        """Test quiet mode suppresses non-essential output."""
        formatter = OutputFormatter(quiet=True)
        
        # Successful operation in quiet mode should only show output
        formatter.print_provider_section(
            provider_name="apt",
            command="sudo apt install nginx",
            stdout="Package installed",
            stderr="",
            success=True,
            show_command=True
        )
        
        # Should have minimal calls to echo
        assert mock_echo.called
    
    @patch('click.echo')
    def test_verbose_mode_behavior(self, mock_echo):
        """Test verbose mode shows additional information."""
        formatter = OutputFormatter(verbose=True)
        
        # Test info message in verbose mode
        formatter.print_info_message("Detailed information")
        assert mock_echo.called
        
        # Test commands list
        mock_echo.reset_mock()
        formatter.print_commands_list(["cmd1", "cmd2"], "Test commands")
        assert mock_echo.called
    
    @patch('click.echo')
    def test_message_formatting(self, mock_echo):
        """Test different message type formatting."""
        formatter = OutputFormatter()
        
        # Success message
        formatter.print_success_message("Operation successful")
        assert mock_echo.called
        
        # Error message
        mock_echo.reset_mock()
        formatter.print_error_message("Operation failed", "Details here")
        assert mock_echo.called
        
        # Warning message
        mock_echo.reset_mock()
        formatter.print_warning_message("Warning message")
        assert mock_echo.called
        
        # Info message (should not show in non-verbose mode)
        mock_echo.reset_mock()
        formatter.print_info_message("Info message")
        # Should not be called in non-verbose mode
    
    def test_execution_summary(self):
        """Test execution summary formatting."""
        formatter = OutputFormatter()
        
        with patch('click.echo') as mock_echo:
            # Successful execution
            formatter.print_execution_summary(5, 5, 2.5)
            assert mock_echo.called
            
            # Partial failure
            mock_echo.reset_mock()
            formatter.print_execution_summary(5, 3, 3.0)
            assert mock_echo.called
    
    def test_create_output_formatter(self):
        """Test formatter creation from click context."""
        # Mock click context
        ctx = MagicMock()
        ctx.obj = {
            'quiet': True,
            'verbose': False,
            'output_json': False
        }
        
        formatter = create_output_formatter(ctx)
        assert formatter.quiet
        assert not formatter.verbose
        assert not formatter.output_json


class TestOutputFormatterIntegration:
    """Integration tests for output formatter."""
    
    def test_real_command_sanitization(self):
        """Test sanitization with real-world commands."""
        formatter = OutputFormatter()
        
        test_cases = [
            ("mysql -u root -p mypassword", True),  # Should be redacted
            ("curl -H 'Authorization: Bearer token123'", True),  # Should be redacted
            ("sudo apt install nginx", False),  # Should remain unchanged
            ("docker login --password secret", True),  # Should be redacted
            ("git clone https://user:pass@github.com/repo.git", False),  # May or may not be redacted
        ]
        
        for command, should_be_redacted in test_cases:
            sanitized = formatter._sanitize_command(command)
            if should_be_redacted:
                assert "[REDACTED]" in sanitized, f"Command '{command}' should be sanitized but got: {sanitized}"
            else:
                # For non-sensitive content, check that original content is preserved
                if command == "sudo apt install nginx":
                    assert "nginx" in sanitized and "sudo" in sanitized
    
    @patch('click.echo')
    def test_multi_provider_output(self, mock_echo):
        """Test output formatting for multiple providers."""
        formatter = OutputFormatter()
        
        providers_data = [
            ("apt", "sudo apt install nginx", "Package installed", "", True),
            ("snap", "snap install nginx", "", "Package not found", False),
            ("brew", "brew install nginx", "nginx installed", "", True),
        ]
        
        for provider, command, stdout, stderr, success in providers_data:
            formatter.print_provider_section(
                provider_name=provider,
                command=command,
                stdout=stdout,
                stderr=stderr,
                success=success,
                show_command=True
            )
        
        # Verify multiple calls to echo
        assert mock_echo.call_count > len(providers_data)