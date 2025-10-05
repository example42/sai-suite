# Repository Management Guide

## Overview

SAIGEN supports multiple package repositories to gather comprehensive software metadata. The repository system provides caching, configurable parsing, and support for various data formats.

## Supported Repository Types

### Built-in Repository Types
- **apt** - Debian/Ubuntu APT repositories
- **brew** - Homebrew formulae (macOS/Linux)
- **winget** - Windows Package Manager
- **dnf/yum** - Red Hat/Fedora repositories
- **pacman** - Arch Linux repositories
- **generic** - Custom repositories with configurable parsing

### Repository Configuration

Repositories are configured in the main SAIGEN configuration file under the `repositories` section:

```yaml
repositories:
  repository-name:
    name: repository-name
    type: apt|brew|winget|dnf|generic
    platform: linux|macos|windows
    url: https://repository.url/path
    enabled: true|false
    priority: 1-100
    cache_ttl_hours: 24
    timeout: 300
    architecture: [amd64, arm64]
    parsing:
      # Parsing configuration (see below)
    credentials:
      # Optional authentication
    metadata:
      description: "Repository description"
      maintainer: "Maintainer name"
```

## Parsing Configuration

### Text Format Parsing
For repositories that provide plain text package lists:

```yaml
parsing:
  format: text
  line_pattern: '^Package:\s*(.+)$'
  name_group: 1
  version_pattern: '^Version:\s*(.+)$'
  version_group: 1
  description_pattern: '^Description:\s*(.+)$'
  description_group: 1
```

### JSON Format Parsing
For JSON-based APIs:

```yaml
parsing:
  format: json
  package_path: [packages]  # Path to package array
  field_mapping:
    name: package_name
    version: latest_version
    description: summary
    homepage: project_url
    maintainer: author
```

### XML Format Parsing
For XML-based repositories:

```yaml
parsing:
  format: xml
  package_xpath: './/package'
  xml_field_mapping:
    name: name
    version: 'version/@ver'
    description: description
```

### YAML Format Parsing
For YAML-based repositories:

```yaml
parsing:
  format: yaml
  package_path: [packages]
  field_mapping:
    name: name
    version: version
    description: description
```

## Cache Management

### Cache Configuration
```yaml
cache:
  directory: ~/.saigen/cache
  max_size_mb: 1000
  default_ttl: 3600
  cleanup_interval: 86400
```

### Cache Commands
```bash
# View cache statistics
saigen repo stats

# Update specific repository cache
saigen repo update ubuntu-main

# Update all repository caches
saigen repo update --all

# Clear cache for specific repository
saigen repo clear ubuntu-main

# Clear all caches
saigen repo clear --all

# List cached repositories
saigen repo list --cached
```

## Repository Security

### Authentication
For repositories requiring authentication:

```yaml
repositories:
  private-repo:
    name: private-repo
    type: generic
    url: https://private.repo.com/api/packages
    credentials:
      username: "${REPO_USERNAME}"
      password: "${REPO_PASSWORD}"
      api_key: "${REPO_API_KEY}"
```

### Security Best Practices
1. Use environment variables for credentials
2. Set appropriate cache TTL values
3. Validate repository URLs and certificates
4. Monitor cache size and cleanup regularly
5. Use HTTPS URLs when possible

## Custom Repository Implementation

### Generic Repository Example
```yaml
repositories:
  custom-api:
    name: custom-api
    type: generic
    platform: linux
    url: https://api.example.com/v1/packages
    enabled: true
    priority: 5
    cache_ttl_hours: 6
    timeout: 120
    parsing:
      format: json
      package_path: [data, packages]
      field_mapping:
        name: pkg_name
        version: current_version
        description: short_desc
        homepage: website
        license: license_type
        size: package_size
        dependencies: deps
        tags: categories
    metadata:
      description: Custom Package API
      maintainer: Example Corp
      api_version: v1
```

### Custom Parser Function
For complex parsing requirements, you can implement custom parsers:

```python
def custom_parser(content: str, repository_info: RepositoryInfo) -> List[RepositoryPackage]:
    """Custom parser for specialized repository formats."""
    packages = []
    # Custom parsing logic here
    return packages

# Register in configuration
repositories:
  custom-format:
    parsing:
      format: custom
      custom_parser: my_module.custom_parser
```

## Troubleshooting

### Common Issues

#### Repository Not Accessible
```bash
# Check repository configuration
saigen config show --section repositories

# Test repository connectivity
saigen repo test ubuntu-main

# Check cache status
saigen repo stats ubuntu-main
```

#### Parsing Errors
```bash
# Validate repository configuration
saigen config validate

# Check parsing with verbose output
saigen repo update ubuntu-main --verbose

# Test parsing with sample data
saigen repo parse-test ubuntu-main --sample-size 10
```

#### Cache Issues
```bash
# Clear corrupted cache
saigen repo clear ubuntu-main

# Rebuild cache
saigen repo update ubuntu-main --force

# Check cache directory permissions
ls -la ~/.saigen/cache/
```

### Performance Optimization

#### Cache Tuning
- Set appropriate `cache_ttl_hours` based on repository update frequency
- Monitor cache size with `saigen repo stats`
- Use `cleanup_interval` to automatically remove expired entries

#### Concurrent Updates
```yaml
generation:
  parallel_requests: 3  # Limit concurrent repository requests
  request_timeout: 120  # Timeout for repository requests
```

#### Repository Priorities
Configure repository priorities to prefer faster or more reliable sources:

```yaml
repositories:
  fast-mirror:
    priority: 10  # Higher priority
  slow-mirror:
    priority: 5   # Lower priority
```

## Integration with Generation

Repositories are automatically used during saidata generation:

```bash
# Generate using all enabled repositories
saigen generate nginx

# Generate using specific repositories
saigen generate nginx --repositories ubuntu-main,homebrew-core

# Generate with repository data context
saigen generate nginx --use-repository-context
```

The generation engine will:
1. Query enabled repositories for package information
2. Use cached data when available
3. Include repository metadata in LLM context
4. Validate generated saidata against repository data