# Security Best Practices for SaiData 0.3

This guide outlines security best practices when creating saidata files using the 0.3 schema format.

## Security Metadata

### Required Security Fields

Always include comprehensive security metadata:

```yaml
metadata:
  security:
    security_contact: "security@example.com"
    vulnerability_disclosure: "https://example.com/security"
    signing_key: "https://example.com/gpg-key"
    sbom_url: "https://example.com/sbom/{{version}}"
```

### CVE Exception Handling

Document known CVEs that are acceptable:

```yaml
metadata:
  security:
    cve_exceptions:
      - "CVE-2023-1234"  # Fixed in version 1.2.3, acceptable for 1.3.0+
      - "CVE-2023-5678"  # Not applicable to our use case
```

## Checksum Validation

### Always Include Checksums

Every downloadable resource should have a checksum:

```yaml
# Sources
sources:
  - name: "main"
    url: "https://example.com/source-{{version}}.tar.gz"
    checksum: "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7"

# Binaries
binaries:
  - name: "main"
    url: "https://example.com/binary-{{version}}.zip"
    checksum: "sha256:fa16d72a078210a54c47dd5bef2f8b9b8a01d94909a51453956b3ec6442ea4c5"

# Scripts
scripts:
  - name: "installer"
    url: "https://example.com/install.sh"
    checksum: "sha256:def456abc789012345678901234567890123456789012345678901234567890123"
```

### Supported Checksum Formats

Use strong cryptographic hash functions:

```yaml
# Recommended: SHA-256
checksum: "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7"

# Acceptable: SHA-512
checksum: "sha512:abc123def456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"

# Avoid: MD5 (deprecated)
# checksum: "md5:5d41402abc4b2a76b9719d911017c592"
```

## HTTPS Requirements

### Secure URLs Only

Always use HTTPS for downloads:

```yaml
# Good
sources:
  - name: "main"
    url: "https://releases.example.com/{{version}}/source.tar.gz"

binaries:
  - name: "main"
    url: "https://releases.example.com/{{version}}/binary.zip"

scripts:
  - name: "installer"
    url: "https://get.example.com/install.sh"

# Bad - insecure HTTP
# url: "http://releases.example.com/{{version}}/source.tar.gz"
```

### Certificate Validation

Ensure custom download commands validate certificates:

```yaml
binaries:
  - name: "main"
    url: "https://releases.example.com/{{version}}/app.zip"
    custom_commands:
      download: "curl -fsSL --tlsv1.2 {{url}} -o app.zip"  # Force TLS 1.2+
```

## Signature Verification

### GPG Signature Verification

Implement signature verification for critical software:

```yaml
binaries:
  - name: "main"
    url: "https://releases.example.com/{{version}}/app.zip"
    checksum: "sha256:fa16d72a078210a54c47dd5bef2f8b9b8a01d94909a51453956b3ec6442ea4c5"
    custom_commands:
      download: |
        curl -fsSL {{url}} -o app.zip
        curl -fsSL {{url}}.sig -o app.zip.sig
        curl -fsSL https://releases.example.com/gpg-key -o signing-key.asc
      extract: |
        gpg --import signing-key.asc
        gpg --verify app.zip.sig app.zip
        unzip -q app.zip
```

### HashiCorp-style Verification

For HashiCorp tools and similar:

```yaml
binaries:
  - name: "terraform"
    url: "https://releases.hashicorp.com/terraform/{{version}}/terraform_{{version}}_{{platform}}_{{architecture}}.zip"
    custom_commands:
      download: |
        curl -fsSL {{url}} -o terraform.zip
        curl -fsSL https://releases.hashicorp.com/terraform/{{version}}/terraform_{{version}}_SHA256SUMS -o checksums.txt
        curl -fsSL https://releases.hashicorp.com/terraform/{{version}}/terraform_{{version}}_SHA256SUMS.sig -o checksums.sig
      extract: |
        gpg --verify checksums.sig checksums.txt
        sha256sum -c checksums.txt --ignore-missing
        unzip -q terraform.zip
```

## Script Security

### Script Validation

Always validate scripts before execution:

```yaml
scripts:
  - name: "installer"
    url: "https://get.example.com/install.sh"
    checksum: "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7"
    interpreter: "bash"
    timeout: 300  # Prevent hanging
    custom_commands:
      download: "curl -fsSL {{url}} -o install.sh"
      install: |
        # Verify checksum before execution
        echo "{{checksum}}" | sha256sum -c -
        # Review script (optional but recommended)
        # less install.sh
        bash install.sh
```

### Environment Isolation

Use restricted environments for script execution:

```yaml
scripts:
  - name: "installer"
    url: "https://get.example.com/install.sh"
    working_dir: "/tmp/sai-install"
    environment:
      PATH: "/usr/bin:/bin"  # Restricted PATH
      HOME: "/tmp/sai-install"  # Isolated home
    timeout: 300
```

### Argument Validation

Validate and sanitize script arguments:

```yaml
scripts:
  - name: "installer"
    url: "https://get.example.com/install.sh"
    arguments: 
      - "--version"
      - "1.0.0"  # Specific version, not user input
      - "--prefix"
      - "/usr/local"  # Safe, predefined path
```

## File Permissions

### Secure File Permissions

Set appropriate permissions for installed files:

```yaml
files:
  - name: "config"
    path: "/etc/app/config.yaml"
    type: "config"
    owner: "root"
    group: "app"
    mode: "0640"  # Owner read/write, group read, no world access
    backup: true

  - name: "secret"
    path: "/etc/app/secret.key"
    type: "config"
    owner: "app"
    group: "app"
    mode: "0600"  # Owner only access

  - name: "binary"
    path: "/usr/local/bin/app"
    type: "binary"
    owner: "root"
    group: "root"
    mode: "0755"  # Standard executable permissions
```

