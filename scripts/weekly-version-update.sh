#!/usr/bin/env bash
#
# Weekly Version Update Script for SAI Suite
#
# This script updates/creates all versions for all software in the saidata directory
# using locally present repositories. Designed to run as a weekly cronjob.
#
# Usage:
#   ./weekly-version-update.sh [OPTIONS]
#
# Options:
#   --saidata-dir PATH    Path to saidata directory (default: ~/saidata)
#   --backup-dir PATH     Path to backup directory (default: ~/saidata-backups)
#   --log-dir PATH        Path to log directory (default: ~/logs/saidata-updates)
#   --skip-default        Skip default.yaml files
#   --no-cache            Don't use cached repository data
#   --dry-run             Check for updates without modifying files (uses --check-only)
#   --verbose             Enable verbose output
#   --help                Show this help message
#
# Cronjob Example (runs every Sunday at 2 AM):
#   0 2 * * 0 /path/to/weekly-version-update.sh --saidata-dir ~/saidata >> ~/logs/saidata-updates/cron.log 2>&1
#
# Note: --dry-run uses saigen's --check-only flag to check for updates without modifying files

set -euo pipefail

# Default configuration
SAIDATA_DIR="${HOME}/saidata"
BACKUP_DIR="${HOME}/saidata-backups"
LOG_DIR="${HOME}/logs/saidata-updates"
SKIP_DEFAULT=""
NO_CACHE=""
DRY_RUN=""
VERBOSE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --saidata-dir)
            SAIDATA_DIR="$2"
            shift 2
            ;;
        --backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --log-dir)
            LOG_DIR="$2"
            shift 2
            ;;
        --skip-default)
            SKIP_DEFAULT="--skip-default"
            shift
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --verbose)
            VERBOSE="--verbose"
            shift
            ;;
        --help)
            grep '^#' "$0" | grep -v '#!/usr/bin/env' | sed 's/^# //' | sed 's/^#//'
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate saidata directory exists
if [[ ! -d "$SAIDATA_DIR" ]]; then
    echo "Error: Saidata directory not found: $SAIDATA_DIR"
    echo "Use --saidata-dir to specify the correct path"
    exit 1
fi

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate timestamp for this run
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/update_${TIMESTAMP}.log"
SUMMARY_FILE="${LOG_DIR}/summary_${TIMESTAMP}.txt"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Function to log errors
log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a "$LOG_FILE" >&2
}

# Start logging
log "=========================================="
log "Weekly Version Update Started"
log "=========================================="
log "Saidata Directory: $SAIDATA_DIR"
log "Backup Directory: $BACKUP_DIR"
log "Log Directory: $LOG_DIR"
log "Skip Default: ${SKIP_DEFAULT:-no}"
log "Use Cache: ${NO_CACHE:-yes}"
log "Dry Run: ${DRY_RUN:-no}"
log "Verbose: ${VERBOSE:-no}"
log ""

# Check if saigen is available
if ! command -v saigen &> /dev/null; then
    log_error "saigen command not found. Please install saigen first."
    exit 1
fi

# Get saigen version
SAIGEN_VERSION=$(saigen --version 2>&1 || echo "unknown")
log "Saigen Version: $SAIGEN_VERSION"
log ""

# Initialize counters
TOTAL_DIRS=0
PROCESSED_DIRS=0
FAILED_DIRS=0
SKIPPED_DIRS=0

# Find all software directories (directories containing default.yaml or OS-specific yaml files)
log "Scanning for software directories..."
SOFTWARE_DIRS=()

