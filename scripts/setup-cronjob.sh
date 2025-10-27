#!/usr/bin/env bash
#
# Setup Cronjob for Weekly Version Updates
#
# This script helps set up a cronjob for automated version updates.
# It provides interactive configuration and validates the setup.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "Weekly Version Update Cronjob Setup"
echo "=========================================="
echo ""

# Check if saigen is available
if ! command -v saigen &> /dev/null; then
    print_error "saigen command not found"
    echo ""
    echo "Please install saigen first:"
    echo "  pip install saigen"
    echo "  # or"
    echo "  cd $PROJECT_ROOT && pip install -e ."
    exit 1
fi

print_success "saigen is installed: $(which saigen)"
echo ""

# Choose script type
echo "Which script would you like to use?"
echo "  1) Bash script (weekly-version-update.sh)"
echo "  2) Python script (weekly_version_update.py) - Recommended"
echo ""
read -p "Enter choice [1-2]: " script_choice

case $script_choice in
    1)
        SCRIPT_PATH="$SCRIPT_DIR/weekly-version-update.sh"
        SCRIPT_TYPE="bash"
        ;;
    2)
        SCRIPT_PATH="$SCRIPT_DIR/weekly_version_update.py"
        SCRIPT_TYPE="python"
        ;;
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

if [[ ! -f "$SCRIPT_PATH" ]]; then
    print_error "Script not found: $SCRIPT_PATH"
    exit 1
fi

if [[ ! -x "$SCRIPT_PATH" ]]; then
    print_warning "Script is not executable, making it executable..."
    chmod +x "$SCRIPT_PATH"
fi

print_success "Using script: $SCRIPT_PATH"
echo ""

# Configure paths
echo "Configure Paths"
echo "---------------"

read -p "Saidata directory [~/saidata]: " saidata_dir
saidata_dir=${saidata_dir:-~/saidata}
saidata_dir="${saidata_dir/#\~/$HOME}"

read -p "Backup directory [~/saidata-backups]: " backup_dir
backup_dir=${backup_dir:-~/saidata-backups}
backup_dir="${backup_dir/#\~/$HOME}"

read -p "Log directory [~/logs/saidata-updates]: " log_dir
log_dir=${log_dir:-~/logs/saidata-updates}
log_dir="${log_dir/#\~/$HOME}"

echo ""

# Validate saidata directory
if [[ ! -d "$saidata_dir" ]]; then
    print_warning "Saidata directory does not exist: $saidata_dir"
    read -p "Create it? [y/N]: " create_dir
    if [[ "$create_dir" =~ ^[Yy]$ ]]; then
        mkdir -p "$saidata_dir"
        print_success "Created directory: $saidata_dir"
    else
        print_error "Cannot proceed without saidata directory"
        exit 1
    fi
fi

# Create other directories
mkdir -p "$backup_dir"
mkdir -p "$log_dir"

print_success "Directories configured:"
echo "  Saidata: $saidata_dir"
echo "  Backup: $backup_dir"
echo "  Logs: $log_dir"
echo ""

# Configure schedule
echo "Configure Schedule"
echo "------------------"
echo "Choose a schedule:"
echo "  1) Weekly (Sunday at 2 AM)"
echo "  2) Daily (Every day at 3 AM)"
echo "  3) Monthly (First day of month at 1 AM)"
echo "  4) Custom"
echo ""
read -p "Enter choice [1-4]: " schedule_choice

case $schedule_choice in
    1)
        CRON_SCHEDULE="0 2 * * 0"
        SCHEDULE_DESC="Weekly (Sunday at 2 AM)"
        ;;
    2)
        CRON_SCHEDULE="0 3 * * *"
        SCHEDULE_DESC="Daily (Every day at 3 AM)"
        ;;
    3)
        CRON_SCHEDULE="0 1 1 * *"
        SCHEDULE_DESC="Monthly (First day of month at 1 AM)"
        ;;
    4)
        echo ""
        echo "Enter cron schedule (e.g., '0 2 * * 0' for Sunday at 2 AM)"
        read -p "Cron schedule: " CRON_SCHEDULE
        SCHEDULE_DESC="Custom: $CRON_SCHEDULE"
        ;;
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

print_success "Schedule: $SCHEDULE_DESC"
echo ""

# Configure options
echo "Configure Options"
echo "-----------------"

