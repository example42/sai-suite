#!/bin/bash
# Example: Using saigen quality --format score in automation scripts
#
# This script demonstrates how to use the score format for:
# - CI/CD quality gates
# - Batch quality assessment
# - Quality tracking over time

set -e

# Configuration
THRESHOLD=0.7
SAIDATA_DIR="software"
REPORT_FILE="quality-report.csv"

echo "Saidata Quality Assessment"
echo "=========================="
echo ""

# Example 1: Simple quality gate
echo "Example 1: Quality Gate"
echo "-----------------------"
SCORE=$(saigen quality --format score --no-repository-check nginx.yaml)
echo "Quality score: $SCORE"

if (( $(echo "$SCORE >= $THRESHOLD" | bc -l) )); then
    echo "✓ Quality check PASSED"
else
    echo "✗ Quality check FAILED (threshold: $THRESHOLD)"
    exit 1
fi
echo ""

# Example 2: Batch assessment with CSV output
echo "Example 2: Batch Assessment"
echo "---------------------------"
echo "file,overall_score,completeness,metadata_richness,status" > "$REPORT_FILE"

for file in "$SAIDATA_DIR"/*/*.yaml; do
    if [ -f "$file" ]; then
        echo -n "Assessing $(basename "$file")... "
        
        # Get overall score
        OVERALL=$(saigen quality --format score --threshold 0.5 --no-repository-check "$file" 2>/dev/null || echo "0.000")
        
        # Get completeness score
        COMPLETENESS=$(saigen quality --format score --metric completeness --threshold 0.5 --no-repository-check "$file" 2>/dev/null || echo "0.000")
        
        # Get metadata richness score
        METADATA=$(saigen quality --format score --metric metadata_richness --threshold 0.5 --no-repository-check "$file" 2>/dev/null || echo "0.000")
        
        # Determine status
        if (( $(echo "$OVERALL >= $THRESHOLD" | bc -l) )); then
            STATUS="PASS"
        else
            STATUS="FAIL"
        fi
        
        echo "$file,$OVERALL,$COMPLETENESS,$METADATA,$STATUS" >> "$REPORT_FILE"
        echo "$STATUS ($OVERALL)"
    fi
done

echo "Report saved to: $REPORT_FILE"
echo ""

# Example 3: Quality tracking over time
echo "Example 3: Quality Tracking"
echo "---------------------------"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
HISTORY_FILE="quality-history.log"

for file in "$SAIDATA_DIR"/*/*.yaml; do
    if [ -f "$file" ]; then
        SCORE=$(saigen quality --format score --threshold 0.5 --no-repository-check "$file" 2>/dev/null || echo "0.000")
        echo "$TIMESTAMP,$(basename "$file"),$SCORE" >> "$HISTORY_FILE"
    fi
done

echo "Quality history updated: $HISTORY_FILE"
echo ""

# Example 4: Metric comparison
echo "Example 4: Metric Comparison"
echo "----------------------------"
FILE="nginx.yaml"

echo "Analyzing $FILE:"
echo "  Overall:              $(saigen quality --format score --threshold 0.5 --no-repository-check "$FILE" 2>/dev/null)"
echo "  Completeness:         $(saigen quality --format score --metric completeness --threshold 0.5 --no-repository-check "$FILE" 2>/dev/null)"
echo "  Metadata Richness:    $(saigen quality --format score --metric metadata_richness --threshold 0.5 --no-repository-check "$FILE" 2>/dev/null)"
echo "  Cross-Reference:      $(saigen quality --format score --metric cross_reference_integrity --threshold 0.5 --no-repository-check "$FILE" 2>/dev/null)"
echo "  Consistency:          $(saigen quality --format score --metric consistency --threshold 0.5 --no-repository-check "$FILE" 2>/dev/null)"
echo ""

echo "All examples completed successfully!"