# Find directories that contain .yaml files with saidata structure
while IFS= read -r -d '' yaml_file; do
    # Get the directory containing this yaml file
    dir=$(dirname "$yaml_file")
    
    # Check if this directory is already in our list
    if [[ ${#SOFTWARE_DIRS[@]} -eq 0 ]] || [[ ! " ${SOFTWARE_DIRS[@]} " =~ " ${dir} " ]]; then
        # Verify it's a saidata file by checking for version and metadata fields
        if grep -q "^version:" "$yaml_file" && grep -q "^metadata:" "$yaml_file"; then
            SOFTWARE_DIRS+=("$dir")
        fi
    fi
done < <(find "$SAIDATA_DIR" -type f -name "*.yaml" -print0)

TOTAL_DIRS=${#SOFTWARE_DIRS[@]}
log "Found $TOTAL_DIRS software directories to process"
log ""

# Check if any directories were found
if [[ $TOTAL_DIRS -eq 0 ]]; then
    log "No software directories found in $SAIDATA_DIR"
    log "Make sure your saidata files have 'version:' and 'metadata:' fields"
    exit 0
fi

# Process each software directory
for software_dir in "${SOFTWARE_DIRS[@]}"; do
    SOFTWARE_NAME=$(basename "$software_dir")
    RELATIVE_PATH="${software_dir#$SAIDATA_DIR/}"
    
    log "----------------------------------------"
    log "Processing: $RELATIVE_PATH"
    log "----------------------------------------"
    
    # Create backup subdirectory for this software
    SOFTWARE_BACKUP_DIR="${BACKUP_DIR}/${TIMESTAMP}/${RELATIVE_PATH}"
    mkdir -p "$SOFTWARE_BACKUP_DIR"
    
    # Run saigen refresh-versions for this directory
    REFRESH_CMD="saigen"
    
    # Add global options (before command)
    [[ -n "$VERBOSE" ]] && REFRESH_CMD="$REFRESH_CMD $VERBOSE"
    
    # Add the command
    REFRESH_CMD="$REFRESH_CMD refresh-versions"
    
    # Add command-specific options
    [[ -n "$DRY_RUN" ]] && REFRESH_CMD="$REFRESH_CMD --check-only"
    [[ -n "$SKIP_DEFAULT" ]] && REFRESH_CMD="$REFRESH_CMD $SKIP_DEFAULT"
    [[ -n "$NO_CACHE" ]] && REFRESH_CMD="$REFRESH_CMD $NO_CACHE"
    
    # Add directory-specific options
    REFRESH_CMD="$REFRESH_CMD --all-variants --backup-dir $SOFTWARE_BACKUP_DIR"
    
    # Add the directory path
    REFRESH_CMD="$REFRESH_CMD $software_dir"
    
    log "Command: $REFRESH_CMD"
    
    # Execute the command
    if eval "$REFRESH_CMD" >> "$LOG_FILE" 2>&1; then
        log "✓ Successfully processed $RELATIVE_PATH"
        ((PROCESSED_DIRS++))
    else
        EXIT_CODE=$?
        if [[ $EXIT_CODE -eq 0 ]]; then
            # Command succeeded but returned 0 (e.g., no updates needed)
            log "✓ Processed $RELATIVE_PATH (no updates needed)"
            ((PROCESSED_DIRS++))
        else
            log_error "Failed to process $RELATIVE_PATH (exit code: $EXIT_CODE)"
            ((FAILED_DIRS++))
        fi
    fi
    
    log ""
done

# Generate summary
log "=========================================="
log "Weekly Version Update Completed"
log "=========================================="
log "Total Directories: $TOTAL_DIRS"
log "Successfully Processed: $PROCESSED_DIRS"
log "Failed: $FAILED_DIRS"
log "Skipped: $SKIPPED_DIRS"
log ""
log "Log File: $LOG_FILE"
log "Backup Directory: ${BACKUP_DIR}/${TIMESTAMP}"
log ""

# Create summary file
cat > "$SUMMARY_FILE" << EOF
Weekly Version Update Summary
========================================
Date: $(date '+%Y-%m-%d %H:%M:%S')
Saidata Directory: $SAIDATA_DIR

Results:
--------
Total Directories: $TOTAL_DIRS
Successfully Processed: $PROCESSED_DIRS
Failed: $FAILED_DIRS
Skipped: $SKIPPED_DIRS

Details:
--------
Log File: $LOG_FILE
Backup Directory: ${BACKUP_DIR}/${TIMESTAMP}

Configuration:
--------------
Skip Default: ${SKIP_DEFAULT:-no}
Use Cache: ${NO_CACHE:-yes}
Dry Run: ${DRY_RUN:-no}
Verbose: ${VERBOSE:-no}
EOF

log "Summary saved to: $SUMMARY_FILE"

# Exit with appropriate code
if [[ $FAILED_DIRS -gt 0 ]]; then
    log "⚠ Some directories failed to process"
    exit 1
else
    log "✓ All directories processed successfully"
    exit 0
fi
