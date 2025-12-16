# Saitest

Agent-based verification tool for generating and validating saidata.

## Overview

Saitest uses LangGraph to orchestrate AI agents that install software in Docker containers, observe system changes, and generate validated saidata files. It's part of the SAI Software Management Suite.

## Features

- **Agent-Based Workflow**: Uses LangGraph for intelligent orchestration
- **Multi-Platform Testing**: Tests software across multiple OS platforms
- **Multi-Provider Support**: Tests different installation methods (apt, dnf, pip, etc.)
- **Automatic Discovery**: Identifies installation methods and expected resources
- **Filesystem Monitoring**: Captures all changes during installation
- **Saidata Generation**: Creates validated saidata with OS-specific overrides
- **Quality Assessment**: Calculates confidence scores and flags low-quality results

## Installation

### From PyPI (when published)

```bash
pip install saitest
```

### From Source

```bash
# Clone the repository
git clone https://github.com/example42/sai-suite.git
cd sai-suite/saitest

# Install in development mode
pip install -e .
```

### Requirements

- Python 3.8 or higher
- Docker (must be installed and running)
- OpenAI API key or Anthropic API key (for LLM agents)

## Quick Start

### Verify Software

```bash
# Verify nginx with automatic platform selection
saitest verify nginx

# Verify with specific platforms
saitest verify apache --platforms ubuntu:22.04,debian:12

# Verbose output
saitest verify redis --verbose

# Custom output directory
saitest verify nginx --output-dir /path/to/output
```

### Test Existing Saidata

```bash
# Test existing saidata file
saitest test software/nginx/default.yaml
```

## Configuration

Saitest requires an LLM API key. Set one of these environment variables:

```bash
# For OpenAI
export OPENAI_API_KEY="your-api-key"

# For Anthropic
export ANTHROPIC_API_KEY="your-api-key"
```

## Output Structure

Saitest generates saidata files with OS-specific overrides:

```
saidata/
└── nginx/
    ├── default.yaml          # Common configuration
    ├── ubuntu/
    │   ├── 22.04.yaml       # Ubuntu 22.04 specific
    │   └── 24.04.yaml       # Ubuntu 24.04 specific
    └── debian/
        └── 12.yaml          # Debian 12 specific
```

## How It Works

1. **Discovery**: Identifies installation methods and expected resources
2. **Platform Selection**: Chooses representative platforms to test
3. **Installation**: Tests each platform-provider combination in Docker
4. **Analysis**: Identifies patterns and variations across platforms
5. **Generation**: Creates saidata with OS-specific overrides
6. **Quality Check**: Validates against schema and calculates confidence

## Architecture

Saitest uses LangGraph to orchestrate multiple AI agents:

- **Discovery Agent**: Researches installation methods
- **Platform Selection Agent**: Selects platforms to test
- **Installation Agent**: Executes installations in containers
- **Analysis Agent**: Identifies patterns and variations
- **Generation Agent**: Creates saidata files
- **Quality Check Agent**: Validates and scores results

## Development

### Running Tests

```bash
# Run all tests
pytest tests/saitest/

# Run with coverage
pytest tests/saitest/ --cov=saitest --cov-report=html
```

### Code Quality

```bash
# Format code
black saitest/
isort saitest/

# Lint
flake8 saitest/

# Type check
mypy saitest/
```

## Documentation

- [Architecture](docs/architecture.md)
- [CLI Reference](docs/cli-reference.md)
- [Examples](docs/examples/)

## License

Apache License 2.0

## Links

- Homepage: https://sai.software
- Documentation: https://sai.software/docs/saitest
- Repository: https://github.com/example42/sai-suite
- Issues: https://github.com/example42/sai-suite/issues
