# Repository Configuration Examples

Examples of SAIGEN repository configurations for different package managers.

## Files

### comprehensive-example.yaml
Comprehensive example showing all available repository configuration options.

Includes:
- Multiple repository types (apt, dnf, brew, npm, pypi, etc.)
- Custom parsers and downloaders
- Cache configuration
- URL templates
- Metadata extraction

### repository-config.yaml
Basic repository configuration example.

Shows:
- Simple repository setup
- Common configuration options
- Basic cache settings

## Usage

```bash
# Use custom repository configuration
saigen --config repository-config.yaml generate nginx

# Update repositories with custom config
saigen --config repository-config.yaml repo update apt
```

## Configuration Format

Repository configurations use YAML format:

```yaml
repositories:
  apt:
    enabled: true
    cache_ttl: 86400
    url: "http://archive.ubuntu.com/ubuntu"
    
  brew:
    enabled: true
    cache_ttl: 3600
    url: "https://formulae.brew.sh/api"
```

## See Also

- [Repository Management Documentation](../../repository-management.md)
- [Repository Configuration Guide](../../repository-configuration.md)
- [Repository Troubleshooting](../../repository-troubleshooting.md)
- [SAIGEN Configuration Guide](../../configuration-guide.md)
