"""Validate command for saigen CLI."""

import asyncio
from pathlib import Path
from typing import Optional

import click
import yaml

from ...core.advanced_validator import AdvancedSaidataValidator
from ...core.validator import SaidataValidator
from ...models.saidata import SaiData
from ...repositories.manager import RepositoryManager
from ...utils.config import get_config


def _schema_version(file_path: Path) -> str:
    try:
        data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return "0.3"
    return "0.4" if isinstance(data, dict) and data.get("version") == "0.4" else "0.3"


@click.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path), required=False)
@click.option(
    "--schema",
    type=click.Path(exists=True, path_type=Path),
    help="Path to custom saidata schema file (defaults to the file's schema version)",
)
@click.option("--show-context", is_flag=True, help="Show detailed context information for errors")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format for validation results",
)
@click.option(
    "--advanced",
    is_flag=True,
    help="Enable advanced validation with quality metrics and repository accuracy checking",
)
@click.option(
    "--no-repository-check",
    is_flag=True,
    help="Skip repository accuracy checking (faster but less comprehensive)",
)
@click.option("--detailed", is_flag=True, help="Show detailed quality metrics and suggestions")
@click.option(
    "--validate-urls",
    is_flag=True,
    help="Enable URL template validation for sources, binaries, and scripts",
)
@click.option(
    "--validate-checksums",
    is_flag=True,
    help="Enable checksum format validation (algorithm:hash format)",
)
@click.option(
    "--auto-recover", is_flag=True, help="Attempt automatic recovery from common validation errors"
)
def validate(
    file_path: Path,
    schema: Optional[Path] = None,
    show_context: bool = False,
    output_format: str = "text",
    advanced: bool = False,
    no_repository_check: bool = False,
    detailed: bool = False,
    validate_urls: bool = False,
    validate_checksums: bool = False,
    auto_recover: bool = False,
) -> None:
    """Validate a saidata YAML file against the saidata schema.

    Comprehensive validation for saidata schema files including:

    \b
    🔍 CORE VALIDATION:
    • JSON schema compliance (saidata-0.3 or saidata-0.4)
    • Required fields and structure validation
    • Enum value validation for build systems, service types, etc.
    • Cross-reference consistency checking

    \b
    🆕 NEW 0.3 FEATURES:
    • URL template validation ({{version}}, {{platform}}, {{architecture}})
    • Checksum format validation (algorithm:hash format)
    • Security metadata validation (CVE exceptions, contacts)
    • Installation method validation (sources, binaries, scripts)
    • Provider configuration validation with overrides
    • Compatibility matrix validation

    \b
    🔧 ADVANCED FEATURES:
    • Quality metrics and scoring (--advanced)
    • Repository accuracy checking (--advanced)
    • Automatic error recovery (--auto-recover)
    • Best practice recommendations
    • Performance and security suggestions

    \b
    🛠️ ERROR RECOVERY:
    The --auto-recover flag attempts to automatically fix common issues:
    • Invalid URL template syntax
    • Incorrect checksum formats
    • Missing required fields with sensible defaults
    • Enum value corrections

    \b
    Examples:

    • Basic schema validation\n
        saigen validate nginx.yaml

    • Validate with URL and checksum checking\n
        saigen validate --validate-urls --validate-checksums terraform.yaml

    • Advanced validation with quality metrics\n
        saigen validate --advanced --detailed kubernetes.yaml

    • Auto-recover from common errors\n
        saigen validate --auto-recover --format json docker.yaml

    • Custom schema validation\n
        saigen validate --schema custom-0.3-schema.json software.yaml

    • Detailed error context for debugging\n
        saigen validate --show-context --format json nginx.yaml

    • Fast validation without repository checks\n
        saigen validate --advanced --no-repository-check large-file.yaml
    """
    # Show help if file_path is missing
    if not file_path:
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        click.echo("\n" + "=" * 70)
        click.echo("ERROR: Missing required argument FILE_PATH")
        click.echo("=" * 70)
        ctx.exit(2)

    try:
        if advanced:
            # Use advanced validation with quality metrics
            asyncio.run(
                _run_advanced_validation(
                    file_path,
                    schema,
                    show_context,
                    output_format,
                    not no_repository_check,
                    detailed,
                    validate_urls,
                    validate_checksums,
                    auto_recover,
                )
            )
        else:
            # Use basic validation
            _run_basic_validation(
                file_path,
                schema,
                show_context,
                output_format,
                validate_urls,
                validate_checksums,
                auto_recover,
            )

    except FileNotFoundError as e:
        raise click.ClickException(f"File not found: {e}")
    except Exception as e:
        raise click.ClickException(f"Validation error: {e}")


