# SAI Examples

This directory contains example configurations and saidata files for the SAI tool.

## Saidata Schema 0.3 Examples

### Complete Examples

- **[saidata-schema-0.3-complete.yaml](saidata-schema-0.3-complete.yaml)** - Comprehensive example demonstrating all schema 0.3 features
  - Packages with logical and actual names
  - Services, files, directories, commands, ports
  - Source build configuration
  - Binary download configuration
  - Script installation configuration
  - Provider-specific overrides
  - Compatibility matrix

### Focused Examples

- **[saidata-simple-package.yaml](saidata-simple-package.yaml)** - Minimal package example
  - Basic package definition
  - Service and port configuration
  - Demonstrates minimum required fields

- **[saidata-source-build.yaml](saidata-source-build.yaml)** - Building from source
  - Source download and build configuration
  - Build system configuration (autotools)
  - Prerequisites and dependencies
  - Provider-specific source overrides

- **[saidata-binary-download.yaml](saidata-binary-download.yaml)** - Pre-compiled binaries
  - Binary download with URL templating
  - Platform and architecture detection
  - Archive extraction configuration
  - Checksum verification

- **[saidata-script-install.yaml](saidata-script-install.yaml)** - Installation scripts
  - Script download and execution
  - Environment variables and arguments
  - Timeout configuration
  - Security features (checksum verification)

## Configuration Examples

### SAI Configuration

- **[sai-config-sample.yaml](sai-config-sample.yaml)** - SAI configuration file example
  - Saidata search paths
  - Provider paths and priorities
  - Execution settings
  - Logging configuration

### Action Files

See [action-files/](action-files/) directory for batch action examples.

## Usage

### Using Saidata Examples

```bash
# Install software using a saidata file
sai install nginx --saidata saidata-simple-package.yaml

# Validate a saidata file
saigen validate saidata-schema-0.3-complete.yaml

# Test a saidata file
saigen test-system saidata-source-build.yaml
```

### Using Configuration Examples

```bash
# Use a custom configuration file
sai --config sai-config-sample.yaml install nginx

# Copy to default location
cp sai-config-sample.yaml ~/.sai/config.yaml
```

## Schema 0.3 Features

### Package Structure

```yaml
packages:
  - name: nginx              # Logical name for cross-referencing
    package_name: nginx      # Actual package name for package managers
    version: "1.24.0"
```

### Installation Methods

**Sources (Build from Source):**
```yaml
sources:
  - name: main
    url: "https://example.com/source-{{version}}.tar.gz"
    build_system: autotools
    configure_args:
      - "--with-feature"
```

**Binaries (Pre-compiled):**
```yaml
binaries:
  - name: main
    url: "https://example.com/binary-{{version}}_{{platform}}_{{architecture}}.zip"
    install_path: "/usr/local/bin"
```

**Scripts (Installation Scripts):**
```yaml
scripts:
  - name: official
    url: "https://example.com/install.sh"
    interpreter: bash
    timeout: 600
```

### Template Functions

```yaml
# Package functions
command: "apt-get install -y {{sai_package(0, 'package_name', 'apt')}}"
command: "apt-get install -y {{sai_package('*', 'package_name', 'apt')}}"

# Source functions
command: "wget {{sai_source(0, 'url', 'source')}}"

# Binary functions
command: "curl -L {{sai_binary(0, 'url', 'binary')}} -o app.zip"

# Script functions
command: "curl -fsSL {{sai_script(0, 'url', 'script')}} | bash"
```

## Documentation

- [Schema 0.3 Guide](../schema-0.3-guide.md) - Complete guide to schema 0.3
- [CLI Reference](../cli-reference.md) - Command-line reference
- [Template Engine](../template-engine.md) - Template engine documentation

## Contributing

When adding new examples:

1. Follow the schema 0.3 format
2. Include comprehensive comments
3. Validate against the schema: `saigen validate your-example.yaml`
4. Test the example: `saigen test-system your-example.yaml`
5. Update this README with a description

## See Also

- [SAI Documentation](../) - Complete SAI documentation
- [SAIGEN Examples](../../../saigen/docs/examples/) - SAIGEN examples
- [Schema Definition](../../../schemas/saidata-0.3-schema.json) - JSON schema file