read -p "Skip default.yaml files? [y/N]: " skip_default
skip_default_flag=""
if [[ "$skip_default" =~ ^[Yy]$ ]]; then
    skip_default_flag="--skip-default"
fi

read -p "Use cached repository data? [Y/n]: " use_cache
no_cache_flag=""
if [[ "$use_cache" =~ ^[Nn]$ ]]; then
    no_cache_flag="--no-cache"
fi

read -p "Enable verbose output? [y/N]: " verbose
verbose_flag=""
if [[ "$verbose" =~ ^[Yy]$ ]]; then
    verbose_flag="--verbose"
fi

# Build command
CRON_COMMAND="$SCRIPT_PATH --saidata-dir $saidata_dir --backup-dir $backup_dir --log-dir $log_dir"

if [[ -n "$skip_default_flag" ]]; then
    CRON_COMMAND="$CRON_COMMAND $skip_default_flag"
fi

if [[ -n "$no_cache_flag" ]]; then
    CRON_COMMAND="$CRON_COMMAND $no_cache_flag"
fi

if [[ -n "$verbose_flag" ]]; then
    CRON_COMMAND="$CRON_COMMAND $verbose_flag"
fi

# Add output redirection
CRON_LOG="$log_dir/cron.log"
CRON_COMMAND="$CRON_COMMAND >> $CRON_LOG 2>&1"

# Full cron entry
CRON_ENTRY="$CRON_SCHEDULE $CRON_COMMAND"

echo ""
echo "=========================================="
echo "Cronjob Configuration"
echo "=========================================="
echo ""
echo "Schedule: $SCHEDULE_DESC"
echo "Command: $CRON_COMMAND"
echo ""
echo "Full cron entry:"
echo "$CRON_ENTRY"
echo ""

# Test run
read -p "Would you like to test the script first? [Y/n]: " test_run
if [[ ! "$test_run" =~ ^[Nn]$ ]]; then
    print_info "Running test with --dry-run..."
    echo ""
    
    TEST_COMMAND="$SCRIPT_PATH --saidata-dir $saidata_dir --backup-dir $backup_dir --log-dir $log_dir --dry-run"
    
    if [[ -n "$skip_default_flag" ]]; then
        TEST_COMMAND="$TEST_COMMAND $skip_default_flag"
    fi
    
    if [[ -n "$no_cache_flag" ]]; then
        TEST_COMMAND="$TEST_COMMAND $no_cache_flag"
    fi
    
    TEST_COMMAND="$TEST_COMMAND --verbose"
    
    if eval "$TEST_COMMAND"; then
        print_success "Test run completed successfully"
    else
        print_error "Test run failed"
        echo ""
        read -p "Continue with cronjob setup anyway? [y/N]: " continue_anyway
        if [[ ! "$continue_anyway" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    echo ""
fi

# Install cronjob
read -p "Install cronjob? [Y/n]: " install_cron
if [[ "$install_cron" =~ ^[Nn]$ ]]; then
    print_info "Cronjob not installed"
    echo ""
    echo "To install manually, add this line to your crontab:"
    echo "$CRON_ENTRY"
    echo ""
    echo "Run: crontab -e"
    exit 0
fi

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -q "weekly-version-update\|weekly_version_update"; then
    print_warning "Existing version update cronjob found"
    read -p "Replace it? [y/N]: " replace_cron
    if [[ "$replace_cron" =~ ^[Yy]$ ]]; then
        # Remove existing entries
        crontab -l 2>/dev/null | grep -v "weekly-version-update\|weekly_version_update" | crontab -
        print_success "Removed existing cronjob"
    else
        print_info "Keeping existing cronjob, not adding new one"
        exit 0
    fi
fi

# Add new cron entry
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

print_success "Cronjob installed successfully!"
echo ""
echo "=========================================="
echo "Setup Complete"
echo "=========================================="
echo ""
echo "Your cronjob has been configured:"
echo "  Schedule: $SCHEDULE_DESC"
echo "  Script: $SCRIPT_PATH"
echo "  Logs: $CRON_LOG"
echo ""
echo "To view your crontab:"
echo "  crontab -l"
echo ""
echo "To edit your crontab:"
echo "  crontab -e"
echo ""
echo "To remove the cronjob:"
echo "  crontab -e"
echo "  # Then delete the line containing 'weekly-version-update' or 'weekly_version_update'"
echo ""
print_success "All done!"
