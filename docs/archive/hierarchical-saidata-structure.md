# Hierarchical Saidata Structure Guide

## Overview

SAI now uses a hierarchical directory structure for organizing saidata files, replacing the previous flat file structure. This new organization provides better scalability, maintainability, and performance as the number of software definitions grows.

## Directory Structure

### Hierarchical Layout

The new structure organizes saidata files using the first two letters of the software name:

```
software/
├── ap/
│   ├── apache/
│   │   └── default.yaml
│   ├── apt/
│   │   └── default.yaml
│   └── aptitude/
│       └── default.yaml
├── do/
│   ├── docker/
│   │   └── default.yaml
│   └── dovecot/
│       └── default.yaml
├── ng/
│   └── nginx/
│       └── default.yaml
├── my/
│   ├── mysql/
│   │   └── default.yaml
│   └── mytop/
│       └── default.yaml
└── re/
    ├── redis/
    │   └── default.yaml
    └── redmine/
        └── default.yaml
```

### Path Resolution Rules

SAI resolves saidata paths using the following algorithm:

1. **Extract Prefix**: Take the first two letters of the software name (lowercase)
2. **Build Path**: Construct path as `software/{prefix}/{software_name}/default.yaml`
3. **Search Locations**: Search in configured saidata paths in order of precedence

### Examples

| Software Name | Prefix | Hierarchical Path |
|---------------|--------|-------------------|
| `nginx` | `ng` | `software/ng/nginx/default.yaml` |
| `apache` | `ap` | `software/ap/apache/default.yaml` |
| `docker` | `do` | `software/do/docker/default.yaml` |
| `mysql` | `my` | `software/my/mysql/default.yaml` |
| `redis` | `re` | `software/re/redis/default.yaml` |
| `postgresql` | `po` | `software/po/postgresql/default.yaml` |
| `kubernetes` | `ku` | `software/ku/kubernetes/default.yaml` |
| `elasticsearch` | `el` | `software/el/elasticsearch/default.yaml` |

## Search Precedence

### Path Search Order

SAI searches for saidata files in the following order:

1. **Local Overrides**: Current directory (`./`)
2. **User Saidata**: User-specific directory (`~/.sai/saidata/`)
3. **Repository Cache**: Cached repository data (`~/.sai/cache/repositories/`)
4. **System Saidata**: System-wide directories

### File Precedence Rules

When multiple saidata files exist for the same software:

1. **Higher precedence paths** override lower precedence paths
2. **Files are merged** when compatible
3. **Conflicts resolved** by taking higher precedence values
4. **Clear error messages** provided for resolution conflicts

### Example Search

For `nginx`, SAI searches in order:

```
1. ./software/ng/nginx/default.yaml                    # Local override
2. ~/.sai/saidata/software/ng/nginx/default.yaml      # User saidata
3. ~/.sai/cache/repositories/main/software/ng/nginx/default.yaml  # Repository
4. /usr/local/share/sai/saidata/software/ng/nginx/default.yaml    # System
```

## Repository Integration

### Repository Structure

The default repository (`https://github.com/example42/saidata`) uses the hierarchical structure:

```
saidata-repository/
├── software/
│   ├── ap/
│   │   ├── apache/
│   │   │   └── default.yaml
│   │   └── apt/
│   │       └── default.yaml
│   ├── do/
│   │   └── docker/
│   │       └── default.yaml
│   └── ng/
│       └── nginx/
│           └── default.yaml
├── providers/
│   ├── apt.yaml
│   ├── brew.yaml
│   └── winget.yaml
└── README.md
```

### Cache Organization

Repository data is cached locally maintaining the hierarchical structure:

```
~/.sai/cache/repositories/
├── saidata-main/                    # Default repository cache
│   ├── software/
│   │   ├── ap/
│   │   │   └── apache/
│   │   │       └── default.yaml
│   │   └── ng/
│   │       └── nginx/
│   │           └── default.yaml
│   └── .repository_metadata
└── custom-repo-branch/              # Custom repository cache
    └── software/
        └── ...
```

## Migration from Flat Structure

### Automatic Migration

SAI handles migration automatically:

1. **Hierarchical First**: Always searches hierarchical structure first
2. **Flat Fallback**: Falls back to flat structure if hierarchical not found
3. **Clear Messages**: Provides clear error messages when files are missing
4. **No Breaking Changes**: Existing flat files continue to work

### Migration Process

The migration process is transparent to users:

```bash
# SAI automatically searches:
# 1. software/ng/nginx/default.yaml  (hierarchical - preferred)
# 2. nginx.yaml                      (flat - fallback)
# 3. Error if neither found

sai install nginx  # Works with either structure
```

### Manual Migration

To manually migrate from flat to hierarchical structure:

```bash
#!/bin/bash
# Migration script example

# Create hierarchical directories
mkdir -p software/{a..z}{a..z}

# Move flat files to hierarchical structure
for file in *.yaml; do
    name=$(basename "$file" .yaml)
    prefix=${name:0:2}
    mkdir -p "software/$prefix/$name"
    mv "$file" "software/$prefix/$name/default.yaml"
done
```

## Creating Saidata Files

### File Location

Create saidata files in the hierarchical structure:

```bash
# For nginx saidata
mkdir -p software/ng/nginx/
vim software/ng/nginx/default.yaml
```

### File Content

Saidata files use the same format regardless of structure:

