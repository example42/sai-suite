# Software-Specific Upstream Repositories Guide

## Overview

In addition to OS distribution repositories (apt, dnf, brew, etc.), SAIGEN supports software-specific upstream repositories provided by software vendors. These repositories allow you to query package information directly from the software vendor's official repository, which is particularly useful for:

- Software that maintains its own package repositories (HashiCorp, Docker, MongoDB, etc.)
- Getting the latest versions before they're available in OS repositories
- Accessing vendor-specific package variants
- Supporting software with multiple installation methods

## Repository Naming Convention

Software-specific upstream repositories follow the naming pattern:

```
{vendor}-{provider}-{os}-{codename}
```

Examples:
- `hashicorp-apt-ubuntu-jammy` - HashiCorp's apt repository for Ubuntu 22.04
- `docker-apt-debian-bookworm` - Docker's apt repository for Debian 12
- `mongodb-yum-rhel-8` - MongoDB's yum repository for RHEL 8
- `postgresql-apt-ubuntu-noble` - PostgreSQL's apt repository for Ubuntu 24.04

## Multiple Repositories Per Provider-OS Combination

SAIGEN supports multiple repositories for the same provider-OS combination. This allows you to:

1. **Query both OS and vendor repositories**: Check both Ubuntu's nginx package and nginx.org's official repository
2. **Prioritize repositories**: Use priority field to control which repository is queried first
3. **Fallback behavior**: If a package isn't found in the primary repository, try the next one

### Repository Priority

Repositories are queried in order of priority (higher priority first):

- **Priority 100**: Vendor-specific upstream repositories (highest)
- **Priority 90**: Official OS repositories (Ubuntu, Debian, etc.)
- **Priority 80**: Community repositories
- **Priority 70**: Third-party repositories

## Configuration Examples

### HashiCorp Repository

HashiCorp provides official repositories for their tools (Terraform, Vault, Consul, etc.):

```yaml
version: "1.0"
repositories:
  # HashiCorp apt repository for Ubuntu 22.04
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
      search: "https://apt.releases.hashicorp.com/"
    
    parsing:
      format: "debian_packages"
      compression: "gzip"
      encoding: "utf-8"
      fields:
        name: "Package"
        version: "Version"
        description: "Description"
        maintainer: "Maintainer"
        homepage: "Homepage"
    
    cache:
      ttl_hours: 24
      max_size_mb: 50
    
    limits:
      requests_per_minute: 60
      timeout_seconds: 300
    
    metadata:
      description: "HashiCorp Official Repository for Ubuntu 22.04"
      maintainer: "HashiCorp"
      priority: 100  # Higher priority than OS repositories
      enabled: true
      official: true
      url: "https://www.hashicorp.com/official-packaging-guide"
  
  # HashiCorp apt repository for Ubuntu 24.04
  - name: "hashicorp-apt-ubuntu-noble"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    architecture: ["amd64", "arm64"]
    
    version_mapping:
      "24.04": "noble"
    
    eol: false
    query_type: "bulk_download"
    
    endpoints:
      packages: "https://apt.releases.hashicorp.com/dists/noble/main/binary-{arch}/Packages.gz"
      search: "https://apt.releases.hashicorp.com/"
    
    parsing:
      format: "debian_packages"
      compression: "gzip"
      encoding: "utf-8"
      fields:
        name: "Package"
        version: "Version"
        description: "Description"
    
    cache:
      ttl_hours: 24
      max_size_mb: 50
    
    metadata:
      description: "HashiCorp Official Repository for Ubuntu 24.04"
      maintainer: "HashiCorp"
      priority: 100
      enabled: true
      official: true
```

### Docker Repository

Docker provides official repositories for Docker Engine and related tools:

```yaml
version: "1.0"
repositories:
  # Docker apt repository for Ubuntu 22.04
  - name: "docker-apt-ubuntu-jammy"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    architecture: ["amd64", "arm64", "armhf"]
    
    version_mapping:
      "22.04": "jammy"
    
    eol: false
    query_type: "bulk_download"
    
    endpoints:
      packages: "https://download.docker.com/linux/ubuntu/dists/jammy/stable/binary-{arch}/Packages.gz"
      search: "https://download.docker.com/linux/ubuntu/"
    
    parsing:
      format: "debian_packages"
      compression: "gzip"
      encoding: "utf-8"
    
    cache:
      ttl_hours: 24
      max_size_mb: 50
    
    metadata:
      description: "Docker Official Repository for Ubuntu 22.04"
      maintainer: "Docker Inc."
      priority: 100
      enabled: true
      official: true
      url: "https://docs.docker.com/engine/install/ubuntu/"
  
  # Docker apt repository for Debian 12
  - name: "docker-apt-debian-bookworm"
    type: "apt"
    platform: "linux"
    distribution: ["debian"]
    architecture: ["amd64", "arm64", "armhf"]
    
    version_mapping:
      "12": "bookworm"
    
    eol: false
    query_type: "bulk_download"
    
    endpoints:
      packages: "https://download.docker.com/linux/debian/dists/bookworm/stable/binary-{arch}/Packages.gz"
      search: "https://download.docker.com/linux/debian/"
    
    parsing:
      format: "debian_packages"
      compression: "gzip"
      encoding: "utf-8"
    
    cache:
      ttl_hours: 24
      max_size_mb: 50
    
    metadata:
      description: "Docker Official Repository for Debian 12"
      maintainer: "Docker Inc."
      priority: 100
      enabled: true
      official: true
```

### PostgreSQL Repository

PostgreSQL provides official repositories with the latest versions:

```yaml
version: "1.0"
repositories:
  # PostgreSQL apt repository for Ubuntu 22.04
  - name: "postgresql-apt-ubuntu-jammy"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    architecture: ["amd64", "arm64"]
    
    version_mapping:
      "22.04": "jammy-pgdg"
    
    eol: false
    query_type: "bulk_download"
    
    endpoints:
      packages: "https://apt.postgresql.org/pub/repos/apt/dists/jammy-pgdg/main/binary-{arch}/Packages.gz"
      search: "https://www.postgresql.org/download/linux/ubuntu/"
    
    parsing:
      format: "debian_packages"
      compression: "gzip"
      encoding: "utf-8"
    
    cache:
      ttl_hours: 24
      max_size_mb: 100
    
    metadata:
      description: "PostgreSQL Official Repository for Ubuntu 22.04"
      maintainer: "PostgreSQL Global Development Group"
      priority: 100
      enabled: true
      official: true
      url: "https://www.postgresql.org/download/"
```

### MongoDB Repository

MongoDB provides official repositories for MongoDB Community and Enterprise:

```yaml
version: "1.0"
repositories:
  # MongoDB yum repository for RHEL 8
  - name: "mongodb-yum-rhel-8"
    type: "yum"
    platform: "linux"
    distribution: ["rhel", "rocky", "alma"]
    architecture: ["x86_64", "aarch64"]
    
    version_mapping:
      "8": "8"
    
    eol: false
    query_type: "bulk_download"
    
    endpoints:
      packages: "https://repo.mongodb.org/yum/redhat/8/mongodb-org/7.0/{arch}/repodata/primary.xml.gz"
      search: "https://repo.mongodb.org/yum/redhat/"
    
    parsing:
      format: "rpm_primary"
      compression: "gzip"
      encoding: "utf-8"
    
    cache:
      ttl_hours: 24
      max_size_mb: 50
    
    metadata:
      description: "MongoDB Official Repository for RHEL 8"
      maintainer: "MongoDB Inc."
      priority: 100
      enabled: true
      official: true
      url: "https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-red-hat/"
```

### Nginx Repository

Nginx provides official repositories with mainline and stable versions:

```yaml
version: "1.0"
repositories:
  # Nginx apt repository for Ubuntu 22.04 (mainline)
  - name: "nginx-apt-ubuntu-jammy"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    architecture: ["amd64", "arm64"]
    
    version_mapping:
      "22.04": "jammy"
    
    eol: false
    query_type: "bulk_download"
    
    endpoints:
      packages: "https://nginx.org/packages/mainline/ubuntu/dists/jammy/nginx/binary-{arch}/Packages.gz"
      search: "https://nginx.org/packages/mainline/ubuntu/"
    
    parsing:
      format: "debian_packages"
      compression: "gzip"
      encoding: "utf-8"
    
    cache:
      ttl_hours: 24
      max_size_mb: 20
    
    metadata:
      description: "Nginx Official Repository (Mainline) for Ubuntu 22.04"
      maintainer: "Nginx Inc."
      priority: 100
      enabled: true
      official: true
      url: "https://nginx.org/en/linux_packages.html"
```

