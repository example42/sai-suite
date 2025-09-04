"""Validate command for saigen CLI."""

from pathlib import Path
from typing import Optional

import click

from ...core.validator import SaidataValidator


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
def validate(
    file_path: Path,
    schema: Optional[Path] = None,
    show_context: bool = False,
    output_format: str = 'text'
) -> None:
    """Validate a saidata YAML file against the schema.
    
    This command validates saidata files for:
    - JSON schema compliance
    - Custom validation rules
    - Cross-reference consistency
    - Best practice recommendations
    
    Examples:
        saigen validate nginx.yaml
        saigen validate --schema custom-schema.json software.yaml
        saigen validate --show-context --format json software.yaml
    """
    try:
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
        
    except FileNotFoundError as e:
        raise click.ClickException(f"File not found: {e}")
    except Exception as e:
        raise click.ClickException(f"Validation error: {e}")


if __name__ == '__main__':
    validate()