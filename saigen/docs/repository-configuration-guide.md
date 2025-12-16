# Repository Configuration Guide

## Overview

This guide explains how to configure package repositories for the SAIGEN tool. Repository configurations enable the `refresh-versions` command to query OS-specific package information and update saidata files with accurate version data.

## Repository Naming Convention

Repository names follow a consistent pattern:

```
{provider}-{os}-{codename}
```

**Examples:**
- `apt-ubuntu-jammy` - Ubuntu 22.04 (Jammy Jellyfish) APT repository
- `apt-debian-bookworm` - Debian 12 (Bookworm) APT repository
- `dnf-fedora-f39` - Fedora 39 DNF repository
- `dnf-rocky-9` - Rocky Linux 9 DNF repository
- `brew-macos` - macOS Homebrew (no version-specific codename)
- `choco-windows` - Windows Chocolatey (no version-specific codename)
- `winget-windows` - Windows winget (no version-specific codename)

**Key Points:**
- Each repository configuration represents ONE specific OS version
- The codename is the distribution's release codename (jammy, bookworm, f39, etc.)
- For OS without version-specific codenames (macOS, Windows), use just the OS name
- Software-specific upstream repositories use pattern: `{provider}-{vendor}-{os}-{codename}` (e.g., `apt-hashicorp-ubuntu-jammy`)

## Repository Configuration Structure

Repository configurations are organized by provider type in `saigen/repositories/configs/`:

```
saigen/repositories/configs/
├── apt.yaml          # All apt-based repositories
├── dnf.yaml          # All dnf/yum-based repositories
├── brew.yaml         # macOS Homebrew
├── choco.yaml        # Windows Chocolatey
├── winget.yaml       # Windows winget
├── zypper.yaml       # SUSE-based
├── pacman.yaml       # Arch-based
└── ...
```

## Configuration File Format

Each provider configuration file contains multiple repository entries:

```yaml
version: "1.0"
repositories:
  - name: "apt-ubuntu-jammy"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    architecture: ["amd64", "arm64", "armhf"]
    
    # Version to codename mapping (single entry per repository)
    version_mapping:
      "22.04": "jammy"
    
    # End-of-life status
    eol: false
    
    # Query type: bulk_download or api
    query_type: "bulk_download"
    
    # Repository endpoints
    endpoints:
      packages: "http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-{arch}/Packages.gz"
      search: "https://packages.ubuntu.com/search?keywords={query}"
    
    # Parsing configuration
    parsing:
      format: "debian_packages"
      compression: "gzip"
      encoding: "utf-8"
    
    # Cache settings
    cache:
      ttl_hours: 24
      max_size_mb: 100
    
    # Rate limiting
    limits:
      requests_per_minute: 60
      timeout_seconds: 300
    
    # Metadata
    metadata:
      description: "Ubuntu 22.04 (Jammy) Main Repository"
      maintainer: "Ubuntu"
      priority: 90
      enabled: true
      official: true
```

## Key Fields

### Required Fields

- **name**: Unique repository identifier following naming convention
- **type**: Provider type (apt, dnf, brew, etc.)
- **platform**: Operating system platform (linux, macos, windows)
- **endpoints**: URLs for package data and search
- **parsing**: Configuration for parsing repository data

### Version Mapping Field

The `version_mapping` field maps OS version strings to distribution codenames:

```yaml
version_mapping:
  "22.04": "jammy"  # Ubuntu 22.04 → jammy
```

**Important:**
- Each repository has ONE version mapping entry
- The key is the OS version string (e.g., "22.04", "11", "39")
- The value is the distribution codename (e.g., "jammy", "bullseye", "f39")
- This allows the system to resolve: OS + version → codename → repository name

**Examples:**

```yaml
# Ubuntu repositories
version_mapping:
  "20.04": "focal"   # apt-ubuntu-focal
  "22.04": "jammy"   # apt-ubuntu-jammy
  "24.04": "noble"   # apt-ubuntu-noble

# Debian repositories
version_mapping:
  "10": "buster"     # apt-debian-buster
  "11": "bullseye"   # apt-debian-bullseye
  "12": "bookworm"   # apt-debian-bookworm

# Fedora repositories
version_mapping:
  "38": "f38"        # dnf-fedora-f38
  "39": "f39"        # dnf-fedora-f39
  "40": "f40"        # dnf-fedora-f40

# Rocky/Alma repositories (version = codename)
version_mapping:
  "8": "8"           # dnf-rocky-8
  "9": "9"           # dnf-rocky-9
```

