"""Test command for saigen CLI."""

import asyncio
import json
from pathlib import Path

import click

from ...core.tester import SaidataTester, SaidataTestType
from ...utils.config import get_config


@click.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path), required=False)
@click.option(
    "--providers", multiple=True, help="Specific providers to test (can be used multiple times)"
)
@click.option(
    "--test-types",
    multiple=True,
    type=click.Choice([t.value for t in SaidataTestType]),
    help="Types of tests to run (can be used multiple times)",
)
@click.option(
    "--no-dry-run",
    is_flag=True,
    help="Disable dry-run mode (WARNING: may perform actual operations)",
)
@click.option("--show-details", is_flag=True, help="Show detailed test information")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format for test results",
)
@click.option("--timeout", type=int, default=300, help="Timeout for test execution in seconds")
@click.pass_context
def test(
    ctx: click.Context,
    file_path: Path,
    providers: tuple,
    test_types: tuple,
    no_dry_run: bool,
    show_details: bool,
    output_format: str,
    timeout: int,
) -> None:
    """Test a saidata YAML file comprehensively.

    This command performs various tests on saidata files including:

    \b
    TEST TYPES:
    • Dry-run testing of package installations
    • Provider compatibility checks
    • Package availability verification
    • Command and service validation
    • MCP server integration testing (TODO)

    \b

    Examples:

    • Basic test\n
        saigen test nginx.yaml

    • Test specific providers\n
        saigen test --providers apt --providers brew software.yaml

    • Run specific test types\n
        saigen test --test-types dry_run --test-types package_availability software.yaml

    • Show detailed results\n
        saigen test --show-details --format json software.yaml

    • WARNING: Perform actual operations\n
        saigen test --no-dry-run software.yaml
    """
    # Show help if file_path is missing
    if not file_path:
        click.echo(ctx.get_help())
        click.echo("\n" + "=" * 70)
        click.echo("ERROR: Missing required argument FILE_PATH")
        click.echo("=" * 70)
        ctx.exit(2)
    
    exit_code = 0

    # Handle dry-run confirmation outside try-catch to avoid catching SystemExit
    dry_run = not no_dry_run
    if not dry_run:
        click.echo(
            "⚠️  WARNING: Dry-run mode disabled. Tests may perform actual operations!", err=True
        )
        if not click.confirm("Do you want to continue?"):
            # User declined, exit gracefully
            ctx.exit(0)

    try:
        # Get configuration
        config = (ctx.obj and ctx.obj.get("config")) or get_config()

        # Convert test types from strings to enums
        selected_test_types = None
        if test_types:
            selected_test_types = [SaidataTestType(t) for t in test_types]

        # Convert providers tuple to list
        selected_providers = list(providers) if providers else None

        # Create tester
        tester = SaidataTester(config)

        # Run tests with timeout
        # Only show informational messages in text mode to keep JSON output clean
        if output_format != "json":
            click.echo(f"🧪 Testing saidata file: {file_path}")
            if selected_providers:
                click.echo(f"📦 Testing providers: {', '.join(selected_providers)}")
            if selected_test_types:
                click.echo(
                    f"🔍 Running test types: {', '.join(t.value for t in selected_test_types)}"
                )

            click.echo(f"⏱️  Timeout: {timeout}s")
            click.echo("")

        # Run the async test function
        try:
            test_suite = asyncio.run(
                asyncio.wait_for(
                    tester.test_file(
                        file_path=file_path,
                        providers=selected_providers,
                        test_types=selected_test_types,
                        dry_run=dry_run,
                    ),
                    timeout=timeout,
                )
            )
        except asyncio.TimeoutError:
            raise click.ClickException(f"Test execution timed out after {timeout} seconds")

        # Output results
        if output_format == "json":
            # JSON output for programmatic use
            output = {
                "file_path": test_suite.file_path,
                "summary": {
                    "total_tests": test_suite.total_tests,
                    "passed": test_suite.passed,
                    "failed": test_suite.failed,
                    "warnings": test_suite.warnings,
                    "skipped": test_suite.skipped,
                    "success_rate": test_suite.success_rate,
                    "duration": test_suite.duration,
                    "has_failures": test_suite.has_failures,
                },
                "results": [
                    {
                        "test_type": result.test_type.value,
                        "severity": result.severity.value,
                        "message": result.message,
                        "provider": result.provider,
                        "duration": result.duration,
                        "details": result.details if show_details else None,
                        "suggestions": result.suggestions,
                    }
                    for result in test_suite.results
                ],
            }
            click.echo(json.dumps(output, indent=2))
        else:
            # Human-readable text output
            report = tester.format_test_report(test_suite, show_details=show_details)
            click.echo(report)

        # Determine exit code
        if test_suite.has_failures:
            exit_code = 1
        elif test_suite.warnings > 0:
            exit_code = 2  # Exit code 2 for warnings

    except FileNotFoundError as e:
        raise click.ClickException(f"File not found: {e}")
    except Exception as e:
        if ctx.obj and ctx.obj.get("verbose"):
            import traceback

            click.echo(f"Error details:\n{traceback.format_exc()}", err=True)
        raise click.ClickException(f"Test execution error: {e}")

    # Exit with the determined code
    ctx.exit(exit_code)


@click.group()
def test_group():
    """Test-related commands."""


# Add the test command to the group
test_group.add_command(test)


# For backwards compatibility, also export the command directly
__all__ = ["test", "test_group"]


if __name__ == "__main__":
    test()
