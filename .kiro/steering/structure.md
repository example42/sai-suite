# Project Structure

## Root Directory Organization
- **Documentation**: `docs/` - Comprehensive documentation including API reference, CLI guide, deployment
- **Examples**: `examples/` - Usage examples, configurations, and use cases
- **Schemas**: `schemas/` - JSON schema definitions
- **Scripts**: `scripts/` - Build, deployment, and utility scripts
- **Tests**: `tests/` - Comprehensive test suite with fixtures
- **Saidata**: `saidata/` - Generated saidata
- **Providerdata**: `providerdata/` - Provider data to support actions

## Core Package Structure (`saigen/`)
## TODEFINE

### Modular Architecture
- Clear separation of concerns between modules
- Each module has specific responsibility
- Minimal coupling between components

## File Naming Conventions
- **Python files**: snake_case (e.g., `core_engine.py`)
- **Test files**: `test_` prefix (e.g., `test_core_engine.py`)
- **Configuration files**: lowercase with extensions (e.g., `pyproject.toml`)
- **Documentation**: kebab-case for multi-word files (e.g., `api-reference.md`)