def _run_basic_validation(
    file_path: Path,
    schema: Optional[Path],
    show_context: bool,
    output_format: str,
    validate_urls: bool = False,
    validate_checksums: bool = False,
    auto_recover: bool = False,
) -> None:
    """Run basic schema validation with version-specific features."""
    # Create validator with optional custom schema.
    validator = SaidataValidator(schema_path=schema)

    # Load and validate the file
    if auto_recover:
        # Use validation with automatic recovery
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            result, recovery_result = validator.validate_with_recovery(data, str(file_path))

            # Show recovery information if any fixes were applied
            if recovery_result and recovery_result.fixed_errors:
                if output_format == "text":
                    click.echo("🔧 Automatic Error Recovery Applied:")
                    recovery_report = validator.format_recovery_report(recovery_result)
                    click.echo(recovery_report)
                    click.echo("")

        except Exception:
            result = validator.validate_file(file_path)
            recovery_result = None
    else:
        # Standard validation
        result = validator.validate_file(file_path)
        recovery_result = None

    if output_format == "json":
        # JSON output for programmatic use
        import json

        output = {
            "file": str(file_path),
            "schema_version": _schema_version(file_path),
            "valid": result.is_valid,
            "total_issues": result.total_issues,
            "validation_features": {
                "url_templates": validate_urls or True,  # Always enabled in 0.3
                "checksums": validate_checksums or True,  # Always enabled in 0.3
                "auto_recovery": auto_recover,
            },
            "errors": [
                {
                    "severity": error.severity,
                    "message": error.message,
                    "path": error.path,
                    "code": error.code,
                    "suggestion": error.suggestion,
                    "context": error.context if show_context else None,
                }
                for error in result.errors
            ],
            "warnings": [
                {
                    "severity": warning.severity,
                    "message": warning.message,
                    "path": warning.path,
                    "code": warning.code,
                    "suggestion": warning.suggestion,
                    "context": warning.context if show_context else None,
                }
                for warning in result.warnings
            ],
            "info": [
                {
                    "severity": info.severity,
                    "message": info.message,
                    "path": info.path,
                    "code": info.code,
                    "suggestion": info.suggestion,
                    "context": info.context if show_context else None,
                }
                for info in result.info
            ],
        }

        # Add recovery information if available
        if recovery_result and recovery_result.fixed_errors:
            output["recovery"] = {
                "fixed_errors": recovery_result.fixed_errors,
                "recovery_notes": recovery_result.recovery_notes,
                "remaining_errors": len(recovery_result.remaining_errors),
            }

        click.echo(json.dumps(output, indent=2))
    else:
        # Human-readable text output
        click.echo(f"📋 Saidata {_schema_version(file_path)} Schema Validation Report")
        click.echo(f"File: {file_path}")
        click.echo("")

        # Show validation features status
        features = []
        if validate_urls or True:  # Always enabled in 0.3
            features.append("URL Templates ✓")
        if validate_checksums or True:  # Always enabled in 0.3
            features.append("Checksums ✓")
        if auto_recover:
            features.append("Auto-Recovery ✓")

        if features:
            click.echo(f"Validation Features: {', '.join(features)}")
            click.echo("")

        report = validator.format_validation_report(result, show_context=show_context)
        click.echo(report)

    # Exit with appropriate code
    if result.has_errors:
        raise click.ClickException("Validation failed with errors")
    elif result.has_warnings:
        click.echo("\nValidation completed with warnings", err=True)


