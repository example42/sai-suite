# Quality Score Format Examples

This directory contains examples demonstrating the `--format score` option for the `saigen quality` command.

## Overview

The `--format score` option returns just the numeric quality score (0.000-1.000) without any additional text, making it ideal for:

- CI/CD quality gates
- Automated testing pipelines
- Batch quality assessment
- Quality tracking over time
- Scripting and automation

## Basic Usage

```bash
# Get overall quality score
saigen quality --format score nginx.yaml

# Get specific metric score
saigen quality --format score --metric completeness nginx.yaml

# Use in quality gate
SCORE=$(saigen quality --format score --threshold 0.7 nginx.yaml)
if (( $(echo "$SCORE >= 0.7" | bc -l) )); then
    echo "Quality check passed"
fi
```

## Output Format

The score format returns a single line with a three-decimal number:

```
0.596
```

No progress messages, no additional text - just the score.

## Available Metrics

When using `--metric`, you can focus on specific quality aspects:

- `completeness` - Required and important fields presence
- `metadata_richness` - Depth and quality of metadata
- `cross_reference_integrity` - Internal consistency
- `repository_alignment` - Alignment with repository data
- `consistency` - Naming and structure consistency

## Examples

### Example 1: CI/CD Quality Gate

```bash
#!/bin/bash
SCORE=$(saigen quality --format score --no-repository-check nginx.yaml)
if (( $(echo "$SCORE >= 0.7" | bc -l) )); then
    echo "✓ Quality check passed: $SCORE"
    exit 0
else
    echo "✗ Quality check failed: $SCORE (threshold: 0.7)"
    exit 1
fi
```

### Example 2: Batch Assessment

```bash
#!/bin/bash
echo "file,score" > quality-report.csv
for file in software/*/*.yaml; do
    SCORE=$(saigen quality --format score --threshold 0.5 --no-repository-check "$file" 2>/dev/null || echo "0.000")
    echo "$file,$SCORE" >> quality-report.csv
done
```

### Example 3: Quality Tracking

```bash
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
for file in software/*/*.yaml; do
    SCORE=$(saigen quality --format score --threshold 0.5 --no-repository-check "$file" 2>/dev/null)
    echo "$TIMESTAMP,$file,$SCORE" >> quality-history.log
done
```

### Example 4: Metric Comparison

```bash
#!/bin/bash
FILE="nginx.yaml"
echo "Quality Metrics for $FILE:"
echo "  Overall:       $(saigen quality --format score --threshold 0.5 --no-repository-check "$FILE")"
echo "  Completeness:  $(saigen quality --format score --metric completeness --threshold 0.5 --no-repository-check "$FILE")"
echo "  Metadata:      $(saigen quality --format score --metric metadata_richness --threshold 0.5 --no-repository-check "$FILE")"
```

## Complete Example Script

See [quality-score-automation.sh](quality-score-automation.sh) for a comprehensive example demonstrating:

- Quality gates
- Batch assessment with CSV output
- Quality tracking over time
- Metric comparison

## Tips

1. **Use `--no-repository-check`** for faster assessment when repository accuracy isn't needed
2. **Set appropriate thresholds** with `--threshold` to control pass/fail behavior
3. **Combine with other tools** like `bc` for numeric comparisons in bash
4. **Redirect stderr** (`2>/dev/null`) to suppress any error messages if needed
5. **Use in parallel** with tools like `xargs` or GNU parallel for large batches

## See Also

- [CLI Reference](../cli-reference.md) - Complete command documentation
- [Quality Assessment Guide](../quality-assessment.md) - Detailed quality metrics explanation
