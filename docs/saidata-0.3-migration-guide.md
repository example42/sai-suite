# SaiData 0.3 Migration Guide

This guide helps you migrate from previous saidata schema versions to the new 0.3 format.

## Overview of Changes

The 0.3 schema introduces significant new capabilities while maintaining the core structure of saidata files. The main changes include:

### New Installation Methods
- **Sources**: Build software from source code
- **Binaries**: Download and install pre-compiled binaries
- **Scripts**: Execute installation scripts with security measures

### Enhanced Security
- Security metadata with CVE exceptions and contacts
- Checksum validation for all downloadable resources
- SBOM (Software Bill of Materials) support

### URL Templating
- Dynamic URL generation with placeholders
- Cross-platform binary downloads
- Version-specific resource URLs

### Enhanced Provider Configuration
- Provider-specific overrides for all resource types
- Package sources with priority settings
- Repository configurations with enhanced metadata

## Migration Steps

### Step 1: Update Version Field

Change the version field from your current version to "0.3":

```yaml
# Before (0.2 or earlier)
version: "0.2"

# After (0.3)
version: "0.3"
```

### Step 2: Enhance Metadata

Add new security and URL fields to your metadata:

```yaml
# Before
metadata:
  name: "nginx"
  description: "HTTP server"
  urls:
    website: "https://nginx.org"
    documentation: "https://nginx.org/docs"

# After - Enhanced with 0.3 fields
metadata:
  name: "nginx"
  description: "HTTP server"
  urls:
    website: "https://nginx.org"
    documentation: "https://nginx.org/docs"
    source: "https://github.com/nginx/nginx"
    issues: "https://trac.nginx.org/nginx"
    support: "https://nginx.org/support"
    download: "https://nginx.org/download"
    changelog: "https://nginx.org/CHANGES"
    license: "https://nginx.org/LICENSE"
    sbom: "https://nginx.org/sbom"
    icon: "https://nginx.org/favicon.ico"
  security:
    security_contact: "security-alert@nginx.org"
    vulnerability_disclosure: "https://nginx.org/security"
    cve_exceptions: ["CVE-2021-23017"]
```

### Step 3: Add New Installation Methods

#### Adding Source Compilation

If your software can be built from source, add a sources section:

```yaml
sources:
  - name: "main"
    url: "https://nginx.org/download/nginx-{{version}}.tar.gz"
    version: "1.24.0"
    build_system: "autotools"
    configure_args:
      - "--with-http_ssl_module"
      - "--with-http_v2_module"
    prerequisites:
      - "build-essential"
      - "libssl-dev"
    checksum: "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7"
```

#### Adding Binary Downloads

For software with pre-compiled binaries:

```yaml
binaries:
  - name: "main"
    url: "https://releases.example.com/{{version}}/app_{{platform}}_{{architecture}}.zip"
    version: "1.0.0"
    checksum: "sha256:fa16d72a078210a54c47dd5bef2f8b9b8a01d94909a51453956b3ec6442ea4c5"
    install_path: "/usr/local/bin"
    executable: "app"
    archive:
      format: "zip"
    permissions: "0755"
```

#### Adding Script Installation

For software with installation scripts:

```yaml
scripts:
  - name: "official"
    url: "https://get.example.com/install.sh"
    checksum: "sha256:def456abc789012345678901234567890123456789012345678901234567890123"
    interpreter: "bash"
    timeout: 300
    arguments: ["--version", "1.0.0"]
    environment:
      INSTALL_DIR: "/usr/local/bin"
```

### Step 4: Enhance Provider Configurations

Update provider configurations to support new installation methods:

```yaml
# Before
providers:
  apt:
    packages:
      - name: "nginx"
        package_name: "nginx"

# After - Enhanced with 0.3 features
providers:
  apt:
    repositories:
      - name: "nginx-official"
        url: "https://nginx.org/packages/ubuntu"
        key: "https://nginx.org/keys/nginx_signing.key"
        type: "upstream"
        recommended: true
        packages:
          - name: "nginx"
            package_name: "nginx"
            version: "1.24.0-1~jammy"
    
    # Provider-specific source builds
    sources:
      - name: "main"
        configure_args:
          - "--prefix=/etc/nginx"
          - "--with-http_ssl_module"
    
    # Provider-specific binaries
    binaries:
      - name: "main"
        install_path: "/usr/sbin"
```

### Step 5: Add Compatibility Matrix

Define compatibility across providers and platforms:

```yaml
compatibility:
  matrix:
    - provider: "apt"
      platform: ["ubuntu", "debian"]
      architecture: ["amd64", "arm64"]
      supported: true
      recommended: true
      tested: true
    
    - provider: "binary"
      platform: ["linux", "darwin", "windows"]
      architecture: ["amd64", "arm64"]
      supported: true
      recommended: true
      notes: "Cross-platform binaries available"
  
  versions:
    latest: "1.24.0"
    minimum: "1.18.0"
    latest_lts: "1.22.1"
    latest_minimum: "1.24.0"
```

## URL Templating Migration

### Before: Static URLs

```yaml
# 0.2 format with static URLs
packages:
  - name: "terraform"
    download_url: "https://releases.hashicorp.com/terraform/1.5.0/terraform_1.5.0_linux_amd64.zip"
```

### After: Dynamic URL Templates

