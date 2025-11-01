# Multi-Provider Testing Example

This example demonstrates how to test software with multiple installation providers (apt, snap, pip, source, etc.) to ensure comprehensive coverage of all installation methods.

## Why Multi-Provider Testing?

- **Installation flexibility**: Users may install software different ways
- **Provider differences**: Different providers may install different files/services
- **Comprehensive coverage**: Ensure all installation methods work
- **Provider-specific overrides**: Generate accurate provider configurations

## How It Works

Saitest automatically tests all available providers:

1. **Discovery Agent** identifies available providers
2. **Cross-references** with providerdata availability
3. **Tests each provider** on each platform
4. **Tags observations** with provider information
5. **Generates provider-specific overrides** in saidata

## Basic Multi-Provider Testing

### Automatic Provider Detection

```bash
saitest verify nginx --platforms ubuntu:22.04
```

**What happens:**
- Discovers nginx is available via: apt, snap, source
- Tests each provider on ubuntu:22.04
- Generates provider-specific overrides

**Output:**

```
Verifying nginx...
✓ Discovery complete: Found 3 providers (apt, snap, source)
✓ Selected platforms: ubuntu:22.04
✓ Testing ubuntu:22.04 with apt... Success
✓ Testing ubuntu:22.04 with snap... Success
✓ Testing ubuntu:22.04 with source... Success
✓ Analysis complete: 45 observations
✓ Generated saidata with 3 provider overrides
```

## Understanding Provider Differences

### Example: Python Across Providers

```bash
saitest verify python --platforms ubuntu:22.04 --verbose
```

**Providers tested:**
- `apt` - System package (python3)
- `snap` - Snap package
- `source` - Build from python.org
- `binary` - Pre-compiled download

**Generated saidata:**

```yaml
version: "0.3"
metadata:
  name: python
  description: "Python programming language"

# Base configuration (common)
packages:
  - name: python
    package_name: python3

# Provider-specific overrides
providers:
  apt:
    packages:
      - name: python
        package_name: python3
        version: "3.10.12"
    files:
      - path: /usr/bin/python3
        purpose: binary
      - path: /usr/lib/python3.10
        purpose: library
  
  snap:
    packages:
      - name: python
        package_name: python
        version: "3.11.0"
    files:
      - path: /snap/bin/python
        purpose: binary
      - path: /snap/python/current
        purpose: library
  
  source:
    sources:
      - name: main
        url: "https://www.python.org/ftp/python/{{version}}/Python-{{version}}.tar.xz"
        build_system: autotools
        configure_args:
          - "--enable-optimizations"
    files:
      - path: /usr/local/bin/python3
        purpose: binary
      - path: /usr/local/lib/python3.11
        purpose: library
  
  binary:
    binaries:
      - name: main
        url: "https://github.com/indygreg/python-build-standalone/releases/download/{{version}}/cpython-{{version}}-{{platform}}-{{architecture}}.tar.gz"
        install_path: "/opt/python"
    files:
      - path: /opt/python/bin/python3
        purpose: binary
```

## Provider Types

### Package Managers

**System Package Managers:**
```bash
# Tests apt, dnf, yum, zypper, pacman, apk
saitest verify nginx --platforms ubuntu:22.04,rockylinux:9,alpine:3.19
```

**Universal Package Managers:**
```bash
# Tests snap, flatpak
saitest verify firefox --platforms ubuntu:22.04
```

**Language Package Managers:**
```bash
# Tests pip, npm, gem, cargo
saitest verify requests --platforms ubuntu:22.04
```

### Alternative Installation Methods

**Source Builds:**
```bash
# Tests building from source
saitest verify nginx --platforms ubuntu:22.04
# Includes source provider if available
```

**Binary Downloads:**
```bash
# Tests pre-compiled binaries
saitest verify golang --platforms ubuntu:22.04
# Includes binary provider if available
```

**Installation Scripts:**
```bash
# Tests installation scripts
saitest verify docker --platforms ubuntu:22.04
# Includes script provider if available
```

## Detailed Provider Testing

### Verbose Output Shows Provider Details

```bash
saitest verify nginx --platforms ubuntu:22.04 --verbose
```

**Output:**

