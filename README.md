# saigen - AI-Powered Saidata Generation Tool

saigen is a comprehensive Python tool for generating, validating, and managing software metadata in YAML format following the saidata JSON schema specification.

## Features

- **Multi-provider Integration**: Supports apt, dnf, brew, winget, and other package repositories
- **AI-Enhanced Generation**: Uses LLMs (OpenAI, Anthropic, Ollama) for intelligent metadata creation
- **Schema Validation**: Validates generated files against official saidata schema
- **RAG Support**: Retrieval-Augmented Generation for improved accuracy
- **Batch Processing**: Generate metadata for multiple software packages efficiently
- **Extensible Architecture**: Modular design for easy extension and customization

## Installation

```bash
pip install saigen
```

For development:
```bash
git clone https://github.com/sai/sai.git
cd sai
pip install -e ".[dev,llm,rag]"
```

## Quick Start

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

- `saigen generate <software>` - Generate saidata for software
- `saigen config --show` - Display current configuration
- `saigen --help` - Show all available commands and options

## Configuration

saigen looks for configuration files in the following locations:
- `~/.saigen/config.yaml` or `~/.saigen/config.json`
- `.saigen.yaml` or `.saigen.json` (in current directory)
- `saigen.yaml` or `saigen.json` (in current directory)

Configuration can also be set via environment variables:
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `SAIGEN_LOG_LEVEL` - Logging level (debug, info, warning, error)
- `SAIGEN_CACHE_DIR` - Cache directory path
- `SAIGEN_OUTPUT_DIR` - Output directory path

Example configuration:
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

## License

MIT License - see LICENSE file for details.