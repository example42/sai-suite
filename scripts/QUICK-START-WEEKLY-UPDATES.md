# Quick Start: Weekly Version Updates

Get started with automated version updates in 5 minutes.

## Prerequisites

```bash
# Ensure saigen is installed
pip install saigen

# Or install from source
cd /path/to/sai-suite
pip install -e .
```

## Option 1: Interactive Setup (Recommended)

```bash
# Run the interactive setup script
./scripts/setup-cronjob.sh
```

Follow the prompts to configure and install your cronjob.

## Option 2: Manual Setup

### Step 1: Choose Your Script

**Bash Script** (simple, lightweight):
```bash
./scripts/weekly-version-update.sh
```

**Python Script** (advanced, parallel processing):
```bash
./scripts/weekly_version_update.py
```

### Step 2: Test Run

```bash
# Test with dry-run
./scripts/weekly-version-update.sh \
  --saidata-dir ~/saidata \
  --dry-run \
  --verbose
```

### Step 3: Install Cronjob

```bash
# Edit crontab
crontab -e

# Add this line (runs every Sunday at 2 AM):
0 2 * * 0 /path/to/sai-suite/scripts/weekly-version-update.sh --saidata-dir ~/saidata >> ~/logs/saidata-updates/cron.log 2>&1
```

## Common Commands

### Run Once Manually

```bash
# Basic run
./scripts/weekly-version-update.sh --saidata-dir ~/saidata

# With options
./scripts/weekly-version-update.sh \
  --saidata-dir ~/saidata \
  --skip-default \
  --verbose
```

### Python Version with Parallel Processing

```bash
# Fast parallel processing
./scripts/weekly_version_update.py \
  --saidata-dir ~/saidata \
  --max-workers 8
```

### Check Logs

```bash
# View latest log
tail -f ~/logs/saidata-updates/update_*.log

# View latest summary
cat ~/logs/saidata-updates/summary_*.txt | tail -n 50
```

### Manage Cronjob

```bash
# View current cronjobs
crontab -l

# Edit cronjobs
crontab -e

# Remove all cronjobs (careful!)
crontab -r
```

## Directory Structure

Your saidata directory should look like:

```
~/saidata/
└── software/
    ├── ng/
    │   └── nginx/
    │       ├── default.yaml
    │       └── ubuntu/
    │           └── 22.04.yaml
    └── ap/
        └── apache/
            └── default.yaml
```

## Troubleshooting

### Script fails with "saigen not found"

```bash
# Check if saigen is installed
which saigen

# Install if needed
pip install saigen
```

### No software directories found

```bash
# Verify your saidata directory
ls -la ~/saidata/software/

# Check for valid saidata files
find ~/saidata -name "*.yaml" -type f
```

### Repository errors

```bash
# Update repository cache
saigen repositories update --all

# Check repository status
saigen repositories list
```

## Next Steps

- Read the [full documentation](README-weekly-updates.md)
- Customize with [configuration file](weekly-update-config.example.yaml)
- Set up notifications (email, Slack)
- Integrate with CI/CD

## Support

- Documentation: [README-weekly-updates.md](README-weekly-updates.md)
- GitHub: https://github.com/example42/sai
- Website: https://sai.software
