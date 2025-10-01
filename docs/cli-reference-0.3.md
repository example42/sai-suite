# SaiGen CLI Reference for Schema 0.3

Complete command-line interface reference for saigen with saidata 0.3 schema support.

## Overview

SaiGen is an AI-powered tool for generating, validating, and managing software metadata (saidata) files using the 0.3 schema format. It supports multiple installation methods, URL templating, enhanced security features, and comprehensive validation.

## Global Options

Available for all commands:

```bash
saigen [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
```

### Global Options

| Option | Description |
|--------|-------------|
| `--config PATH` | Configuration file path |
| `--llm-provider PROVIDER` | LLM provider (openai, anthropic, ollama) |
| `--verbose, -v` | Enable verbose output |
| `--dry-run` | Show what would be done without executing |
| `--version` | Show version and exit |
| `--help` | Show help message |

## Commands

### generate

Generate saidata files using the 0.3 schema format.

```bash
saigen generate [OPTIONS] SOFTWARE_NAME
```

#### Options

| Option | Description |
|--------|-------------|
| `--output, -o PATH` | Output file path (default: `<software_name>.yaml`) |
| `--providers PROVIDERS` | Target providers (apt, brew, binary, source, script, etc.) |
| `--no-rag` | Disable RAG context injection |
| `--force` | Overwrite existing files |
| `--log-file PATH` | Log file for detailed generation process |

#### New 0.3 Features

The generate command now creates files with:

- **Multiple installation methods**: sources, binaries, scripts
- **URL templating**: `{{version}}`, `{{platform}}`, `{{architecture}}`
- **Enhanced security metadata**: CVE exceptions, security contacts
- **Provider-specific configurations**: Overrides for all resource types
- **Compatibility matrices**: Cross-platform compatibility tracking

#### Examples

```bash
# Basic generation with 0.3 schema
saigen generate nginx

# Target specific installation methods
saigen generate --providers apt,brew,binary,source terraform

# Generate with comprehensive logging
saigen generate --log-file ./generation.json --verbose kubernetes

# Dry run to preview 0.3 features
saigen generate --dry-run --verbose docker

# Force overwrite with custom output
saigen generate --force --output custom-nginx.yaml nginx
```

#### Generated 0.3 Structure

```yaml
version: "0.3"
metadata:
  name: "software-name"
  # Enhanced metadata with security fields
sources:
  # Source build configurations
binaries:
  # Binary download configurations with templating
scripts:
  # Script installation configurations
providers:
  # Provider-specific configurations and overrides
compatibility:
  # Compatibility matrix and version information
```

### validate

Validate saidata files against the 0.3 schema with comprehensive checking.

```bash
saigen validate [OPTIONS] FILE_PATH
```

#### Options

| Option | Description |
|--------|-------------|
| `--schema PATH` | Custom schema file (defaults to saidata-0.3-schema.json) |
| `--show-context` | Show detailed error context |
| `--format FORMAT` | Output format (text, json) |
| `--advanced` | Enable quality metrics and repository checking |
| `--no-repository-check` | Skip repository accuracy checking |
| `--detailed` | Show detailed quality metrics |
| `--validate-urls` | Enable URL template validation |
| `--validate-checksums` | Enable checksum format validation |
| `--auto-recover` | Attempt automatic error recovery |

#### New 0.3 Validation Features

- **URL template validation**: Validates `{{version}}`, `{{platform}}`, `{{architecture}}` syntax
- **Checksum format validation**: Ensures `algorithm:hash` format
- **Security metadata validation**: Validates CVE exceptions and security contacts
- **Installation method validation**: Validates sources, binaries, scripts configurations
- **Provider override validation**: Ensures provider-specific configurations are valid
- **Compatibility matrix validation**: Validates platform/architecture combinations

#### Examples

```bash
# Basic 0.3 schema validation
saigen validate nginx.yaml

# Validate with URL and checksum checking
saigen validate --validate-urls --validate-checksums terraform.yaml

# Advanced validation with quality metrics
saigen validate --advanced --detailed kubernetes.yaml

# Auto-recover from common errors
saigen validate --auto-recover --format json docker.yaml

# Custom schema validation
saigen validate --schema custom-0.3-schema.json software.yaml

# Detailed error context for debugging
saigen validate --show-context --format json nginx.yaml
```

#### Validation Output

```bash
📋 Saidata 0.3 Schema Validation Report
File: nginx.yaml

Validation Features: URL Templates ✓, Checksums ✓, Auto-Recovery ✓

✓ Schema validation passed
✓ URL templates validated (3 templates checked)
✓ Checksums validated (5 checksums verified)
✓ Security metadata validated
✓ Provider configurations validated
✓ Compatibility matrix validated

Overall Score: 0.95/1.00
```

### test

Test saidata installation methods and provider configurations.