```yaml
# 0.3 format with templating
binaries:
  - name: "main"
    url: "https://releases.hashicorp.com/terraform/{{version}}/terraform_{{version}}_{{platform}}_{{architecture}}.zip"
    version: "1.5.0"
```

This allows the same configuration to work across:
- Multiple versions: `1.5.0`, `1.6.0`, etc.
- Multiple platforms: `linux`, `darwin`, `windows`
- Multiple architectures: `amd64`, `arm64`, `386`

## Security Enhancements

### Adding Checksums

All downloadable resources should include checksums:

```yaml
sources:
  - name: "main"
    url: "https://example.com/source.tar.gz"
    checksum: "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7"

binaries:
  - name: "main"
    url: "https://example.com/binary.zip"
    checksum: "sha256:fa16d72a078210a54c47dd5bef2f8b9b8a01d94909a51453956b3ec6442ea4c5"

scripts:
  - name: "installer"
    url: "https://example.com/install.sh"
    checksum: "sha256:def456abc789012345678901234567890123456789012345678901234567890123"
```

### Security Metadata

Add comprehensive security information:

```yaml
metadata:
  security:
    security_contact: "security@example.com"
    vulnerability_disclosure: "https://example.com/security"
    cve_exceptions:
      - "CVE-2023-1234"  # Fixed in version 1.2.3
    signing_key: "https://example.com/gpg-key"
    sbom_url: "https://example.com/sbom/{{version}}"
```

## Validation and Testing

### Validate Your Migrated Files

Use the saigen validate command to check your migrated files:

```bash
# Basic validation
saigen validate nginx.yaml

# Advanced validation with 0.3 features
saigen validate --validate-urls --validate-checksums nginx.yaml

# Comprehensive validation with quality metrics
saigen validate --advanced --detailed nginx.yaml

# Auto-recover from common migration issues
saigen validate --auto-recover nginx.yaml
```

### Test Installation Methods

Use the test command to verify your installation methods work:

```bash
# Test all installation methods
saigen test nginx.yaml

# Test specific providers
saigen test --providers apt,binary nginx.yaml

# Test with dry-run (safe)
saigen test --dry-run nginx.yaml
```

## Common Migration Issues

### Issue 1: Invalid URL Templates

**Problem**: URL templates with invalid placeholders
```yaml
# Invalid
url: "https://example.com/{{invalid_placeholder}}/app.zip"
```

**Solution**: Use only supported placeholders
```yaml
# Valid
url: "https://example.com/{{version}}/app_{{platform}}_{{architecture}}.zip"
```

### Issue 2: Incorrect Checksum Format

**Problem**: Checksums without algorithm prefix
```yaml
# Invalid
checksum: "b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7"
```

**Solution**: Include algorithm prefix
```yaml
# Valid
checksum: "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7"
```

### Issue 3: Missing Required Fields

**Problem**: New installation methods without required fields
```yaml
# Invalid - missing required fields
binaries:
  - url: "https://example.com/app.zip"
```

**Solution**: Include all required fields
```yaml
# Valid
binaries:
  - name: "main"  # Required
    url: "https://example.com/app.zip"  # Required
```

### Issue 4: Enum Value Errors

**Problem**: Invalid enum values for new fields
```yaml
# Invalid
sources:
  - name: "main"
    build_system: "invalid_system"
```

**Solution**: Use valid enum values
```yaml
# Valid
sources:
  - name: "main"
    build_system: "autotools"  # Valid: autotools, cmake, make, meson, ninja, custom
```

## Automated Migration

### Using Auto-Recovery

The validate command can automatically fix many common issues:

```bash
# Attempt automatic migration fixes
saigen validate --auto-recover old-format.yaml > migrated.yaml
```

### Using Generation for New Files

For complex migrations, consider regenerating with the new schema:

```bash
# Generate fresh 0.3 format file
saigen generate --providers apt,brew,binary nginx

# Compare with your existing file and merge manually
```

## Best Practices for 0.3

1. **Always use HTTPS URLs** for security
2. **Include checksums** for all downloadable resources
3. **Use URL templating** for cross-platform compatibility
4. **Provide multiple installation methods** when available
5. **Include comprehensive security metadata**
6. **Test across target platforms** and providers
7. **Use meaningful names** for installation method entries
8. **Document platform-specific differences** in compatibility matrix
9. **Follow semantic versioning** in version fields
10. **Validate regularly** during development

## Getting Help

If you encounter issues during migration:

1. **Use verbose validation**: `saigen validate --show-context --detailed file.yaml`
2. **Check the examples**: Review files in `examples/saidata-0.3-examples/`
3. **Use auto-recovery**: `saigen validate --auto-recover file.yaml`
4. **Generate fresh files**: `saigen generate software-name` for comparison
5. **Check documentation**: Review the 0.3 schema documentation

## Migration Checklist

- [ ] Update version field to "0.3"
- [ ] Enhance metadata with new URL and security fields
- [ ] Add appropriate installation methods (sources/binaries/scripts)
- [ ] Update provider configurations with new features
- [ ] Add compatibility matrix
- [ ] Include checksums for all downloadable resources
- [ ] Use URL templating where applicable
- [ ] Validate with 0.3 schema
- [ ] Test installation methods
- [ ] Review security metadata
- [ ] Document any platform-specific requirements
- [ ] Update any automation or CI/CD that uses the saidata files