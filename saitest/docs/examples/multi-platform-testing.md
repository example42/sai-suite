# Multi-Platform Testing Example

This example demonstrates how to test software across multiple platforms to ensure comprehensive coverage and identify platform-specific differences.

## Why Multi-Platform Testing?

- **Platform differences**: Different OSes may use different package names, paths, or configurations
- **Version variations**: Different OS versions may have different software versions
- **Package manager diversity**: Test apt, dnf, zypper, etc.
- **Deployment coverage**: Match your production environments

## Basic Multi-Platform Testing

### Test Multiple Ubuntu Versions

```bash
saitest verify nginx --platforms ubuntu:22.04,ubuntu:24.04,ubuntu:20.04
```

**Result:**
- Tests nginx on three Ubuntu versions
- Identifies version-specific differences
- Generates ubuntu/22.04.yaml, ubuntu/24.04.yaml, ubuntu/20.04.yaml

### Test Debian Family

```bash
saitest verify apache --platforms ubuntu:22.04,debian:12,debian:11
```

**Result:**
- Tests across Ubuntu and Debian
- Both use apt but may have different package names
- Identifies Debian vs Ubuntu differences

### Test RHEL Family

```bash
saitest verify postgresql --platforms rockylinux:8,rockylinux:9,fedora:40
```

**Result:**
- Tests across RHEL-compatible distributions
- All use dnf/yum but may have different repos
- Identifies RHEL vs Fedora differences

## Comprehensive Platform Coverage

### Test All Major Distributions

```bash
saitest verify mysql \
  --platforms ubuntu:22.04,debian:12,rockylinux:9,fedora:40,alpine:3.19 \
  --output-dir ./saidata \
  --verbose
```

**Platforms tested:**
- Ubuntu 22.04 (apt)
- Debian 12 (apt)
- Rocky Linux 9 (dnf)
- Fedora 40 (dnf)
- Alpine 3.19 (apk)

**Output structure:**

```
./saidata/mysql/
├── default.yaml          # Common configuration
├── ubuntu/
│   └── 22.04.yaml       # Ubuntu-specific
├── debian/
│   └── 12.yaml          # Debian-specific
├── rockylinux/
│   └── 9.yaml           # Rocky-specific
├── fedora/
│   └── 40.yaml          # Fedora-specific
└── alpine/
    └── 3.19.yaml        # Alpine-specific
```

## Understanding Platform Differences

### Example: Nginx Across Platforms

**default.yaml** (common):

```yaml
version: "0.3"
metadata:
  name: nginx
  description: "High-performance HTTP server"

packages:
  - name: nginx
    package_name: nginx

services:
  - name: nginx
    type: systemd
    enabled: true

commands:
  - name: nginx
    path: /usr/sbin/nginx
```

**ubuntu/22.04.yaml** (Ubuntu-specific):

```yaml
version: "0.3"

packages:
  - name: nginx
    package_name: nginx-full  # Ubuntu uses nginx-full
    version: "1.18.0"

files:
  - path: /etc/nginx/sites-available/default  # Ubuntu-specific path
    purpose: config
```

**debian/12.yaml** (Debian-specific):

```yaml
version: "0.3"

packages:
  - name: nginx
    package_name: nginx-light  # Debian uses nginx-light
    version: "1.22.1"

files:
  - path: /etc/nginx/nginx.conf  # Different default config
    purpose: config
```

**rockylinux/9.yaml** (Rocky-specific):

```yaml
version: "0.3"

packages:
  - name: nginx
    package_name: nginx
    version: "1.20.1"

files:
  - path: /etc/nginx/nginx.conf
    purpose: config
  - path: /usr/lib/systemd/system/nginx.service  # Different service path
    purpose: service
```

## Platform Selection Strategies

### Strategy 1: LTS Versions

Focus on long-term support releases for stability:

```bash
saitest verify software \
  --platforms ubuntu:22.04,debian:12,rockylinux:9
```

### Strategy 2: Current + LTS

Test both current and LTS versions:

```bash
saitest verify software \
  --platforms ubuntu:24.04,ubuntu:22.04,debian:12,debian:11
```

### Strategy 3: Package Manager Diversity

Test different package managers:

```bash
saitest verify software \
  --platforms ubuntu:22.04,rockylinux:9,alpine:3.19
# apt, dnf, apk
```

### Strategy 4: Target Environments

Match your production environments:

```bash
# If you deploy to Ubuntu and Rocky
saitest verify software \
  --platforms ubuntu:22.04,rockylinux:9
```

## Analyzing Platform Differences

### Verbose Output Shows Differences

```bash
saitest verify nginx \
  --platforms ubuntu:22.04,debian:12,rockylinux:9 \
  --verbose
```

**Output highlights differences:**

```
[Analysis Agent]
→ Aggregating observations across 3 platforms

Common patterns (in default.yaml):
- Service: nginx.service (systemd)
- Binary: /usr/sbin/nginx
- Port: 80/tcp, 443/tcp
- Command: nginx

Platform variations (in OS overrides):
- Package name:
  - ubuntu:22.04 → nginx-full
  - debian:12 → nginx-light
  - rockylinux:9 → nginx

- Config location:
  - ubuntu:22.04 → /etc/nginx/sites-available/default
  - debian:12 → /etc/nginx/nginx.conf
  - rockylinux:9 → /etc/nginx/nginx.conf

- Version:
  - ubuntu:22.04 → 1.18.0
  - debian:12 → 1.22.1
  - rockylinux:9 → 1.20.1
```