## Creating Upstream Repository Configurations

### Step 1: Identify the Repository

1. Check the software vendor's documentation for official repositories
2. Identify the repository URL and structure
3. Determine supported OS versions and architectures
4. Check if the repository uses standard formats (apt, yum, etc.)

### Step 2: Determine Repository Details

Gather the following information:

- **Repository URL**: Base URL for package lists
- **Supported OS versions**: Which OS versions are supported
- **Codenames**: OS version to codename mapping
- **Architecture**: Supported architectures (amd64, arm64, etc.)
- **Package format**: debian_packages, rpm_primary, etc.
- **Compression**: gzip, xz, bzip2, none

### Step 3: Create Configuration File

Choose the appropriate provider-specific configuration file:

- `saigen/repositories/configs/apt.yaml` - For apt-based repositories
- `saigen/repositories/configs/dnf.yaml` - For dnf/yum-based repositories
- `saigen/repositories/configs/zypper.yaml` - For zypper-based repositories

### Step 4: Add Repository Entry

Add a new repository entry to the configuration file:

```yaml
- name: "{vendor}-{provider}-{os}-{codename}"
  type: "{provider}"
  platform: "{platform}"
  distribution: ["{os}"]
  architecture: ["{arch1}", "{arch2}"]
  
  version_mapping:
    "{version}": "{codename}"
  
  eol: false
  query_type: "bulk_download"
  
  endpoints:
    packages: "{package_list_url}"
    search: "{search_url}"
  
  parsing:
    format: "{format}"
    compression: "{compression}"
    encoding: "utf-8"
  
  cache:
    ttl_hours: 24
    max_size_mb: 50
  
  limits:
    requests_per_minute: 60
    timeout_seconds: 300
  
  metadata:
    description: "{description}"
    maintainer: "{vendor}"
    priority: 100
    enabled: true
    official: true
    url: "{documentation_url}"
```

### Step 5: Test the Configuration

```bash
# List all repositories to verify it's loaded
saigen repositories list-repos

# Test querying a package from the new repository
saigen repositories search --repository {vendor}-{provider}-{os}-{codename} {package_name}

# Test refresh-versions with the new repository
saigen refresh-versions {saidata_file} --verbose
```

## Using Upstream Repositories with refresh-versions

When you run `saigen refresh-versions` on an OS-specific saidata file, SAIGEN will:

1. **Detect OS context** from the file path (e.g., `ubuntu/22.04.yaml`)
2. **Resolve repository names** for that OS version
3. **Query all matching repositories** in priority order:
   - First: Vendor-specific repositories (priority 100)
   - Then: Official OS repositories (priority 90)
   - Finally: Other repositories (priority < 90)
4. **Use the first match** found

### Example Workflow

```bash
# Refresh Terraform saidata for Ubuntu 22.04
# This will query both hashicorp-apt-ubuntu-jammy (priority 100)
# and apt-ubuntu-jammy (priority 90)
saigen refresh-versions software/te/terraform/ubuntu/22.04.yaml --verbose

# Output will show which repository was used:
# Querying repository: hashicorp-apt-ubuntu-jammy
# Found: terraform 1.6.5 in hashicorp-apt-ubuntu-jammy
```

## Repository Priority and Fallback

### Priority Levels

- **100**: Vendor upstream repositories (highest priority)
- **90**: Official OS repositories
- **80**: Community repositories
- **70**: Third-party repositories
- **60**: Experimental repositories

### Fallback Behavior

If a package is not found in the highest priority repository:

1. SAIGEN tries the next repository with lower priority
2. Continues until a match is found or all repositories are exhausted
3. Logs which repository provided the package (in verbose mode)
4. Returns None if no repository has the package

### Disabling Repositories

To temporarily disable a repository without removing it:

