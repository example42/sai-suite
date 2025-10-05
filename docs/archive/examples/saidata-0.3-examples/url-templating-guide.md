# URL Templating Guide for SaiData 0.3

This guide demonstrates best practices for using URL templating in saidata 0.3 schema files.

## Supported Placeholders

The 0.3 schema supports three main placeholders for dynamic URL generation:

- `{{version}}` - Software version (e.g., "1.5.0", "v2.1.3")
- `{{platform}}` - Target platform (e.g., "linux", "darwin", "windows")
- `{{architecture}}` - Target architecture (e.g., "amd64", "arm64", "386")

## Platform Values

Standard platform values used in URL templating:

- `linux` - Linux distributions
- `darwin` - macOS
- `windows` - Microsoft Windows
- `freebsd` - FreeBSD
- `openbsd` - OpenBSD
- `netbsd` - NetBSD
- `solaris` - Solaris/illumos

## Architecture Values

Standard architecture values:

- `amd64` - 64-bit x86 (Intel/AMD)
- `arm64` - 64-bit ARM (Apple Silicon, ARM64)
- `386` - 32-bit x86
- `armhf` - 32-bit ARM with hardware floating point
- `s390x` - IBM System z
- `ppc64le` - PowerPC 64-bit little endian

## URL Templating Examples

### Basic Binary Downloads

```yaml
binaries:
  - name: "main"
    url: "https://releases.example.com/{{version}}/binary_{{platform}}_{{architecture}}.zip"
    version: "1.5.0"
```

This resolves to:
- Linux AMD64: `https://releases.example.com/1.5.0/binary_linux_amd64.zip`
- macOS ARM64: `https://releases.example.com/1.5.0/binary_darwin_arm64.zip`
- Windows AMD64: `https://releases.example.com/1.5.0/binary_windows_amd64.zip`

### HashiCorp-style URLs

```yaml
binaries:
  - name: "terraform"
    url: "https://releases.hashicorp.com/terraform/{{version}}/terraform_{{version}}_{{platform}}_{{architecture}}.zip"
    version: "1.6.0"
```

Resolves to:
- `https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip`

### GitHub Releases

```yaml
binaries:
  - name: "kubectl"
    url: "https://github.com/kubernetes/kubernetes/releases/download/v{{version}}/kubectl-{{platform}}-{{architecture}}"
    version: "1.28.0"
```

### Source Archives

```yaml
sources:
  - name: "main"
    url: "https://github.com/user/repo/archive/v{{version}}.tar.gz"
    version: "2.1.0"
    build_system: "cmake"
```

### Version-specific Scripts

```yaml
scripts:
  - name: "installer"
    url: "https://raw.githubusercontent.com/user/repo/{{version}}/install.sh"
    version: "v1.0.0"
```

## Advanced Templating Patterns

### Conditional Platform Handling

Some projects use different naming conventions:

```yaml
# Example: Different executable names per platform
binaries:
  - name: "main"
    url: "https://releases.example.com/{{version}}/app_{{version}}_{{platform}}_{{architecture}}.tar.gz"
    version: "1.0.0"
    executable: "app"  # Linux/macOS
  
providers:
  binary:
    binaries:
      - name: "main"
        url: "https://releases.example.com/{{version}}/app_{{version}}_windows_{{architecture}}.zip"
        executable: "app.exe"  # Windows override
```

### Multiple Archive Formats

```yaml
binaries:
  - name: "linux"
    url: "https://releases.example.com/{{version}}/app-{{version}}-{{platform}}-{{architecture}}.tar.gz"
    version: "1.0.0"
    archive:
      format: "tar.gz"
  
  - name: "windows"
    url: "https://releases.example.com/{{version}}/app-{{version}}-{{platform}}-{{architecture}}.zip"
    version: "1.0.0"
    archive:
      format: "zip"
```

### Provider-specific Overrides