```
[Discovery Agent]
→ Querying saigen repository cache...
→ Found nginx in apt repository
→ Found nginx in snap store
→ Scanning providerdata directory...
→ Available providers with providerdata: apt, snap, source, binary
→ Will test: apt, snap, source
✓ Discovery complete

[Installation Agent - ubuntu:22.04 with apt]
→ Spawning container: ubuntu:22.04
→ Loading providerdata for apt
→ Install command: apt-get update && apt-get install -y nginx
→ Capturing filesystem baseline...
→ Executing installation...
→ Installation complete (23.4s)
→ Capturing changes...
→ Found 89 new files
→ Found 1 service: nginx.service
→ Found 3 binaries: nginx, nginx-debug, nginx-module-*
→ Testing: dpkg -l nginx
✓ Installation successful

[Installation Agent - ubuntu:22.04 with snap]
→ Spawning container: ubuntu:22.04
→ Loading providerdata for snap
→ Install command: snap install nginx
→ Capturing filesystem baseline...
→ Executing installation...
→ Installation complete (18.7s)
→ Capturing changes...
→ Found 45 new files
→ Found 1 service: snap.nginx.daemon.service
→ Found 1 binary: /snap/bin/nginx
→ Testing: snap list nginx
✓ Installation successful

[Installation Agent - ubuntu:22.04 with source]
→ Spawning container: ubuntu:22.04
→ Loading providerdata for source
→ Install command: wget https://nginx.org/download/nginx-1.24.0.tar.gz && ...
→ Capturing filesystem baseline...
→ Executing installation...
→ Installation complete (156.3s)
→ Capturing changes...
→ Found 67 new files
→ Found 0 services (manual service setup required)
→ Found 1 binary: /usr/local/sbin/nginx
✓ Installation successful

[Analysis Agent]
→ Aggregating observations by provider...
→ apt: 89 files, 1 service, 3 binaries
→ snap: 45 files, 1 service, 1 binary
→ source: 67 files, 0 services, 1 binary
→ Identifying provider-specific patterns...
✓ Analysis complete
```

## Provider-Specific Observations

### File Locations Differ by Provider

**apt provider:**
```yaml
files:
  - path: /usr/sbin/nginx
    purpose: binary
  - path: /etc/nginx/nginx.conf
    purpose: config
  - path: /var/log/nginx
    purpose: logs
```

**snap provider:**
```yaml
files:
  - path: /snap/bin/nginx
    purpose: binary
  - path: /var/snap/nginx/common/conf/nginx.conf
    purpose: config
  - path: /var/snap/nginx/common/logs
    purpose: logs
```

**source provider:**
```yaml
files:
  - path: /usr/local/sbin/nginx
    purpose: binary
  - path: /usr/local/etc/nginx/nginx.conf
    purpose: config
  - path: /usr/local/var/log/nginx
    purpose: logs
```

### Service Configurations Differ

**apt provider:**
```yaml
services:
  - name: nginx
    type: systemd
    unit_file: /lib/systemd/system/nginx.service
    enabled: true
```

**snap provider:**
```yaml
services:
  - name: snap.nginx.daemon
    type: systemd
    unit_file: /etc/systemd/system/snap.nginx.daemon.service
    enabled: true
```

**source provider:**
```yaml
services: []
# No automatic service setup - manual configuration required
```

## Testing Specific Providers

### Test Only Package Managers

Saitest automatically tests all available providers. To focus on specific providers, ensure only those providers have providerdata available.

```bash
# Tests all available providers
saitest verify nginx --platforms ubuntu:22.04
```

### Cross-Platform Provider Testing

```bash
# Test apt across Debian family
saitest verify nginx --platforms ubuntu:22.04,debian:12

# Test dnf across RHEL family
saitest verify nginx --platforms rockylinux:9,fedora:40

# Test multiple package managers
saitest verify nginx --platforms ubuntu:22.04,rockylinux:9,alpine:3.19
# Tests apt, dnf, apk
```

## Provider Extensibility

### Automatic Support for New Providers

Saitest automatically supports any provider with valid providerdata:

```bash
# Check available providers
ls providers/

# Output:
# apt.yaml
# dnf.yaml
# snap.yaml
# pip.yaml
# npm.yaml
# ... etc
```

**When you add a new provider:**
1. Create `providers/newprovider.yaml` with providerdata
2. Saitest automatically detects and tests it
3. No code changes needed

### Example: Custom Provider

**providers/custom.yaml:**
```yaml
metadata:
  name: custom
  type: package_manager

actions:
  - name: install
    command: "custom-pkg install {{sai_packages('custom')}}"
  
  - name: status
    command: "custom-pkg list {{sai_packages('custom')}}"
```

**Usage:**
```bash
# Automatically tests custom provider if software is available
saitest verify software --platforms ubuntu:22.04
```

## Analyzing Provider Results

### Compare Provider Observations