```yaml
# software/ng/nginx/default.yaml
version: "0.2"
metadata:
  name: nginx
  description: "High-performance HTTP server and reverse proxy"
  homepage: "https://nginx.org/"
  license: "BSD-2-Clause"
  
packages:
  - name: nginx
    version: "1.20.1"
    
providers:
  apt:
    packages:
      - name: nginx
        version: "1.20.1"
  brew:
    packages:
      - name: nginx
        version: "1.21.0"
        
actions:
  install:
    apt: "apt-get install -y nginx"
    brew: "brew install nginx"
  start:
    systemd: "systemctl start nginx"
    brew: "brew services start nginx"
```

## Best Practices

### Directory Organization

1. **Consistent Naming**: Use lowercase software names
2. **Standard Structure**: Always use `software/{prefix}/{name}/default.yaml`
3. **Clear Prefixes**: Ensure prefixes are meaningful and consistent
4. **Avoid Conflicts**: Check for existing software with same prefix

### File Management

1. **Single Source**: Keep one authoritative saidata file per software
2. **Version Control**: Use git for tracking changes to saidata files
3. **Documentation**: Document custom saidata files and their purpose
4. **Testing**: Test saidata files before deploying to production

### Repository Management

1. **Fork Repository**: Create organization fork for customizations
2. **Branch Strategy**: Use feature branches for saidata updates
3. **Pull Requests**: Use PRs for reviewing saidata changes
4. **Automated Testing**: Set up CI/CD for saidata validation

## Advanced Usage

### Custom Hierarchical Structures

For organizations with specific needs:

```yaml
# Custom saidata paths with hierarchical structure
saidata_paths:
  - "./custom-saidata"                    # Local overrides
  - "~/.sai/company-saidata"             # Company-specific
  - "~/.sai/cache/repositories/"          # Repository cache
```

### Multiple File Support

Future support for multiple files per software:

```
software/ng/nginx/
├── default.yaml      # Main saidata file
├── enterprise.yaml   # Enterprise-specific configuration
└── minimal.yaml      # Minimal installation variant
```

### Namespace Support

Potential future support for namespaced software:

```
software/
├── apache/
│   ├── httpd/
│   │   └── default.yaml
│   └── kafka/
│       └── default.yaml
└── nginx/
    ├── nginx/
    │   └── default.yaml
    └── nginx-plus/
        └── default.yaml
```

## Troubleshooting

### Common Issues

#### "Saidata not found"

**Cause**: Software not available in hierarchical structure

**Solution**:
```bash
# Check expected path
ls ~/.sai/cache/repositories/*/software/ng/nginx/

# Search for software
find ~/.sai/cache/repositories/ -name "*nginx*" -type f

# Update repository
sai repository update --force
```

#### "Path resolution failed"

**Cause**: Issues with hierarchical path construction

**Solution**:
```bash
# Check software name
echo "nginx" | cut -c1-2  # Should output "ng"

# Verify directory structure
ls ~/.sai/cache/repositories/*/software/ng/

# Use verbose mode
sai info nginx --verbose
```

#### "Multiple saidata files found"

**Cause**: Conflicts between different precedence levels

**Solution**:
```bash
# Check all locations
find . ~/.sai/ -name "*nginx*" -path "*/software/*" -type f

# Remove conflicting files
rm ./software/ng/nginx/default.yaml  # Remove local override

# Use specific path
sai info nginx --saidata-path ~/.sai/cache/repositories/main/
```

### Debug Information

Get detailed path resolution information:

```bash
# Enable debug logging
export SAI_LOG_LEVEL=debug

# Run with verbose output
sai --verbose info nginx

# Check repository status
sai repository status --detailed
```

## Performance Considerations

### Benefits of Hierarchical Structure

1. **Faster Lookups**: Direct path construction instead of directory scanning
2. **Better Caching**: More efficient filesystem caching
3. **Reduced I/O**: Fewer directory traversals
4. **Scalability**: Handles thousands of software definitions efficiently

### Performance Optimization

1. **SSD Storage**: Use SSD for cache directory for better performance
2. **Cache Warming**: Pre-populate cache with frequently used saidata
3. **Parallel Operations**: Enable parallel saidata loading when possible
4. **Memory Caching**: Cache frequently accessed saidata in memory

## Future Enhancements

### Planned Features

1. **Multiple File Support**: Support for variant-specific saidata files
2. **Namespace Support**: Hierarchical namespaces for software organization
3. **Symlink Support**: Symbolic links for software aliases
4. **Index Files**: Directory indexes for faster discovery
5. **Compression**: Compressed saidata files for reduced storage

### Compatibility

The hierarchical structure is designed to be:

1. **Backward Compatible**: Existing flat files continue to work
2. **Forward Compatible**: Extensible for future enhancements
3. **Tool Agnostic**: Works with standard filesystem tools
4. **Version Control Friendly**: Git-friendly directory structure

## Resources

### Related Documentation

- [Repository Configuration Guide](./repository-configuration.md)
- [Repository Troubleshooting](./repository-troubleshooting.md)
- [Configuration Guide](./configuration-guide.md)
- [Command Reference](./command-reference.md)

### Tools and Scripts

```bash
# Validate hierarchical structure
find software/ -name "default.yaml" | while read file; do
    echo "Validating: $file"
    sai validate "$file"
done

# Generate directory structure
for letter1 in {a..z}; do
    for letter2 in {a..z}; do
        mkdir -p "software/$letter1$letter2"
    done
done

# Find software by prefix
find software/ -maxdepth 2 -type d -name "ng*" | sort
```