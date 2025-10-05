"""System-level testing command for saidata files."""

import logging
from pathlib import Path

import click

from saigen.testing.reporter import TestReporter
from saigen.testing.runner import TestRunner

logger = logging.getLogger(__name__)


@click.command(name="test-system")
@click.argument("saidata_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--real-install",
    is_flag=True,
    help="Perform actual installation (WARNING: modifies system)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "junit"]),
    default="text",
    help="Output format for test results",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Write report to file",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--batch",
    is_flag=True,
    help="Test all saidata files in directory",
)
def test_system(
    saidata_path: Path,
    real_install: bool,
    output_format: str,
    output: Path | None,
    verbose: bool,
    batch: bool,
) -> None:
    """Test saidata files on real systems.

    This command validates saidata files by checking:
    - Package existence in repositories
    - Installation capability (with --real-install)
    - Service availability
    - File locations

    Examples:
        # Dry-run test (checks package existence only)
        saigen test-system nginx.yaml

        # Test with actual installation
        saigen test-system --real-install nginx.yaml

        # Test all files in directory
        saigen test-system --batch packages/

        # Generate JSON report
        saigen test-system --format json -o report.json nginx.yaml

        # Generate JUnit XML for CI
        saigen test-system --format junit -o results.xml nginx.yaml
    """
    if verbose:
        logging.basicConfig(level=logging.INFO)

    # Warn about real installation
    if real_install:
        click.echo(
            "⚠️  WARNING: Real installation mode enabled. This will modify your system!",
            err=True,
        )
        if not click.confirm("Do you want to continue?"):
            return

    # Create runner and reporter
    runner = TestRunner(
        dry_run=not real_install,
        verbose=verbose,
        real_install=real_install,
    )
    reporter = TestReporter(output_format=output_format)

    try:
        if batch:
            # Batch mode - test all files in directory
            if not saidata_path.is_dir():
                raise click.ClickException(
                    f"Path must be a directory for batch mode: {saidata_path}"
                )

            click.echo(f"🧪 Testing all saidata files in: {saidata_path}")
            suites = runner.run_batch(saidata_path)

            if not suites:
                click.echo("No saidata files found")
                return

            report = reporter.report_batch(suites, output_file=output)
            if not output:
                click.echo(report)

            # Exit with error if any tests failed
            total_failed = sum(s.failed + s.errors for s in suites)
            if total_failed > 0:
                raise click.Abort()

        else:
            # Single file mode
            if not saidata_path.is_file():
                raise click.ClickException(f"File not found: {saidata_path}")

            click.echo(f"🧪 Testing saidata: {saidata_path}")
            suite = runner.run_tests(saidata_path)

            report = reporter.report(suite, output_file=output)
            if not output:
                click.echo(report)

            # Exit with error if tests failed
            if suite.failed > 0 or suite.errors > 0:
                raise click.Abort()

    except Exception as e:
        if verbose:
            import traceback

            click.echo(f"Error details:\n{traceback.format_exc()}", err=True)
        raise click.ClickException(f"Test execution error: {e}")


if __name__ == "__main__":
    test_system()