### EOL Field

The `eol` field indicates end-of-life OS versions:

```yaml
eol: false  # Active OS version
eol: true   # End-of-life OS version
```

When `eol: true`, the system logs an informational message when querying the repository but continues to function normally.

### Query Type Field

The `query_type` field determines how packages are queried:

```yaml
query_type: "bulk_download"  # Download full package list (apt, dnf)
query_type: "api"            # Query per-package via API (npm, pip, cargo)
```

**Bulk Download:**
- Used for repositories that provide complete package lists
- Downloads and caches the entire package index
- Examples: apt, dnf, zypper, pacman

**API:**
- Used for repositories that require per-package queries
- Queries the API for each package individually
- Examples: npm, pip, cargo, winget, rubygems, maven, nuget

## Adding New OS Versions

To add support for a new OS version:

### 1. Identify the Codename

Find the distribution codename for the OS version:
- Ubuntu: https://wiki.ubuntu.com/Releases
- Debian: https://www.debian.org/releases/
- Fedora: https://fedoraproject.org/wiki/Releases
- Rocky/Alma: Version number is the codename

### 2. Add Repository Entry

Add a new repository entry to the appropriate provider file:

```yaml
# In saigen/repositories/configs/apt.yaml

repositories:
  # ... existing repositories ...
  
  # New Ubuntu 26.04 repository
  - name: "apt-ubuntu-oracular"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    architecture: ["amd64", "arm64", "armhf"]
    
    version_mapping:
      "26.04": "oracular"  # New mapping
    
    eol: false
    query_type: "bulk_download"
    
    endpoints:
      packages: "http://archive.ubuntu.com/ubuntu/dists/oracular/main/binary-{arch}/Packages.gz"
      search: "https://packages.ubuntu.com/search?keywords={query}"
    
    parsing:
      format: "debian_packages"
      compression: "gzip"
      encoding: "utf-8"
    
    cache:
      ttl_hours: 24
      max_size_mb: 100
    
    limits:
      requests_per_minute: 60
      timeout_seconds: 300
    
    metadata:
      description: "Ubuntu 26.04 (Oracular) Main Repository"
      maintainer: "Ubuntu"
      priority: 90
      enabled: true
      official: true
```

### 3. Validate Configuration

Validate the repository configuration:

```bash
# Validate repository configuration
saigen repositories validate-config saigen/repositories/configs/apt.yaml

# List all repositories to verify
saigen repositories list-repos --provider apt
```

### 4. Test Repository

Test the repository with a known package:

```bash
# Test querying the new repository
saigen repositories search --repository apt-ubuntu-oracular nginx
```

## Software-Specific Upstream Repositories

Some software vendors provide their own package repositories. These should be configured as separate repository entries:

```yaml
# In saigen/repositories/configs/apt.yaml

repositories:
  # HashiCorp repository for Ubuntu 22.04
  - name: "apt-hashicorp-ubuntu-jammy"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    architecture: ["amd64", "arm64"]
    
    version_mapping:
      "22.04": "jammy"
    
    eol: false
    query_type: "bulk_download"
    
    endpoints:
      packages: "https://apt.releases.hashicorp.com/dists/jammy/main/binary-{arch}/Packages.gz"
    
    parsing:
      format: "debian_packages"
      compression: "gzip"
    
    cache:
      ttl_hours: 24
      max_size_mb: 10
    
    metadata:
      description: "HashiCorp Official Repository for Ubuntu 22.04"
      maintainer: "HashiCorp"
      vendor: "hashicorp"
      priority: 95  # Higher priority than default Ubuntu repos
      enabled: true
      official: true
```

**Usage:**

When refreshing saidata for HashiCorp products, specify the vendor repository:

```bash
saigen refresh-versions --repository apt-hashicorp-ubuntu-jammy terraform.yaml
```

## Repository Configuration Template

Use this template when adding new repositories:

