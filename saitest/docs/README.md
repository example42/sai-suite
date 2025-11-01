# Saitest Documentation

Saitest is an agent-based verification tool that automatically generates and validates saidata by testing software installations across multiple platforms and providers.

## Overview

Saitest uses LangGraph to orchestrate AI agents that:
- Install software in Docker containers
- Observe system changes (files, services, ports)
- Analyze patterns across platforms
- Generate validated saidata following schema 0.3
- Create OS-specific overrides for platform differences

## Quick Start

```bash
# Verify software and generate saidata
saitest verify nginx --platforms ubuntu:22.04,debian:12 --output-dir ./saidata

# Test existing saidata
saitest test software/nginx/default.yaml

# Verbose output
saitest verify apache --verbose
```

## Key Features

- **Agent-Based Workflow**: LangGraph orchestrates 6 specialized agents for intelligent verification
- **Multi-Platform Testing**: Test across Ubuntu, Debian, CentOS, Rocky, Fedora, and more
- **Multi-Provider Support**: Test apt, dnf, pip, gem, npm, brew, and any provider with providerdata
- **Container Isolation**: Docker-based testing environments for safe, reproducible installations
- **Filesystem Monitoring**: Captures all changes during installation
- **Providerdata Integration**: Uses same commands as sai for consistency
- **OS-Specific Overrides**: Generates default.yaml and platform-specific override files
- **Confidence Scoring**: Quality assessment with human review flagging
- **Saigen Integration**: Leverages repository cache for package metadata

## Documentation

- [Architecture](architecture.md) - Design details and component overview
- [CLI Reference](cli-reference.md) - Command documentation and options
- [Examples](examples/) - Usage examples and workflows

## Workflow

```
Discovery → Platform Selection → Installation → Analysis → Generation → Quality Check
```

1. **Discovery Agent**: Researches installation methods and providers
2. **Platform Selection Agent**: Chooses representative test platforms
3. **Installation Agent**: Installs software and monitors changes
4. **Analysis Agent**: Identifies patterns and variations
5. **Generation Agent**: Creates saidata with overrides
6. **Quality Check Agent**: Validates and scores results

## Integration

Saitest integrates with the sai-suite monorepo:

```python
# Import from saigen
from saigen.repositories import RepositoryDownloader
from saigen.models.saidata import SaidataModel

# Import from saitest
from saitest.core.orchestrator import run_verification
from saitest.models.observation import Observation
```

## Requirements

- Python 3.10+
- Docker (for container-based testing)
- LangGraph and LangChain
- OpenAI or Anthropic API key

## Installation

```bash
# Install with saitest support
pip install sai-suite[saitest]

# Or install from source
cd sai-suite/saitest
pip install -e .
```

## Configuration

Set your LLM API key:

```bash
export OPENAI_API_KEY="your-key-here"
# or
export ANTHROPIC_API_KEY="your-key-here"
```

## Output Structure

Saitest generates saidata with OS-specific overrides:

```
output/
└── nginx/
    ├── default.yaml          # Base configuration
    ├── ubuntu/
    │   └── 22.04.yaml       # Ubuntu 22.04 specific
    └── debian/
        └── 12.yaml          # Debian 12 specific
```

## Contributing

See the main [sai-suite documentation](../../docs/README.md) for contribution guidelines.

## License

See [LICENSE](../../LICENSE) in the repository root.