```yaml
metadata:
  enabled: false  # Set to false to disable
```

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
- **InfluxData**: InfluxDB, Telegraf, Chronograf
- **Redis**: Redis server
- **Node.js**: Node.js runtime (via NodeSource)
- **Kubernetes**: kubectl, kubeadm, kubelet

### Finding Official Repositories

Check the software's official documentation:

1. Look for "Installation" or "Download" pages
2. Search for "Official Repository" or "Package Repository"
3. Check for OS-specific installation guides
4. Look for repository setup scripts or instructions

## Best Practices

### Repository Configuration

1. **Use official repositories**: Only add repositories from trusted vendors
2. **Set appropriate priority**: Vendor repositories should have priority 100
3. **Document the source**: Include URL to vendor's documentation
4. **Test thoroughly**: Verify package queries work correctly
5. **Keep updated**: Monitor vendor repository changes

### Maintenance

1. **Regular testing**: Test repository connectivity periodically
2. **Version updates**: Update version_mapping when new OS versions are released
3. **EOL tracking**: Mark repositories as EOL when OS versions reach end-of-life
4. **Documentation**: Keep documentation URLs current

### Security

1. **HTTPS only**: Use HTTPS endpoints for all repositories
2. **Verify authenticity**: Ensure repositories are from official vendor domains
3. **Monitor changes**: Watch for unexpected repository changes
4. **Checksum validation**: Enable checksum validation where available

## Troubleshooting

### Repository Not Found

If SAIGEN can't find a vendor repository:

```bash
# List all repositories to verify it's loaded
saigen repositories list-repos | grep {vendor}

# Check repository configuration file
cat saigen/repositories/configs/{provider}.yaml | grep {vendor}

# Verify repository is enabled
saigen repositories list-repos --detailed | grep {vendor}
```

### Package Not Found

If a package isn't found in the vendor repository:

```bash
# Test repository connectivity
curl -I {repository_packages_url}

# Search for package manually
saigen repositories search --repository {vendor}-{provider}-{os} {package}

# Check if package name differs
# Vendor repositories may use different package names
```

### Priority Issues

If the wrong repository is being used:

```bash
# Check repository priorities
saigen repositories list-repos --detailed | grep priority

# Verify vendor repository has priority 100
# OS repositories should have priority 90

# Use --verbose to see which repository is queried
saigen refresh-versions {file} --verbose
```

## Examples

### Adding HashiCorp Repository for Multiple OS Versions

```yaml
# In saigen/repositories/configs/apt.yaml
repositories:
  # Ubuntu 20.04
  - name: "hashicorp-apt-ubuntu-focal"
    version_mapping:
      "20.04": "focal"
    endpoints:
      packages: "https://apt.releases.hashicorp.com/dists/focal/main/binary-{arch}/Packages.gz"
    metadata:
      priority: 100
  
  # Ubuntu 22.04
  - name: "hashicorp-apt-ubuntu-jammy"
    version_mapping:
      "22.04": "jammy"
    endpoints:
      packages: "https://apt.releases.hashicorp.com/dists/jammy/main/binary-{arch}/Packages.gz"
    metadata:
      priority: 100
  
  # Ubuntu 24.04
  - name: "hashicorp-apt-ubuntu-noble"
    version_mapping:
      "24.04": "noble"
    endpoints:
      packages: "https://apt.releases.hashicorp.com/dists/noble/main/binary-{arch}/Packages.gz"
    metadata:
      priority: 100
```

### Using Multiple Repositories for Same Software

```bash
# Terraform saidata will check both repositories:
# 1. hashicorp-apt-ubuntu-jammy (priority 100) - vendor repository
# 2. apt-ubuntu-jammy (priority 90) - OS repository

# Refresh will use HashiCorp's version if available
saigen refresh-versions software/te/terraform/ubuntu/22.04.yaml

# Result: Uses Terraform 1.6.5 from hashicorp-apt-ubuntu-jammy
# Instead of Terraform 1.3.0 from apt-ubuntu-jammy
```

## Additional Resources

- [Repository Configuration Schema](../../schemas/repository-config-schema.json)
- [Repository Management Guide](repository-management.md)
- [Refresh Versions Command Reference](refresh-versions-command.md)
- [SAIGEN CLI Reference](cli-reference.md)