```bash
saigen test [OPTIONS] FILE_PATH
```

#### Options

| Option | Description |
|--------|-------------|
| `--providers PROVIDERS` | Specific providers to test |
| `--test-types TYPES` | Types of tests (packages, services, files, sources, binaries, scripts) |
| `--no-dry-run` | Disable dry-run mode (WARNING: performs actual operations) |
| `--show-details` | Show detailed test information |
| `--format FORMAT` | Output format (text, json) |
| `--timeout SECONDS` | Test execution timeout |

#### New 0.3 Test Types

- **sources**: Test source compilation configurations
- **binaries**: Test binary download and installation
- **scripts**: Test script execution (with security validation)
- **url-templates**: Test URL template resolution
- **checksums**: Test checksum validation
- **security**: Test security metadata and validation

#### Examples

```bash
# Test all installation methods
saigen test nginx.yaml

# Test specific 0.3 installation methods
saigen test --test-types sources,binaries,scripts terraform.yaml

# Test with specific providers
saigen test --providers apt,binary nginx.yaml

# Dry run testing (safe, default)
saigen test --show-details nginx.yaml

# Test URL template resolution
saigen test --test-types url-templates kubernetes.yaml
```

### quality

Analyze saidata quality with comprehensive metrics for 0.3 schema.

```bash
saigen quality [OPTIONS] FILE_PATH
```

#### Options

| Option | Description |
|--------|-------------|
| `--metric METRIC` | Focus on specific quality metric |
| `--threshold FLOAT` | Quality score threshold (default: 0.7) |
| `--no-repository-check` | Skip repository accuracy checking |
| `--format FORMAT` | Output format (text, json, csv) |
| `--export PATH` | Export detailed report to file |

#### New 0.3 Quality Metrics

- **url_template_quality**: URL template syntax and best practices
- **checksum_coverage**: Percentage of resources with checksums
- **security_metadata_completeness**: Security field coverage
- **installation_method_diversity**: Variety of installation options
- **provider_configuration_quality**: Provider override completeness
- **compatibility_matrix_coverage**: Platform/architecture coverage

#### Examples

```bash
# Comprehensive quality analysis
saigen quality nginx.yaml

# Focus on security metrics
saigen quality --metric security_metadata_completeness vault.yaml

# Export detailed quality report
saigen quality --export quality-report.json --format json terraform.yaml

# Set custom quality threshold
saigen quality --threshold 0.8 kubernetes.yaml
```

### batch

Generate multiple saidata files in batch mode.

```bash
saigen batch [OPTIONS]
```

#### Options

| Option | Description |
|--------|-------------|
| `--input-file, -f PATH` | Input file with software names (one per line) |
| `--output-dir PATH` | Output directory for generated files |
| `--providers PROVIDERS` | Target providers for all generations |
| `--parallel JOBS` | Number of parallel jobs |
| `--continue-on-error` | Continue batch even if some generations fail |
| `--log-dir PATH` | Directory for generation logs |

#### Examples

```bash
# Batch generate from file list
saigen batch --input-file software-list.txt --output-dir ./saidata

# Parallel generation with specific providers
saigen batch --input-file list.txt --parallel 4 --providers apt,brew,binary

# Continue on errors with logging
saigen batch --input-file list.txt --continue-on-error --log-dir ./logs
```

### config

Manage saigen configuration for 0.3 schema features.

```bash
saigen config [SUBCOMMAND] [OPTIONS]
```

#### Subcommands

- `show`: Display current configuration
- `set`: Set configuration values
- `samples`: Manage sample data for RAG
- `providers`: Configure LLM providers
- `repositories`: Configure package repositories

#### New 0.3 Configuration Options

```bash
# Configure 0.3 schema validation
saigen config set validation.schema_version "0.3"
saigen config set validation.validate_url_templates true
saigen config set validation.validate_checksums true
saigen config set validation.auto_recovery true

# Configure security features
saigen config set security.require_checksums true
saigen config set security.require_https_urls true
saigen config set security.validate_signatures true

# Configure installation methods
saigen config set generation.include_sources true
saigen config set generation.include_binaries true
saigen config set generation.include_scripts true
```

### cache

Manage repository cache for enhanced 0.3 generation.

```bash
saigen cache [SUBCOMMAND] [OPTIONS]
```

#### Subcommands

- `update`: Update repository cache
- `clear`: Clear cache
- `stats`: Show cache statistics
- `info`: Show cache information

#### Examples

```bash
# Update all repository caches
saigen cache update

# Clear cache for fresh data
saigen cache clear

# Show cache statistics
saigen cache stats
```

### repositories

Manage package repository integrations.

```bash
saigen repositories [SUBCOMMAND] [OPTIONS]
```

#### Subcommands

- `list`: List available repositories
- `search`: Search packages in repositories
- `info`: Get package information
- `stats`: Repository statistics
- `update-cache`: Update repository cache

