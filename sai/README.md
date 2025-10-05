# SAI - Software Action Interface

Lightweight CLI tool for executing software management actions using provider-based configurations.

## Quick Start

```bash
pip install sai
```

## Features

- **Provider-based Actions**: Execute install, configure, start, stop, and other actions
- **Multi-platform Support**: Works across Linux, macOS, and Windows
- **Extensible Providers**: Support for package managers, containers, and custom providers
- **Configuration Management**: Flexible YAML/JSON configuration system
- **Dry-run Mode**: Preview actions before execution

## Basic Usage

```bash
# Install software
sai install nginx

# Configure software
sai configure postgresql --config prod.yaml

# List installed software
sai list installed

# Execute actions from a configuration file
sai apply --config infrastructure.yaml
```

## When to Use SAI

Use SAI when you need to:
- Deploy software using existing saidata
- Execute software management in production environments
- Run automated deployments in CI/CD pipelines
- Manage software lifecycle across multiple systems

## Installation Options

```bash
# Lightweight installation (execution only)
pip install sai

# With generation support (includes saigen)
pip install sai[generation]

# Development installation
pip install sai[dev]
```

## Documentation

- [Full Documentation](https://sai.software/docs)
- [When to Use What](https://github.com/example42/sai-suite/blob/main/docs/when-to-use-what.md)
- [Installation Guide](https://github.com/example42/sai-suite/blob/main/docs/installation.md)
- [CLI Guide](https://sai.software/docs/sai-cli-guide)

## Related Tools

- **[SAIGEN](https://pypi.org/project/saigen/)** - AI-powered tool for generating saidata
- **[Saidata Repository](https://github.com/example42/saidata)** - Collection of software metadata

## Links

- **Homepage**: https://sai.software
- **Repository**: https://github.com/example42/sai-suite
- **Issues**: https://github.com/example42/sai-suite/issues
- **PyPI**: https://pypi.org/project/sai/

## License

MIT License - see [LICENSE](https://github.com/example42/sai-suite/blob/main/LICENSE) for details.
