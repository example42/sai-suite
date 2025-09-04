# Repository Management Migration Guide

This guide explains how to migrate from the legacy repository system to the new universal YAML-driven system.

## Overview

The new repository management system provides:

- **Universal Support**: 50+ package managers via YAML configuration
- **No Code Changes**: Add new repositories without writing Python code
- **Consistent Interface**: Same API for all repository types
- **Better Performance**: Optimized caching and concurrent operations
- **Enhanced Security**: Built-in validation and rate limiting

## Migration Steps

### 1. Update Your Code

Replace the old `RepositoryManager` with `EnhancedRepositoryManager`:

```python
# Old way
from saigen.repositories.manager import RepositoryManager

manager = RepositoryManager(cache_dir, config_dir)

# New way
from saigen.repositories.manager import EnhancedRepositoryManager

manager = EnhancedRepositoryManager(
    cache_dir=cache_dir,
    config_dir=config_dir,
    use_universal=True  # Enable new system
)
```

### 2. Convert Repository Configurations

The new system uses YAML configuration files instead of hardcoded downloaders.

#### Old System (Python Code)
```python
# Custom downloader class required
class CustomRepositoryDownloader(BaseRepositoryDownloader):
    async def download_package_list(self):
        # Custom implementation
        pass
```

#### New System (YAML Configuration)
```yaml
version: "1.0"
repositories:
  - name: "custom-repo"
    type: "generic"
    platform: "linux"
    endpoints:
      packages: "https://example.com/packages.json"
    parsing:
      format: "json"
      fields:
        name: "name"
        version: "version"
        description: "description"
```

### 3. Use Built-in Configurations

The new system includes comprehensive configurations for major package managers:

```bash
# List available repositories
saigen repositories list-repos

# Search across all repositories
saigen repositories search "redis"

# Get repository statistics
saigen repositories stats
```

### 4. Configuration Directory Structure

Organize your repository configurations:

```
~/.saigen/config/repositories/
├── linux-repositories.yaml      # Linux package managers
├── macos-repositories.yaml      # macOS package managers  
├── windows-repositories.yaml    # Windows package managers
├── language-repositories.yaml   # Language-specific (npm, pypi, etc.)
└── custom-repositories.yaml     # Your custom repositories
```

## Configuration Examples

### Basic Repository Configuration

```yaml
version: "1.0"
repositories:
  - name: "my-repo"
    type: "generic"
    platform: "linux"
    endpoints:
      packages: "https://repo.example.com/packages.json"
    parsing:
      format: "json"
      fields:
        name: "name"
        version: "version"
        description: "description"
    metadata:
      description: "My Custom Repository"
      priority: 80
      enabled: true
```

### Advanced Configuration with Authentication

```yaml
version: "1.0"
repositories:
  - name: "private-repo"
    type: "generic"
    platform: "universal"
    endpoints:
      packages: "https://private.example.com/api/packages"
      search: "https://private.example.com/api/search?q={query}"
    parsing:
      format: "json"
      fields:
        name: "name"
        version: "latest_version"
        description: "description"
    auth:
      type: "bearer"
      token: "${PRIVATE_REPO_TOKEN}"
    cache:
      ttl_hours: 4
      max_size_mb: 100
    limits:
      requests_per_minute: 100
      timeout_seconds: 300
    metadata:
      description: "Private Repository"
      priority: 100
      enabled: true
```

### XML Repository Configuration

```yaml
version: "1.0"
repositories:
  - name: "xml-repo"
    type: "generic"
    platform: "linux"
    endpoints:
      packages: "https://repo.example.com/metadata.xml"
    parsing:
      format: "xml"
      patterns:
        package_xpath: ".//package"
      fields:
        name: "@name"
        version: "@version"
        description: "description"
        homepage: "homepage"
    metadata:
      description: "XML-based Repository"
      priority: 70
      enabled: true
```

## API Changes

### Repository Manager Methods

Most methods remain the same, but with enhanced capabilities:

