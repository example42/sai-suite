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
```

2. Generate saidata for a software package:
```bash
saigen generate nginx
```

3. Validate generated saidata:
```bash
saigen validate nginx.yaml
```

## Configuration

saigen looks for configuration files in the following locations:
- `~/.saigen/config.yaml`
- `.saigen.yaml` (in current directory)
- `saigen.yaml` (in current directory)

Example configuration:
```yaml
llm_providers:
  openai:
    provider: openai
    model: gpt-3.5-turbo
    max_tokens: 4000
    temperature: 0.1

repositories:
  apt:
    type: apt
    enabled: true
    cache_ttl: 3600

generation:
  default_providers: [apt, brew, winget]
  output_directory: ./saidata
```

## License

MIT License - see LICENSE file for details.