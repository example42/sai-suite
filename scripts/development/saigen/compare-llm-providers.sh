#!/usr/bin/env bash
#
# Compare saidata generation quality across different LLM providers
# Usage: ./compare-llm-providers.sh <software-list-file>
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_BASE_DIR="${OUTPUT_BASE_DIR:-./llm-comparison-$(date +%Y%m%d-%H%M%S)}"
REPORT_FILE="${OUTPUT_BASE_DIR}/comparison-report.md"

# LLM providers to compare
PROVIDERS=("openai" ollama_gptoss "anthropic" "ollama_deepseek70b")
#PROVIDERS=("ollama_qwen3" "ollama_devstral" "ollama_deepseek8b" "ollama_deepseek70b" "ollama_phi3" "ollama_gptoss")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v saigen &> /dev/null; then
        log_error "saigen command not found. Please install saigen first."
        exit 1
    fi
    
    if [ $# -eq 0 ]; then
        log_error "Usage: $0 <software-list-file>"
        exit 1
    fi
    
    local software_list="$1"
    if [ ! -f "$software_list" ]; then
        log_error "Software list file not found: $software_list"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Create output directories
setup_directories() {
    log_info "Setting up output directories..."
    
    mkdir -p "$OUTPUT_BASE_DIR"
    for provider in "${PROVIDERS[@]}"; do
        mkdir -p "${OUTPUT_BASE_DIR}/${provider}"
    done
    
    log_success "Directories created at: $OUTPUT_BASE_DIR"
}

# Generate saidata for a provider
generate_for_provider() {
    local provider="$1"
    local software_list="$2"
    local output_dir="${OUTPUT_BASE_DIR}/${provider}"
    
    log_info "Generating saidata using ${provider}..."
    
    # Track start time
    local start_time=$(date +%s)
    
    # Run batch generation with --llm-provider option
    local result=0
    if saigen --llm-provider "$provider" batch \
        --input-file "$software_list" \
        --output-dir "$output_dir" \
        --force; then
        log_success "Generation completed for ${provider}"
        result=0
    else
        log_error "Generation failed for ${provider}"
        result=1
    fi
    
    # Track end time and calculate duration
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Save timing info
    echo "$duration" > "${output_dir}/.timing"
    
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    log_info "Time spent: ${minutes}m ${seconds}s"
    
    return $result
}

# Run quality assessment for a provider
assess_quality() {
    local provider="$1"
    local output_dir="${OUTPUT_BASE_DIR}/${provider}"
    
    log_info "Assessing quality for ${provider}..."
    
    # Quality command works on individual files, so we'll process each
    local quality_summary="${output_dir}/quality-summary.txt"
    > "$quality_summary"  # Clear file
    
    local total_score=0
    local file_count=0
    
    # Find all YAML files recursively (they're in subdirs like ng/nginx/default.yaml)
    while IFS= read -r yaml_file; do
        if [ -f "$yaml_file" ]; then
            # Extract software name from path (e.g., ng/nginx/default.yaml -> nginx)
            local software_name=$(basename "$(dirname "$yaml_file")")
            log_info "  Assessing ${software_name}..."
            
            local quality_output=$(saigen quality "$yaml_file" --format score --threshold 0.1 2>&1 || true)
            echo "=== ${software_name} ===" >> "$quality_summary"
            echo "$quality_output" >> "$quality_summary"
            echo "" >> "$quality_summary"
            
            # Try to extract score (this is approximate)
            local score=$(echo "$quality_output" | grep -i "score\|quality" | head -1 | grep -oE '[0-9]+(\.[0-9]+)?' | head -1 || echo "0")
            if [ -n "$score" ] && [ "$score" != "0" ]; then
                total_score=$(echo "$total_score + $score" | bc -l 2>/dev/null || echo "$total_score")
                file_count=$((file_count + 1))
            fi
        fi
    done < <(find "$output_dir" -name "*.yaml" -type f)
    
    if [ $file_count -gt 0 ]; then
        local avg_score=$(echo "scale=2; $total_score / $file_count" | bc -l 2>/dev/null || echo "0")
        echo "=== SUMMARY ===" >> "$quality_summary"
        echo "Average Score: ${avg_score}" >> "$quality_summary"
        echo "Files Assessed: ${file_count}" >> "$quality_summary"
        log_success "Quality assessment completed for ${provider} (avg: ${avg_score})"
    else
        log_warning "No files to assess for ${provider}"
    fi
    
    echo "$quality_summary"
    return 0
}

# Get quality info for a software from summary file
get_quality_info() {
    local quality_file="$1"
    local software="$2"
    
    if [ ! -f "$quality_file" ]; then
        echo "N/A"
        return
    fi
    
    # Extract quality score for specific software (it's on the line after the === software === line)
    local score=$(grep -A 1 "^=== ${software} ===" "$quality_file" | tail -1 | grep -oE '[0-9]+\.[0-9]+' || echo "")
    
    if [ -n "$score" ]; then
        echo "$score"
    else
        echo "N/A"
    fi
}

# Generate comparison report
generate_report() {
    local software_list="$1"
    
    log_info "Generating comparison report..."
    
    cat > "$REPORT_FILE" << 'EOF'
# LLM Provider Comparison Report

This report compares saidata generation quality across different LLM providers.

## Summary

EOF
    
    echo "| Provider | Status | Time Spent | Quality File |" >> "$REPORT_FILE"
    echo "|----------|--------|------------|--------------|" >> "$REPORT_FILE"
    
    for provider in "${PROVIDERS[@]}"; do
        local quality_file="${OUTPUT_BASE_DIR}/${provider}/quality-summary.txt"
        local timing_file="${OUTPUT_BASE_DIR}/${provider}/.timing"
        local time_display="N/A"
        
        if [ -f "$timing_file" ]; then
            local duration=$(cat "$timing_file")
            local minutes=$((duration / 60))
            local seconds=$((duration % 60))
            time_display="${minutes}m ${seconds}s"
        fi
        
        if [ -f "$quality_file" ]; then
            echo "| ${provider} | ✅ Success | ${time_display} | \`${provider}/quality-summary.txt\` |" >> "$REPORT_FILE"
        else
            echo "| ${provider} | ❌ Failed | ${time_display} | N/A |" >> "$REPORT_FILE"
        fi
    done
    
    echo "" >> "$REPORT_FILE"
    echo "## Software-by-Software Comparison" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    # Read software list and compare each
    while IFS= read -r software || [ -n "$software" ]; do
        # Skip empty lines and comments
        [[ -z "$software" || "$software" =~ ^[[:space:]]*# ]] && continue
        
        echo "### ${software}" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        echo "| Provider | Quality Score | Generated File |" >> "$REPORT_FILE"
        echo "|----------|---------------|----------------|" >> "$REPORT_FILE"
        
        local files_generated=0
        
        for provider in "${PROVIDERS[@]}"; do
            local quality_file="${OUTPUT_BASE_DIR}/${provider}/quality-summary.txt"
            local quality_info=$(get_quality_info "$quality_file" "$software")
            
            # Find the saidata file (it's in a subdir structure like ng/nginx/default.yaml)
            local saidata_file=$(find "${OUTPUT_BASE_DIR}/${provider}" -type f -path "*/${software}/default.yaml" 2>/dev/null | head -1)
            
            if [ -n "$saidata_file" ] && [ -f "$saidata_file" ]; then
                echo "| ${provider} | ${quality_info} | ✅ |" >> "$REPORT_FILE"
                files_generated=$((files_generated + 1))
            else
                echo "| ${provider} | N/A | ❌ |" >> "$REPORT_FILE"
            fi
        done
        
        if [ $files_generated -gt 0 ]; then
            echo "" >> "$REPORT_FILE"
            echo "_Review quality summaries in each provider directory for detailed comparison._" >> "$REPORT_FILE"
        fi
        echo "" >> "$REPORT_FILE"
        
    done < "$software_list"
    
    # Add generation details
    cat >> "$REPORT_FILE" << EOF

## Generation Details

- **Date:** $(date)
- **Software List:** ${software_list}
- **Output Directory:** ${OUTPUT_BASE_DIR}
- **Providers Tested:** ${PROVIDERS[*]}

## Files Generated

EOF
    
    for provider in "${PROVIDERS[@]}"; do
        echo "### ${provider}" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        ls -1 "${OUTPUT_BASE_DIR}/${provider}/" 2>/dev/null || echo "No files generated"
        echo '```' >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    done
    
    log_success "Report generated: $REPORT_FILE"
}

# Main execution
main() {
    local software_list="$1"
    
    echo "========================================="
    echo "  LLM Provider Comparison Tool"
    echo "========================================="
    echo ""
    
    check_prerequisites "$@"
    setup_directories
    
    # Generate saidata for each provider
    for provider in "${PROVIDERS[@]}"; do
        echo ""
        echo "========================================="
        echo "  Processing: ${provider}"
        echo "========================================="
        generate_for_provider "$provider" "$software_list" || true
    done
    
    # Assess quality for each provider
    echo ""
    echo "========================================="
    echo "  Quality Assessment"
    echo "========================================="
    for provider in "${PROVIDERS[@]}"; do
        assess_quality "$provider" || true
    done
    
    # Generate comparison report
    echo ""
    echo "========================================="
    echo "  Generating Report"
    echo "========================================="
    generate_report "$software_list"
    
    echo ""
    log_success "Comparison complete!"
    log_info "Results saved to: $OUTPUT_BASE_DIR"
    log_info "Report available at: $REPORT_FILE"
    echo ""
    echo "To view the report:"
    echo "  cat $REPORT_FILE"
}

# Run main function
main "$@"
