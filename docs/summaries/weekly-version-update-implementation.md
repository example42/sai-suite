# Weekly Version Update Implementation Summary

**Date:** October 22, 2025  
**Purpose:** Automated cronjob system for updating package versions across all saidata files

## Overview

Implemented a comprehensive solution for automated weekly updates of package versions in saidata files using locally present repositories. The system includes both bash and Python implementations, interactive setup, and extensive documentation.

## Components Created

### 1. Bash Script (`scripts/weekly-version-update.sh`)

**Purpose:** Lightweight shell script for automated version updates

**Features:**
- Automatic discovery of saidata directories
- Batch processing of all software configurations
- Timestamped backups and logging
- Comprehensive error handling
- Dry-run mode for testing
- Configurable via command-line options

**Key Functions:**
- `log()` - Timestamped logging to file and console
- `log_error()` - Error logging with stderr output
- Directory scanning with validation
- Per-software backup management
- Summary generation with statistics

**Usage:**
```bash
./scripts/weekly-version-update.sh \
  --saidata-dir ~/saidata \
  --backup-dir ~/saidata-backups \
  --log-dir ~/logs/saidata-updates
```

### 2. Python Script (`scripts/weekly_version_update.py`)

**Purpose:** Advanced version update script with parallel processing (recommended)

**Features:**
- Parallel processing with configurable workers
- Comprehensive logging with multiple handlers
- Automatic backup cleanup with retention policy
- JSON result export for analysis
- Progress tracking and statistics
- Better error handling and recovery

**Key Classes:**
- `VersionUpdateManager` - Main orchestration class
  - `discover_software_directories()` - Find all saidata files
  - `process_directory()` - Update single software directory
  - `process_all_directories()` - Batch processing with parallelization
  - `generate_summary()` - Create detailed reports
  - `cleanup_old_backups()` - Manage backup retention

**Usage:**
```bash
./scripts/weekly_version_update.py \
  --saidata-dir ~/saidata \
  --max-workers 4 \
  --retention-days 30
```

### 3. Interactive Setup Script (`scripts/setup-cronjob.sh`)

**Purpose:** User-friendly cronjob configuration and installation

**Features:**
- Interactive prompts for all configuration
- Script selection (bash vs Python)
- Path configuration with validation
- Schedule selection (weekly, daily, monthly, custom)
- Test run before installation
- Automatic cronjob installation
- Existing cronjob detection and replacement

**Workflow:**
1. Validate saigen installation
2. Choose script type
3. Configure paths (with directory creation)
4. Select schedule
5. Configure options
6. Test run (optional)
7. Install cronjob

**Usage:**
```bash
./scripts/setup-cronjob.sh
```

### 4. Documentation (`scripts/README-weekly-updates.md`)

**Purpose:** Comprehensive user guide

**Contents:**
- Overview and features
- Usage examples for all scripts
- Cronjob setup instructions
- Directory structure requirements
- Output file descriptions
- Troubleshooting guide
- CI/CD integration examples
- Best practices

### 5. Configuration Example (`scripts/weekly-update-config.example.yaml`)

**Purpose:** Advanced configuration template for Python script

**Sections:**
- Paths configuration
- Processing options (parallel, workers, caching)
- Backup management (retention, cleanup)
- Logging configuration
- Repository configuration
- Filtering options (software, providers)
- Notification configuration (email, Slack, webhook)
- Error handling
- Performance tuning
- Advanced options

## Integration Points

### With Existing SAI Suite Components

1. **saigen CLI** - Uses `saigen refresh-versions` command
2. **Repository Manager** - Leverages local repository caches
3. **Configuration System** - Respects saigen configuration
4. **Validation System** - Can validate after updates

### With External Systems

1. **Cron** - Standard Unix cronjob integration
2. **CI/CD** - GitHub Actions example provided
3. **Monitoring** - Log files and JSON results for analysis
4. **Notifications** - Email, Slack, webhook support (config example)

## Technical Details

### Discovery Algorithm

```
1. Scan saidata directory recursively for .yaml files
2. For each yaml file:
   a. Load and parse YAML
   b. Check for 'version' and 'metadata' fields
   c. If valid saidata, add parent directory to list
   d. Handle OS-specific subdirectories (ubuntu/, debian/, etc.)
3. Deduplicate directory list
4. Return sorted list of software directories
```

### Processing Flow

```
For each software directory:
  1. Create timestamped backup subdirectory
  2. Build saigen refresh-versions command with options:
     - --all-variants (process all files in directory)
     - --backup-dir (software-specific backup location)
     - --skip-default (optional)
     - --no-cache (optional)
  3. Execute command and capture output
  4. Parse results and update statistics
  5. Log success/failure
  6. Continue to next directory (even on error)
```

### Parallel Processing (Python only)

```
1. Create asyncio semaphore with max_workers limit
2. Create task for each directory with semaphore
3. Execute all tasks concurrently with asyncio.gather()
4. Collect results from all tasks
5. Generate summary statistics
```

### Backup Management

