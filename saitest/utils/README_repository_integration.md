# Repository Integration

This module provides integration with saigen's repository system to discover valid installation providers for software packages.

## Overview

The `RepositoryIntegration` class queries saigen's repository cache and cross-references with available providerdata to identify providers that have both:
1. Package data in repositories
2. Valid providerdata definitions

## Key Components

### RepositoryIntegration Class

Main class for repository integration functionality.

```python
from saitest.utils import RepositoryIntegration

async with RepositoryIntegration() as integration:
    # Get available providers
    providers = integration.get_available_providers()
    
    # Discover providers for a package
    valid_providers, versions = await integration.discover_providers_for_package(
        "nginx",
        platform="linux"
    )
```

### Convenience Functions

#### get_available_providers_with_validation()

Get list of providers that have valid providerdata (synchronous operation).

```python
from saitest.utils import get_available_providers_with_validation

providers = await get_available_providers_with_validation()
# Returns: ['brew', 'cargo', 'choco', 'composer', 'dnf', ...]
```

#### discover_providers()

Discover valid providers for a specific package.

```python
from saitest.utils import discover_providers

valid_providers, versions = await discover_providers(
    "nginx",
    platform="linux"
)
# Returns: (['apt', 'dnf', 'snap'], {'apt': '1.24.0', 'dnf': '1.24.0', 'snap': '1.24.0'})
```

## Usage in Discovery Agent

The repository integration is designed to be used in the Discovery Agent:

```python
from saitest.utils import RepositoryIntegration

async def discovery_agent(state: VerificationState) -> VerificationState:
    software = state['software']
    
    async with RepositoryIntegration() as integration:
        # Get available providerdata
        available_providers = integration.get_available_providers()
        
        # Query repositories for package
        valid_providers, versions = await integration.discover_providers_for_package(
            software,
            platform="linux"
        )
        
        # Store in state
        state['installation_methods'] = valid_providers
        state['package_versions'] = versions
        
        # If no repository data, fall back to LLM
        if not valid_providers:
            llm_discovery(state)
    
    return state
```

## Provider Validation

The integration automatically validates that providers have both:

1. **Repository Data**: Package information from saigen's repository cache
2. **Providerdata**: Valid provider definitions in the `providers/` directory

Only providers that pass both checks are returned as valid installation methods.

### Supported Provider Action Types

The integration supports providers with different action structures:

- **Single command**: `command: "apt-get install {{package}}"`
- **Template**: `template: "brew install {{package}}"`
- **Multi-step**: `steps: [{command: "apt-get update"}, {command: "apt-get install"}]`

Providers using multi-step actions (like apt, docker, emerge) have their steps automatically combined into a single command chain using `&&`.

## Error Handling

The module includes comprehensive error handling:

- `RepositoryIntegrationError`: Raised when repository operations fail
- Graceful fallback when repository cache is empty
- Logging of validation failures and missing data

## Requirements

- Saigen's repository manager must be initialized
- Repository cache should be populated (via `saigen cache update`)
- Providerdata files must exist in `providers/` directory

## Notes

- Repository queries are asynchronous and require `await`
- Provider availability check is synchronous (only checks providerdata)
- Empty repository cache will result in zero valid providers (expected behavior)
- Invalid providerdata files are automatically filtered out with warnings
