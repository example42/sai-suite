# Repository Configuration Files

## Overview

This directory contains YAML configuration files for package repositories used by SAIGEN to query package information. Each file is organized by provider type (apt, dnf, brew, etc.) and contains repository definitions for different operating systems and versions.

## File Organization

### Provider-Specific Files

Repository configurations are organized by provider type:

- **`apt.yaml`** - All apt-based repositories (Ubuntu, Debian, Mint, etc.)
- **`dnf.yaml`** - All dnf/yum-based repositories (Fedora, RHEL, Rocky, Alma, CentOS)
- **`brew.yaml`** - macOS Homebrew repositories
- **`choco.yaml`** - Windows Chocolatey repositories
- **`winget.yaml`** - Windows winget repositories
- **`zypper.yaml`** - SUSE-based repositories (SLES, openSUSE)
- **`pacman.yaml`** - Arch-based repositories
- **`apk.yaml`** - Alpine repositories
- **`emerge.yaml`** - Gentoo repositories
- **`nix.yaml`** - NixOS repositories
- **Language package managers**: `npm.yaml`, `pip.yaml`, `cargo.yaml`, `gem.yaml`, `maven.yaml`, `composer.yaml`, `nuget.yaml`

### Vendor-Specific Files

Software vendors that maintain their own repositories have dedicated files:

- **`hashicorp-apt.yaml`** - HashiCorp's apt repositories (Terraform, Vault, Consul, etc.)
- **`docker-apt.yaml`** - Docker's apt repositories (Docker Engine, containerd, etc.)
- **Additional vendor files can be added as needed**

## Repository Naming Convention

### OS Distribution Repositories

Format: `{provider}-{os}-{codename}`

Examples:
- `apt-ubuntu-jammy` - Ubuntu 22.04 (Jammy) apt repository
- `apt-debian-bookworm` - Debian 12 (Bookworm) apt repository
- `dnf-fedora-39` - Fedora 39 dnf repository
- `brew-macos` - macOS Homebrew repository

### Vendor-Specific Repositories

Format: `{vendor}-{provider}-{os}-{codename}`

Examples:
- `hashicorp-apt-ubuntu-jammy` - HashiCorp's apt repository for Ubuntu 22.04
- `docker-apt-debian-bookworm` - Docker's apt repository for Debian 12
- `postgresql-apt-ubuntu-noble` - PostgreSQL's apt repository for Ubuntu 24.04

## Repository Configuration Structure

Each repository entry must include:

```yaml
version: "1.0"
repositories:
  - name: "{provider}-{os}-{codename}"
    type: "{provider}"                    # apt, dnf, brew, etc.
    platform: "{platform}"                # linux, macos, windows
    distribution: ["{os}"]                # ubuntu, debian, fedora, etc.
    architecture: ["{arch1}", "{arch2}"]  # amd64, arm64, etc.
    
    # Version to codename mapping (REQUIRED for OS-specific repos)
    version_mapping:
      "{version}": "{codename}"           # e.g., "22.04": "jammy"
    
    # End-of-life status (default: false)
    eol: false
    
    # Query type: bulk_download or api (default: bulk_download)
    query_type: "bulk_download"
    
    # Repository endpoints
    endpoints:
      packages: "{package_list_url}"      # URL to package list
      search: "{search_url}"              # Optional search URL
      info: "{info_url}"                  # Optional info URL
    
    # Parsing configuration
    parsing:
      format: "{format}"                  # debian_packages, rpm_primary, etc.
      compression: "{compression}"        # gzip, xz, bzip2, none
      encoding: "utf-8"
      fields:                             # Field mappings
        name: "Package"
        version: "Version"
        description: "Description"
        # ... additional fields
    
    # Cache settings
    cache:
      ttl_hours: 24                       # Cache time-to-live
      max_size_mb: 100                    # Maximum cache size
    
    # Rate limiting
    limits:
      requests_per_minute: 60
      timeout_seconds: 300
    
    # Metadata
    metadata:
      description: "{description}"
      maintainer: "{maintainer}"
      priority: 90                        # 100 for vendor repos, 90 for OS repos
      enabled: true
      official: true
      url: "{documentation_url}"
```

