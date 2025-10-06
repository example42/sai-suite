"""Quality assessment command for saigen CLI."""

import asyncio
from pathlib import Path
from typing import Optional

import click
import yaml

from ...core.advanced_validator import AdvancedSaidataValidator, QualityMetric
from ...core.validator import SaidataValidator
from ...models.saidata import SaiData
from ...repositories.manager import RepositoryManager
from ...utils.config import get_config


@click.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path), required=False)
@click.option(
    "--metric",
    type=click.Choice([m.value for m in QualityMetric]),
    help="Focus on a specific quality metric",
)
@click.option(
    "--threshold",
    type=float,
    default=0.7,
    help="Quality score threshold for pass/fail (default: 0.7)",
)
@click.option("--no-repository-check", is_flag=True, help="Skip repository accuracy checking")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "csv"]),
    default="text",
    help="Output format",
)
@click.option("--export", type=click.Path(path_type=Path), help="Export detailed report to file")
def quality(
    file_path: Path,
    metric: Optional[str] = None,
    threshold: float = 0.7,
    no_repository_check: bool = False,
    output_format: str = "text",
    export: Optional[Path] = None,
) -> None:
    """Assess quality metrics for a saidata file.

    This command provides comprehensive quality assessment including:

    • Completeness scoring
    • Metadata richness analysis
    • Cross-reference integrity checking
    • Repository alignment verification
    • Consistency validation
    • Overall accuracy assessment

    \b
    Examples:

    • Basic quality assessment\n
        saigen quality nginx.yaml

    • Focus on specific metric with custom threshold\n
        saigen quality --metric completeness --threshold 0.8 software.yaml

    • Export detailed report\n
        saigen quality --format json --export report.json software.yaml

    • Skip repository checks for faster assessment\n
        saigen quality --no-repository-check software.yaml
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
        asyncio.run(
            _run_quality_assessment(
                file_path, metric, threshold, not no_repository_check, output_format, export
            )
        )
    except Exception as e:
        raise click.ClickException(f"Quality assessment error: {e}")


async def _run_quality_assessment(
    file_path: Path,
    metric_filter: Optional[str],
    threshold: float,
    check_repository_accuracy: bool,
    output_format: str,
    export_path: Optional[Path],
) -> None:
    """Run quality assessment."""
    # Load saidata file
    with open(file_path, "r", encoding="utf-8") as f:
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
            cache_dir = config.get("cache_dir", Path.home() / ".saigen" / "cache")
            config_dir = config.get(
                "repository_config_dir", Path.home() / ".saigen" / "repositories"
            )

            repository_manager = RepositoryManager(cache_dir, config_dir)
            await repository_manager.initialize()

            click.echo("🔍 Initializing repository data...", err=True)
        except Exception as e:
            click.echo(f"⚠️  Repository checking disabled: {e}", err=True)
            check_repository_accuracy = False

    # Create advanced validator
    base_validator = SaidataValidator()
    advanced_validator = AdvancedSaidataValidator(repository_manager, base_validator)

    # Run quality assessment
    click.echo("📊 Assessing quality metrics...", err=True)
    quality_report = await advanced_validator.validate_comprehensive(
        saidata, check_repository_accuracy
    )

    # Filter by specific metric if requested
    if metric_filter:
        metric_enum = QualityMetric(metric_filter)
        if metric_enum not in quality_report.metric_scores:
            raise click.ClickException(f"Metric '{metric_filter}' not available in report")

        filtered_scores = {metric_enum: quality_report.metric_scores[metric_enum]}
        quality_report.metric_scores = filtered_scores

    # Generate output
    if output_format == "json":
        output = _format_json_output(quality_report, file_path, threshold)
        result_text = output
    elif output_format == "csv":
        output = _format_csv_output(quality_report, file_path)
        result_text = output
    else:
        output = _format_text_output(quality_report, file_path, threshold, metric_filter)
        result_text = output

    # Display output
    click.echo(result_text)

    # Export if requested
    if export_path:
        with open(export_path, "w", encoding="utf-8") as f:
            if output_format == "json":
                import json

                json.dump(json.loads(result_text), f, indent=2)
            else:
                f.write(result_text)
        click.echo(f"📄 Report exported to {export_path}", err=True)

    # Clean up
    if repository_manager:
        await repository_manager.close()

    # Exit with appropriate code based on threshold
    if quality_report.overall_score < threshold:
        raise click.ClickException(
            f"Quality score {quality_report.overall_score:.2f} below threshold {threshold}"
        )


def _format_json_output(quality_report, file_path: Path, threshold: float) -> str:
    """Format quality report as JSON."""
    import json

    output = {
        "file": str(file_path),
        "overall_score": quality_report.overall_score,
        "threshold": threshold,
        "passed": quality_report.overall_score >= threshold,
        "metrics": {
            metric.value: {
                "score": score.score,
                "max_score": score.max_score,
                "passed": score.score >= threshold,
                "details": score.details,
                "issues_count": len(score.issues),
                "suggestions_count": len(score.suggestions),
            }
            for metric, score in quality_report.metric_scores.items()
        },
        "repository_accuracy": quality_report.repository_accuracy,
        "recommendations_count": len(quality_report.recommendations),
        "cross_reference_issues_count": len(quality_report.cross_reference_issues),
        "assessment_time": quality_report.generated_at.isoformat(),
    }

    return json.dumps(output, indent=2)


def _format_csv_output(quality_report, file_path: Path) -> str:
    """Format quality report as CSV."""
    lines = []

    # Header
    lines.append("file,metric,score,max_score,issues,suggestions")

    # Overall score
    lines.append(
        f"{file_path},overall,{quality_report.overall_score:.3f},1.000,0,{len(quality_report.recommendations)}"
    )

    # Individual metrics
    for metric, score in quality_report.metric_scores.items():
        lines.append(
            f"{file_path},{metric.value},{score.score:.3f},{score.max_score:.3f},"
            f"{len(score.issues)},{len(score.suggestions)}"
        )

    return "\n".join(lines)


def _format_text_output(
    quality_report, file_path: Path, threshold: float, metric_filter: Optional[str]
) -> str:
    """Format quality report as human-readable text."""
    lines = []

    # Header
    lines.append("=" * 60)
    lines.append("SAIDATA QUALITY ASSESSMENT")
    lines.append("=" * 60)
    lines.append(f"File: {file_path}")
    lines.append(
        f"Assessment Time: {quality_report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    lines.append("")

    # Overall score (if not filtering by specific metric)
    if not metric_filter:
        score_emoji = "🟢" if quality_report.overall_score >= threshold else "🔴"
        status = "PASS" if quality_report.overall_score >= threshold else "FAIL"
        lines.append(
            f"Overall Quality Score: {score_emoji} {
                quality_report.overall_score:.3f}/1.000 ({status})")
        lines.append(f"Threshold: {threshold}")
        lines.append("")

    # Metric details
    if metric_filter:
        lines.append(f"Metric: {metric_filter.replace('_', ' ').title()}")
        lines.append("-" * 40)
    else:
        lines.append("Quality Metrics:")
        lines.append("-" * 40)

    for metric, score in quality_report.metric_scores.items():
        score_emoji = "🟢" if score.score >= threshold else "🔴"
        metric_name = metric.value.replace("_", " ").title()

        lines.append(f"{metric_name}:")
        lines.append(f"  Score: {score_emoji} {score.score:.3f}/{score.max_score:.3f}")

        # Show key details
        if score.details:
            important_details = []
            for key, value in score.details.items():
                if isinstance(value, (int, float)) and key.endswith("_score"):
                    important_details.append(f"{key.replace('_', ' ')}: {value:.2f}")
                elif isinstance(value, bool):
                    status = "✅" if value else "❌"
                    important_details.append(f"{key.replace('_', ' ')}: {status}")
                elif isinstance(value, int) and key.endswith("_count"):
                    important_details.append(f"{key.replace('_', ' ')}: {value}")

            if important_details:
                lines.append(f"  Details: {', '.join(important_details[:3])}")

        # Show top issues
        if score.issues:
            lines.append(f"  Issues ({len(score.issues)}):")
            for issue in score.issues[:2]:  # Show top 2 issues
                lines.append(f"    • {issue}")
            if len(score.issues) > 2:
                lines.append(f"    ... and {len(score.issues) - 2} more")

        # Show top suggestions
        if score.suggestions:
            lines.append(f"  Suggestions ({len(score.suggestions)}):")
            for suggestion in score.suggestions[:2]:  # Show top 2 suggestions
                lines.append(f"    • {suggestion}")
            if len(score.suggestions) > 2:
                lines.append(f"    ... and {len(score.suggestions) - 2} more")

        lines.append("")

    # Repository accuracy summary
    if quality_report.repository_accuracy and not metric_filter:
        lines.append("Repository Accuracy:")
        lines.append("-" * 40)
        for provider, accuracy in quality_report.repository_accuracy.items():
            accuracy_emoji = "🟢" if accuracy >= 0.8 else "🟡" if accuracy >= 0.6 else "🔴"
            lines.append(f"  {provider}: {accuracy_emoji} {accuracy:.3f}")
        lines.append("")

    # Top recommendations
    if quality_report.recommendations and not metric_filter:
        lines.append("Top Recommendations:")
        lines.append("-" * 40)
        for i, rec in enumerate(quality_report.recommendations[:5], 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

    # Summary
    if not metric_filter:
        lines.append("Summary:")
        lines.append("-" * 40)
        lines.append(
            f"Schema Validation: {
                '✅ PASSED' if not quality_report.validation_result.has_errors else '❌ FAILED'}")
        lines.append(
            f"Quality Threshold: {
                '✅ PASSED' if quality_report.overall_score >= threshold else '❌ FAILED'}")
        lines.append(f"Cross-Reference Issues: {len(quality_report.cross_reference_issues)}")
        lines.append(f"Total Recommendations: {len(quality_report.recommendations)}")

    return "\n".join(lines)


if __name__ == "__main__":
    quality()