### Directory Permissions

Secure directory access:

```yaml
directories:
  - name: "config"
    path: "/etc/app"
    owner: "root"
    group: "app"
    mode: "0750"  # Owner full, group read/execute, no world access

  - name: "data"
    path: "/var/lib/app"
    owner: "app"
    group: "app"
    mode: "0700"  # Owner only access

  - name: "logs"
    path: "/var/log/app"
    owner: "app"
    group: "adm"
    mode: "0750"  # Owner full, group read/execute
```

## Binary Security

### Capability Management

Set appropriate capabilities for binaries:

```yaml
binaries:
  - name: "main"
    url: "https://releases.example.com/{{version}}/app.zip"
    install_path: "/usr/local/bin"
    permissions: "0755"
    custom_commands:
      install: |
        install -m 755 app /usr/local/bin/app
        # Set capabilities instead of setuid
        setcap cap_net_bind_service=+ep /usr/local/bin/app
```

### Strip Debugging Information

Remove debugging symbols from production binaries:

```yaml
sources:
  - name: "main"
    url: "https://example.com/source-{{version}}.tar.gz"
    build_system: "make"
    build_args:
      - "CFLAGS=-O2 -s"  # Optimize and strip
    custom_commands:
      install: |
        make install
        strip /usr/local/bin/app  # Strip debugging symbols
```

## Service Security

### Secure Service Configuration

Configure services with security in mind:

```yaml
services:
  - name: "app"
    service_name: "app"
    type: "systemd"
    enabled: false  # Manual start for security-critical services
    config_files: 
      - "/etc/systemd/system/app.service"
      - "/etc/app/app.conf"

files:
  - name: "systemd-service"
    path: "/etc/systemd/system/app.service"
    type: "config"
    owner: "root"
    group: "root"
    mode: "0644"
    # Service file should include security hardening:
    # User=app
    # Group=app
    # NoNewPrivileges=true
    # ProtectSystem=strict
    # ProtectHome=true
    # PrivateTmp=true
```

## Container Security

### Secure Container Configuration

Use security-focused container settings:

```yaml
containers:
  - name: "app"
    image: "app"
    tag: "1.0.0"
    registry: "docker.io"
    ports: ["8080:8080"]
    volumes: 
      - "/app/data:/data:ro"  # Read-only mount
    environment:
      # Avoid secrets in environment variables
      CONFIG_FILE: "/config/app.yaml"
    labels:
      security.level: "high"
      # Security scanning labels
      security.scan.enabled: "true"
```

## Validation Commands

### Security Validation

Include security-focused validation commands:

```yaml
binaries:
  - name: "main"
    url: "https://releases.example.com/{{version}}/app.zip"
    custom_commands:
      validation: |
        # Verify binary integrity
        app --version
        # Check for security features
        checksec --file=/usr/local/bin/app
        # Verify no setuid bits
        test "$(stat -c %a /usr/local/bin/app)" = "755"
```

### Runtime Security Checks

```yaml
services:
  - name: "app"
    service_name: "app"
    custom_commands:
      validation: |
        # Verify service is running as correct user
        systemctl show app --property=User | grep -q "User=app"
        # Check process security
        ps aux | grep app | grep -v grep
        # Verify listening ports
        netstat -tlnp | grep :8080
```

## Compliance and Auditing

### Audit Trail

Maintain audit trails for security-sensitive operations:

```yaml
files:
  - name: "audit-log"
    path: "/var/log/app/audit.log"
    type: "log"
    owner: "app"
    group: "adm"
    mode: "0640"
    backup: true

directories:
  - name: "audit"
    path: "/var/log/app"
    owner: "app"
    group: "adm"
    mode: "0750"
```

### Compliance Metadata

Include compliance-relevant information:

```yaml
metadata:
  security:
    security_contact: "security@example.com"
    vulnerability_disclosure: "https://example.com/security"
    # Compliance frameworks
    compliance:
      - "SOC2"
      - "ISO27001"
      - "NIST"
```

## Security Testing

### Automated Security Testing

Include security testing in validation:

```yaml
custom_commands:
  validation: |
    # Basic security checks
    app --version
    # Check for known vulnerabilities
    # trivy fs /usr/local/bin/app
    # Verify file permissions
    find /etc/app -type f -exec ls -la {} \;
```

### Penetration Testing

Document security testing procedures:

```yaml
compatibility:
  matrix:
    - provider: "binary"
      platform: ["linux"]
      architecture: ["amd64"]
      supported: true
      tested: true
      notes: "Security tested with static analysis and penetration testing"
```

## Incident Response

### Security Contact Information

Always provide security contact information:

```yaml
metadata:
  security:
    security_contact: "security@example.com"
    vulnerability_disclosure: "https://example.com/security"
```

### Emergency Procedures

Document emergency response procedures:

```yaml
# Include in notes or documentation
compatibility:
  matrix:
    - provider: "binary"
      platform: ["linux"]
      notes: "Emergency security updates available at https://example.com/security-updates"
```

## Summary Checklist

- [ ] Use HTTPS URLs exclusively
- [ ] Include SHA-256 or SHA-512 checksums for all downloads
- [ ] Implement GPG signature verification where available
- [ ] Set secure file and directory permissions
- [ ] Use restricted environments for script execution
- [ ] Configure services with security hardening
- [ ] Include comprehensive security metadata
- [ ] Document CVE exceptions with justification
- [ ] Provide security contact information
- [ ] Include security validation commands
- [ ] Test across security-focused scenarios
- [ ] Maintain audit trails for sensitive operations
- [ ] Follow principle of least privilege
- [ ] Regularly update security metadata
- [ ] Document compliance requirements