```python
# Get packages (same API)
packages = await manager.get_packages("ubuntu-main")

# Search packages (enhanced with more filters)
result = await manager.search_packages(
    query="redis",
    platform="linux",
    repository_type="apt"
)

# Get statistics (enhanced data)
stats = await manager.get_statistics()
```

### New Methods

```python
# Get supported platforms
platforms = manager.get_supported_platforms()
# Returns: ['linux', 'macos', 'windows', 'universal']

# Get supported repository types  
types = manager.get_supported_types()
# Returns: ['apt', 'brew', 'npm', 'pypi', ...]

# Filter repositories
repos = manager.get_all_repository_info(
    platform="linux",
    repository_type="apt"
)
```

## CLI Commands

### List Repositories
```bash
# List all repositories
saigen repositories list-repos

# Filter by platform
saigen repositories list-repos --platform linux

# Filter by type
saigen repositories list-repos --type apt

# JSON output
saigen repositories list-repos --format json
```

### Search Packages
```bash
# Search across all repositories
saigen repositories search "redis"

# Search with filters
saigen repositories search "nginx" --platform linux --limit 10

# JSON output
saigen repositories search "docker" --format json
```

### Repository Statistics
```bash
# Show overall statistics
saigen repositories stats

# Platform-specific statistics
saigen repositories stats --platform linux

# JSON output for automation
saigen repositories stats --format json
```

### Package Information
```bash
# Get package details
saigen repositories info "redis"

# Specific version
saigen repositories info "redis" --version "6.2.0"

# Platform filter
saigen repositories info "nginx" --platform linux
```

### Cache Management
```bash
# Update all repository caches
saigen repositories update-cache

# Update specific repository
saigen repositories update-cache --repository ubuntu-main

# Force update
saigen repositories update-cache --force
```

## Backward Compatibility

The `EnhancedRepositoryManager` maintains backward compatibility:

```python
# This still works
manager = EnhancedRepositoryManager(
    cache_dir=cache_dir,
    config_dir=config_dir,
    use_universal=False  # Use legacy system
)
```

## Performance Improvements

The new system provides significant performance improvements:

- **Concurrent Operations**: Multiple repositories processed in parallel
- **Intelligent Caching**: Smart cache invalidation and updates
- **Streaming Parsers**: Memory-efficient processing of large repositories
- **Connection Pooling**: Optimized HTTP connections
- **Rate Limiting**: Built-in protection against API limits

## Security Enhancements

- **URL Validation**: Only safe URL schemes allowed
- **Size Limits**: Protection against DoS attacks
- **Authentication**: Support for various auth methods
- **Input Validation**: Comprehensive validation of all inputs

## Troubleshooting

### Common Issues

1. **Repository Not Found**
   ```bash
   # Check available repositories
   saigen repositories list-repos
   
   # Verify configuration
   saigen repositories stats
   ```

2. **Authentication Errors**
   ```bash
   # Check environment variables
   echo $PRIVATE_REPO_TOKEN
   
   # Verify auth configuration in YAML
   ```

3. **Cache Issues**
   ```bash
   # Clear and update cache
   saigen repositories update-cache --force
   ```

4. **Performance Issues**
   ```bash
   # Check repository statistics
   saigen repositories stats
   
   # Update cache for faster access
   saigen repositories update-cache
   ```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
saigen --verbose repositories search "package-name"
```

## Best Practices

1. **Configuration Organization**: Group repositories by platform or type
2. **Cache Management**: Set appropriate TTL values based on update frequency
3. **Rate Limiting**: Configure limits to respect API quotas
4. **Authentication**: Use environment variables for sensitive tokens
5. **Monitoring**: Regularly check repository statistics and health

## Getting Help

- Check the [Repository Configuration Schema](../schemas/repository-config-schema.json)
- Review [example configurations](../examples/repository-configs/)
- Use `saigen repositories --help` for CLI help
- Enable verbose mode for detailed logging