# Refresh Versions Command

## Overview

The `refresh-versions` command updates package version information in existing saidata files by querying package repositories directly, without using LLM services. This provides a fast, cost-free way to keep saidata files synchronized with upstream package versions.

## Features

- **No LLM costs**: Queries repositories directly
- **Fast execution**: Typically completes in seconds
- **Safe updates**: Creates backups before modifying files
- **Selective updates**: Target specific providers
- **Check mode**: Preview changes without modifying files
- **OS-specific support**: Automatically detects OS from file paths and queries appropriate repositories
- **Directory processing**: Update all saidata variants in a directory at once
- **File creation**: Create missing OS-specific files with accurate version data
- **Interactive mode**: Review changes before applying

## Usage

### Basic Usage

```bash
# Refresh all package versions in a single saidata file
saigen refresh-versions nginx.yaml

# Refresh all saidata files in a directory (default.yaml + OS-specific)
saigen refresh-versions --all-variants software/ng/nginx/

# Refresh only OS-specific files, skip default.yaml
saigen refresh-versions --all-variants --skip-default software/ng/nginx/

# Create missing OS-specific files with version data
saigen refresh-versions --all-variants --create-missing software/ng/nginx/

# Interactive mode - review changes before applying
saigen refresh-versions --interactive nginx.yaml

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
- `--all-variants`: Process all saidata files in directory (default.yaml + OS-specific)
- `--skip-default`: Skip default.yaml when processing directory
- `--create-missing`: Create OS-specific files that don't exist
- `--interactive`: Show diff and prompt before applying changes

### Global Options

- `--verbose, -v`: Enable verbose output
- `--dry-run`: Show what would be done without executing

## How It Works

### Single File Refresh

1. **Load saidata**: Reads the existing saidata YAML file
2. **Detect OS context**: Extracts OS and version from file path (e.g., `ubuntu/22.04.yaml`)
3. **Extract packages**: Collects all packages with version information from:
   - Top-level packages
   - Provider-specific packages
   - Package sources
   - Repository packages
   - Binaries
   - Sources
   - Scripts
4. **Select repository**: Chooses OS-specific repository based on detected context (e.g., `apt-ubuntu-jammy`)
5. **Query repositories**: Searches package repositories for current versions
6. **Update versions**: Updates version fields in the saidata object
7. **Save changes**: Writes the updated saidata back to file

### Directory Refresh

1. **Scan directory**: Discovers all YAML files (default.yaml and OS-specific files)
2. **Process each file**: Applies single file refresh logic to each file with appropriate OS context
3. **Aggregate results**: Collects updates, warnings, and errors from all files
4. **Display summary**: Shows per-file results and overall statistics

### OS Detection from File Paths

The command automatically detects OS information from file paths:

- `software/ng/nginx/ubuntu/22.04.yaml` → OS: ubuntu, Version: 22.04 → Repository: apt-ubuntu-jammy
- `software/ng/nginx/debian/11.yaml` → OS: debian, Version: 11 → Repository: apt-debian-bullseye
- `software/ng/nginx/fedora/39.yaml` → OS: fedora, Version: 39 → Repository: dnf-fedora-f39
- `software/ng/nginx/default.yaml` → No OS context → Uses generic provider repositories

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

### Single File Refresh

```bash
# Refresh a single OS-specific file
saigen refresh-versions software/ng/nginx/ubuntu/22.04.yaml
```

Output:
```
Refreshing: software/ng/nginx/ubuntu/22.04.yaml
OS Context: ubuntu 22.04 (jammy)
Repository: apt-ubuntu-jammy

Updates:
  • apt/nginx: 1.18.0 → 1.18.0-6ubuntu14.4
  
Results:
  Total packages: 1
  Updated: 1
  Unchanged: 0
  Execution time: 2.1s
```

### Directory Refresh with All Variants

```bash
# Refresh all saidata files in a directory
saigen refresh-versions --all-variants software/ng/nginx/
```

Output:
```
Processing directory: software/ng/nginx/
Found files:
  • default.yaml
  • ubuntu/22.04.yaml
  • ubuntu/24.04.yaml
  • debian/11.yaml

Refreshing default.yaml...
  ✓ Updated 1 package

Refreshing ubuntu/22.04.yaml...
  OS Context: ubuntu 22.04 (jammy)
  Repository: apt-ubuntu-jammy
  ✓ Updated 1 package

Refreshing ubuntu/24.04.yaml...
  OS Context: ubuntu 24.04 (noble)
  Repository: apt-ubuntu-noble
  ✓ Updated 1 package

Refreshing debian/11.yaml...
  OS Context: debian 11 (bullseye)
  Repository: apt-debian-bullseye
  ✓ Updated 1 package

Summary:
  Files processed: 4
  Total updates: 4
  Warnings: 0
  Errors: 0
  Execution time: 5.3s
