# SAIGEN Documentation

Documentation for SAIGEN (SAI Data Generation) - the AI-powered metadata generation tool.

## 📖 Contents

### Core Documentation
- **[generation-engine.md](generation-engine.md)** - Generation engine and best practices
- **[generation-logging.md](generation-logging.md)** - Logging and debugging
- **[testing-guide.md](testing-guide.md)** - Testing saidata files
- **[TESTING-QUICKSTART.md](TESTING-QUICKSTART.md)** - Quick testing guide

### Repository Management
- **[repository-management.md](repository-management.md)** - Managing package repositories
- **[repository-configuration.md](repository-configuration.md)** - Configuring repositories
- **[repository-troubleshooting.md](repository-troubleshooting.md)** - Troubleshooting repositories
- **[repository-parser-improvements.md](repository-parser-improvements.md)** - Parser enhancements

### Features
- **[rag-indexing-guide.md](rag-indexing-guide.md)** - RAG (Retrieval-Augmented Generation)
- **[vllm-dgx-setup.md](vllm-dgx-setup.md)** - vLLM setup for NVIDIA DGX systems
- **[refresh-versions-command.md](refresh-versions-command.md)** - Refresh versions feature
- **[refresh-versions-quick-reference.md](refresh-versions-quick-reference.md)** - Quick reference
- **[retry-generation-feature.md](retry-generation-feature.md)** - Retry failed generations
- **[stats-command.md](stats-command.md)** - Statistics and reporting

### URL Features
- **[URL-FEATURE-README.md](URL-FEATURE-README.md)** - URL generation overview
- **[url-validation-filter.md](url-validation-filter.md)** - URL validation
- **[url-filter-quick-reference.md](url-filter-quick-reference.md)** - Quick reference

### Examples
- **[examples/](examples/)** - Configuration examples and samples
  - [saigen-config-sample.yaml](examples/saigen-config-sample.yaml) - Sample configuration
  - [vllm-config-dgx.yaml](examples/vllm-config-dgx.yaml) - vLLM configuration for DGX
  - [software_lists/](examples/software_lists/) - Software package lists
  - [saidata_samples/](examples/saidata_samples/) - Example saidata files

## 🚀 Quick Start

```bash
# Install SAIGEN
pip install saigen

# Basic usage
saigen generate nginx --provider apt
saigen validate nginx.yaml
saigen test nginx.yaml

# Repository management
saigen repo update apt
saigen repo search nginx
```

## 📚 Related Documentation

### General Documentation
- [When to Use What](../../docs/when-to-use-what.md) - Choose between SAI and SAIGEN
- [Installation Guide](../../docs/installation.md) - Installation instructions
- [Architecture](../../docs/architecture-diagram.md) - System architecture

### Package Information
- [SAIGEN Package README](../README.md) - Package overview
- [Main Repository README](../../README.md) - Repository overview

## 🔗 External Resources

- **Homepage**: https://sai.software
- **Repository**: https://github.com/example42/sai-suite
- **PyPI**: https://pypi.org/project/saigen/
- **Issues**: https://github.com/example42/sai-suite/issues

## 📝 Contributing

See the main [MONOREPO.md](../../MONOREPO.md) for development guidelines.