```yaml
- name: "{provider}-{os}-{codename}"
  type: "{provider}"
  platform: "{linux|macos|windows}"
  distribution: ["{os}"]
  architecture: ["{arch1}", "{arch2}"]
  
  version_mapping:
    "{version}": "{codename}"
  
  eol: false
  query_type: "{bulk_download|api}"
  
  endpoints:
    packages: "{url_to_package_list}"
    search: "{url_to_search_endpoint}"
  
  parsing:
    format: "{format_type}"
    compression: "{gzip|xz|none}"
    encoding: "utf-8"
  
  cache:
    ttl_hours: 24
    max_size_mb: 100
  
  limits:
    requests_per_minute: 60
    timeout_seconds: 300
  
  metadata:
    description: "{OS} {version} ({codename}) {provider} Repository"
    maintainer: "{maintainer}"
    priority: 90
    enabled: true
    official: true
```

## Validation Process

Repository configurations are validated when loaded:

### Schema Validation

Configurations must conform to `schemas/repository-config-schema.json`:

- All required fields must be present
- Field types must match schema definitions
- `version_mapping` must be a dictionary with string keys and values
- `eol` must be a boolean
- `query_type` must be "bulk_download" or "api"

### Runtime Validation

Additional validation occurs at runtime:

```python
# Version mapping validation
- Keys must match pattern: ^[0-9.]+$
- Values must match pattern: ^[a-z0-9-]+$

# Endpoint validation
- URLs must be valid and accessible
- Placeholders ({arch}, {query}) must be valid

# Cache validation
- ttl_hours must be positive
- max_size_mb must be positive
```

### Validation Commands

```bash
# Validate a specific configuration file
saigen repositories validate-config saigen/repositories/configs/apt.yaml

# Validate all repository configurations
saigen repositories validate-all

# List all repositories with validation status
saigen repositories list-repos --validate
```

## Best Practices

1. **One Repository Per OS Version**: Each repository should represent a single OS version
2. **Consistent Naming**: Follow the naming convention strictly
3. **Accurate Metadata**: Provide clear descriptions and maintainer information
4. **Appropriate TTL**: Set cache TTL based on repository update frequency
5. **Priority Levels**: Use priority to control repository selection when multiple match
6. **EOL Marking**: Mark end-of-life repositories with `eol: true`
7. **Test Before Committing**: Always test new repository configurations
8. **Document Vendor Repos**: Clearly document software-specific upstream repositories

## Troubleshooting

### Repository Not Found

If a repository is not found:

```bash
# List all available repositories
saigen repositories list-repos

# Check if repository is loaded
saigen repositories list-repos --provider apt | grep jammy
```

### Invalid Configuration

If configuration validation fails:

```bash
# Validate configuration
saigen repositories validate-config saigen/repositories/configs/apt.yaml

# Check error messages for specific issues
```

### Endpoint Not Accessible

If repository endpoints are not accessible:

```bash
# Test endpoint connectivity
curl -I "http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64/Packages.gz"

# Check if URL is correct in configuration
```

### Version Mapping Issues

If codename resolution fails:

```bash
# Verify version_mapping in configuration
grep -A 2 "version_mapping" saigen/repositories/configs/apt.yaml

# Check if version string matches exactly
```

## Repository Schema Reference

### version_mapping Field

**Type:** `object` (dictionary with string keys and values)

**Description:** Maps OS version string to distribution codename for this specific repository.

**Structure:**
```json
{
  "version_mapping": {
    "{version}": "{codename}"
  }
}
```

**Validation Rules:**
- Must be an object/dictionary
- Keys must match pattern: `^[0-9.]+$` (version numbers like "22.04", "11", "39")
- Values must match pattern: `^[a-z0-9-]+$` (codenames like "jammy", "bullseye", "f39")
- Each repository should have ONE version mapping entry

**Examples:**

```yaml
# Ubuntu 22.04
version_mapping:
  "22.04": "jammy"

# Debian 11
version_mapping:
  "11": "bullseye"

# Fedora 39
version_mapping:
  "39": "f39"

# Rocky Linux 9
version_mapping:
  "9": "9"
```

**Purpose:**
- Allows the codename resolver to find the codename for a given OS version
- Enables OS-specific repository selection (e.g., ubuntu 22.04 → jammy → apt-ubuntu-jammy)
- Each repository represents one OS version, so only one mapping is needed

### eol Field

**Type:** `boolean`

**Default:** `false`

