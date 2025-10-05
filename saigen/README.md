# SAIGEN - SAI Data Generation

AI-powered tool for generating, validating, and managing software metadata (saidata) in YAML format.

## Quick Start

```bash
pip install saigen
```

## Features

- **Universal Repository Support**: 50+ package managers (apt, dnf, brew, winget, npm, pypi, cargo, etc.)
- **AI-Enhanced Generation**: Uses LLMs (OpenAI, Anthropic, Ollama) for intelligent metadata creation
- **Schema Validation**: Validates generated files against official saidata schema
- **RAG Support**: Retrieval-Augmented Generation for improved accuracy
- **Batch Processing**: Generate metadata for multiple software packages efficiently
- **Comprehensive CLI**: Full-featured repository management and package search

## Basic Usage

```bash
# Generate saidata for a package
saigen generate nginx --provider apt

# Validate saidata
saigen validate nginx.yaml

# Batch generation
saigen batch generate --from package-list.txt

# Update repository cache
saigen repo update apt

# Search for packages
saigen repo search nginx
```

## When to Use SAIGEN

Use SAIGEN when you need to:
- Create new saidata files for software packages
- Generate metadata from package repositories
- Validate and test saidata files
- Build software catalogs and inventories
- Contribute to the saidata repository

## Installation Options

```bash
# Basic installation
pip install saigen

# With LLM support (OpenAI, Anthropic)
pip install saigen[llm]

# With RAG support (embeddings, vector search)
pip install saigen[rag]

# With all features
pip install saigen[all]

# Development installation
pip install saigen[dev]
```

## Supported Repositories

SAIGEN supports 50+ package managers including:

- **Linux**: apt, dnf, yum, pacman, zypper, apk
- **macOS**: brew, macports
- **Windows**: winget, chocolatey, scoop
- **Language**: npm, pypi, cargo, gem, maven, nuget
- **Container**: docker, podman
- **And many more...**

## Documentation

- [Full Documentation](https://sai.software/docs/saigen)
- [When to Use What](https://github.com/example42/sai-suite/blob/main/docs/when-to-use-what.md)
- [Installation Guide](https://github.com/example42/sai-suite/blob/main/docs/installation.md)
- [SAIGEN Guide](https://sai.software/docs/saigen-guide)

## Related Tools

- **[SAI](https://pypi.org/project/sai/)** - Lightweight CLI for executing software management actions
- **[Saidata Repository](https://github.com/example42/saidata)** - Collection of software metadata

## Links

- **Homepage**: https://sai.software
- **Repository**: https://github.com/example42/sai-suite
- **Issues**: https://github.com/example42/sai-suite/issues
- **PyPI**: https://pypi.org/project/saigen/

## License

MIT License - see [LICENSE](https://github.com/example42/sai-suite/blob/main/LICENSE) for details.
