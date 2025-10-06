# SAI Monorepo Structure

This repository contains both SAI and SAIGEN as separate pip packages in a monorepo structure.

## Repository Structure

```
sai-suite/
├── sai/                    # SAI package (lightweight execution tool)
│   ├── pyproject.toml     # SAI package configuration
│   ├── __init__.py        # Package root
│   ├── cli/               # SAI source code
│   ├── core/
│   └── ...
├── saigen/                # SAIGEN package (generation tool)
│   ├── pyproject.toml     # SAIGEN package configuration
│   ├── saigen/            # SAIGEN source code
│   └── ...
├── pyproject.toml         # Workspace configuration
├── tests/                 # Shared tests
├── docs/                  # Documentation
├── scripts/               # Build and deployment scripts
└── README.md
```

## Package Independence

Each package can be:
- **Installed independently**: `pip install sai` or `pip install saigen`
- **Built separately**: Each has its own `pyproject.toml`
- **Versioned independently**: Separate version numbers
- **Published separately**: Independent PyPI releases

## Installation Options

### For End Users

```bash
# Install SAI only (lightweight, for execution)
pip install sai

# Install SAIGEN only (for metadata generation)
pip install saigen

# Install SAI with generation support
pip install sai[generation]

# Install SAIGEN with all features
pip install saigen[all]
```

### For Developers

```bash
# Clone the repository
git clone https://github.com/example42/sai-suite.git
cd sai-suite

# Install both in editable mode
./scripts/install-local.sh both

# Or install individually
./scripts/install-local.sh sai
./scripts/install-local.sh saigen
```

## Building Packages

```bash
# Build both packages
./scripts/build-packages.sh

# This creates:
# - sai/dist/sai-*.whl
# - saigen/dist/saigen-*.whl
# - dist/ (copies of both)
```

## Publishing Packages

```bash
# Publish to TestPyPI (for testing)
./scripts/publish-packages.sh test both

# Publish to PyPI (production)
./scripts/publish-packages.sh prod both

# Publish individual packages
./scripts/publish-packages.sh prod sai
./scripts/publish-packages.sh prod saigen
```

## Development Workflow

### Working on SAI

```bash
# Install SAI in editable mode
pip install -e ./sai[dev]

# Make changes to sai/
# Run tests
pytest tests/sai/

# Build and test
cd sai && python -m build && cd ..
```

### Working on SAIGEN

```bash
# Install SAIGEN in editable mode
pip install -e ./saigen[dev]

# Make changes to saigen/
# Run tests
pytest tests/saigen/

# Build and test
cd saigen && python -m build && cd ..
```

### Working on Both

```bash
# Install both in editable mode
./scripts/install-local.sh both

# Make changes to either package
# Run all tests
pytest

# Build both
./scripts/build-packages.sh
```

## Shared Resources

### Shared Configuration
- `pyproject.toml` (root): Workspace-level configuration
- `.github/workflows/`: CI/CD for both packages
- `tests/`: Test suite covering both packages

### Shared Documentation
- `docs/`: Comprehensive documentation
- `README.md`: Main project README
- `CHANGELOG.md`: Combined changelog

### Shared Tools
- `scripts/`: Build, test, and deployment scripts
- `.pre-commit-config.yaml`: Code quality hooks
- `Makefile`: Common development tasks

## Dependency Management

### SAI Dependencies (Minimal)
- Core execution libraries only
- No AI/ML dependencies
- Lightweight for production use

### SAIGEN Dependencies (Comprehensive)
- All SAI dependencies
- AI/ML libraries (optional)
- Repository integration tools
- Generation and validation tools

### Optional Dependencies
- `sai[generation]`: Adds SAIGEN as dependency
- `saigen[llm]`: Adds LLM providers
- `saigen[rag]`: Adds RAG capabilities
- `saigen[all]`: All features

## Version Management

Each package maintains its own version using `setuptools-scm`:

```bash
# Versions are derived from git tags
git tag sai-v0.1.0
git tag saigen-v0.1.0

# Or use a shared version
git tag v0.1.0
```

## Testing

```bash
# Test everything
pytest

# Test SAI only
pytest tests/sai/

# Test SAIGEN only
pytest tests/saigen/

# Test with coverage
pytest --cov=sai --cov=saigen
```

## CI/CD

The repository uses GitHub Actions for:
- **Separate builds**: Each package builds independently
- **Separate tests**: Package-specific test suites
- **Separate releases**: Independent PyPI publishing
- **Shared quality checks**: Linting, type checking for both

## Benefits of This Structure

### For Users
- **Choice**: Install only what you need
- **Lightweight**: SAI remains minimal
- **Flexibility**: Add features via optional dependencies

### For Developers
- **Shared code**: Common utilities and models
- **Unified testing**: Single test suite
- **Consistent tooling**: Shared development tools
- **Easy maintenance**: One repository to manage

### For the Project
- **Clear separation**: Distinct purposes
- **Independent releases**: Version at different paces
- **Reduced coupling**: Clean interfaces
- **Better organization**: Logical structure

## Migration Notes

### From Old Structure
The previous single-package structure has been split into:
- `sai/` → Core execution tool
- `saigen/` → Generation tool

### Compatibility
- Existing imports remain unchanged
- CLI commands work the same
- Configuration files compatible
- No breaking changes for users

## Documentation

- [When to Use What](docs/when-to-use-what.md) - Choosing between SAI and SAIGEN
- [Installation Guide](docs/installation.md) - Detailed installation instructions
- [Development Workflow](#development-workflow) - Contributing to the project

## Questions?

- **Which package do I need?** See [When to Use What](docs/when-to-use-what.md)
- **How do I install?** See [Installation Guide](docs/installation.md)
- **How do I contribute?** See [Development Workflow](#development-workflow)
- **Issues?** Open an issue on GitHub
