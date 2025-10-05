# Project Structure

This repository contains two complementary tools that work together to provide a complete software management solution.

## Overview

### SAI (Software Action Interface)
- **Purpose**: Execute software management actions using provider-based configurations
- **Location**: `sai/` directory
- **CLI Command**: `sai`
- **Focus**: Action execution, provider management, system administration

### SAIGEN (SAI Generation)
- **Purpose**: Generate and validate software metadata using AI
- **Location**: `saigen/` directory  
- **CLI Command**: `saigen`
- **Focus**: Metadata generation, AI integration, repository analysis

## Directory Structure

```
├── sai/                           # SAI CLI Tool
│   ├── __init__.py               # Package initialization
│   ├── cli/                      # Command-line interface
│   │   ├── __init__.py
│   │   └── main.py              # Main CLI entry point
│   ├── models/                   # Data models
│   │   ├── __init__.py
│   │   ├── config.py            # SAI configuration models
│   │   └── provider_data.py     # Provider data models
│   └── utils/                    # Utilities
│       ├── __init__.py
│       └── config.py            # Configuration management
│
├── saigen/                        # SAIGEN AI Generation Tool
│   ├── __init__.py               # Package initialization
│   ├── cli/                      # Command-line interface
│   │   ├── __init__.py
│   │   ├── main.py              # Main CLI entry point
│   │   └── commands/            # CLI command modules
│   ├── core/                     # Core generation engine
│   │   └── __init__.py
│   ├── llm/                      # LLM integrations
│   │   ├── __init__.py
│   │   └── providers/           # LLM provider implementations
│   ├── models/                   # Data models
│   │   ├── __init__.py
│   │   ├── config.py            # SAIGEN configuration models
│   │   ├── generation.py        # Generation request/result models
│   │   ├── repository.py        # Repository data models
│   │   └── saidata.py          # SaiData schema models
│   ├── repositories/             # Package repository integrations
│   │   ├── __init__.py
│   │   └── downloaders/         # Repository data downloaders
│   └── utils/                    # Utilities
│       ├── __init__.py
│       └── config.py            # Configuration management
│
├── cache/repositories/            # Repository-based saidata cache
│   ├── ansible.yaml
│   ├── docker.yaml
│   └── ...                      # Other software metadata files
│
├── providers/                     # Provider configuration files
│   └── ...                      # Provider-specific configurations
│
├── schemas/                       # JSON schema definitions
│   └── ...                      # Schema files for validation
│
├── docs/                          # Documentation
│   ├── api-reference.md
│   ├── configuration-guide.md
│   └── project-structure.md     # This file
│
├── tests/                         # Test suite
│   ├── run_basic_tests.py       # Basic test runner
│   ├── test_config.py           # Configuration tests
│   └── test_models.py           # Model validation tests
│
└── examples/                      # Usage examples
    └── ...                       # Example configurations and scripts
```

## Data Flow

1. **SAIGEN** analyzes package repositories and uses AI to generate saidata files
2. **SAI** reads saidata files and provider configurations to execute actions
3. Both tools share common schemas and data formats but operate independently

## Configuration Separation

### SAI Configuration
- Location: `~/.sai/config.yaml`
- Focus: Provider priorities, execution settings, paths
- Models: `sai.models.config.SaiConfig`

### SAIGEN Configuration  
- Location: `~/.saigen/config.yaml`
- Focus: LLM providers, generation settings, repository configuration
- Models: `saigen.models.config.SaigenConfig`

## Development Guidelines

### Adding SAI Features
- Add CLI commands in `sai/cli/`
- Add data models in `sai/models/`
- Focus on execution and provider management
- Test with `sai` command

### Adding SAIGEN Features
- Add CLI commands in `saigen/cli/commands/`
- Add data models in `saigen/models/`
- Focus on generation and AI integration
- Test with `saigen` command

### Shared Components
- Schemas in `schemas/` directory
- Documentation in `docs/` directory
- Tests should cover both tools appropriately
- Examples should demonstrate both tools working together

## Testing Strategy

- **Unit Tests**: Test individual components of both tools
- **Integration Tests**: Test interaction between sai and saigen
- **End-to-End Tests**: Test complete workflows from generation to execution
- **Basic Tests**: Quick validation tests in `tests/run_basic_tests.py`

## Deployment

Both tools are packaged together but can be used independently:
- Single `pip install sai` installs both `sai` and `saigen` commands
- Users can choose to use one or both tools based on their needs
- Configuration files are separate to avoid conflicts