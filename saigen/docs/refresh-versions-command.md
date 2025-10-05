# Refresh Versions Command

## Overview

The `refresh-versions` command updates package version information in existing saidata files by querying package repositories directly, without using LLM services. This provides a fast, cost-free way to keep saidata files synchronized with upstream package versions.

## Features

- **No LLM costs**: Queries repositories directly
- **Fast execution**: Typically completes in seconds
- **Safe updates**: Creates backups before modifying files
- **Selective updates**: Target specific providers
- **Check mode**: Preview changes without modifying files
- **Batch processing**: Update multiple files at once (via shell)

## Usage

### Basic Usage

```bash
# Refresh all package versions in a saidata file
saigen refresh-versions nginx.yaml

# Check for updates without modifying the file
saigen refresh-versions --check-only nginx.yaml

# Refresh specific providers only
saigen refresh-versions --providers apt,brew nginx.yaml

# Save to a different file
saigen refresh-versions --output nginx-updated.yaml nginx.yaml

# Skip cache for latest data
saigen refresh-versions --no-cache nginx.yaml

# Show all packages including unchanged ones
saigen --verbose refresh-versions --show-unchanged nginx.yaml
```

### Options

- `--output, -o PATH`: Output file path (default: overwrite input file)
- `--providers TEXT`: Target specific providers (e.g., apt, brew, winget)
- `--backup / --no-backup`: Create backup of original file (default: enabled)
- `--backup-dir PATH`: Directory for backup files (default: same as input file)
- `--check-only`: Check for version updates without modifying files
- `--show-unchanged`: Show packages that are already up-to-date
- `--use-cache / --no-cache`: Use cached repository data (default: enabled)

### Global Options

- `--verbose, -v`: Enable verbose output
- `--dry-run`: Show what would be done without executing

## How It Works

1. **Load saidata**: Reads the existing saidata YAML file
2. **Extract packages**: Collects all packages with version information from:
   - Top-level packages
   - Provider-specific packages
   - Package sources
   - Repository packages
   - Binaries
   - Sources
   - Scripts
3. **Query repositories**: Searches package repositories for current versions
4. **Update versions**: Updates version fields in the saidata object
5. **Save changes**: Writes the updated saidata back to file

## What Gets Updated

The command updates version information in these locations:

- `packages[].version`
- `providers.<provider>.packages[].version`
- `providers.<provider>.package_sources[].packages[].version`
- `providers.<provider>.repositories[].packages[].version`
- `providers.<provider>.binaries[].version`
- `providers.<provider>.sources[].version`
- `providers.<provider>.scripts[].version`

All other fields remain unchanged, preserving manual customizations.

## Examples

### Check for Outdated Versions

```bash
# Check which packages need updates
saigen refresh-versions --check-only nginx.yaml
```

Output:
```
Check Results for nginx:
  Total packages checked: 5
  Updates available: 2
  Already up-to-date: 3
  Execution time: 1.23s

Available Updates:
  • apt/nginx: 1.20.1 → 1.24.0
  • brew/nginx: 1.20.1 → 1.25.3
```

### Update Specific Providers

```bash
# Only update apt and brew packages
saigen refresh-versions --providers apt,brew nginx.yaml
```

### Batch Update Multiple Files

```bash
# Update all saidata files in a directory
for file in saidata/*.yaml; do
  saigen refresh-versions "$file"
done
```

### CI/CD Integration

```bash
# Check for outdated versions in CI pipeline
if saigen refresh-versions --check-only nginx.yaml | grep -q "Updates available: [1-9]"; then
  echo "Versions are outdated!"
  exit 1
fi
```

## Backup Management

By default, the command creates timestamped backups before modifying files:

```
nginx.yaml
nginx.backup.20250410_143022.yaml
```

To disable backups:

```bash
saigen refresh-versions --no-backup nginx.yaml
```

To specify a backup directory:

```bash
saigen refresh-versions --backup-dir ./backups nginx.yaml
```

## Repository Cache

The command uses cached repository data by default for faster execution. Cache is stored in:

```
~/.saigen/cache/repositories/
```

To force fresh queries:

```bash
saigen refresh-versions --no-cache nginx.yaml
```

## Troubleshooting

### Package Not Found

If a package cannot be found in the repository:

```
Warnings:
  ⚠ Could not find version for nginx in apt repository
```

This can happen if:
- The package name doesn't match the repository's naming
- The repository cache is outdated (try `--no-cache`)
- The repository is not available

### Version Mismatch

If the command finds a different package:

```
Using closest match: nginx-full v1.24.0
```

This indicates the exact package name wasn't found, and a similar package was used instead. Verify the package name is correct.

## Best Practices

1. **Use check-only first**: Always preview changes before applying
2. **Keep backups enabled**: Allows easy rollback if needed
3. **Target specific providers**: Faster and more predictable
4. **Use in CI/CD**: Automate version checking in pipelines
5. **Combine with validate**: Run validation after updates

```bash
# Safe update workflow
saigen refresh-versions --check-only nginx.yaml
saigen refresh-versions nginx.yaml
saigen validate nginx.yaml
```

## Comparison with Update Command

| Feature | refresh-versions | update |
|---------|-----------------|--------|
| LLM usage | No | Yes |
| Cost | Free | Costs tokens |
| Speed | Fast (seconds) | Slower (minutes) |
| Updates | Versions only | All metadata |
| Use case | Version sync | Full regeneration |

Use `refresh-versions` for routine version updates, and `update` for comprehensive metadata refreshes.
