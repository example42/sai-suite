# Security Configuration

## Overview

SAI includes security features to protect against command injection and path traversal attacks. These features are configurable to balance security with flexibility.

## Allowed Detection Binaries

Detection commands are restricted to a configurable list of allowed executables to prevent command injection attacks.

### Default Allowed Binaries

By default, SAI allows the following executables in detection commands:

- **System utilities**: `which`, `ls`, `cat`
- **Debian/Ubuntu**: `dpkg`, `apt`
- **RedHat/Fedora/CentOS**: `rpm`, `yum`, `dnf`
- **SUSE**: `zypper`
- **Arch Linux**: `pacman`
- **Alpine Linux**: `apk`
- **FreeBSD**: `pkg`
- **macOS**: `brew`
- **Windows**: `choco`, `winget`

### Configuration Methods

#### 1. Configuration File

Add to your SAI configuration file (`~/.sai/config.yaml` or `.sai.yaml`):

```yaml
allowed_detection_binaries:
  - which
  - ls
  - cat
  - dpkg
  - rpm
  - brew
  - apt
  - yum
  - dnf
  - zypper
  - pacman
  - apk
  - pkg
  - choco
  - winget
  - custom-tool  # Add your custom tools here
```

#### 2. Environment Variable

Set the `SAI_ALLOWED_DETECTION_BINARIES` environment variable with a comma-separated list:

```bash
export SAI_ALLOWED_DETECTION_BINARIES="which,ls,cat,dpkg,rpm,brew,apt,custom-tool"
```

The environment variable takes precedence over the configuration file.

### Adding Custom Binaries

If you need to use a custom detection command that's not in the default list:

1. **Temporary (current session)**:
   ```bash
   export SAI_ALLOWED_DETECTION_BINARIES="which,ls,cat,dpkg,rpm,brew,apt,my-custom-tool"
   sai install software
   ```

2. **Permanent (configuration file)**:
   ```yaml
   # ~/.sai/config.yaml
   allowed_detection_binaries:
     - which
     - ls
     - cat
     # ... other defaults ...
     - my-custom-tool
   ```

### Error Handling

If a detection command uses a blocked executable, you'll see an error like:

```
SecurityError: Executable 'unauthorized-tool' not allowed in detection command

Suggestions:
  1. Add 'unauthorized-tool' to allowed_detection_binaries in your config
  2. Use SAI_ALLOWED_DETECTION_BINARIES environment variable
  3. Check if the detection command is correct

Details:
  executable: unauthorized-tool
  allowed_binaries: ['which', 'ls', 'cat', 'dpkg', 'rpm', ...]
```

## Path Traversal Protection

SAI automatically protects against path traversal attacks when extracting archives (tar, zip) from repositories.

### How It Works

- All archive members are validated before extraction
- Paths attempting to write outside the target directory are blocked
- Absolute paths and parent directory references (`..`) are rejected

### Example

If an archive contains a malicious entry like:
- `../../../etc/passwd`
- `/etc/shadow`

SAI will block the extraction and raise a `SecurityError`:

```
SecurityError: Blocked path traversal: ../../../etc/passwd
```

## Security Levels

SAI supports different security levels (configured via `saidata_security_level`):

- **strict**: Maximum security, strict validation
- **moderate**: Balanced security and flexibility (default)
- **permissive**: Minimal restrictions (not recommended for production)

```yaml
# ~/.sai/config.yaml
saidata_security_level: moderate
```

## Best Practices

1. **Minimize allowed binaries**: Only add executables you actually need
2. **Review detection commands**: Ensure provider detection commands use safe executables
3. **Use environment variables for testing**: Test new binaries with env vars before adding to config
4. **Keep security level at moderate or strict**: Only use permissive for development/testing
5. **Verify archive sources**: Only use trusted repository sources
6. **Enable signature verification**: Set `saidata_verify_signatures: true` (default)

## Troubleshooting

### Detection Command Blocked

**Problem**: Detection command fails with "Executable not allowed" error

**Solution**:
1. Check which executable is blocked in the error message
2. Verify it's a legitimate tool you want to allow
3. Add it to your configuration or environment variable
4. Re-run the command

### Archive Extraction Fails

**Problem**: Repository update fails with "Blocked path traversal" error

**Solution**:
1. This indicates a potentially malicious archive
2. Verify the repository source is trusted
3. Report the issue to the repository maintainer
4. Do not disable path traversal protection

## Related Configuration

See also:
- [Configuration Guide](configuration.md) - General configuration options
- [Provider Configuration](providers.md) - Provider-specific settings
- [Repository Management](repositories.md) - Repository security settings
