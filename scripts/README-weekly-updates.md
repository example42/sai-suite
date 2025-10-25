# Weekly Version Update Script

Automated script for updating package versions across all saidata files using locally present repositories.

## Overview

The `weekly-version-update.sh` script scans a saidata directory, identifies all software configurations, and updates their package versions by querying local repository caches. It's designed to run as a weekly cronjob to keep your saidata files synchronized with upstream package versions.

## Features

- **Automatic Discovery**: Scans directory tree for all saidata files
- **Batch Processing**: Updates all software configurations in one run
- **OS-Specific Support**: Handles both default.yaml and OS-specific variants
- **Backup Management**: Creates timestamped backups before modifications
- **Comprehensive Logging**: Detailed logs with timestamps and summaries
- **Error Handling**: Continues processing even if individual updates fail
- **Dry Run Mode**: Preview changes without modifying files
- **Flexible Configuration**: Command-line options for customization

## Usage

### Basic Usage

```bash
./scripts/weekly-version-update.sh
```

This uses default paths:
- Saidata directory: `~/saidata`
- Backup directory: `~/saidata-backups`
- Log directory: `~/logs/saidata-updates`

### Custom Paths

```bash
./scripts/weekly-version-update.sh \
  --saidata-dir /path/to/saidata \
  --backup-dir /path/to/backups \
  --log-dir /path/to/logs
```

### Options

| Option | Description |
|--------|-------------|
| `--saidata-dir PATH` | Path to saidata directory (default: ~/saidata) |
| `--backup-dir PATH` | Path to backup directory (default: ~/saidata-backups) |
| `--log-dir PATH` | Path to log directory (default: ~/logs/saidata-updates) |
| `--skip-default` | Skip default.yaml files (only update OS-specific) |
| `--no-cache` | Don't use cached repository data (fetch fresh) |
| `--dry-run` | Show what would be done without executing |
| `--verbose` | Enable verbose output |
| `--help` | Show help message |

### Examples

**Dry run to preview changes:**
```bash
./scripts/weekly-version-update.sh --dry-run --verbose
```

**Update only OS-specific files:**
```bash
./scripts/weekly-version-update.sh --skip-default
```

**Force fresh repository data:**
```bash
./scripts/weekly-version-update.sh --no-cache
```

## Setting Up as Cronjob

### Weekly Updates (Sunday at 2 AM)

```bash
# Edit crontab
crontab -e

# Add this line:
0 2 * * 0 /path/to/sai-suite/scripts/weekly-version-update.sh --saidata-dir ~/saidata >> ~/logs/saidata-updates/cron.log 2>&1
```

### Daily Updates (Every day at 3 AM)

```bash
0 3 * * * /path/to/sai-suite/scripts/weekly-version-update.sh --saidata-dir ~/saidata >> ~/logs/saidata-updates/cron.log 2>&1
```

### Monthly Updates (First day of month at 1 AM)

```bash
0 1 1 * * /path/to/sai-suite/scripts/weekly-version-update.sh --saidata-dir ~/saidata >> ~/logs/saidata-updates/cron.log 2>&1
```

## Directory Structure

The script expects a saidata directory structure like:

```
saidata/
├── software/
│   ├── ng/
│   │   └── nginx/
│   │       ├── default.yaml
│   │       ├── ubuntu/
│   │       │   └── 22.04.yaml
│   │       └── debian/
│   │           └── 12.yaml
│   ├── ap/
│   │   └── apache/
│   │       ├── default.yaml
│   │       └── centos/
│   │           └── 8.yaml
│   └── ...
```

## Output Files

### Log Files

Each run creates timestamped log files:

```
~/logs/saidata-updates/
├── update_20241022_020000.log      # Detailed execution log
├── summary_20241022_020000.txt     # Summary report
└── cron.log                        # Cronjob output (if run via cron)
```

### Backup Files

Backups are organized by timestamp and software:

```
~/saidata-backups/
└── 20241022_020000/
    └── software/
        ├── ng/
        │   └── nginx/
        │       ├── default.yaml.backup.20241022_020001
        │       └── ubuntu/
        │           └── 22.04.yaml.backup.20241022_020002
        └── ap/
            └── apache/
                └── default.yaml.backup.20241022_020003
```

## How It Works

1. **Discovery Phase**
   - Scans saidata directory for all .yaml files
   - Validates files contain saidata structure (version + metadata fields)
   - Groups files by software directory

2. **Processing Phase**
   - For each software directory:
     - Creates backup subdirectory
     - Runs `saigen refresh-versions --all-variants`
     - Logs results and errors

3. **Summary Phase**
   - Generates summary statistics
   - Creates summary report file
   - Exits with appropriate status code

## Repository Requirements

The script uses locally cached repository data. Ensure repositories are configured and cached:

```bash
# Check available repositories
saigen repositories list

# Update repository cache
saigen repositories update

# Check cache status
saigen cache stats
```

## Troubleshooting

### Script fails with "saigen command not found"

Ensure saigen is installed and in your PATH:

```bash
# Check installation
which saigen

# Install if needed
pip install saigen

# Or activate virtual environment
source .venv/bin/activate
```

### No software directories found

Verify your saidata directory structure:

```bash
# Check for yaml files
find ~/saidata -name "*.yaml" -type f

# Verify saidata format
saigen validate ~/saidata/software/ng/nginx/default.yaml
```

### Repository not configured errors

Update repository configurations:

```bash
# List available repositories
saigen repositories list

# Update specific repository
saigen repositories update apt

# Update all repositories
saigen repositories update --all
```

### Permission errors

Ensure script has execute permissions and write access:

```bash
# Make script executable
chmod +x scripts/weekly-version-update.sh

# Check directory permissions
ls -la ~/saidata
ls -la ~/saidata-backups
```

## Integration with CI/CD

You can integrate this script into CI/CD pipelines:

### GitHub Actions Example

```yaml
name: Weekly Version Update

on:
  schedule:
    - cron: '0 2 * * 0'  # Every Sunday at 2 AM
  workflow_dispatch:  # Manual trigger

jobs:
  update-versions:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install saigen
        run: pip install saigen
      
      - name: Update repository cache
        run: saigen repositories update --all
      
      - name: Run version updates
        run: |
          ./scripts/weekly-version-update.sh \
            --saidata-dir ./saidata \
            --backup-dir ./backups \
            --log-dir ./logs
      
      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          commit-message: 'chore: update package versions'
          title: 'Weekly Package Version Updates'
          body: 'Automated version updates from weekly cronjob'
          branch: 'automated/version-updates'
```

## Best Practices

1. **Test First**: Always run with `--dry-run` before actual execution
2. **Monitor Logs**: Regularly check log files for errors or warnings
3. **Backup Retention**: Implement backup cleanup policy (e.g., keep last 30 days)
4. **Cache Updates**: Update repository cache before running (or use `--no-cache`)
5. **Notifications**: Set up email notifications for cronjob failures
6. **Version Control**: Commit updated saidata files to version control

## Related Commands

- `saigen refresh-versions` - Update versions for single file/directory
- `saigen repositories update` - Update repository cache
- `saigen validate` - Validate saidata files
- `saigen cache stats` - Check cache statistics

## Support

For issues or questions:
- GitHub: https://github.com/example42/sai
- Documentation: https://sai.software
