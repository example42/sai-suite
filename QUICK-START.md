# Quick Start Guide - SAI Monorepo

## For End Users

### Install SAI (Lightweight Execution)

```bash
pip install sai
sai --version
```

### Install SAIGEN (Metadata Generation)

```bash
pip install saigen
saigen --version
```

### Install Both

```bash
# Option 1: Install separately
pip install sai saigen

# Option 2: Install SAI with generation support
pip install sai[generation]
```

## For Contributors

### Clone and Setup

```bash
# Clone repository
git clone https://github.com/example42/sai-python.git
cd sai-python

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install both packages in editable mode
make install-both
```

### Common Tasks

```bash
# Run tests
make test

# Format code
make format

# Run linters
make lint

# Build packages
make build

# See all commands
make help
```

### Development Workflow

```bash
# 1. Make changes to code
vim sai/cli/main.py

# 2. Run tests
pytest tests/sai/

# 3. Format and lint
make format
make lint

# 4. Build and verify
make build
```

## Package Structure

```
sai-python/
├── sai/              # SAI package
│   ├── sai/          # Source code
│   ├── pyproject.toml
│   └── README.md
├── saigen/           # SAIGEN package
│   ├── saigen/       # Source code
│   ├── pyproject.toml
│   └── README.md
├── tests/            # Tests for both
├── docs/             # Documentation
└── scripts/          # Build scripts
```

## Key Commands

### Installation

```bash
make install-sai      # Install SAI only
make install-saigen   # Install SAIGEN only
make install-both     # Install both
```

### Testing

```bash
make test             # Run all tests
make test-sai         # Test SAI only
make test-saigen      # Test SAIGEN only
make coverage         # With coverage report
```

### Building

```bash
make build            # Build both packages
make build-sai        # Build SAI only
make build-saigen     # Build SAIGEN only
```

### Publishing

```bash
make publish-test     # Publish to TestPyPI
make publish-prod     # Publish to PyPI
```

## Documentation

- [When to Use What](docs/when-to-use-what.md) - Choose the right tool
- [Installation Guide](docs/installation.md) - Detailed installation
- [Monorepo Structure](MONOREPO.md) - Repository architecture
- [Implementation Summary](docs/summaries/monorepo-implementation.md) - Technical details

## Need Help?

- **Which package?** → [When to Use What](docs/when-to-use-what.md)
- **How to install?** → [Installation Guide](docs/installation.md)
- **How to contribute?** → [MONOREPO.md](MONOREPO.md)
- **Found a bug?** → [Open an issue](https://github.com/example42/sai-python/issues)

## Quick Reference

| Task | Command |
|------|---------|
| Install SAI | `pip install sai` |
| Install SAIGEN | `pip install saigen` |
| Install both | `pip install sai[generation]` |
| Dev setup | `make install-both` |
| Run tests | `make test` |
| Format code | `make format` |
| Build packages | `make build` |
| Clean up | `make clean` |

## Next Steps

1. **End Users**: See [Installation Guide](docs/installation.md)
2. **Contributors**: See [MONOREPO.md](MONOREPO.md)
3. **Confused?**: See [When to Use What](docs/when-to-use-what.md)