```yaml
binaries:
  - name: "main"
    url: "https://releases.example.com/{{version}}/app_{{platform}}_{{architecture}}.tar.gz"
    version: "1.0.0"

providers:
  brew:
    binaries:
      - name: "main"
        url: "https://releases.example.com/{{version}}/app_darwin_{{architecture}}.tar.gz"
        install_path: "/opt/homebrew/bin"
  
  choco:
    binaries:
      - name: "main"
        url: "https://releases.example.com/{{version}}/app_windows_{{architecture}}.zip"
        install_path: "C:\\tools\\app"
        executable: "app.exe"
```

## Security Considerations

### Always Use HTTPS

```yaml
# Good
binaries:
  - name: "main"
    url: "https://releases.example.com/{{version}}/app.zip"

# Bad - insecure
binaries:
  - name: "main"
    url: "http://releases.example.com/{{version}}/app.zip"
```

### Include Checksums

```yaml
binaries:
  - name: "main"
    url: "https://releases.example.com/{{version}}/app_{{platform}}_{{architecture}}.zip"
    version: "1.0.0"
    checksum: "sha256:fa16d72a078210a54c47dd5bef2f8b9b8a01d94909a51453956b3ec6442ea4c5"
```

### Verify Signatures

```yaml
binaries:
  - name: "main"
    url: "https://releases.example.com/{{version}}/app_{{platform}}_{{architecture}}.zip"
    version: "1.0.0"
    checksum: "sha256:fa16d72a078210a54c47dd5bef2f8b9b8a01d94909a51453956b3ec6442ea4c5"
    custom_commands:
      download: "curl -fsSL {{url}} -o app.zip && curl -fsSL {{url}}.sig -o app.zip.sig"
      extract: "gpg --verify app.zip.sig app.zip && unzip -q app.zip"
```

## Testing URL Templates

### Validation Commands

Use custom validation commands to test URL resolution:

```yaml
binaries:
  - name: "main"
    url: "https://releases.example.com/{{version}}/app_{{platform}}_{{architecture}}.zip"
    version: "1.0.0"
    custom_commands:
      validation: "app --version | grep -q '1.0.0'"
      version: "app --version | cut -d' ' -f2"
```

### Platform-specific Testing

```yaml
compatibility:
  matrix:
    - provider: "binary"
      platform: ["linux", "darwin", "windows"]
      architecture: ["amd64", "arm64"]
      supported: true
      tested: true
      notes: "URL templating tested across all platforms"
```

## Common Patterns by Project Type

### Go Projects

```yaml
binaries:
  - name: "main"
    url: "https://github.com/user/project/releases/download/v{{version}}/project_{{version}}_{{platform}}_{{architecture}}.tar.gz"
```

### Rust Projects

```yaml
binaries:
  - name: "main"
    url: "https://github.com/user/project/releases/download/v{{version}}/project-v{{version}}-{{architecture}}-unknown-{{platform}}-gnu.tar.gz"
```

### Node.js Projects

```yaml
binaries:
  - name: "main"
    url: "https://nodejs.org/dist/v{{version}}/node-v{{version}}-{{platform}}-{{architecture}}.tar.xz"
```

### Python Projects

```yaml
sources:
  - name: "main"
    url: "https://pypi.org/packages/source/p/project/project-{{version}}.tar.gz"
```

## Error Handling

### Invalid Placeholders

The schema validator will catch invalid placeholders:

```yaml
# This will cause a validation error
binaries:
  - name: "main"
    url: "https://example.com/{{invalid_placeholder}}/app.zip"
```

### Missing Required Fields

```yaml
# This will cause a validation error - missing required fields
binaries:
  - name: "main"
    # Missing url field
    version: "1.0.0"
```

## Best Practices Summary

1. **Use HTTPS URLs** for security
2. **Include checksums** for integrity verification
3. **Test URL templates** across target platforms
4. **Use standard platform/architecture values** for compatibility
5. **Provide fallbacks** through provider-specific overrides
6. **Document platform-specific differences** in compatibility matrix
7. **Validate templates** during development
8. **Use meaningful names** for binary/source/script entries
9. **Include version validation** commands
10. **Follow project-specific URL patterns** when available