**Description:** Indicates if this is an end-of-life OS version/repository.

**Values:**
- `false`: Active, supported OS version
- `true`: End-of-life OS version (no longer officially supported)

**Behavior:**
- When `eol: true`, the system logs an informational message when querying the repository
- Repository continues to function normally (no blocking)
- Useful for maintaining historical saidata files

**Examples:**

```yaml
# Active OS version
eol: false

# End-of-life OS version
eol: true
```

**Use Cases:**
- Mark Ubuntu 18.04 (EOL April 2023) as `eol: true`
- Mark Debian 9 (EOL June 2022) as `eol: true`
- Keep EOL repositories for users who still need them

### query_type Field

**Type:** `string` (enum)

**Default:** `"bulk_download"`

**Description:** Method for querying packages from this repository.

**Values:**
- `"bulk_download"`: Download full package list (apt, dnf, zypper, pacman)
- `"api"`: Query per-package via API (npm, pip, cargo, winget, rubygems)

**Bulk Download:**
- Downloads complete package index file
- Caches entire package list locally
- Efficient for repositories with bulk download endpoints
- Examples: apt, dnf, zypper, pacman, apk

**API:**
- Queries API for each package individually
- Caches individual API responses
- Required for repositories without bulk download
- Examples: npm, pip, cargo, winget, rubygems, maven, nuget

**Examples:**

```yaml
# Bulk download repository (apt)
query_type: "bulk_download"
endpoints:
  packages: "http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64/Packages.gz"

# API-based repository (npm)
query_type: "api"
endpoints:
  packages: "https://registry.npmjs.org/{package}"
  search: "https://registry.npmjs.org/-/v1/search?text={query}"
```

**Cache Behavior:**
- Bulk download: Caches entire package list with `cache.ttl_hours`
- API: Caches individual responses with `cache.api_cache_ttl_seconds`

### Complete Field Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Unique repository identifier |
| `type` | string | Yes | - | Provider type (apt, dnf, brew, etc.) |
| `platform` | string | Yes | - | Operating system platform |
| `distribution` | array | No | [] | Supported distributions |
| `architecture` | array | No | [] | Supported architectures |
| `version_mapping` | object | No | {} | OS version to codename mapping |
| `eol` | boolean | No | false | End-of-life status |
| `query_type` | string | No | "bulk_download" | Query method |
| `endpoints` | object | Yes | - | Repository URLs |
| `parsing` | object | Yes | - | Parsing configuration |
| `cache` | object | No | - | Cache settings |
| `limits` | object | No | - | Rate limiting settings |
| `auth` | object | No | - | Authentication configuration |
| `metadata` | object | No | - | Repository metadata |

### Validation Examples

**Valid Configuration:**

```yaml
- name: "apt-ubuntu-jammy"
  type: "apt"
  platform: "linux"
  distribution: ["ubuntu"]
  
  version_mapping:
    "22.04": "jammy"  # Valid: version → codename
  
  eol: false  # Valid: boolean
  
  query_type: "bulk_download"  # Valid: enum value
  
  endpoints:
    packages: "http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-{arch}/Packages.gz"
  
  parsing:
    format: "debian_packages"
    compression: "gzip"
```

**Invalid Configuration:**

```yaml
- name: "apt-ubuntu-jammy"
  type: "apt"
  platform: "linux"
  
  version_mapping:
    "22.04": "Jammy"  # Invalid: codename must be lowercase
  
  eol: "false"  # Invalid: must be boolean, not string
  
  query_type: "download"  # Invalid: must be "bulk_download" or "api"
  
  endpoints:
    packages: "http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-{arch}/Packages.gz"
  
  parsing:
    format: "debian_packages"
```

### Schema Validation Commands

```bash
# Validate repository configuration against schema
saigen repositories validate-config saigen/repositories/configs/apt.yaml

# Validate all repository configurations
saigen repositories validate-all

# Check specific field validation
saigen repositories validate-field version_mapping '{"22.04": "jammy"}'
```

## See Also

- [Refresh Versions Command](refresh-versions-command.md)
- [Repository Management](repository-management.md)
- [Repository Troubleshooting](repository-troubleshooting.md)
- [Saidata Structure Documentation](saidata-structure-guide.md)
- [Repository Configuration Schema](../../schemas/repository-config-schema.json)