```
Backup Structure:
  backup_dir/
    YYYYMMDD_HHMMSS/          # Timestamp of run
      software/
        prefix/
          software_name/
            default.yaml.backup.YYYYMMDD_HHMMSS
            os/
              version.yaml.backup.YYYYMMDD_HHMMSS

Cleanup Process:
  1. List all timestamped directories in backup_dir
  2. Parse timestamp from directory name
  3. Compare with retention cutoff date
  4. Remove directories older than retention period
```

## Usage Patterns

### Basic Weekly Cronjob

```bash
# Crontab entry
0 2 * * 0 /path/to/weekly-version-update.sh --saidata-dir ~/saidata >> ~/logs/saidata-updates/cron.log 2>&1
```

### Advanced with Python

```bash
# Crontab entry with parallel processing
0 2 * * 0 /path/to/weekly_version_update.py --saidata-dir ~/saidata --max-workers 8 --retention-days 30
```

### CI/CD Integration

```yaml
# GitHub Actions
on:
  schedule:
    - cron: '0 2 * * 0'
jobs:
  update-versions:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install saigen
        run: pip install saigen
      - name: Update versions
        run: ./scripts/weekly-version-update.sh --saidata-dir ./saidata
      - name: Create PR
        uses: peter-evans/create-pull-request@v5
```

## Output Files

### Log Files

- `update_YYYYMMDD_HHMMSS.log` - Detailed execution log
- `summary_YYYYMMDD_HHMMSS.txt` - Summary report
- `results_YYYYMMDD_HHMMSS.json` - JSON results (Python only)
- `cron.log` - Cronjob output (if run via cron)

### Backup Files

- Organized by timestamp and software path
- Individual file backups with timestamps
- Automatic cleanup based on retention policy

## Error Handling

### Bash Script

- Continues processing on individual failures
- Logs all errors with context
- Returns exit code 1 if any failures
- Preserves partial results

### Python Script

- Try-catch blocks around each directory
- Detailed exception logging with traceback
- Statistics tracking for failures
- Graceful degradation on errors

## Performance Considerations

### Bash Script

- Sequential processing only
- Suitable for small to medium saidata collections
- Lower memory footprint
- Simpler debugging

### Python Script

- Parallel processing with configurable workers
- Suitable for large saidata collections
- Higher memory usage with parallelization
- Better performance on multi-core systems

**Benchmarks (estimated):**
- 100 software directories, sequential: ~10-15 minutes
- 100 software directories, parallel (4 workers): ~3-5 minutes
- 1000 software directories, parallel (8 workers): ~20-30 minutes

## Best Practices

1. **Test First**: Always run with `--dry-run` before production
2. **Monitor Logs**: Set up log rotation and monitoring
3. **Backup Retention**: Balance storage vs. recovery needs
4. **Cache Strategy**: Use cache for speed, `--no-cache` for accuracy
5. **Parallel Workers**: Match to CPU cores (typically 2-8)
6. **Schedule**: Off-peak hours to avoid resource contention
7. **Notifications**: Set up alerts for failures
8. **Version Control**: Commit updated saidata to git

## Future Enhancements

### Potential Improvements

1. **Notification System**: Implement email/Slack notifications
2. **Diff Generation**: Create human-readable diffs of changes
3. **Rollback Support**: Automatic rollback on validation failures
4. **Incremental Updates**: Track last update time, skip unchanged
5. **Priority Queuing**: Update critical software first
6. **Health Checks**: Verify repository availability before processing
7. **Metrics Export**: Prometheus/Grafana integration
8. **Web Dashboard**: Real-time progress monitoring

### Configuration File Support

The example configuration file provides a template for:
- Advanced filtering (include/exclude software)
- Notification configuration
- Performance tuning
- Error handling policies

Implementation would require:
- YAML config parser in Python script
- Notification service integrations
- Enhanced filtering logic
- Configuration validation

## Testing

### Manual Testing

```bash
# Test bash script
./scripts/weekly-version-update.sh --dry-run --verbose

# Test Python script
./scripts/weekly_version_update.py --dry-run --verbose --sequential

# Test setup script
./scripts/setup-cronjob.sh
```

### Validation

```bash
# Verify script permissions
ls -la scripts/weekly-version-update.sh
ls -la scripts/weekly_version_update.py
ls -la scripts/setup-cronjob.sh

# Verify saigen availability
which saigen
saigen --version

# Verify saidata directory
ls -la ~/saidata/software/
```

## Troubleshooting

### Common Issues

1. **"saigen command not found"**
   - Solution: Install saigen or activate virtual environment

2. **"No software directories found"**
   - Solution: Verify saidata directory structure and file format

3. **"Repository not configured"**
   - Solution: Run `saigen repositories update --all`

4. **Permission errors**
   - Solution: Check script execute permissions and directory write access

5. **Cronjob not running**
   - Solution: Check crontab syntax, verify paths are absolute

## Documentation Updates

Updated the following files:
- `scripts/README.md` - Added weekly update scripts section
- `scripts/README-weekly-updates.md` - New comprehensive guide
- `docs/summaries/weekly-version-update-implementation.md` - This file

## Conclusion

The weekly version update system provides a robust, automated solution for keeping saidata files synchronized with upstream package versions. The dual implementation (bash and Python) offers flexibility for different use cases, while the interactive setup script makes deployment straightforward. Comprehensive documentation and examples ensure users can quickly adopt and customize the system for their needs.