## Key Fields

### version_mapping

Maps OS version numbers to distribution codenames. Each repository should have ONE mapping entry since each repository represents a specific OS version.

Examples:
```yaml
# Ubuntu repositories
version_mapping:
  "20.04": "focal"      # Ubuntu 20.04 → focal
  "22.04": "jammy"      # Ubuntu 22.04 → jammy
  "24.04": "noble"      # Ubuntu 24.04 → noble

# Debian repositories
version_mapping:
  "11": "bullseye"      # Debian 11 → bullseye
  "12": "bookworm"      # Debian 12 → bookworm

# Fedora repositories
version_mapping:
  "39": "f39"           # Fedora 39 → f39
  "40": "f40"           # Fedora 40 → f40
```

### eol (End-of-Life)

Indicates whether the OS version is end-of-life:
- `false` - Active, supported OS version (default)
- `true` - End-of-life OS version (still accessible but no longer supported)

### query_type

Determines how packages are queried:
- `bulk_download` - Download full package list (apt, dnf, etc.)
- `api` - Query per-package via API (npm, pip, cargo, etc.)

### priority

Controls repository query order (higher priority = queried first):
- **100** - Vendor-specific upstream repositories (highest)
- **90** - Official OS repositories
- **80** - Community repositories
- **70** - Third-party repositories

## Adding New Repositories

### Step 1: Choose the Correct File

- For OS distribution repositories: Add to provider-specific file (e.g., `apt.yaml`, `dnf.yaml`)
- For vendor repositories: Create or add to vendor-specific file (e.g., `hashicorp-apt.yaml`)

### Step 2: Gather Repository Information

Collect the following details:
1. Repository URL and structure
2. Supported OS versions and codenames
3. Supported architectures
4. Package list format and compression
5. Official documentation URL

### Step 3: Add Repository Entry

Add a new repository entry following the structure above. Ensure:
- Unique repository name following naming convention
- Correct version_mapping for the OS version
- Appropriate priority (100 for vendor repos, 90 for OS repos)
- Valid endpoints and parsing configuration

### Step 4: Test the Configuration

```bash
# Validate configuration syntax
python -c "import yaml; yaml.safe_load(open('saigen/repositories/configs/{file}.yaml'))"

# List repositories to verify it's loaded
saigen repositories list-repos | grep {repository_name}

# Test package search
saigen repositories search --repository {repository_name} {package}
```

## Multiple Repositories Per Provider-OS

SAIGEN supports multiple repositories for the same provider-OS combination. This enables:

1. **Vendor + OS repositories**: Query both vendor-specific and OS repositories
2. **Priority-based selection**: Higher priority repositories are queried first
3. **Fallback behavior**: If package not found, try next repository

Example:
```yaml
# In apt.yaml - OS repository (priority 90)
- name: "apt-ubuntu-jammy"
  metadata:
    priority: 90

# In hashicorp-apt.yaml - Vendor repository (priority 100)
- name: "hashicorp-apt-ubuntu-jammy"
  metadata:
    priority: 100
```

When querying for Terraform on Ubuntu 22.04:
1. First tries: `hashicorp-apt-ubuntu-jammy` (priority 100)
2. If not found, tries: `apt-ubuntu-jammy` (priority 90)

## Common Vendor Repositories

### Software with Official Repositories

Many popular software projects provide official repositories:

- **HashiCorp**: Terraform, Vault, Consul, Nomad, Packer
- **Docker**: Docker Engine, Docker Compose, containerd
- **PostgreSQL**: PostgreSQL database server
- **MongoDB**: MongoDB Community and Enterprise
- **Nginx**: Nginx web server (mainline and stable)
- **MariaDB**: MariaDB database server
- **Elastic**: Elasticsearch, Logstash, Kibana
- **Grafana**: Grafana, Loki, Tempo
- **Node.js**: Node.js runtime (via NodeSource)
- **Kubernetes**: kubectl, kubeadm, kubelet

