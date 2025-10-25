# OS-Specific File Creation Feature

## Overview

The refresh-versions command will support **creating** OS-specific saidata files when they don't exist, not just updating existing ones. This enables easy addition of support for new OS versions.

## Use Case

When a new OS version is released (e.g., Ubuntu 26.04), you want to automatically create the OS-specific file with version information from the repository, without manually creating the file structure.

## Feature: `--create-missing` Flag

### Behavior

**Without flag** (default):
```bash
saigen refresh-versions ng/nginx/ --all-variants --providers apt

# Output:
⚠ File ubuntu/26.04.yaml does not exist, skipping
✓ Updated ubuntu/22.04.yaml
✓ Updated ubuntu/24.04.yaml
```

**With flag**:
```bash
saigen refresh-versions ng/nginx/ --all-variants --create-missing --providers apt

# Output:
✓ Created ubuntu/26.04.yaml with version 1.26.0
✓ Updated ubuntu/22.04.yaml
✓ Updated ubuntu/24.04.yaml
```

## File Creation Logic

### 1. Determine What to Create

The command will create files for OS versions that:
- Have a configured repository (e.g., `apt-ubuntu-oracular` for Ubuntu 26.04)
- Don't already have an OS-specific file
- Are specified in the refresh operation (via directory scan or explicit path)

### 2. Query Repository

Query the appropriate OS-specific repository:
```
OS: ubuntu, Version: 26.04
→ Resolve codename: oracular
→ Repository: apt-ubuntu-oracular
→ Query for package: nginx
→ Result: package_name=nginx-core, version=1.26.0
```

### 3. Compare with default.yaml

Load `default.yaml` to determine what needs to be included:

```yaml
# default.yaml
providers:
  apt:
    packages:
      - name: main
        package_name: nginx  # Common name
```

**Comparison**:
- Repository returned: `nginx-core`
- Default.yaml has: `nginx`
- **Different** → Include package_name in new file

### 4. Generate Minimal YAML

Create file with **only** what differs from default.yaml:

```yaml
# ubuntu/26.04.yaml (newly created)
providers:
  apt:
    packages:
      - name: main
        package_name: nginx-core  # Differs from default
        version: "1.26.0"         # Always include (OS-specific)
```

**If package name matched default.yaml**:
```yaml
# debian/13.yaml (newly created)
providers:
  apt:
    packages:
      - name: main
        version: "1.22.0"  # Only version (name inherited from default)
```

## Directory Structure Creation

If the OS directory doesn't exist, create it:

```bash
# Before:
ng/nginx/
  default.yaml
  ubuntu/
    22.04.yaml

# After --create-missing for debian/13:
ng/nginx/
  default.yaml
  ubuntu/
    22.04.yaml
  debian/          # ← Created
    13.yaml        # ← Created
```

## Examples

### Example 1: Add Support for New Ubuntu Version

```bash
# Ubuntu 26.04 is released, repository apt-ubuntu-oracular is configured
saigen refresh-versions ng/nginx/ --all-variants --create-missing --providers apt

# Creates: ng/nginx/ubuntu/26.04.yaml
```

### Example 2: Add Support for Multiple OS Versions

```bash
# Add Debian 13 and Rocky 10 support
saigen refresh-versions ng/nginx/ --all-variants --create-missing --providers apt,dnf

# Creates:
# - ng/nginx/debian/13.yaml (from apt-debian-trixie)
# - ng/nginx/rocky/10.yaml (from dnf-rocky-10)
```

### Example 3: Selective Creation

```bash
# Only create for specific OS
saigen refresh-versions ng/nginx/ubuntu/26.04.yaml --create-missing --provider apt

# Creates only: ng/nginx/ubuntu/26.04.yaml
```

## Requirements Added

### Requirement 8: OS-Specific File Creation

**Acceptance Criteria:**

1. WHEN an OS-specific file does not exist and the `--create-missing` flag is used, THE System SHALL create the file
2. WHEN creating an OS-specific file, THE System SHALL query the appropriate repository for that OS version
3. WHEN creating an OS-specific file, THE System SHALL only include fields that differ from default.yaml
4. WHEN creating an OS-specific file, THE System SHALL always include provider-specific version information
5. WHEN creating an OS-specific file, THE System SHALL include package_name only if it differs from default.yaml
6. WHEN creating an OS-specific file, THE System SHALL use the minimal YAML structure (only providers section with necessary overrides)
7. WHEN the `--create-missing` flag is not used, THE System SHALL skip non-existent files and log a warning
8. THE System SHALL create the necessary directory structure (e.g., `ubuntu/` directory) if it doesn't exist

## Implementation Tasks

### Task Group 7: OS-Specific File Creation

1. **File existence checking** - Detect missing files during scan
2. **`--create-missing` flag** - Add CLI option
3. **File creation logic** - Generate minimal YAML with only differences
4. **Directory creation** - Create OS directories as needed
5. **Comparison with default.yaml** - Determine what to include
6. **Tests** - Comprehensive testing of creation scenarios

**Estimated Effort**: 6-8 hours

## Benefits

1. **Easy OS Version Support**: Add new OS versions without manual file creation
2. **Consistency**: Automatically follows the minimal override pattern
3. **Accuracy**: Queries real repository data for new OS versions
4. **Time Saving**: Bulk creation for multiple OS versions
5. **Correctness**: Only includes necessary overrides, avoiding duplication

## Safety Considerations

1. **Opt-in**: Requires explicit `--create-missing` flag
2. **Validation**: Created files are validated against schema
3. **Logging**: Clear logging of what was created
4. **Check-only mode**: Can preview what would be created with `--check-only --create-missing`
5. **Repository requirement**: Only creates if repository is configured

## Future Enhancements

Potential future additions (out of scope for this spec):

1. **Template-based creation**: Use templates for more complex structures
2. **Batch creation**: Create files for all configured repositories at once
3. **Interactive mode**: Prompt for which OS versions to create
4. **Metadata inclusion**: Optionally include additional metadata fields
5. **Multi-provider creation**: Create files with multiple providers at once

## Summary

The `--create-missing` flag transforms the refresh-versions command from an update-only tool to a creation+update tool, making it easy to add support for new OS versions as they're released. The feature maintains the principle of minimal overrides by only including fields that differ from default.yaml.
