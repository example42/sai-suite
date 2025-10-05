# Installation Guide

The SAI Software Management Suite consists of two complementary tools that can be installed separately or together based on your needs.

## Quick Start

### Install SAI Only (Lightweight)

If you only need to execute software management actions using existing saidata:

```bash
pip install sai
```

This installs the lightweight SAI CLI tool with minimal dependencies.

**Use this when:**
- You're deploying software using existing saidata
- You're running SAI in production environments
- You want minimal dependencies and fast installation
- You're using SAI in CI/CD pipelines

### Install SAIGEN Only (Generation Tool)

If you only need to generate and manage saidata:

```bash
pip install saigen
```

This installs the SAIGEN tool with all generation capabilities.

**Use this when:**
- You're creating new saidata files
- You're maintaining software metadata catalogs
- You need AI-powered metadata generation
- You're working with package repositories

### Install SAI with Generation Support

If you need both execution and generation capabilities:

```bash
pip install sai[generation]
```

This installs SAI with SAIGEN included as an optional dependency.

**Use this when:**
- You need both execution and generation in one environment
- You're developing and testing saidata
- You want a complete toolkit for software management

### Install SAIGEN with All Features

For full SAIGEN capabilities including LLM and RAG support:

```bash
# With LLM support (OpenAI, Anthropic)
pip install saigen[llm]

# With RAG support (embeddings, vector search)
pip install saigen[rag]

# With all features
pip install saigen[all]
```

## Installation Options Comparison

| Package | Size | Dependencies | Use Case |
|---------|------|--------------|----------|
| `sai` | Small | Minimal | Production execution |
| `saigen` | Medium | Standard | Metadata generation |
| `sai[generation]` | Medium | Standard | Development & testing |
| `saigen[llm]` | Large | +AI providers | AI-powered generation |
| `saigen[rag]` | Large | +ML libraries | Advanced RAG features |
| `saigen[all]` | Largest | Everything | Full development suite |

## Development Installation

For contributing to the project:

```bash
# Clone the repository
git clone https://github.com/example42/sai-python.git
cd sai-python

# Install both packages in editable mode with dev dependencies
pip install -e ./sai[dev]
pip install -e ./saigen[dev]

# Or install workspace dev dependencies
pip install -e .[dev]
```

## Verify Installation

After installation, verify the tools are available:

```bash
# Check SAI
sai --version
sai --help

# Check SAIGEN (if installed)
saigen --version
saigen --help
```

## Docker Installation

Pre-built Docker images are available:

```bash
# SAI only
docker pull sai/sai:latest

# SAIGEN only
docker pull sai/saigen:latest

# Full suite
docker pull sai/suite:latest
```

## Upgrading

```bash
# Upgrade SAI
pip install --upgrade sai

# Upgrade SAIGEN
pip install --upgrade saigen

# Upgrade both
pip install --upgrade sai saigen
```

## Uninstallation

```bash
# Remove SAI
pip uninstall sai

# Remove SAIGEN
pip uninstall saigen

# Remove both
pip uninstall sai saigen
```

## Platform-Specific Notes

### Linux
No special requirements. Works on all major distributions.

### macOS
No special requirements. Compatible with both Intel and Apple Silicon.

### Windows
- Requires Python 3.8 or higher
- Some features may require Windows Subsystem for Linux (WSL)

## Troubleshooting

### Import Errors

If you see import errors after installation:

```bash
# Ensure you're using the correct Python environment
which python
python --version

# Reinstall in the correct environment
pip install --force-reinstall sai
```

### Dependency Conflicts

If you encounter dependency conflicts:

```bash
# Use a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install sai
```

### Permission Errors

If you get permission errors during installation:

```bash
# Install for current user only
pip install --user sai

# Or use a virtual environment (recommended)
```

## Next Steps

- **SAI Users**: See [SAI CLI Guide](./sai-cli-guide.md)
- **SAIGEN Users**: See [SAIGEN Guide](./saigen-guide.md)
- **Developers**: See [Development Guide](./development.md)
