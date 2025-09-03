# Troubleshooting Guide

This guide helps resolve common issues with the SAI Software Management Suite.

## Provider Loading Issues

### Provider Validation Errors

**Problem**: Provider YAML files fail to load with validation errors.

**Common Causes**:
1. **Variable Mapping Format**: Variables can be defined as either strings or objects
2. **Missing Required Fields**: Provider must have `name`, `type`, and at least one action
3. **Invalid Provider Type**: Must be one of the supported provider types

**Solutions**:

#### Variable Mapping Format
Variables support both string and object formats:

```yaml
# ✅ Correct - String format
variables:
  npm_prefix: "$(npm config get prefix)"

# ✅ Correct - Object format  
variables:
  custom_var:
    value: "default_value"
    config_key: "app.custom_var"
    environment: "CUSTOM_VAR"

# ✅ Correct - Mixed format
variables:
  "*":
    config_key: "{{variable_name}}"
  npm_prefix: "$(npm config get prefix)"
```

#### Required Provider Fields
Every provider must include:

```yaml
version: "1.0"
provider:
  name: "provider-name"        # Required
  type: "package_manager"      # Required - see supported types below
  display_name: "Display Name" # Optional
  description: "Description"   # Optional
  platforms: ["linux"]        # Optional
  capabilities: ["install"]    # Optional

actions:
  install:                     # At least one action required
    template: "command {{saidata.metadata.name}}"
```

#### Supported Provider Types
- `package_manager` - Package managers (apt, brew, npm, etc.)
- `container` - Container platforms (docker, podman)
- `binary` - Binary installations
- `source` - Source code installations
- `cloud` - Cloud service providers
- `custom` - Custom implementations
- `debug` - Debugging tools
- `trace` - Tracing tools
- `profile` - Profiling tools
- `security` - Security scanners
- `sbom` - Software Bill of Materials tools
- `troubleshoot` - Troubleshooting tools
- `network` - Network tools
- `audit` - Audit tools
- `backup` - Backup tools

### File Size Errors

**Problem**: "Provider file too large" error when loading YAML files.

**Solution**: Provider YAML files are limited to 10MB for security. If you have a legitimate need for larger files, consider:
1. Splitting large providers into multiple files
2. Using external references instead of inline data
3. Optimizing YAML structure to reduce size

### Schema Validation Errors

**Problem**: JSON schema validation fails even with valid YAML.

**Debugging Steps**:
1. Validate YAML syntax with a YAML parser
2. Check that all required fields are present
3. Verify field types match schema expectations
4. Use `sai validate <provider-file>` command (when available)

## Performance Issues

### Slow Provider Loading

**Problem**: Provider loading takes too long.

**Solutions**:
1. **Enable Caching**: Caching is enabled by default but can be configured:
   ```python
   loader = ProviderLoader(enable_caching=True)
   ```

2. **Reduce Provider Count**: Only include providers you need in your provider directories

3. **Optimize Provider Files**: Remove unnecessary mappings and actions

### Memory Usage

**Problem**: High memory usage when loading many providers.

**Solutions**:
1. Load providers on-demand instead of all at once
2. Use provider filtering to load only relevant providers
3. Clear provider cache periodically if not needed

## Configuration Issues

### Provider Not Found

**Problem**: SAI cannot find installed providers.

**Debugging Steps**:
1. Check provider search paths:
   - Current directory: `./providers/`
   - User directory: `~/.sai/providers/`
   - System directory: `/etc/sai/providers/` (Unix)

2. Verify provider YAML files are in correct locations
3. Check file permissions (must be readable)
4. Validate YAML syntax and schema compliance

### Provider Priority Issues

**Problem**: Wrong provider is selected for actions.

**Solution**: Configure provider priorities in SAI configuration:
```yaml
provider_priorities:
  apt: 1      # Higher priority (lower number)
  brew: 2
  snap: 3     # Lower priority (higher number)
```

## Error Messages

### Common Error Patterns

| Error Pattern | Cause | Solution |
|---------------|-------|----------|
| `Pydantic model validation failed` | Schema mismatch | Check field types and required fields |
| `JSON schema validation failed` | Invalid YAML structure | Validate against provider schema |
| `Failed to parse YAML` | Syntax error | Check YAML syntax |
| `Provider file too large` | File exceeds 10MB limit | Reduce file size or split provider |
| `Permission denied` | File permissions | Check file is readable |

### Getting Detailed Error Information

Enable debug logging to get more detailed error information:

```bash
export SAI_LOG_LEVEL=debug
sai install nginx
```

Or in Python:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Getting Help

If you encounter issues not covered in this guide:

1. **Check Logs**: Enable debug logging for detailed error information
2. **Validate Files**: Use schema validation tools to check YAML files
3. **Test Isolation**: Try loading individual provider files to isolate issues
4. **Community Support**: Check GitHub issues or create a new issue with:
   - Error messages and stack traces
   - Provider YAML files (sanitized)
   - System information (OS, Python version)
   - Steps to reproduce the issue

## Best Practices

### Provider Development
1. Start with minimal provider and add features incrementally
2. Test provider loading after each change
3. Use consistent naming conventions
4. Document custom variables and mappings
5. Validate against schema before deployment

### Performance
1. Keep provider files small and focused
2. Use caching for frequently accessed providers
3. Avoid loading all providers if only using a subset
4. Monitor memory usage in production environments

### Security
1. Validate provider files from untrusted sources
2. Use file permissions to protect provider configurations
3. Avoid storing sensitive data in provider YAML files
4. Regular security audits of provider configurations