```

### Create Missing OS-Specific Files

```bash
# Create OS-specific files for Ubuntu 24.04 if they don't exist
saigen refresh-versions --all-variants --create-missing software/ng/nginx/
```

Output:
```
Processing directory: software/ng/nginx/
Found files:
  • default.yaml
  • ubuntu/22.04.yaml

Creating missing file: ubuntu/24.04.yaml
  OS Context: ubuntu 24.04 (noble)
  Repository: apt-ubuntu-noble
  Querying apt-ubuntu-noble for nginx...
  ✓ Created ubuntu/24.04.yaml with version 1.24.0-2ubuntu1

Summary:
  Files processed: 2
  Files created: 1
  Total updates: 2
```

### Skip Default.yaml

```bash
# Only refresh OS-specific files, skip default.yaml
saigen refresh-versions --all-variants --skip-default software/ng/nginx/
```

This is useful when you want to update OS-specific packaged versions without touching the upstream version in default.yaml.

### Interactive Mode

```bash
# Review changes before applying
saigen refresh-versions --interactive software/ng/nginx/ubuntu/22.04.yaml
```

Output:
```
Proposed changes for ubuntu/22.04.yaml:

providers:
  apt:
    packages:
      - name: nginx
-       version: "1.18.0"
+       version: "1.18.0-6ubuntu14.4"

Apply these changes? [y/N]: y
✓ Changes applied
```

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

### CI/CD Integration

```bash
# Check for outdated versions in CI pipeline
if saigen refresh-versions --check-only nginx.yaml | grep -q "Updates available: [1-9]"; then
  echo "Versions are outdated!"
  exit 1
fi
```

## OS-Specific File Behavior

### Default.yaml Version Policy

The `default.yaml` file should contain **upstream/official versions** from the software's official releases, not OS-packaged versions. This represents the canonical software version independent of OS packaging.

When refreshing `default.yaml`:
- Top-level `packages[].version` is updated to the latest upstream release
- Provider-specific version fields are NOT updated (these belong in OS-specific files)
- Package names that are consistent across all OS versions are included

### OS-Specific Files

OS-specific files (e.g., `ubuntu/22.04.yaml`, `debian/11.yaml`) contain **OS-packaged versions** and any OS-specific overrides:

```yaml
# ubuntu/22.04.yaml
version: "0.3"
providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx-full  # Only if different from default.yaml
        version: "1.18.0-6ubuntu14.4"  # OS-packaged version
```

### Merge Behavior

When saidata is loaded on a specific OS, the OS-specific file overrides fields from `default.yaml`:

1. Load `default.yaml` (upstream versions, common package names)
2. Load `{os}/{version}.yaml` (OS-specific overrides)
3. Merge: OS-specific values override default values
4. Result: Accurate package names and versions for that OS

### Creating OS-Specific Files

Use `--create-missing` to generate OS-specific files:

```bash
saigen refresh-versions --all-variants --create-missing software/ng/nginx/
```

The command will:
1. Query the appropriate OS-specific repository (e.g., apt-ubuntu-noble)
2. Create minimal YAML with only necessary overrides
3. Include version information (always OS-specific)
4. Include package_name only if it differs from default.yaml

### EOL OS Version Support

The system maintains repository configurations for end-of-life (EOL) OS versions to support historical saidata files. When querying an EOL repository, you'll see an informational message:

```
ℹ Repository apt-ubuntu-focal is for EOL OS version Ubuntu 20.04
```

EOL repositories remain functional as long as the upstream repositories are accessible.

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

### Repository Not Configured

If an OS-specific repository is not configured:

```
⚠ Repository apt-ubuntu-noble not configured. Skipping ubuntu/24.04.yaml
```

This means the repository configuration for that OS version doesn't exist. You can:
1. Add the repository configuration (see [Repository Configuration Guide](repository-configuration-guide.md))
2. Skip that OS version
3. Use a different OS version that has a configured repository

### Missing Codename Mapping

If the OS version cannot be mapped to a codename:

```
⚠ Could not resolve codename for ubuntu 26.04
```

This means the repository configuration doesn't have a version_mapping entry for that OS version. Update the repository configuration to add the mapping.

### Network Errors

If repository queries fail due to network issues:

```
✗ Failed to access repository apt-ubuntu-jammy: Connection timeout
```

The command will retry with exponential backoff. If it continues to fail:
- Check your internet connection
- Verify the repository URL is accessible
- Try again later if the repository is temporarily unavailable

### Invalid File Path

If the file path doesn't follow the expected structure:

```
⚠ Could not extract OS information from path: custom/nginx.yaml
```

The command will treat the file as OS-agnostic and use generic provider repositories. Ensure your saidata follows the standard structure: `software/{prefix}/{name}/{os}/{version}.yaml`

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
