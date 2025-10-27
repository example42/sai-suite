# Saidata Structure Guide

## Overview

This guide explains the hierarchical structure of saidata files, the relationship between `default.yaml` and OS-specific files, and how they merge to provide accurate software metadata for different operating systems.

## Directory Structure

Saidata files follow a hierarchical structure organized by software name:

```
software/
├── {prefix}/              # First two letters of software name
│   └── {software}/        # Software name
│       ├── default.yaml   # Generic/upstream defaults
│       ├── ubuntu/        # Ubuntu-specific overrides
│       │   ├── 20.04.yaml
│       │   ├── 22.04.yaml
│       │   └── 24.04.yaml
│       ├── debian/        # Debian-specific overrides
│       │   ├── 10.yaml
│       │   ├── 11.yaml
│       │   └── 12.yaml
│       ├── fedora/        # Fedora-specific overrides
│       │   ├── 38.yaml
│       │   ├── 39.yaml
│       │   └── 40.yaml
│       └── rocky/         # Rocky Linux-specific overrides
│           ├── 8.yaml
│           └── 9.yaml
```

**Example for nginx:**

```
software/
└── ng/
    └── nginx/
        ├── default.yaml
        ├── ubuntu/
        │   ├── 20.04.yaml
        │   ├── 22.04.yaml
        │   └── 24.04.yaml
        ├── debian/
        │   ├── 11.yaml
        │   └── 12.yaml
        └── fedora/
            └── 39.yaml
```

## File Types

### default.yaml - Upstream/Generic Metadata

The `default.yaml` file contains **upstream/official information** about the software:

- Latest official release version from the software vendor
- Common package names that work across most OS versions
- Generic metadata (description, homepage, license)
- Installation methods (sources, binaries, scripts)
- Common configuration across all OS versions

**Purpose:**
- Represents the canonical software version independent of OS packaging
- Provides fallback values when OS-specific files don't exist
- Contains information that doesn't vary by OS

**Example default.yaml:**

```yaml
version: "0.3"

metadata:
  name: "nginx"
  description: "High-performance HTTP server and reverse proxy"
  homepage: "https://nginx.org"
  license: "BSD-2-Clause"
  version: "1.26.0"  # Latest upstream release

packages:
  - name: "nginx"
    package_name: "nginx"  # Common name across most OSes
    version: "1.26.0"      # Upstream version

sources:
  - name: "main"
    url: "https://nginx.org/download/nginx-{{version}}.tar.gz"
    build_system: "autotools"
    checksum: "sha256:abc123..."

binaries:
  - name: "official"
    url: "https://nginx.org/packages/mainline/{{platform}}/nginx-{{version}}.tar.gz"
    platform: ["linux", "macos"]
    architecture: ["amd64", "arm64"]
```

### OS-Specific Files - Packaged Versions and Overrides

OS-specific files (e.g., `ubuntu/22.04.yaml`, `debian/11.yaml`) contain **OS-packaged versions** and any OS-specific overrides:

- Package versions as distributed by the OS package manager
- OS-specific package names (if different from default)
- Provider-specific configurations
- Only fields that differ from default.yaml

**Purpose:**
- Provide accurate package names and versions for specific OS versions
- Override default values when OS packaging differs
- Minimize duplication by only including necessary overrides

**Example ubuntu/22.04.yaml:**

```yaml
version: "0.3"

providers:
  apt:
    packages:
      - name: "nginx"
        package_name: "nginx-core"  # Ubuntu-specific package name
        version: "1.18.0-6ubuntu14.4"  # Ubuntu 22.04 packaged version
```

**Example debian/11.yaml:**

```yaml
version: "0.3"

providers:
  apt:
    packages:
      - name: "nginx"
        version: "1.18.0-6+deb11u3"  # Debian 11 packaged version
        # package_name not included - same as default.yaml
```

## Merge Behavior

When saidata is loaded for a specific OS, the system merges `default.yaml` with the OS-specific file:

### Merge Process

1. **Load default.yaml**: Read base configuration with upstream versions
2. **Detect OS context**: Identify current OS and version (e.g., Ubuntu 22.04)
3. **Load OS-specific file**: Read `ubuntu/22.04.yaml` if it exists
4. **Deep merge**: OS-specific values override default values
5. **Result**: Complete saidata with accurate information for that OS

### Merge Rules

- **OS-specific overrides default**: Values in OS-specific files take precedence
- **Deep merge**: Nested structures are merged recursively
- **Array replacement**: Arrays in OS-specific files replace default arrays
- **Null values**: Null in OS-specific file removes the field
- **Missing fields**: Fields not in OS-specific file use default values

### Merge Example

