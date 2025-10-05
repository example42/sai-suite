# SAI Action File Examples

Examples of SAI action files for executing software management operations.

## Files

### simple.yaml
Basic action file with minimal configuration.

```yaml
# Simple installation
actions:
  - software: nginx
    action: install
```

### flexible.yaml
Action file with multiple operations and configurations.

```yaml
# Multiple actions with configurations
actions:
  - software: nginx
    action: install
    config:
      version: latest
  
  - software: postgresql
    action: configure
    config_file: postgres.conf
```

### extra-params.yaml
Action file demonstrating extra parameters and advanced options.

```yaml
# Advanced configuration with extra parameters
actions:
  - software: nginx
    action: install
    provider: apt
    extra_params:
      enable_ssl: true
      port: 8080
```

### simple.json
JSON format action file (alternative to YAML).

## Usage

```bash
# Execute action file
sai apply --config simple.yaml

# Dry run to preview actions
sai apply --config flexible.yaml --dry-run

# With specific provider
sai apply --config extra-params.yaml --provider apt
```

## See Also

- [SAI Apply Command Documentation](../../sai-apply-command.md)
- [SAI CLI Reference](../../cli-reference.md)
- [Template Engine Documentation](../../template-engine.md)