```bash
saitest verify nginx --platforms ubuntu:22.04 --verbose
```

**Analysis output:**

```
[Analysis Agent]
→ Provider comparison:

apt provider:
- Files: 89 (system locations)
- Services: 1 (systemd)
- Binaries: 3 (nginx, nginx-debug, nginx-module-*)
- Config: /etc/nginx/
- Logs: /var/log/nginx/

snap provider:
- Files: 45 (snap locations)
- Services: 1 (snap.nginx.daemon)
- Binaries: 1 (/snap/bin/nginx)
- Config: /var/snap/nginx/common/conf/
- Logs: /var/snap/nginx/common/logs/

source provider:
- Files: 67 (custom locations)
- Services: 0 (manual setup)
- Binaries: 1 (/usr/local/sbin/nginx)
- Config: /usr/local/etc/nginx/
- Logs: /usr/local/var/log/nginx/

Recommendations:
- apt: Best for system integration
- snap: Best for isolation and updates
- source: Best for customization
```

## Best Practices

### 1. Test All Available Providers

```bash
# Let saitest discover and test all providers
saitest verify software --platforms ubuntu:22.04
```

### 2. Verify Provider-Specific Overrides

```bash
# Generate saidata
saitest verify nginx --output-dir ./saidata

# Review provider overrides
cat ./saidata/nginx/default.yaml
# Check providers.apt, providers.snap, etc.
```

### 3. Test Provider Combinations

```bash
# Test providers across platforms
saitest verify software \
  --platforms ubuntu:22.04,debian:12,rockylinux:9
# Tests apt on Ubuntu/Debian, dnf on Rocky
```

### 4. Document Provider Differences

Generated saidata automatically documents provider differences:

```yaml
providers:
  apt:
    # apt-specific configuration
  snap:
    # snap-specific configuration
  source:
    # source-specific configuration
```

## Common Provider Patterns

### Pattern 1: System vs Universal Packages

```yaml
# System package (apt)
providers:
  apt:
    packages:
      - name: firefox
        package_name: firefox
    files:
      - path: /usr/bin/firefox

# Universal package (snap)
providers:
  snap:
    packages:
      - name: firefox
        package_name: firefox
    files:
      - path: /snap/bin/firefox
```

### Pattern 2: Language Packages

```yaml
# System package
providers:
  apt:
    packages:
      - name: requests
        package_name: python3-requests

# Language package manager
providers:
  pip:
    packages:
      - name: requests
        package_name: requests
```

### Pattern 3: Source vs Binary

```yaml
# Build from source
providers:
  source:
    sources:
      - url: "https://example.com/software-{{version}}.tar.gz"
        build_system: autotools

# Pre-compiled binary
providers:
  binary:
    binaries:
      - url: "https://example.com/software-{{version}}-{{platform}}.tar.gz"
        install_path: "/opt/software"
```

## Troubleshooting

### Provider Not Found

```
Warning: Provider 'custom' not found in providerdata. Skipping.
```

**Solution:**
- Ensure providerdata file exists: `providers/custom.yaml`
- Verify providerdata is valid YAML
- Check provider name matches

### Provider Test Failed

```
Error: Installation with snap failed (snap not available)
```

**Solution:**
- Verify provider is available on platform
- Check if provider needs setup (e.g., snap needs snapd)
- Review error messages with --verbose

### Inconsistent Provider Results

```
Warning: Significant differences between providers
```

**Solution:**
- Review provider-specific overrides
- Verify each provider manually
- May be expected behavior (different installation methods)

## Advanced Patterns

### Test Provider Subsets

```bash
# Test only system package managers
# (Saitest tests all available providers automatically)
saitest verify software --platforms ubuntu:22.04,rockylinux:9
```

### Compare Provider Performance

```bash
saitest verify nginx --platforms ubuntu:22.04 --verbose
```

**Output shows timing:**
```
✓ Testing ubuntu:22.04 with apt... Success (23.4s)
✓ Testing ubuntu:22.04 with snap... Success (18.7s)
✓ Testing ubuntu:22.04 with source... Success (156.3s)
```

### Provider-Specific Testing

```bash
# Test software that's only available via specific providers
saitest verify python-package --platforms ubuntu:22.04
# Tests pip, apt (python3-package), etc.
```

## Next Steps

- [Multi-Platform Testing](multi-platform-testing.md) - Test across platforms
- [CI/CD Integration](ci-cd-integration.md) - Automate provider testing
- [CLI Reference](../cli-reference.md) - Complete provider list
- [Architecture](../architecture.md) - Provider integration details