**default.yaml:**
```yaml
version: "0.3"
metadata:
  name: "nginx"
  version: "1.26.0"

packages:
  - name: "nginx"
    package_name: "nginx"
    version: "1.26.0"

providers:
  apt:
    packages:
      - name: "nginx"
        package_name: "nginx"
```

**ubuntu/22.04.yaml:**
```yaml
version: "0.3"
providers:
  apt:
    packages:
      - name: "nginx"
        package_name: "nginx-core"
        version: "1.18.0-6ubuntu14.4"
```

**Merged result on Ubuntu 22.04:**
```yaml
version: "0.3"
metadata:
  name: "nginx"
  version: "1.26.0"  # From default.yaml

packages:
  - name: "nginx"
    package_name: "nginx"  # From default.yaml
    version: "1.26.0"      # From default.yaml

providers:
  apt:
    packages:
      - name: "nginx"
        package_name: "nginx-core"  # From ubuntu/22.04.yaml (overridden)
        version: "1.18.0-6ubuntu14.4"  # From ubuntu/22.04.yaml (overridden)
```

## Version Policy

### Default.yaml Version Policy

The `default.yaml` file should contain **upstream/official versions**:

- Top-level `metadata.version` and `packages[].version` represent the latest official release
- These versions come from the software vendor's official releases
- Provider-specific version fields should NOT be in default.yaml
- Package names should be the most common name across OS versions

**Rationale:**
- Provides a canonical reference for the software's current version
- Independent of OS packaging decisions
- Useful for users who want to know the latest upstream version
- Serves as a baseline for OS-specific overrides

### OS-Specific Version Policy

OS-specific files contain **OS-packaged versions**:

- Provider-specific `packages[].version` represents the version in that OS's repositories
- These versions may lag behind upstream releases
- Versions include OS-specific suffixes (e.g., `-6ubuntu14.4`, `+deb11u3`)
- Accurately reflect what users will get when installing via package manager

**Rationale:**
- Users need to know what version they'll actually get
- OS packaging often includes security patches and backports
- Version strings match what package managers report

## Creating OS-Specific Files

### Manual Creation

Create OS-specific files manually when you know the OS-specific values:

```bash
mkdir -p software/ng/nginx/ubuntu
cat > software/ng/nginx/ubuntu/22.04.yaml << 'EOF'
version: "0.3"
providers:
  apt:
    packages:
      - name: "nginx"
        package_name: "nginx-core"
        version: "1.18.0-6ubuntu14.4"
EOF
```

### Automated Creation

Use the `refresh-versions` command with `--create-missing` to automatically create OS-specific files:

```bash
# Create missing OS-specific files with accurate version data
saigen refresh-versions --all-variants --create-missing software/ng/nginx/
```

This will:
1. Query the appropriate OS-specific repository (e.g., apt-ubuntu-jammy)
2. Retrieve current package names and versions
3. Create minimal YAML with only necessary overrides
4. Include version information (always OS-specific)
5. Include package_name only if it differs from default.yaml

### Minimal Override Principle

OS-specific files should only include fields that differ from default.yaml:

**Good (minimal):**
```yaml
version: "0.3"
providers:
  apt:
    packages:
      - name: "nginx"
        version: "1.18.0-6ubuntu14.4"  # Only version differs
```

**Bad (unnecessary duplication):**
```yaml
version: "0.3"
metadata:
  name: "nginx"  # Unnecessary - same as default.yaml
  description: "High-performance HTTP server"  # Unnecessary
  
packages:
  - name: "nginx"  # Unnecessary - same as default.yaml
    package_name: "nginx"  # Unnecessary
    version: "1.26.0"  # Unnecessary

providers:
  apt:
    packages:
      - name: "nginx"
        package_name: "nginx"  # Unnecessary - same as default.yaml
        version: "1.18.0-6ubuntu14.4"
```

## Override Validation

### Validate Overrides Command

Use the `validate-overrides` command to check for unnecessary duplication:

```bash
# Validate a specific OS-specific file
saigen validate-overrides software/ng/nginx/ubuntu/22.04.yaml

# Validate all OS-specific files in a directory
saigen validate-overrides --all software/ng/nginx/
```

**Output:**
```
Validating: ubuntu/22.04.yaml

Unnecessary overrides (identical to default.yaml):
  ⚠ metadata.name: "nginx"
  ⚠ metadata.description: "High-performance HTTP server"
  ⚠ providers.apt.packages[0].package_name: "nginx"

Necessary overrides (differ from default.yaml):
  ✓ providers.apt.packages[0].version: "1.18.0-6ubuntu14.4"

Recommendation: Remove 3 unnecessary overrides
```

### Automatic Cleanup

Remove unnecessary overrides automatically:

