# Saidata 0.3 Schema Features Guide

This guide demonstrates the new features introduced in saidata schema version 0.3, with practical examples from the sample files.

## Table of Contents
- [Installation Methods](#installation-methods)
- [URL Templating](#url-templating)
- [Checksum Validation](#checksum-validation)
- [Enhanced Metadata](#enhanced-metadata)
- [Package Naming](#package-naming)

## Installation Methods

Schema 0.3 introduces three new installation methods beyond traditional package managers:

### 1. Source Compilation

Build software from source code with full control over compilation options.

**Example: Python with optimizations** (`py/python/default.yaml`)

```yaml
sources:
  - name: "python-source"
    url: "https://www.python.org/ftp/python/{{version}}/Python-{{version}}.tar.xz"
    version: "3.12.1"
    checksum: "sha256:9ed8b8e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0"
    build_system: "autotools"
    configure_args:
      - "--prefix=/usr/local"
      - "--enable-optimizations"
      - "--with-lto"
      - "--enable-shared"
    prerequisites:
      - "gcc"
      - "make"
      - "libssl-dev"
      - "zlib1g-dev"
    install_prefix: "/usr/local"
```

**Supported Build Systems:**
- `autotools` - GNU Autotools (./configure && make && make install)
- `cmake` - CMake build system
- `make` - Simple Makefile
- `meson` - Meson build system
- `ninja` - Ninja build system
- `custom` - Custom build commands

**Example: Go with custom build** (`go/golang/default.yaml`)

```yaml
sources:
  - name: "golang-source"
    url: "https://go.dev/dl/go{{version}}.src.tar.gz"
    version: "1.21.5"
    build_system: "custom"
    custom_commands:
      build: "cd src && ./make.bash"
      install: "mkdir -p /usr/local/go && cp -r . /usr/local/go/"
      validation: "cd src && ./run.bash"
    prerequisites: ["gcc", "make"]
    environment:
      GOROOT: "/usr/local/go"
      PATH: "$PATH:/usr/local/go/bin"
```

### 2. Binary Downloads

Download and install pre-compiled binaries with platform/architecture detection.

**Example: Terraform** (`te/terraform/default.yaml`)

```yaml
binaries:
  - name: "terraform"
    url: "https://releases.hashicorp.com/terraform/{{version}}/terraform_{{version}}_{{platform}}_{{architecture}}.zip"
    version: "1.5.0"
    checksum: "sha256:9e9f3e6750a640d3f27f9b5f6b1e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e"
    archive:
      format: "zip"
      strip_components: 0
    install_path: "/usr/local/bin/terraform"
    platform_map:
      linux: "linux"
      darwin: "darwin"
      windows: "windows"
    architecture_map:
      amd64: "amd64"
      arm64: "arm64"
```

**Archive Formats Supported:**
- `tar.gz` - Gzip compressed tar
- `tar.bz2` - Bzip2 compressed tar
- `tar.xz` - XZ compressed tar
- `zip` - ZIP archive
- `7z` - 7-Zip archive
- `none` - No archive (direct binary)

**Example: Node.js with verification** (`no/nodejs/default.yaml`)

```yaml
binaries:
  - name: "nodejs-binary"
    url: "https://nodejs.org/dist/v{{version}}/node-v{{version}}-{{platform}}-{{architecture}}.tar.xz"
    version: "20.10.0"
    checksum: "sha256:b2f6b9f8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0"
    archive:
      format: "tar.xz"
      strip_components: 1
    install_path: "/usr/local"
    post_install:
      - "npm config set prefix /usr/local"
    verification:
      command: "node --version"
      expected_output: "v{{version}}"
```

### 3. Script Installation

Execute installation scripts with security controls and verification.

**Example: NVM (Node Version Manager)** (`no/nodejs/default.yaml`)

```yaml
scripts:
  - name: "nvm-installer"
    url: "https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh"
    checksum: "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    interpreter: "/bin/bash"
    arguments: []
    timeout: 300
    requires_root: false
    idempotent: true
    post_install:
      - "source ~/.nvm/nvm.sh"
      - "nvm install {{version}}"
      - "nvm use {{version}}"
    verification:
      command: "node --version"
      expected_output: "v{{version}}"
    environment:
      NVM_DIR: "$HOME/.nvm"
```

**Script Security Features:**
- `checksum` - Verify script integrity before execution
- `timeout` - Prevent hanging installations
- `requires_root` - Explicit privilege requirements
- `idempotent` - Safe to run multiple times
- `verification` - Confirm successful installation

## URL Templating

Use placeholders in URLs for dynamic version, platform, and architecture substitution.

### Available Placeholders

- `{{version}}` - Software version (e.g., "1.21.5")
- `{{platform}}` - Operating system (e.g., "linux", "darwin", "windows")
- `{{architecture}}` - CPU architecture (e.g., "amd64", "arm64")

### Platform Mapping

Map generic platform names to provider-specific values:

```yaml
platform_map:
  linux: "linux"
  darwin: "darwin"
  windows: "win"
```

### Architecture Mapping

Map generic architecture names to provider-specific values:

```yaml
architecture_map:
  amd64: "x64"
  arm64: "arm64"
  armv7l: "armv7l"
```

### Example: Go Binary URL

```yaml
url: "https://go.dev/dl/go{{version}}.{{platform}}-{{architecture}}.tar.gz"
```

Resolves to:
- Linux AMD64: `https://go.dev/dl/go1.21.5.linux-amd64.tar.gz`
- macOS ARM64: `https://go.dev/dl/go1.21.5.darwin-arm64.tar.gz`
- Windows AMD64: `https://go.dev/dl/go1.21.5.windows-amd64.tar.gz`

## Checksum Validation

All downloads (sources, binaries, scripts) support checksum validation for security.

### Format

```
algorithm:hash
```

### Supported Algorithms

- `sha256` - SHA-256 (64 hex characters)
- `sha512` - SHA-512 (128 hex characters)
- `md5` - MD5 (32 hex characters) - not recommended

### Examples

```yaml
# SHA-256 (recommended)
checksum: "sha256:9e9f3e6750a640d3f27f9b5f6b1e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e"

# SHA-512 (more secure)
checksum: "sha512:abc123...def456"  # 128 hex characters

# MD5 (legacy, not recommended)
checksum: "md5:5d41402abc4b2a76b9719d911017c592"
```

### Validation Process

1. Download file
2. Calculate checksum
3. Compare with expected value
4. Abort if mismatch detected

## Enhanced Metadata

Schema 0.3 adds comprehensive metadata fields for better software documentation.

### Security Metadata

```yaml
metadata:
  security:
    security_contact: "security@example.com"
    vulnerability_disclosure: "https://example.com/security"
    sbom_url: "https://example.com/sbom.json"
    signing_key: "https://example.com/gpg-key.asc"
    cve_exceptions: ["CVE-2023-1234"]
```

### Extended URLs

```yaml
metadata:
  urls:
    website: "https://example.com"
    documentation: "https://docs.example.com"
    source: "https://github.com/example/project"
    issues: "https://github.com/example/project/issues"
    support: "https://example.com/support"
    download: "https://example.com/download"
    changelog: "https://example.com/changelog"
    license: "https://example.com/LICENSE"
    sbom: "https://example.com/sbom.json"
    icon: "https://example.com/icon.png"
```

## Package Naming

Schema 0.3 requires both logical and actual package names for clarity.

### Structure

```yaml
packages:
  - name: "logical-name"        # Component/role name
    package_name: "actual-name"  # Real package name in repository
    version: "1.0.0"
```

### Examples

**Simple case** (nginx):
```yaml
packages:
  - name: "nginx"
    package_name: "nginx"
    version: "1.24.0"
```

**Multi-component** (MongoDB):
```yaml
packages:
  - name: "server"
    package_name: "mongodb-org-server"
    version: "7.0.0"
  - name: "shell"
    package_name: "mongodb-org-shell"
    version: "7.0.0"
  - name: "tools"
    package_name: "mongodb-org-tools"
    version: "7.0.0"
```

**Provider-specific** (Node.js on Ubuntu):
```yaml
providers:
  apt:
    packages:
      - name: "nodejs"
        package_name: "nodejs"  # Ubuntu package name
        version: "20.10.0"
```

## Complete Examples

See these sample files for comprehensive 0.3 feature demonstrations:

### Sources + Binaries + Scripts
- `go/golang/default.yaml` - All three installation methods
- `no/nodejs/default.yaml` - All three installation methods
- `py/python/default.yaml` - Sources and scripts

### Binary Downloads
- `te/terraform/default.yaml` - URL templating with platform/arch mapping

### Traditional Packages
- `ng/nginx/default.yaml` - Package manager installation
- `do/docker/default.yaml` - Multi-package configuration
- `mo/mongodb/default.yaml` - Multi-component packages

## Migration from 0.2

Key changes when migrating from 0.2 to 0.3:

1. **Add package_name field**:
   ```yaml
   # 0.2
   packages:
     - name: "nginx"
   
   # 0.3
   packages:
     - name: "nginx"
       package_name: "nginx"
   ```

2. **Update version**:
   ```yaml
   version: "0.3"
   ```

3. **Consider new installation methods**:
   - Add `sources` for compilation options
   - Add `binaries` for direct downloads
   - Add `scripts` for installer scripts

4. **Use URL templating**:
   ```yaml
   url: "https://example.com/{{version}}/app-{{platform}}-{{architecture}}.tar.gz"
   ```

5. **Add checksums**:
   ```yaml
   checksum: "sha256:abc123..."
   ```

## Validation

Validate your 0.3 saidata files:

```bash
saigen validate path/to/saidata.yaml
```

The validator checks:
- Schema compliance
- URL template syntax
- Checksum format
- Required fields
- Enum values

## Best Practices

1. **Always include checksums** for security
2. **Use URL templates** for multi-platform support
3. **Provide multiple installation methods** when available
4. **Document prerequisites** for source builds
5. **Include verification commands** for scripts
6. **Set appropriate timeouts** for long-running operations
7. **Use sha256 or sha512** for checksums (not md5)
8. **Test on multiple platforms** before publishing

## Resources

- [Saidata Schema 0.3 Specification](../schemas/saidata-0.3-schema.json)
- [Sample Files](../docs/saidata_samples/)
- [Migration Guide](../docs/SAIDATA_SAMPLES_MIGRATION.md)
- [Validation Guide](../docs/validation-guide.md)
