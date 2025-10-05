"""Output formatting utilities for SAI CLI tool."""

from enum import Enum
from typing import List, Optional

import click


class OutputType(str, Enum):
    """Output type enumeration for color coding."""

    STDOUT = "stdout"
    STDERR = "stderr"
    INFO = "info"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    COMMAND = "command"


class OutputFormatter:
    """Handles consistent output formatting across SAI commands."""

    def __init__(self, quiet: bool = False, verbose: bool = False, output_json: bool = False):
        """Initialize the output formatter.

        Args:
            quiet: Whether to suppress non-essential output
            verbose: Whether to show verbose output
            output_json: Whether to output in JSON format
        """
        self.quiet = quiet
        self.verbose = verbose
        self.output_json = output_json

    def format_provider_header(self, provider_name: str, success: bool = True) -> str:
        """Format a provider header with consistent styling.

        Args:
            provider_name: Name of the provider
            success: Whether the operation was successful

        Returns:
            Formatted header string
        """
        if success:
            return click.style(f"── {provider_name} ──", fg="cyan", bold=True)
        else:
            return click.style(f"── {provider_name} (failed) ──", fg="red", bold=True)

    def format_command(self, command: str, provider_name: Optional[str] = None) -> str:
        """Format a command for display.

        Args:
            command: Command to format
            provider_name: Optional provider name for context

        Returns:
            Formatted command string
        """
        # Sanitize sensitive information
        safe_command = self._sanitize_command(command)

        if provider_name:
            provider_part = click.style(f"[{provider_name}]", fg="blue", dim=True)
            command_part = click.style(safe_command, bold=True)
            return f"{provider_part} {command_part}"
        else:
            return click.style(safe_command, bold=True)

    def format_output(self, text: str, output_type: OutputType) -> str:
        """Format output text with appropriate color coding.

        Args:
            text: Text to format
            output_type: Type of output for color coding

        Returns:
            Formatted text string
        """
        if not text:
            return ""

        # Color mapping for different output types
        color_map = {
            OutputType.STDOUT: "white",  # Standard output - white/default
            OutputType.STDERR: "red",  # Error output - red
            OutputType.INFO: "blue",  # Info messages - blue
            OutputType.SUCCESS: "green",  # Success messages - green
            OutputType.ERROR: "red",  # Error messages - red
            OutputType.WARNING: "yellow",  # Warning messages - yellow
            OutputType.COMMAND: "cyan",  # Command display - cyan
        }

        # Dim stderr to make it less prominent but still visible
        dim = output_type == OutputType.STDERR

        color = color_map.get(output_type, "white")
        return click.style(text, fg=color, dim=dim)

    def print_provider_section(
        self,
        provider_name: str,
        command: str,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        success: bool = True,
        show_command: bool = True,
    ):
        """Print a complete provider section with header, command, and output.

        Args:
            provider_name: Name of the provider
            command: Command that was executed
            stdout: Standard output from command
            stderr: Standard error from command
            success: Whether the operation was successful
            show_command: Whether to show the command
        """
        if self.quiet and success:
            # In quiet mode, only show output for successful operations
            if stdout and stdout.strip():
                click.echo(self.format_output(stdout.strip(), OutputType.STDOUT))
            return

        # Print provider header
        header = self.format_provider_header(provider_name, success)
        click.echo(f"\n{header}")

        # Print command if requested and not quiet
        if show_command and not self.quiet:
            formatted_command = self.format_command(command)
            click.echo(f"Executing: {formatted_command}")

        # Print outputs with appropriate formatting
        if stdout and stdout.strip():
            formatted_stdout = self.format_output(stdout.strip(), OutputType.STDOUT)
            click.echo(formatted_stdout)

        if stderr and stderr.strip():
            formatted_stderr = self.format_output(stderr.strip(), OutputType.STDERR)
            click.echo(formatted_stderr, err=True)

    def print_single_provider_output(
        self,
        provider_name: str,
        command: str,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        success: bool = True,
        show_provider: bool = False,
    ):
        """Print output for a single provider without section headers.

        Args:
            provider_name: Name of the provider
            command: Command that was executed
            stdout: Standard output from command
            stderr: Standard error from command
            success: Whether the operation was successful
            show_provider: Whether to show provider name in command
        """
        if self.quiet and not success:
            return

        # Show command if verbose or if it failed
        if (self.verbose or not success) and not self.quiet:
            formatted_command = self.format_command(
                command, provider_name if show_provider else None
            )
            click.echo(f"Executing: {formatted_command}")

        # Print outputs
        if stdout and stdout.strip():
            formatted_stdout = self.format_output(stdout.strip(), OutputType.STDOUT)
            click.echo(formatted_stdout)

        if stderr and stderr.strip():
            formatted_stderr = self.format_output(stderr.strip(), OutputType.STDERR)
            click.echo(formatted_stderr, err=True)

        # If no output and not quiet, show a simple success indicator for successful operations
        elif success and not self.quiet and not stdout and not stderr:
            self.print_success_message("Operation completed successfully")

    def print_success_message(self, message: str):
        """Print a success message with appropriate formatting.

        Args:
            message: Success message to print
        """
        if not self.quiet:
            formatted_message = self.format_output(f"✓ {message}", OutputType.SUCCESS)
            click.echo(formatted_message)

    def print_error_message(self, message: str, details: Optional[str] = None):
        """Print an error message with appropriate formatting.

        Args:
            message: Error message to print
            details: Optional error details for verbose mode
        """
        formatted_message = self.format_output(f"✗ {message}", OutputType.ERROR)
        click.echo(formatted_message, err=True)

        if details and self.verbose:
            formatted_details = self.format_output(f"Details: {details}", OutputType.ERROR)
            click.echo(formatted_details, err=True)

    def print_warning_message(self, message: str):
        """Print a warning message with appropriate formatting.

        Args:
            message: Warning message to print
        """
        if not self.quiet:
            formatted_message = self.format_output(f"⚠ {message}", OutputType.WARNING)
            click.echo(formatted_message, err=True)

    def print_info_message(self, message: str):
        """Print an info message with appropriate formatting.

        Args:
            message: Info message to print
        """
        if self.verbose:
            formatted_message = self.format_output(f"ℹ {message}", OutputType.INFO)
            click.echo(formatted_message)

    def print_execution_summary(
        self, total_actions: int, successful_actions: int, execution_time: float
    ):
        """Print execution summary with appropriate formatting.

        Args:
            total_actions: Total number of actions
            successful_actions: Number of successful actions
            execution_time: Total execution time
        """
        if self.quiet:
            return

        failed_actions = total_actions - successful_actions

        if failed_actions == 0:
            message = f"Successfully executed {successful_actions}/{total_actions} actions"
            self.print_success_message(message)
        else:
            message = (
                f"Executed {successful_actions}/{total_actions} actions ({failed_actions} failed)"
            )
            self.print_error_message(message)

        if self.verbose:
            self.print_info_message(f"Execution time: {execution_time:.2f}s")
            success_rate = (successful_actions / total_actions) * 100 if total_actions > 0 else 0
            self.print_info_message(f"Success rate: {success_rate:.1f}%")

    def print_commands_list(self, commands: List[str], title: str = "Commands executed"):
        """Print a list of commands with consistent formatting.

        Args:
            commands: List of commands to display
            title: Title for the command list
        """
        if not commands or self.quiet:
            return

        self.print_info_message(title)
        for cmd in commands:
            formatted_cmd = self.format_command(cmd)
            click.echo(f"  {formatted_cmd}")

    def _sanitize_command(self, command: str) -> str:
        """Sanitize command for safe display.

        Args:
            command: Command to sanitize

        Returns:
            Sanitized command string
        """
        # List of patterns that might contain sensitive information
        sensitive_patterns = ["password", "passwd", "secret", "key", "token", "auth"]

        # Enhanced sanitization with regex patterns for better security
        import re

        # More comprehensive sensitive patterns
        sensitive_patterns = [
            r"--password[=\s]+\S+",
            r"--passwd[=\s]+\S+",
            r"--secret[=\s]+\S+",
            r"--key[=\s]+\S+",
            r"--token[=\s]+\S+",
            r"--auth[=\s]+\S+",
            r"-p\s+\S+",  # -p password
            r"mysql.*-p\S*",  # mysql -p patterns
        ]

        # Apply regex-based sanitization first
        sanitized_command = command
        for pattern in sensitive_patterns:
            sanitized_command = re.sub(
                pattern, "[REDACTED]", sanitized_command, flags=re.IGNORECASE
            )

        # Fallback to word-based sanitization
        words = sanitized_command.split()
        sanitized_words = []

        for i, word in enumerate(words):
            # Check if this word or the previous word suggests sensitive data
            is_sensitive = False

            # Check current word
            for pattern in ["password", "passwd", "secret", "key", "token", "auth"]:
                if pattern.lower() in word.lower():
                    is_sensitive = True
                    break

            # Check if previous word was a flag that might precede sensitive data
            if i > 0:
                prev_word = words[i - 1].lower()
                for pattern in ["password", "passwd", "secret", "key", "token", "auth"]:
                    if pattern in prev_word or prev_word.startswith("-") and pattern in prev_word:
                        is_sensitive = True
                        break

            if is_sensitive and not word.startswith("-"):
                sanitized_words.append("[REDACTED]")
            else:
                sanitized_words.append(word)

        return " ".join(sanitized_words)


def create_output_formatter(ctx: click.Context) -> OutputFormatter:
    """Create an output formatter from click context.

    Args:
        ctx: Click context containing CLI options

    Returns:
        Configured OutputFormatter instance
    """
    return OutputFormatter(
        quiet=ctx.obj.get("quiet", False),
        verbose=ctx.obj.get("verbose", False),
        output_json=ctx.obj.get("output_json", False),
    )
