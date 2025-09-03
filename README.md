# SAI Software Management Suite

This repository contains two complementary tools for software metadata management:

## 🔧 SAI - Software Action Interface CLI Tool

A lightweight CLI tool for executing software management actions using provider-based configurations.

**Key Features:**
- **Provider-based Actions**: Execute install, configure, start, stop, and other actions
- **Multi-platform Support**: Works across Linux, macOS, and Windows
- **Extensible Providers**: Support for package managers, containers, and custom providers
- **Configuration Management**: Flexible YAML/JSON configuration system
- **Dry-run Mode**: Preview actions before execution

## 🤖 SAIGEN - AI-Powered Saidata Generation Tool

An AI-enhanced tool for generating, validating, and managing software metadata in YAML format.

**Key Features:**
- **Multi-provider Integration**: Supports apt, dnf, brew, winget, and other package repositories
- **AI-Enhanced Generation**: Uses LLMs (OpenAI, Anthropic, Ollama) for intelligent metadata creation
- **Schema Validation**: Validates generated files against official saidata schema
- **RAG Support**: Retrieval-Augmented Generation for improved accuracy
- **Batch Processing**: Generate metadata for multiple software packages efficiently
- **Extensible Architecture**: Modular design for easy extension and customization

## Installation

### Install Both Tools
```bash
pip install sai  # Installs both sai and saigen
```

### Development Installation
```bash
git clone https://github.com/example42/sai.git
cd sai
pip install -e ".[dev,llm,rag]"
```

## Quick Start

### SAI CLI Tool

1. Execute software actions using providers:
```bash
# Install nginx using available providers
sai install nginx

# Start a service
sai start nginx

# Configure with specific provider
sai configure nginx --provider apt

# Dry run to preview actions
sai install nginx --dry-run
```

2. View available providers and statistics:
```bash
sai providers list
sai actions nginx
sai stats --detailed
sai config-show
```

### SAIGEN AI Generation Tool

1. Configure your LLM provider:
```bash
export OPENAI_API_KEY="your-api-key"
# or
export ANTHROPIC_API_KEY="your-api-key"
```

2. Generate saidata for a software package:
```bash
saigen generate nginx
```

3. View current configuration:
```bash
saigen config --show
```

4. Generate with specific options:
```bash
saigen generate nginx --llm-provider openai --providers apt brew --output nginx.yaml
```

## Commands

### SAI Commands
- `sai install <software>` - Install software using available providers
- `sai configure <software>` - Configure software
- `sai start <software>` - Start software/service
- `sai stop <software>` - Stop software/service
- `sai providers list` - List available providers
- `sai actions <software>` - Show available actions for software
- `sai stats` - Show comprehensive statistics about providers and actions
- `sai config-show` - Display current SAI configuration
- `sai version` - Show version information

### SAIGEN Commands
- `saigen generate <software>` - Generate saidata for software
- `saigen config --show` - Display current configuration
- `saigen --help` - Show all available commands and options

## Troubleshooting

For common issues and solutions, see the [Troubleshooting Guide](docs/troubleshooting.md).

## Configuration

### SAI Configuration

SAI looks for configuration files in:
- `~/.sai/config.yaml` or `~/.sai/config.json`
- `.sai.yaml` or `.sai.json` (in current directory)
- `sai.yaml` or `sai.json` (in current directory)

Example SAI configuration:
```yaml
config_version: "0.1.0"
log_level: info

# Provider search paths
saidata_paths:
  - "."
  - "~/.sai/saidata"
  - "/usr/local/share/sai/saidata"

provider_paths:
  - "providers"
  - "~/.sai/providers"
  - "/usr/local/share/sai/providers"

# Provider priorities (lower number = higher priority)
provider_priorities:
  apt: 1
  brew: 2
  winget: 3

# Execution settings
max_concurrent_actions: 3
action_timeout: 300
require_confirmation: true
dry_run_default: false
```

### SAIGEN Configuration

SAIGEN looks for configuration files in:
- `~/.saigen/config.yaml` or `~/.saigen/config.json`
- `.saigen.yaml` or `.saigen.json` (in current directory)
- `saigen.yaml` or `saigen.json` (in current directory)

Configuration can also be set via environment variables:
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `SAIGEN_LOG_LEVEL` - Logging level (debug, info, warning, error)
- `SAIGEN_CACHE_DIR` - Cache directory path
- `SAIGEN_OUTPUT_DIR` - Output directory path

Example SAIGEN configuration:
```yaml
config_version: "0.1.0"
log_level: info

llm_providers:
  openai:
    provider: openai
    model: gpt-3.5-turbo
    max_tokens: 4000
    temperature: 0.1
    timeout: 30
    max_retries: 3
    enabled: true
  anthropic:
    provider: anthropic
    model: claude-3-sonnet-20240229
    enabled: false

repositories:
  apt:
    type: apt
    enabled: true
    cache_ttl: 3600
    priority: 1

cache:
  directory: ~/.saigen/cache
  max_size_mb: 1000
  default_ttl: 3600

rag:
  enabled: true
  index_directory: ~/.saigen/rag_index
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
  max_context_items: 5

generation:
  default_providers: [apt, brew, winget]
  output_directory: ./saidata
  parallel_requests: 3
  request_timeout: 120

validation:
  strict_mode: true
  auto_fix_common_issues: true
```

## Repository Structure

```
├── sai/                    # SAI CLI Tool
│   ├── cli/               # CLI interface and commands
│   ├── models/            # Data models (config, provider data)
│   └── utils/             # Utilities (config management)
├── saigen/                # SAIGEN AI Generation Tool
│   ├── cli/               # CLI interface and commands
│   ├── core/              # Core generation engine
│   ├── llm/               # LLM provider integrations
│   ├── models/            # Data models (saidata, generation)
│   ├── repositories/      # Package repository integrations
│   └── utils/             # Utilities and helpers
├── saidata/               # Generated saidata files
├── providers/             # Provider data files
├── schemas/               # JSON schema definitions
├── docs/                  # Documentation
├── tests/                 # Test suite
└── examples/              # Usage examples
```

## Project Relationship

- **SAI** consumes saidata files and provider configurations to execute software management actions
- **SAIGEN** generates saidata files using AI and repository data that SAI can then use
- Both tools share common schemas and data formats but operate independently
- SAI focuses on execution and action management
- SAIGEN focuses on metadata generation and validation

## Use Cases

### SAI Use Cases
- Automated software deployment and configuration
- Cross-platform software management
- Infrastructure as Code implementations
- CI/CD pipeline integrations
- System administration automation

### SAIGEN Use Cases
- Generating metadata for new software packages
- Updating existing saidata with latest information
- Bulk metadata generation for software catalogs
- AI-assisted software documentation
- Repository data analysis and enrichment

## License

MIT License - see LICENSE file for details.