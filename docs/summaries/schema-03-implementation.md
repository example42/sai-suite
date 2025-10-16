# Schema 0.3 Implementation Guide

**Date**: 2025-10-16  
**Purpose**: Document schema 0.3 structure and implementation approach for SAI

## Summary

SAI uses saidata schema 0.3 exclusively. This document provides guidance on the schema structure, key concepts, and implementation details.

**Note**: Backward compatibility with schema 0.2 is not required. All saidata files use schema 0.3.

## Schema 0.3 Key Features

### 1. Package Structure
- **name**: Logical identifier for cross-referencing within saidata
- **package_name**: Actual package name used by package managers
- Both fields are required

**Example:**
```yaml
packages:
  - name: nginx
    package_name: nginx
```

**Provider Override:**
```yaml
providers:
  brew:
    packages:
      - name: nginx
        package_name: nginx-full  # Different package name for brew
```

### 2. Installation Methods

**Packages** - Traditional package manager installation:
```yaml
packages:
  - name: nginx
    package_name: nginx
```

**Sources** - Build from source code:
```yaml
sources:
  - name: main
    url: "https://nginx.org/download/nginx-{{version}}.tar.gz"
    build_system: autotools
    checksum: "sha256:abc123..."
```

**Binaries** - Pre-compiled executable downloads:
```yaml
binaries:
  - name: main
    url: "https://releases.example.com/{{version}}/app_{{platform}}_{{architecture}}.tar.gz"
    checksum: "sha256:def456..."
    install_path: "/usr/local/bin"
```

**Scripts** - Installation script execution:
```yaml
scripts:
  - name: official
    url: "https://get.example.com/install.sh"
    checksum: "sha256:ghi789..."
    interpreter: bash
    timeout: 600
```

### 3. URL Templating

URLs support dynamic placeholders:
- `{{version}}` - Software version
- `{{platform}}` - OS platform (linux, darwin, windows)
- `{{architecture}}` - CPU architecture (amd64, arm64, 386)

**Example:**
```yaml
url: "https://releases.example.com/{{version}}/app_{{platform}}_{{architecture}}.tar.gz"
```

### 4. Security Features

- **Checksums**: Required for sources, binaries, and scripts
- **Format**: `algorithm:hash` (e.g., `sha256:abc123...`)
- **Validation**: Verified before installation/execution

## Template Functions

### Package Functions
```yaml
# Get single package field
{{sai_package(0, 'package_name', 'apt')}}

# Get all package names
{{sai_package('*', 'package_name', 'apt')}}

# Get logical name
{{sai_package(0, 'name')}}
```

### Installation Method Functions
```yaml
# Source build
{{sai_source(0, 'url', 'source')}}

# Binary download
{{sai_binary(0, 'url', 'binary')}}

# Script installation
{{sai_script(0, 'url', 'script')}}
```

### Function Signature
```
function_name(index_or_wildcard, field, provider_name)
```

Where:
- `index_or_wildcard`: `0`, `1`, `2`, ... or `'*'` for all
- `field`: Field name to extract
- `provider_name`: Provider for provider-specific lookup (optional)

## Implementation Components

### 1. Data Models (sai/models/saidata.py)

**New Models:**
- `Source` - Source build configuration
- `Binary` - Binary download configuration
- `Script` - Script installation configuration
- `BuildSystem` - Enum for build systems
- `CustomCommands` - Custom command overrides
- `ArchiveConfig` - Archive extraction configuration

**Updated Models:**
- `Package` - Added `package_name` field (required)
- `ProviderConfig` - Added `sources`, `binaries`, `scripts` arrays
- `SaiData` - Added top-level `sources`, `binaries`, `scripts` arrays

### 2. Schema Validation (sai/core/saidata_loader.py)

**Updates:**
- Use `saidata-0.3-schema.json` for validation
- Validate `package_name` field presence
- Validate new resource types (sources, binaries, scripts)
- Provide clear error messages for missing fields

### 3. Template Engine (sai/providers/template_engine.py)

**New Functions:**
- `sai_source()` - Access source configurations
- `sai_binary()` - Access binary configurations
- `sai_script()` - Access script configurations

**Updated Functions:**
- `sai_package()` - Added `field` parameter for field selection

**Context Builder:**
- Include `sources`, `binaries`, `scripts` arrays
- Convert new models to dictionaries
- Support provider-specific lookups

### 4. Provider YAML Files

**Updated Syntax:**
```yaml
# Old approach (not used)
command: "apt-get install -y {{saidata.packages.*.name}}"

# Current approach
command: "apt-get install -y {{sai_package('*', 'package_name', 'apt')}}"
```

## Development Guidelines

### For Saidata Authors

1. **Always use schema 0.3**:
   ```yaml
   version: "0.3"
   ```

2. **Provide both name and package_name**:
   ```yaml
   packages:
     - name: nginx
       package_name: nginx
   ```

3. **Include checksums for security**:
   ```yaml
   sources:
     - name: main
       url: "..."
       checksum: "sha256:abc123..."
   ```

4. **Use URL templating**:
   ```yaml
   url: "https://example.com/{{version}}/app_{{platform}}_{{architecture}}.tar.gz"
   ```

### For Provider Authors

1. **Use explicit field parameters**:
   ```yaml
   command: "{{sai_package(0, 'package_name', 'apt')}}"
   ```

2. **Specify provider for lookups**:
   ```yaml
   command: "{{sai_package('*', 'package_name', 'apt')}}"
   ```

3. **Use appropriate functions**:
   - `sai_package()` for packages
   - `sai_source()` for source builds
   - `sai_binary()` for binary downloads
   - `sai_script()` for script installations

### For SAI Developers

1. **Schema validation**: Use `saidata-0.3-schema.json`
2. **Model validation**: Ensure both `name` and `package_name` are present
3. **Template resolution**: Support all new functions
4. **Error messages**: Provide clear guidance on schema 0.3 requirements

## Testing Strategy

### Unit Tests
- Model validation with schema 0.3 fields
- Template function resolution
- Context builder with new arrays
- Schema validation errors

### Integration Tests
- End-to-end saidata loading
- Provider action execution
- Source/binary/script provider functionality

### Test Fixtures
- Complete saidata examples
- Minimal package examples
- Source build examples
- Binary download examples
- Script installation examples

## Related Specifications

- `.kiro/specs/sai-schema-0.3-support/` - SAI implementation spec
- `.kiro/specs/saidata-schema-0.3-update/` - SAIGEN implementation spec
- `schemas/saidata-0.3-schema.json` - Official schema definition

## References

- Commit 9fb7a22: Updated providers with new template syntax
- Commit b2fc687: SAIGEN schema 0.3 support implementation
- Schema file: `schemas/saidata-0.3-schema.json`
- Steering documents: `.kiro/steering/tech.md`, `.kiro/steering/product.md`