## Testing Version Ranges

### Test Multiple Versions of Same OS

```bash
# Test nginx across Ubuntu versions
saitest verify nginx \
  --platforms ubuntu:20.04,ubuntu:22.04,ubuntu:24.04
```

**Use cases:**
- Identify version-specific changes
- Ensure backward compatibility
- Plan migration paths

### Test Debian Versions

```bash
saitest verify postgresql \
  --platforms debian:10,debian:11,debian:12
```

### Test Fedora Versions

```bash
saitest verify redis \
  --platforms fedora:38,fedora:39,fedora:40
```

## Batch Multi-Platform Testing

### Test Multiple Software Across Platforms

```bash
#!/bin/bash
# batch-verify.sh

PLATFORMS="ubuntu:22.04,debian:12,rockylinux:9"
SOFTWARE_LIST="nginx apache postgresql redis mysql"

for software in $SOFTWARE_LIST; do
  echo "Verifying $software across platforms..."
  saitest verify "$software" \
    --platforms "$PLATFORMS" \
    --output-dir ./saidata \
    --verbose
  
  echo "---"
done
```

### Parallel Testing (Future)

```bash
# Currently sequential, parallel support coming
for platform in ubuntu:22.04 debian:12 rockylinux:9; do
  saitest verify nginx --platforms "$platform" &
done
wait
```

## Platform-Specific Testing

### Test Only Ubuntu

```bash
saitest verify software --platforms ubuntu:22.04,ubuntu:24.04
```

### Test Only RHEL Family

```bash
saitest verify software --platforms rockylinux:8,rockylinux:9,fedora:40
```

### Test Only Debian

```bash
saitest verify software --platforms debian:11,debian:12
```

## Interpreting Results

### High Confidence Across All Platforms

```
Results:
- Platforms tested: 5
- Observations: 342
- Confidence: 0.94
- Needs review: No
```

**Interpretation:**
- Software behaves consistently across platforms
- Minor differences captured in overrides
- Ready to use

### Platform-Specific Issues

```
Results:
- Platforms tested: 3
- Observations: 156
- Confidence: 0.72
- Needs review: Yes

Issues:
- rockylinux:9: Installation failed (package not found)
- alpine:3.19: Service not detected
```

**Actions:**
- Review failed platforms
- Check if software is available
- Verify package names
- May need manual configuration

### Significant Variations

```
[Analysis Agent]
→ Significant variations detected:
  - 3 different package names
  - 2 different config locations
  - 4 different service paths
→ Confidence: 0.81
```

**Actions:**
- Review OS-specific overrides
- Verify each platform manually
- Test generated saidata

## Best Practices

### 1. Start with 2-3 Platforms

```bash
# Initial verification
saitest verify software --platforms ubuntu:22.04,debian:12
```

### 2. Add More Platforms Gradually

```bash
# Expand coverage
saitest verify software \
  --platforms ubuntu:22.04,debian:12,rockylinux:9,fedora:40
```

### 3. Test Target Environments

```bash
# Match production
saitest verify software --platforms ubuntu:22.04,rockylinux:9
```

### 4. Include Different Package Managers

```bash
# Diverse package managers
saitest verify software \
  --platforms ubuntu:22.04,rockylinux:9,alpine:3.19
# apt, dnf, apk
```

### 5. Test LTS Versions

```bash
# Focus on stability
saitest verify software \
  --platforms ubuntu:22.04,debian:12,rockylinux:9
```

## Troubleshooting

### Platform Not Supported

```
Error: Platform 'custom:1.0' is not supported
```

**Solution:**
- Use supported platform identifiers
- Check available platforms in CLI reference
- Request support for new platforms

### Platform Test Failed

```
Warning: ubuntu:22.04 test failed (package not found)
```

**Solution:**
- Verify package exists on that platform
- Check package name
- Review error messages with --verbose

### Inconsistent Results

```
Warning: Significant variations across platforms
```

**Solution:**
- Review OS-specific overrides
- Verify each platform manually
- May be expected behavior

## Advanced Patterns

### Test Specific OS Families

```bash
# Debian family
DEBIAN_PLATFORMS="ubuntu:22.04,ubuntu:24.04,debian:11,debian:12"
saitest verify software --platforms "$DEBIAN_PLATFORMS"

# RHEL family
RHEL_PLATFORMS="rockylinux:8,rockylinux:9,fedora:40"
saitest verify software --platforms "$RHEL_PLATFORMS"
```

### Compare Platform Results

```bash
# Test on Ubuntu
saitest verify nginx --platforms ubuntu:22.04 --output-dir ./ubuntu-test

# Test on Debian
saitest verify nginx --platforms debian:12 --output-dir ./debian-test

# Compare
diff ./ubuntu-test/nginx/default.yaml ./debian-test/nginx/default.yaml
```

### Incremental Platform Addition

```bash
# Start with one platform
saitest verify software --platforms ubuntu:22.04 --output-dir ./saidata

# Add more platforms
saitest verify software \
  --platforms ubuntu:22.04,debian:12 \
  --output-dir ./saidata

# Add even more
saitest verify software \
  --platforms ubuntu:22.04,debian:12,rockylinux:9 \
  --output-dir ./saidata
```

## Next Steps

- [Multi-Provider Testing](multi-provider-testing.md) - Test multiple installation methods
- [CI/CD Integration](ci-cd-integration.md) - Automate platform testing
- [CLI Reference](../cli-reference.md) - Complete platform list
- [Basic Verification](basic-verification.md) - Simple verification workflow