#### Examples

```bash
# List all repositories
saigen repositories list

# Search for packages
saigen repositories search nginx

# Get package information
saigen repositories info nginx --version 1.24.0
```

### index

Manage RAG (Retrieval-Augmented Generation) index for better 0.3 generation.

```bash
saigen index [SUBCOMMAND] [OPTIONS]
```

#### Subcommands

- `build`: Build RAG index from sample data
- `update`: Update existing index
- `stats`: Show index statistics
- `search`: Search index content

#### Examples

```bash
# Build RAG index from 0.3 examples
saigen index build --source examples/saidata-0.3-examples/

# Update index with new samples
saigen index update

# Search index for similar software
saigen index search nginx
```

### update

Update saigen components and data.

```bash
saigen update [SUBCOMMAND] [OPTIONS]
```

#### Subcommands

- `schema`: Update to latest schema version
- `samples`: Update sample data
- `repositories`: Update repository configurations
- `all`: Update all components

#### Examples

```bash
# Update to latest 0.3 schema
saigen update schema

# Update sample data with 0.3 examples
saigen update samples

# Update all components
saigen update all
```

## Error Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error |
| 2 | Validation failed |
| 3 | Generation failed |
| 4 | Configuration error |
| 5 | Network/repository error |
| 6 | File I/O error |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SAIGEN_CONFIG` | Configuration file path | `~/.saigen/config.yaml` |
| `SAIGEN_CACHE_DIR` | Cache directory | `~/.saigen/cache` |
| `SAIGEN_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `SAIGEN_LLM_PROVIDER` | Default LLM provider | `openai` |
| `SAIGEN_SCHEMA_VERSION` | Default schema version | `0.3` |

## Configuration File

Example configuration for 0.3 schema:

```yaml
# ~/.saigen/config.yaml
schema:
  version: "0.3"
  validation:
    validate_url_templates: true
    validate_checksums: true
    auto_recovery: true

generation:
  include_sources: true
  include_binaries: true
  include_scripts: true
  default_providers: ["apt", "brew", "binary"]

security:
  require_checksums: true
  require_https_urls: true
  validate_signatures: false

llm_providers:
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4"
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    model: "claude-3-sonnet-20240229"

rag:
  use_default_samples: true
  default_samples_directory: "examples/saidata-0.3-examples"
  index_directory: "~/.saigen/rag_index"

repositories:
  cache_dir: "~/.saigen/cache/repositories"
  config_dir: "~/.saigen/repositories"
  update_interval: 86400  # 24 hours
```

## Tips and Best Practices

### For Generation

1. **Use specific providers**: `--providers apt,brew,binary,source` for comprehensive coverage
2. **Enable logging**: `--log-file generation.log` for debugging and cost tracking
3. **Preview with dry-run**: `--dry-run --verbose` to see what will be generated
4. **Target platforms**: Consider your target platforms when selecting providers

### For Validation

1. **Use advanced validation**: `--advanced --detailed` for comprehensive checking
2. **Enable auto-recovery**: `--auto-recover` to fix common issues automatically
3. **Validate URLs and checksums**: `--validate-urls --validate-checksums` for security
4. **Check context**: `--show-context` for detailed error information

### For Testing

1. **Always dry-run first**: Default behavior is safe, use `--no-dry-run` carefully
2. **Test incrementally**: Start with `--test-types packages` then add more
3. **Use timeouts**: `--timeout 300` to prevent hanging tests
4. **Test cross-platform**: Use different provider combinations

### For Quality

1. **Set appropriate thresholds**: `--threshold 0.8` for production files
2. **Export reports**: `--export report.json` for tracking over time
3. **Focus on metrics**: `--metric security_metadata_completeness` for specific areas
4. **Regular quality checks**: Include in CI/CD pipelines

## Troubleshooting

### Common Issues

1. **Schema validation errors**: Use `--auto-recover` or check migration guide
2. **URL template errors**: Verify placeholder syntax and supported values
3. **Checksum format errors**: Ensure `algorithm:hash` format
4. **Provider configuration errors**: Check provider-specific documentation
5. **Generation failures**: Check LLM provider configuration and API keys

### Debug Commands

```bash
# Verbose validation with context
saigen validate --show-context --detailed --verbose file.yaml

# Debug generation with logging
saigen generate --verbose --log-file debug.log --dry-run software

# Test specific components
saigen test --test-types url-templates --show-details file.yaml

# Check configuration
saigen config show --verbose
```

### Getting Help

1. **Built-in help**: `saigen COMMAND --help`
2. **Verbose output**: Add `--verbose` to any command
3. **Configuration check**: `saigen config show`
4. **Example files**: Check `examples/saidata-0.3-examples/`
5. **Migration guide**: See `docs/saidata-0.3-migration-guide.md`