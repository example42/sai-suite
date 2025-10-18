# Project Structure

## Root Directory Organization
- **Documentation**: `docs/` - General/shared documentation (installation, architecture, migration guides)
- **Summaries**: `docs/summaries/` - All Kiro's summaries of advice or spec activities must be stored here and not in the main dir
- **Archive**: `docs/archive/` - Obsolete documentation kept for reference
- **TODOs**: `docs/TODO/` - TODO lists and pending tasks (not archived)
- **Examples**: `examples/` - Shared examples only (CI/CD integrations)
- **Schemas**: `schemas/` - JSON schema definitions
  - `saidata-0.3-schema.json` - Saidata schema with packages, sources, binaries, scripts
  - `providerdata-0.1-schema.json` - Provider action definitions
  - `applydata-0.1-schema.json` - Batch operation definitions
- **Scripts**: `scripts/` - Build, deployment, and utility scripts
- **Development Scripts**: `scripts/development/` - All demo and development scripts organized by package (sai/, saigen/)
- **Tests**: `tests/` - Comprehensive test suite organized by package (sai/, saigen/, shared/, integration/)
  - `tests/fixtures/` - Test fixtures including saidata examples
- **Saidata**: Repository-based saidata (cached in `~/.sai/cache/repositories/`)
- **Providerdata**: `providers/` - Provider data to support actions



## Core Package Structure

### SAI CLI Tool (`sai/`)
- **`sai/cli/`** - Command-line interface and main entry point
- **`sai/core/`** - Core execution engine and action loader
- **`sai/models/`** - Configuration and provider data models
- **`sai/providers/`** - Provider implementations and base classes
- **`sai/utils/`** - Configuration management and utilities
- **`sai/docs/`** - SAI-specific documentation (CLI reference, configuration guides)
- **`sai/docs/examples/`** - SAI configuration examples (action files, config samples)

### SAIGEN AI Tool (`saigen/`)
- **`saigen/cli/`** - Command-line interface with command modules
- **`saigen/core/`** - Core generation engine and logic
- **`saigen/llm/`** - LLM provider integrations (OpenAI, Anthropic, etc.)
- **`saigen/models/`** - Data models for saidata, generation, and configuration
- **`saigen/repositories/`** - Package repository integrations and downloaders
- **`saigen/testing/`** - Testing framework for saidata validation
- **`saigen/utils/`** - Utilities and configuration management
- **`saigen/docs/`** - SAIGEN-specific documentation (CLI reference, generation guides, repository management)
- **`saigen/docs/examples/`** - SAIGEN examples (repository configs, saidata samples, testing examples, software lists)

### Modular Architecture
- Clear separation of concerns between modules
- Each module has specific responsibility
- Minimal coupling between components

## Documentation Structure

### General Documentation (`docs/`)
- Shared documentation applicable to both packages
- Installation guides, architecture diagrams, implementation guides
- Implementation summaries in `docs/summaries/`
- Obsolete docs archived in `docs/archive/`

### Package-Specific Documentation
- **`sai/docs/`** - SAI execution tool documentation
  - CLI reference, configuration guides, examples
- **`saigen/docs/`** - SAIGEN generation tool documentation
  - CLI reference, generation guides, repository management, testing, examples

### Documentation Organization
- Each documentation directory has a README.md index
- Examples stored with their respective packages in `{package}/docs/examples/`
- Cross-references use relative paths
- Obsolete documentation archived in `docs/archive/`, not deleted

## Examples and Scripts Organization

### Examples Structure
- **`examples/`** - Shared examples only (CI/CD integrations)
- **`sai/docs/examples/`** - SAI-specific examples (action files, configurations)
- **`saigen/docs/examples/`** - SAIGEN-specific examples (repository configs, saidata samples, testing)

### Development Scripts Structure
- **`scripts/development/sai/`** - SAI demo and development scripts
- **`scripts/development/saigen/`** - SAIGEN demo and development scripts
- Each directory has a README.md explaining the scripts

### Examples Guidelines
- Package-specific examples live with their documentation
- Shared examples (CI/CD) stay in root `examples/`
- Demo scripts go in `scripts/development/{package}/`
- Obsolete examples archived in `docs/archive/examples/`

## Tests Organization

### Tests Structure
- **`tests/sai/`** - SAI-specific tests (CLI, execution engine, providers)
- **`tests/saigen/`** - SAIGEN-specific tests (generation, LLM, repositories)
- **`tests/shared/`** - Shared component tests (models, config)
- **`tests/integration/`** - Integration tests (cross-component, workflows)
- **`tests/fixtures/`** - Shared test fixtures
- **`tests/archive/`** - Obsolete/duplicate tests

### Tests Guidelines
- Tests organized by package matching code structure
- Each test directory has a README.md
- Run package-specific tests: `pytest tests/sai/` or `pytest tests/saigen/`
- Integration tests cover cross-component functionality
- Obsolete tests archived, not deleted
- Obsolete examples archived in `docs/archive/examples/`

## File Naming Conventions
- **Python files**: snake_case (e.g., `core_engine.py`)
- **Test files**: `test_` prefix (e.g., `test_core_engine.py`)
- **Configuration files**: lowercase with extensions (e.g., `pyproject.toml`)
- **Documentation**: kebab-case for multi-word files (e.g., `api-reference.md`)
- **Summary files**: Descriptive names in `docs/summaries/` (e.g., `monorepo-implementation.md`)