```bash
# Remove unnecessary overrides from a file
saigen validate-overrides --clean software/ng/nginx/ubuntu/22.04.yaml

# Clean all OS-specific files in a directory
saigen validate-overrides --clean --all software/ng/nginx/
```

## Best Practices

### 1. Keep default.yaml Generic

- Use upstream versions, not OS-packaged versions
- Include common package names that work across most OSes
- Don't include provider-specific version information
- Focus on information that doesn't vary by OS

### 2. Minimize OS-Specific Overrides

- Only include fields that actually differ from default.yaml
- Don't duplicate metadata, descriptions, or URLs
- Focus on package names and versions
- Use `validate-overrides` to check for unnecessary duplication

### 3. Use Consistent Naming

- Follow the directory structure: `{os}/{version}.yaml`
- Use official OS version numbers (22.04, 11, 39, etc.)
- Don't use codenames in file names (use version numbers)

### 4. Document Differences

Add comments to explain why overrides are necessary:

```yaml
version: "0.3"
providers:
  apt:
    packages:
      - name: "nginx"
        # Ubuntu uses nginx-core as the base package
        package_name: "nginx-core"
        version: "1.18.0-6ubuntu14.4"
```

### 5. Keep Files Updated

- Use `refresh-versions` regularly to update versions
- Review and update OS-specific files when new OS versions are released
- Remove files for EOL OS versions when no longer needed

### 6. Test Merging

Test that OS-specific files merge correctly:

```bash
# Load and display merged saidata for specific OS
saigen show --os ubuntu --os-version 22.04 software/ng/nginx/

# Validate merged result
saigen validate --os ubuntu --os-version 22.04 software/ng/nginx/
```

## Common Patterns

### Pattern 1: Version-Only Override

Most common pattern - only version differs:

```yaml
version: "0.3"
providers:
  apt:
    packages:
      - name: "nginx"
        version: "1.18.0-6ubuntu14.4"
```

### Pattern 2: Package Name and Version Override

Package name differs on this OS:

```yaml
version: "0.3"
providers:
  apt:
    packages:
      - name: "nginx"
        package_name: "nginx-full"
        version: "1.18.0-6ubuntu14.4"
```

### Pattern 3: Multiple Providers

Different versions for different providers:

```yaml
version: "0.3"
providers:
  apt:
    packages:
      - name: "nginx"
        version: "1.18.0-6ubuntu14.4"
  
  snap:
    packages:
      - name: "nginx"
        version: "1.24.0"
```

### Pattern 4: Additional OS-Specific Packages

OS provides additional related packages:

```yaml
version: "0.3"
providers:
  apt:
    packages:
      - name: "nginx"
        version: "1.18.0-6ubuntu14.4"
      
      # Ubuntu-specific additional packages
      - name: "nginx-extras"
        package_name: "nginx-extras"
        version: "1.18.0-6ubuntu14.4"
```

## Troubleshooting

### Override Not Taking Effect

If an OS-specific override doesn't seem to work:

1. **Check file location**: Ensure file is in correct directory (`{os}/{version}.yaml`)
2. **Check OS detection**: Verify system correctly detects OS and version
3. **Check merge logic**: Use `saigen show` to see merged result
4. **Check YAML syntax**: Validate YAML is well-formed

```bash
# Check OS detection
saigen config show-os

# View merged saidata
saigen show --os ubuntu --os-version 22.04 software/ng/nginx/

# Validate YAML syntax
yamllint software/ng/nginx/ubuntu/22.04.yaml
```

### Duplicate Information

If OS-specific files contain unnecessary duplicates:

```bash
# Check for unnecessary overrides
saigen validate-overrides software/ng/nginx/ubuntu/22.04.yaml

# Automatically remove duplicates
saigen validate-overrides --clean software/ng/nginx/ubuntu/22.04.yaml
```

### Missing OS-Specific File

If an OS-specific file doesn't exist:

```bash
# Create missing OS-specific files
saigen refresh-versions --all-variants --create-missing software/ng/nginx/

# Or create manually
mkdir -p software/ng/nginx/ubuntu
touch software/ng/nginx/ubuntu/24.04.yaml
```

### Incorrect Version

If version in OS-specific file is outdated:

```bash
# Refresh versions from repositories
saigen refresh-versions software/ng/nginx/ubuntu/22.04.yaml

# Or refresh all files
saigen refresh-versions --all-variants software/ng/nginx/
```

## See Also

- [Refresh Versions Command](refresh-versions-command.md)
- [Repository Configuration Guide](repository-configuration-guide.md)
- [Saidata Schema 0.3 Guide](schema-0.3-guide.md)
- [Repository Management](repository-management.md)
