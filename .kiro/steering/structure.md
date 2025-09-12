# Project Structure

## Root Directory Organization
- **Documentation**: `docs/` - Comprehensive documentation including API reference, CLI guide, deployment
- **Examples**: `examples/` - Usage examples, configurations, and use cases
- **Schemas**: `schemas/` - JSON schema definitions
- **Scripts**: `scripts/` - Build, deployment, and utility scripts
- **Tests**: `tests/` - Comprehensive test suite with fixtures
- **Saidata**: Repository-based saidata (cached in `~/.sai/cache/repositories/`)
- **Providerdata**: `providerdata/` - Provider data to support actions

## Core Package Structure

### SAI CLI Tool (`sai/`)
- **`sai/cli/`** - Command-line interface and main entry point
- **`sai/models/`** - Configuration and provider data models
- **`sai/utils/`** - Configuration management and utilities

### SAIGEN AI Tool (`saigen/`)
- **`saigen/cli/`** - Command-line interface with command modules
- **`saigen/core/`** - Core generation engine and logic
- **`saigen/llm/`** - LLM provider integrations (OpenAI, Anthropic, etc.)
- **`saigen/models/`** - Data models for saidata, generation, and configuration
- **`saigen/repositories/`** - Package repository integrations and downloaders
- **`saigen/utils/`** - Utilities and configuration management

### Modular Architecture
- Clear separation of concerns between modules
- Each module has specific responsibility
- Minimal coupling between components

## File Naming Conventions
- **Python files**: snake_case (e.g., `core_engine.py`)
- **Test files**: `test_` prefix (e.g., `test_core_engine.py`)
- **Configuration files**: lowercase with extensions (e.g., `pyproject.toml`)
- **Documentation**: kebab-case for multi-word files (e.g., `api-reference.md`)