### Adding Vendor Repositories

To add a vendor repository:

1. Create a new file: `{vendor}-{provider}.yaml`
2. Add repository entries for each OS version
3. Set priority to 100 (higher than OS repositories)
4. Document the vendor's official repository URL

See `hashicorp-apt.yaml` and `docker-apt.yaml` for examples.

## Best Practices

### Configuration

1. **Use HTTPS**: Always use HTTPS endpoints for security
2. **Verify URLs**: Test repository URLs before adding
3. **Document sources**: Include official documentation URLs
4. **Set appropriate priority**: Vendor repos = 100, OS repos = 90
5. **Mark EOL versions**: Set `eol: true` for end-of-life OS versions

### Maintenance

1. **Regular testing**: Verify repository connectivity periodically
2. **Update version_mapping**: Add new OS versions as released
3. **Monitor EOL dates**: Mark repositories as EOL when appropriate
4. **Keep documentation current**: Update URLs and descriptions

### Security

1. **HTTPS only**: Never use HTTP for repository endpoints
2. **Verify authenticity**: Ensure repositories are from official sources
3. **Monitor changes**: Watch for unexpected repository changes
4. **Enable checksums**: Use checksum validation where available

## Troubleshooting

### Configuration Errors

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('saigen/repositories/configs/{file}.yaml'))"

# Check for duplicate repository names
grep -h "name:" saigen/repositories/configs/*.yaml | sort | uniq -d

# Verify version_mapping format
grep -A 2 "version_mapping:" saigen/repositories/configs/{file}.yaml
```

### Repository Not Loading

```bash
# List all loaded repositories
saigen repositories list-repos

# Check for specific repository
saigen repositories list-repos | grep {repository_name}

# View detailed repository information
saigen repositories list-repos --detailed
```

### Endpoint Issues

```bash
# Test repository endpoint connectivity
curl -I {repository_packages_url}

# Download and inspect package list
curl {repository_packages_url} | gunzip | head -n 50

# Verify parsing format
# Check if package list matches expected format (debian_packages, rpm_primary, etc.)
```

## Examples

### Example 1: Adding Ubuntu 26.04 Repository

```yaml
# In apt.yaml
- name: "apt-ubuntu-oracular"
  type: "apt"
  platform: "linux"
  distribution: ["ubuntu"]
  architecture: ["amd64", "arm64", "armhf"]
  
  version_mapping:
    "26.04": "oracular"
  
  eol: false
  query_type: "bulk_download"
  
  endpoints:
    packages: "http://archive.ubuntu.com/ubuntu/dists/oracular/main/binary-{arch}/Packages.gz"
  
  # ... rest of configuration
  
  metadata:
    description: "Ubuntu 26.04 (Oracular) Main Repository"
    priority: 90
```

### Example 2: Adding HashiCorp Repository

```yaml
# In hashicorp-apt.yaml
- name: "hashicorp-apt-ubuntu-jammy"
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
  
  # ... rest of configuration
  
  metadata:
    description: "HashiCorp Official Repository for Ubuntu 22.04"
    maintainer: "HashiCorp"
    priority: 100  # Higher than OS repositories
    official: true
```

### Example 3: Marking EOL Repository

```yaml
# In apt.yaml
- name: "apt-ubuntu-bionic"
  type: "apt"
  platform: "linux"
  distribution: ["ubuntu"]
  
  version_mapping:
    "18.04": "bionic"
  
  eol: true  # Mark as end-of-life
  
  endpoints:
    packages: "http://archive.ubuntu.com/ubuntu/dists/bionic/main/binary-{arch}/Packages.gz"
  
  metadata:
    description: "Ubuntu 18.04 (Bionic) Main Repository - EOL"
    priority: 85  # Lower priority for EOL versions
```

## Additional Resources

- [Upstream Repositories Guide](../docs/upstream-repositories-guide.md)
- [Repository Configuration Schema](../../schemas/repository-config-schema.json)
- [Repository Management Guide](../docs/repository-management.md)
- [Refresh Versions Command](../docs/refresh-versions-command.md)