async def _run_advanced_validation(
    file_path: Path,
    schema: Optional[Path],
    show_context: bool,
    output_format: str,
    check_repository_accuracy: bool,
    detailed: bool,
    validate_urls: bool = False,
    validate_checksums: bool = False,
    auto_recover: bool = False,
) -> None:
    """Run advanced validation with quality metrics."""
    # Load saidata file
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Check if this is a supported saidata file
    version = data.get("version", "unknown")
    if version not in ("0.3", "0.4"):
        click.echo(
            f"⚠️  Warning: File version is '{version}', but validating against 0.3 schema", err=True
        )

    # Parse as SaiData model
    try:
        saidata = SaiData.model_validate(data)
    except Exception as e:
        raise click.ClickException(f"Failed to parse saidata: {e}")

    # Initialize repository manager if needed
    repository_manager = None
    if check_repository_accuracy:
        try:
            config = get_config()
            cache_dir = config.get("cache_dir", Path.home() / ".saigen" / "cache")
            config_dir = config.get(
                "repository_config_dir", Path.home() / ".saigen" / "repositories"
            )

            repository_manager = RepositoryManager(cache_dir, config_dir)
            await repository_manager.initialize()

            click.echo("🔍 Checking repository accuracy...", err=True)
        except Exception as e:
            click.echo(f"⚠️  Repository checking disabled: {e}", err=True)
            check_repository_accuracy = False

    # Create advanced validator with the selected schema
    base_validator = SaidataValidator(schema_path=schema)
    advanced_validator = AdvancedSaidataValidator(repository_manager, base_validator)

    # Apply auto-recovery if requested
    recovery_result = None
    if auto_recover:
        try:
            validation_result, recovery_result = base_validator.validate_with_recovery(
                data, str(file_path)
            )
            if recovery_result and recovery_result.fixed_errors:
                # Re-parse the recovered data
                saidata = SaiData.model_validate(recovery_result.recovered_data)
                if output_format == "text":
                    click.echo("🔧 Automatic Error Recovery Applied:")
                    recovery_report = base_validator.format_recovery_report(recovery_result)
                    click.echo(recovery_report)
                    click.echo("")
        except Exception as e:
            click.echo(f"⚠️  Auto-recovery failed: {e}", err=True)

    # Run comprehensive validation
    click.echo("🔍 Running advanced validation...", err=True)
    quality_report = await advanced_validator.validate_comprehensive(
        saidata, check_repository_accuracy
    )

    if output_format == "json":
        # JSON output for programmatic use
        import json

        output = {
            "file": str(file_path),
            "schema_version": _schema_version(file_path),
            "file_version": version,
            "overall_score": quality_report.overall_score,
            "valid": quality_report.validation_result.is_valid,
            "validation_features": {
                "url_templates": validate_urls or True,  # Always enabled in 0.3
                "checksums": validate_checksums or True,  # Always enabled in 0.3
                "auto_recovery": auto_recover,
                "repository_accuracy": check_repository_accuracy,
                "advanced_metrics": True,
            },
            "quality_metrics": {
                metric.value: {
                    "score": score.score,
                    "max_score": score.max_score,
                    "details": score.details,
                    "issues": score.issues,
                    "suggestions": score.suggestions,
                }
                for metric, score in quality_report.metric_scores.items()
            },
            "repository_accuracy": quality_report.repository_accuracy,
            "cross_reference_issues": [
                {
                    "severity": issue.severity,
                    "message": issue.message,
                    "path": issue.path,
                    "code": issue.code,
                    "suggestion": issue.suggestion,
                }
                for issue in quality_report.cross_reference_issues
            ],
            "recommendations": quality_report.recommendations,
            "validation_errors": [
                {
                    "severity": error.severity,
                    "message": error.message,
                    "path": error.path,
                    "code": error.code,
                    "suggestion": error.suggestion,
                    "context": error.context if show_context else None,
                }
                for error in quality_report.validation_result.errors
            ],
            "validation_warnings": [
                {
                    "severity": warning.severity,
                    "message": warning.message,
                    "path": warning.path,
                    "code": warning.code,
                    "suggestion": warning.suggestion,
                    "context": warning.context if show_context else None,
                }
                for warning in quality_report.validation_result.warnings
            ],
            "generated_at": quality_report.generated_at.isoformat(),
        }

        # Add recovery information if available
        if recovery_result and recovery_result.fixed_errors:
            output["recovery"] = {
                "fixed_errors": recovery_result.fixed_errors,
                "recovery_notes": recovery_result.recovery_notes,
                "remaining_errors": len(recovery_result.remaining_errors),
            }

        click.echo(json.dumps(output, indent=2))
    else:
        # Human-readable text output
        click.echo(f"📋 Advanced Saidata {_schema_version(file_path)} Schema Validation Report")
        click.echo(f"File: {file_path}")
        click.echo(f"File Version: {version}")
        click.echo("")

        # Show validation features status
        features = []
        if validate_urls or True:  # Always enabled in 0.3
            features.append("URL Templates ✓")
        if validate_checksums or True:  # Always enabled in 0.3
            features.append("Checksums ✓")
        if auto_recover:
            features.append("Auto-Recovery ✓")
        if check_repository_accuracy:
            features.append("Repository Accuracy ✓")
        features.append("Quality Metrics ✓")

        click.echo(f"Validation Features: {', '.join(features)}")
        click.echo("")

        report = advanced_validator.format_quality_report(quality_report, detailed=detailed)
        click.echo(report)

    # Clean up repository manager
    if repository_manager:
        await repository_manager.close()

    # Exit with appropriate code
    if quality_report.validation_result.has_errors:
        raise click.ClickException("Validation failed with errors")
    elif quality_report.overall_score < 0.6:
        click.echo(f"\n⚠️  Quality score is low: {quality_report.overall_score:.2f}/1.00", err=True)
    elif quality_report.validation_result.has_warnings:
        click.echo("\nValidation completed with warnings", err=True)


if __name__ == "__main__":
    validate()
