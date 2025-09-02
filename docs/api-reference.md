# API Reference

## Core Models

### SaiData

The main data structure representing software metadata.

```python
from saigen.models.saidata import SaiData

saidata = SaiData(
    version="0.2.0",
    metadata={
        "name": "nginx",
        "display_name": "NGINX Web Server",
        "description": "High-performance HTTP server and reverse proxy",
        "category": "web-server",
        "tags": ["web", "server", "proxy"]
    },
    packages=[
        {
            "name": "nginx",
            "version": "1.24.0"
        }
    ]
)
```

### Configuration

Configuration management for saigen.

```python
from saigen.utils.config import get_config, ConfigManager

# Get current configuration
config = get_config()

# Create custom configuration manager
manager = ConfigManager(config_path=Path("custom-config.yaml"))
config = manager.load_config()

# Update configuration
manager.update_config({
    "log_level": "debug",
    "generation": {
        "parallel_requests": 5
    }
})
```

### Generation Request

Request structure for generating saidata.

```python
from saigen.models.generation import GenerationRequest, LLMProvider

request = GenerationRequest(
    software_name="nginx",
    target_providers=["apt", "brew", "winget"],
    llm_provider=LLMProvider.OPENAI,
    use_rag=True,
    user_hints={
        "category": "web-server",
        "description": "Popular web server"
    }
)
```

## Configuration Options

### LLM Providers

```yaml
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
    max_tokens: 4000
    temperature: 0.1
    enabled: false
```

### Repository Configuration

```yaml
repositories:
  apt:
    type: apt
    enabled: true
    cache_ttl: 3600
    priority: 1
  
  brew:
    type: brew
    enabled: true
    cache_ttl: 7200
    priority: 2
```

### Cache Configuration

```yaml
cache:
  directory: ~/.saigen/cache
  max_size_mb: 1000
  default_ttl: 3600
  cleanup_interval: 86400
```

### RAG Configuration

```yaml
rag:
  enabled: true
  index_directory: ~/.saigen/rag_index
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
  max_context_items: 5
  similarity_threshold: 0.7
```

## Environment Variables

- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `SAIGEN_LOG_LEVEL` - Logging level (debug, info, warning, error)
- `SAIGEN_CACHE_DIR` - Cache directory path
- `SAIGEN_OUTPUT_DIR` - Output directory path

## Error Handling

All models use Pydantic validation and will raise `ValidationError` for invalid data:

```python
from pydantic import ValidationError
from saigen.models.saidata import SaiData

try:
    saidata = SaiData(
        version="invalid-version",  # Invalid format
        metadata={"name": "test"}
    )
except ValidationError as e:
    print(f"Validation error: {e}")
```

## Security

- API keys are stored as `SecretStr` and masked in configuration display
- Configuration files are saved with secure permissions (0o600)
- YAML loading uses `safe_load` to prevent code execution
- Input validation prevents injection attacks