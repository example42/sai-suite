# Saidata Schema 0.3 Guide

Complete guide to the saidata schema version 0.3, including new features, template functions, and migration information.

## Table of Contents

- [Overview](#overview)
- [What's New in Schema 0.3](#whats-new-in-schema-03)
- [Package Structure](#package-structure)
- [Installation Methods](#installation-methods)
- [Template Functions](#template-functions)
- [Provider Overrides](#provider-overrides)
- [Examples](#examples)
- [Migration from 0.2](#migration-from-02)

## Overview

Schema 0.3 introduces significant enhancements to the saidata format, providing more flexibility and power for software management across different platforms and installation methods.

**Key Improvements:**
- Multiple installation methods (packages, sources, binaries, scripts)
- Enhanced package structure with logical and actual names
- New template functions for flexible configuration
- Provider-specific overrides for all resource types
- URL templating with platform/architecture detection

## What's New in Schema 0.3

### 1. Multiple Installation Methods

Schema 0.3 supports four installation methods:

- **Packages**: Traditional package manager installation
- **Sources**: Build from source code
- **Binaries**: Download and install pre-compiled binaries
- **Scripts**: Execute installation scripts

### 2. Enhanced Package Structure

Packages now distinguish between:
- **`name`**: Logical identifier for cross-referencing
- **`package_name`**: Actual package name used by package managers

This allows the same logical name to map to different package names across providers.

### 3. New Template Functions

- `sai_package(index, field, provider)` - Enhanced with field parameter
- `sai_source(index, field, provider)` - Access source configurations
- `sai_binary(index, field, provider)` - Access binary configurations
- `sai_script(index, field, provider)` - Access script configurations

### 4. Provider Overrides

All resource types (packages, sources, binaries, scripts) can now have provider-specific overrides.

### 5. URL Templating

URLs support dynamic placeholders:
- `{{version}}` - Software version
- `{{platform}}` - Target platform (linux, darwin, windows)
- `{{architecture}}` - Target architecture (amd64, arm64, etc.)

## Package Structure

### Basic Package Definition

```yaml
version: "0.3"

metadata:
  name: nginx
  description: "High-performance HTTP server"

packages:
  - name: nginx              # Logical name for cross-referencing
    package_name: nginx      # Actual package name for package managers
    version: "1.24.0"
```

### Package with Provider Overrides

```yaml
packages:
  - name: nginx
    package_name: nginx
    version: "1.24.0"

providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx-full  # Different package name for apt
        version: "1.24.0-1ubuntu1"
  
  brew:
    packages:
      - name: nginx
        package_name: nginx       # Same package name for brew
        version: "1.24.0"
```

## Installation Methods

### 1. Source Builds

Build software from source code with configurable build systems.

```yaml
sources:
  - name: main
    url: "https://nginx.org/download/nginx-{{version}}.tar.gz"
    version: "1.24.0"
    build_system: autotools
    configure_args:
      - "--with-http_ssl_module"
      - "--with-http_v2_module"
    build_args:
      - "-j4"
    prerequisites:
      - build-essential
      - libssl-dev
    checksum: "sha256:abc123..."
```

**Supported Build Systems:**
- `autotools` - GNU Autotools (./configure, make, make install)
- `cmake` - CMake build system
- `make` - Plain Makefile
- `meson` - Meson build system
- `ninja` - Ninja build system
- `custom` - Custom build commands

**Key Fields:**
- `url` - Source download URL (supports templating)
- `build_system` - Build system type
- `configure_args` - Arguments for configure step
- `build_args` - Arguments for build step
- `install_args` - Arguments for install step
- `prerequisites` - Required packages for building
- `checksum` - Source checksum for verification

### 2. Binary Downloads

Download and install pre-compiled binaries.

```yaml
binaries:
  - name: main
    url: "https://releases.example.com/{{version}}/app_{{version}}_{{platform}}_{{architecture}}.zip"
    version: "1.5.0"
    platform: linux
    architecture: amd64
    checksum: "sha256:def456..."
    install_path: "/usr/local/bin"
    executable: "app"
    archive:
      format: "zip"
      strip_prefix: "app-1.5.0/"
    permissions: "0755"
```

**Key Fields:**
- `url` - Binary download URL (supports templating)
- `platform` - Target platform (linux, darwin, windows)
- `architecture` - Target architecture (amd64, arm64, etc.)
- `install_path` - Installation directory
- `executable` - Executable file name
- `archive` - Archive extraction configuration
- `permissions` - File permissions (octal format)
- `checksum` - Binary checksum for verification

### 3. Script Installations

Execute installation scripts with security features.

```yaml
scripts:
  - name: official
    url: "https://get.example.com/install.sh"
    version: "1.0.0"
    interpreter: bash
    checksum: "sha256:ghi789..."
    arguments:
      - "--channel"
      - "stable"
    environment:
      INSTALL_DIR: "/usr/local"
    timeout: 600
```

**Key Fields:**
- `url` - Script download URL
- `interpreter` - Script interpreter (bash, sh, python, etc.)
- `arguments` - Script arguments
- `environment` - Environment variables
- `working_dir` - Working directory for execution
- `timeout` - Execution timeout in seconds
- `checksum` - Script checksum for verification

## Template Functions

Template functions provide dynamic access to saidata fields in provider configurations.

### sai_package()

Get package field values with provider-specific lookup.

**Syntax:**
```
sai_package(index_or_wildcard, field, provider)
```

**Parameters:**
- `index_or_wildcard`: `0`, `1`, `2`, ... or `'*'` for all packages
- `field`: Field to extract (`'package_name'`, `'name'`, `'version'`, etc.)
- `provider`: Provider name for provider-specific lookup (optional)

**Examples:**
```yaml
# Get first package name for apt
command: "apt-get install -y {{sai_package(0, 'package_name', 'apt')}}"

# Get all package names for apt (space-separated)
command: "apt-get install -y {{sai_package('*', 'package_name', 'apt')}}"

# Get logical name
command: "echo Installing {{sai_package(0, 'name')}}"

# Get version
command: "apt-get install -y {{sai_package(0, 'package_name', 'apt')}}={{sai_package(0, 'version')}}"
```

**Available Fields:**
- `name` - Logical name
- `package_name` - Actual package name
- `version` - Package version
- `alternatives` - Alternative package names
- `repository` - Repository name
- `checksum` - Package checksum
- `signature` - Package signature
- `download_url` - Download URL

### sai_source()

Get source build configuration fields.

**Syntax:**
```
sai_source(index, field, provider)
```

**Examples:**
```yaml
# Download source tarball
command: "wget {{sai_source(0, 'url', 'source')}}"

# Get build system
command: "echo Build system: {{sai_source(0, 'build_system')}}"

# Get version
command: "echo Version: {{sai_source(0, 'version')}}"
```

**Available Fields:**
- `name` - Logical name
- `url` - Download URL
- `version` - Source version
- `build_system` - Build system type
- `build_dir` - Build directory
- `source_dir` - Source directory
- `install_prefix` - Installation prefix
- `checksum` - Source checksum

### sai_binary()

Get binary download configuration fields.

**Syntax:**
```
sai_binary(index, field, provider)
```

**Examples:**
```yaml
# Download binary
command: "curl -L {{sai_binary(0, 'url', 'binary')}} -o app.zip"

# Get platform
command: "echo Platform: {{sai_binary(0, 'platform')}}"

# Get architecture
command: "echo Architecture: {{sai_binary(0, 'architecture')}}"
```

**Available Fields:**
- `name` - Logical name
- `url` - Download URL
- `version` - Binary version
- `platform` - Target platform
- `architecture` - Target architecture
- `install_path` - Installation path
- `executable` - Executable name
- `checksum` - Binary checksum

### sai_script()

Get script installation configuration fields.

**Syntax:**
```
sai_script(index, field, provider)
```

**Examples:**
```yaml
# Download and execute installation script
command: "curl -fsSL {{sai_script(0, 'url', 'script')}} | {{sai_script(0, 'interpreter')}}"

# Get interpreter
command: "echo Interpreter: {{sai_script(0, 'interpreter')}}"

# Get timeout
command: "echo Timeout: {{sai_script(0, 'timeout')}}"
```

**Available Fields:**
- `name` - Logical name
- `url` - Script URL
- `version` - Script version
- `interpreter` - Script interpreter
- `checksum` - Script checksum
- `timeout` - Execution timeout

### Template Resolution Order

Template functions follow a hierarchical resolution order with OS-specific overrides:

1. **OS-specific provider overrides**: `saidata.providers.{provider}.{resource_type}` from OS override file
2. **Default provider overrides**: `saidata.providers.{provider}.{resource_type}` from default file
3. **OS-specific defaults**: `saidata.{resource_type}` from OS override file
4. **Base defaults**: `saidata.{resource_type}` from default file

**Example:**

For `{{sai_package(0, 'package_name', 'apt')}}` on Ubuntu 22.04:

1. Check `software/ap/apache/ubuntu/22.04.yaml` → `providers.apt.packages[0].package_name`
2. Check `software/ap/apache/default.yaml` → `providers.apt.packages[0].package_name`
3. Check `software/ap/apache/ubuntu/22.04.yaml` → `packages[0].package_name`
4. Check `software/ap/apache/default.yaml` → `packages[0].package_name`

## Provider Overrides

Provider overrides allow customization of all resource types for specific providers.

### Package Overrides

```yaml
packages:
  - name: nginx
    package_name: nginx

providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx-full
        version: "1.24.0-1ubuntu1"
  
  brew:
    packages:
      - name: nginx
        package_name: nginx
        version: "1.24.0"
```

### Source Overrides

```yaml
sources:
  - name: main
    url: "https://example.com/source.tar.gz"
    build_system: autotools

providers:
  source:
    sources:
      - name: main
        configure_args:
          - "--prefix=/usr/local"
          - "--enable-feature"
```

### Binary Overrides

```yaml
binaries:
  - name: main
    url: "https://example.com/binary.zip"

providers:
  binary:
    binaries:
      - name: main
        install_path: "/opt/app"
        permissions: "0755"
```

### Script Overrides

```yaml
scripts:
  - name: official
    url: "https://example.com/install.sh"

providers:
  script:
    scripts:
      - name: official
        timeout: 1200
        environment:
          CUSTOM_VAR: "value"
```

## Examples

See the [examples directory](examples/) for complete examples:

- [saidata-schema-0.3-complete.yaml](examples/saidata-schema-0.3-complete.yaml) - Complete example with all features
- [saidata-simple-package.yaml](examples/saidata-simple-package.yaml) - Minimal package example
- [saidata-source-build.yaml](examples/saidata-source-build.yaml) - Source build example
- [saidata-binary-download.yaml](examples/saidata-binary-download.yaml) - Binary download example
- [saidata-script-install.yaml](examples/saidata-script-install.yaml) - Script installation example

## Migration from 0.2

### Key Changes

1. **Package Structure**: Add `package_name` field to all packages
2. **Version Field**: Update version from `"0.2"` to `"0.3"`
3. **Template Functions**: Update `sai_package()` calls to include field parameter
4. **New Resources**: Optionally add sources, binaries, or scripts

### Migration Steps

#### Step 1: Update Version

```yaml
# Before (0.2)
version: "0.2"

# After (0.3)
version: "0.3"
```

#### Step 2: Add package_name Field

```yaml
# Before (0.2)
packages:
  - name: nginx
    version: "1.24.0"

# After (0.3)
packages:
  - name: nginx              # Logical name
    package_name: nginx      # Actual package name
    version: "1.24.0"
```

#### Step 3: Update Template Functions (Provider YAML)

```yaml
# Before (0.2)
command: "apt-get install -y {{sai_package(saidata, 'apt', 0)}}"

# After (0.3)
command: "apt-get install -y {{sai_package(0, 'package_name', 'apt')}}"
```

#### Step 4: Add Installation Methods (Optional)

```yaml
# Add source build support
sources:
  - name: main
    url: "https://example.com/source-{{version}}.tar.gz"
    build_system: autotools

# Add binary download support
binaries:
  - name: main
    url: "https://example.com/binary-{{version}}_{{platform}}_{{architecture}}.zip"

# Add script installation support
scripts:
  - name: official
    url: "https://example.com/install.sh"
    interpreter: bash
```

### Backward Compatibility

**Note:** Schema 0.3 is not backward compatible with 0.2. All saidata files must be updated to use the 0.3 format.

The main breaking changes are:
1. `package_name` field is now required for all packages
2. Template function signature changed from `sai_package(context, provider, index)` to `sai_package(index, field, provider)`

## Best Practices

### 1. Always Provide Both Names

```yaml
packages:
  - name: nginx              # Logical name for cross-referencing
    package_name: nginx      # Actual package name
```

### 2. Use Checksums for Security

```yaml
sources:
  - name: main
    url: "https://example.com/source.tar.gz"
    checksum: "sha256:abc123..."  # Always include checksums

binaries:
  - name: main
    url: "https://example.com/binary.zip"
    checksum: "sha256:def456..."

scripts:
  - name: official
    url: "https://example.com/install.sh"
    checksum: "sha256:ghi789..."
```

### 3. Use URL Templating

```yaml
binaries:
  - name: main
    url: "https://releases.example.com/{{version}}/app_{{version}}_{{platform}}_{{architecture}}.zip"
    version: "1.5.0"
```

### 4. Specify Prerequisites

```yaml
sources:
  - name: main
    url: "https://example.com/source.tar.gz"
    build_system: autotools
    prerequisites:
      - build-essential
      - libssl-dev
      - libpcre3-dev
```

### 5. Set Timeouts for Scripts

```yaml
scripts:
  - name: official
    url: "https://example.com/install.sh"
    interpreter: bash
    timeout: 600  # 10 minutes
```

### 6. Use Provider Overrides

```yaml
providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx-full  # Use full version on Ubuntu
  
  brew:
    packages:
      - name: nginx
        package_name: nginx       # Use standard version on macOS
```

## See Also

- [CLI Reference](cli-reference.md) - Complete command reference
- [Template Engine](template-engine.md) - Template engine documentation
- [Examples](examples/) - Complete examples
- [Schema Definition](../../schemas/saidata-0.3-schema.json) - JSON schema file
