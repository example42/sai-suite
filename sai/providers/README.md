# Provider System

This module implements the provider YAML loading system for the SAI CLI tool.

## Components

### ProviderLoader

The `ProviderLoader` class is responsible for:

- Scanning directories for provider YAML files (including specialized subdirectories)
- Loading and parsing YAML files
- Validating provider data against JSON schema
- Validating provider data using Pydantic models
- Error handling for malformed or invalid provider files
- Caching and performance optimization

### BaseProvider

The `BaseProvider` class provides a common interface for all providers:

- Wraps validated `ProviderData` instances
- Provides access to provider metadata and capabilities
- Supports querying supported actions and priorities

### ProviderFactory

The `ProviderFactory` class creates provider instances:

- Uses `ProviderLoader` to load provider data
- Creates `BaseProvider` instances from validated data
- Supports loading from multiple directories with precedence rules

## Usage

```python
from sai.providers import ProviderLoader, ProviderFactory

# Create a loader
loader = ProviderLoader()

# Load providers from a directory
providers = loader.load_providers_from_directory(Path("providers"))

# Or use the factory for convenience
factory = ProviderFactory.create_default_factory()
provider_instances = factory.create_providers()
```

## Error Handling

The loader implements robust error handling:

- **ProviderLoadError**: Raised when YAML parsing fails
- **ProviderValidationError**: Raised when validation fails
- Continues loading valid providers when some fail
- Provides detailed error messages with context

## Validation

Provider YAML files are validated at two levels:

1. **JSON Schema Validation**: Against `schemas/providerdata-0.1-schema.json`
2. **Pydantic Model Validation**: Against the `ProviderData` model

This ensures provider files are both structurally correct and semantically valid.

## Directory Structure

The loader searches for provider files in:

- Project `providers/` directory
- `providers/specialized/` subdirectory  
- User-specific directories (`~/.sai/providers`)
- System directories (`/etc/sai/providers`)

Later directories take precedence over earlier ones for duplicate provider names.