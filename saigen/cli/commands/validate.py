"""Validate command for saigen CLI."""

import asyncio
from pathlib import Path
from typing import Optional

import click
import yaml

from ...core.validator import SaidataValidator
from ...core.advanced_validator import AdvancedSaidataValidator
from ...models.saidata import SaiData
from ...repositories.manager import RepositoryManager
from ...utils.config import get_config


@click.command()
@click.argument('file_path', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--schema', 
    type=click.Path(exists=True, path_type=Path),
    help='Path to custom saidata schema file'
)
@click.option(
    '--show-context',
    is_flag=True,
    help='Show detailed context information for errors'
)
@click.option(
    '--format',
    'output_format',
    type=click.Choice(['text', 'json']),
    default='text',
    help='Output format for validation results'
)
@click.option(
    '--advanced',
    is_flag=True,
    help='Enable advanced validation with quality metrics and repository accuracy checking'
)
@click.option(
    '--no-repository-check',
    is_flag=True,
    help='Skip repository accuracy checking (faster but less comprehensive)'
)
@click.option(
    '--detailed',
    is_flag=True,
    help='Show detailed quality metrics and suggestions'
)
def validate(
    file_path: Path,
    schema: Optional[Path] = None,
    show_context: bool = False,
    output_format: str = 'text',
    advanced: bool = False,
    no_repository_check: bool = False,
    detailed: bool = False
) -> None:
    """Validate a saidata YAML file against the schema.
    
    This command validates saidata files for:
    - JSON schema compliance
    - Custom validation rules
    - Cross-reference consistency
    - Best practice recommendations
    - Quality metrics (with --advanced)
    - Repository accuracy checking (with --advanced)
    
    Examples:
        saigen validate nginx.yaml
        saigen validate --advanced --detailed nginx.yaml
        saigen validate --schema custom-schema.json software.yaml
        saigen validate --show-context --format json software.yaml
        saigen validate --advanced --no-repository-check software.yaml
    """
    try:
        if advanced:
            # Use advanced validation with quality metrics
            asyncio.run(_run_advanced_validation(
                file_path, schema, show_context, output_format, 
                not no_repository_check, detailed
            ))
        else:
            # Use basic validation
            _run_basic_validation(file_path, schema, show_context, output_format)
        
    except FileNotFoundError as e:
        raise click.ClickException(f"File not found: {e}")
    except Exception as e:
        raise click.ClickException(f"Validation error: {e}")


def _run_basic_validation(
    file_path: Path,
    schema: Optional[Path],
    show_context: bool,
    output_format: str
) -> None:
    """Run basic schema validation."""
    # Create validator with optional custom schema
    validator = SaidataValidator(schema_path=schema)
    
    # Validate the file
    result = validator.validate_file(file_path)
    
    if output_format == 'json':
        # JSON output for programmatic use
        import json
        output = {
            'file': str(file_path),
            'valid': result.is_valid,
            'total_issues': result.total_issues,
            'errors': [
                {
                    'severity': error.severity,
                    'message': error.message,
                    'path': error.path,
                    'code': error.code,
                    'suggestion': error.suggestion,
                    'context': error.context if show_context else None
                }
                for error in result.errors
            ],
            'warnings': [
                {
                    'severity': warning.severity,
                    'message': warning.message,
                    'path': warning.path,
                    'code': warning.code,
                    'suggestion': warning.suggestion,
                    'context': warning.context if show_context else None
                }
                for warning in result.warnings
            ],
            'info': [
                {
                    'severity': info.severity,
                    'message': info.message,
                    'path': info.path,
                    'code': info.code,
                    'suggestion': info.suggestion,
                    'context': info.context if show_context else None
                }
                for info in result.info
            ]
        }
        click.echo(json.dumps(output, indent=2))
    else:
        # Human-readable text output
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
    detailed: bool
) -> None:
    """Run advanced validation with quality metrics."""
    # Load saidata file
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
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
            cache_dir = config.get('cache_dir', Path.home() / '.saigen' / 'cache')
            config_dir = config.get('repository_config_dir', Path.home() / '.saigen' / 'repositories')
            
            repository_manager = RepositoryManager(cache_dir, config_dir)
            await repository_manager.initialize()
            
            click.echo("🔍 Checking repository accuracy...", err=True)
        except Exception as e:
            click.echo(f"⚠️  Repository checking disabled: {e}", err=True)
            check_repository_accuracy = False
    
    # Create advanced validator
    base_validator = SaidataValidator(schema_path=schema)
    advanced_validator = AdvancedSaidataValidator(repository_manager, base_validator)
    
    # Run comprehensive validation
    click.echo("🔍 Running advanced validation...", err=True)
    quality_report = await advanced_validator.validate_comprehensive(
        saidata, check_repository_accuracy
    )
    
    if output_format == 'json':
        # JSON output for programmatic use
        import json
        output = {
            'file': str(file_path),
            'overall_score': quality_report.overall_score,
            'valid': quality_report.validation_result.is_valid,
            'quality_metrics': {
                metric.value: {
                    'score': score.score,
                    'max_score': score.max_score,
                    'details': score.details,
                    'issues': score.issues,
                    'suggestions': score.suggestions
                }
                for metric, score in quality_report.metric_scores.items()
            },
            'repository_accuracy': quality_report.repository_accuracy,
            'cross_reference_issues': [
                {
                    'severity': issue.severity,
                    'message': issue.message,
                    'path': issue.path,
                    'code': issue.code,
                    'suggestion': issue.suggestion
                }
                for issue in quality_report.cross_reference_issues
            ],
            'recommendations': quality_report.recommendations,
            'validation_errors': [
                {
                    'severity': error.severity,
                    'message': error.message,
                    'path': error.path,
                    'code': error.code,
                    'suggestion': error.suggestion,
                    'context': error.context if show_context else None
                }
                for error in quality_report.validation_result.errors
            ],
            'validation_warnings': [
                {
                    'severity': warning.severity,
                    'message': warning.message,
                    'path': warning.path,
                    'code': warning.code,
                    'suggestion': warning.suggestion,
                    'context': warning.context if show_context else None
                }
                for warning in quality_report.validation_result.warnings
            ],
            'generated_at': quality_report.generated_at.isoformat()
        }
        click.echo(json.dumps(output, indent=2))
    else:
        # Human-readable text output
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


if __name__ == '__main__':
    validate()