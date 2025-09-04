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
  ubuntu-main:
    name: ubuntu-main
    type: apt
    platform: linux
    url: http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64/Packages.gz
    enabled: true
    priority: 10
    cache_ttl_hours: 24
    architecture: [amd64]
    parsing:
      format: text
      line_pattern: '^Package:\s*(.+)$'
      name_group: 1
    metadata:
      description: Ubuntu Main Repository
      maintainer: Ubuntu
  
  homebrew-core:
    name: homebrew-core
    type: brew
    platform: macos
    url: https://formulae.brew.sh/api/formula.json
    enabled: true
    priority: 10
    cache_ttl_hours: 12
    parsing:
      format: json
      field_mapping:
        name: name
        version: versions.stable
        description: desc
    metadata:
      description: Homebrew Core Formulae
      maintainer: Homebrew
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
## Generation Engine API

### GenerationEngine

Core engine for orchestrating saidata creation with LLM providers.

```python
from saigen.core.generation_engine import GenerationEngine
from saigen.models.generation import GenerationRequest, LLMProvider

# Initialize with configuration
config = {
    "llm_providers": {
        "openai": {
            "api_key": "sk-...",
            "model": "gpt-3.5-turbo",
            "max_tokens": 4000,
            "temperature": 0.1
        }
    }
}
engine = GenerationEngine(config)

# Generate saidata
request = GenerationRequest(
    software_name="nginx",
    target_providers=["apt", "brew"],
    llm_provider=LLMProvider.OPENAI,
    use_rag=True
)
result = await engine.generate_saidata(request)

# Check results
if result.success:
    print(f"Generated saidata for {result.saidata.metadata.name}")
    print(f"Tokens used: {result.tokens_used}")
    print(f"Cost: ${result.cost_estimate:.4f}")
    
    # Save to file
    await engine.save_saidata(result.saidata, Path("nginx.yaml"))
```

## Validation API

### SaidataValidator

Comprehensive validation system for saidata files.

```python
from saigen.core.validator import SaidataValidator

# Create validator
validator = SaidataValidator()

# Validate file
result = validator.validate_file(Path("nginx.yaml"))

# Validate data dictionary
result = validator.validate_data(saidata_dict)

# Format validation report
report = validator.format_validation_report(result, show_context=True)
print(report)
```

### ValidationResult

```python
from saigen.core.validator import ValidationResult, ValidationError

# Check validation results
if result.is_valid:
    print("✅ Validation passed")
else:
    print(f"❌ Validation failed with {len(result.errors)} errors")
    
# Access specific issues
for error in result.errors:
    print(f"Error: {error.message}")
    print(f"Path: {error.path}")
    print(f"Suggestion: {error.suggestion}")
```

## LLM Provider API

### OpenAI Provider

```python
from saigen.llm.providers.openai import OpenAIProvider
from saigen.models.generation import GenerationContext

# Initialize provider
config = {
    "api_key": "sk-...",
    "model": "gpt-3.5-turbo",
    "max_tokens": 4000,
    "temperature": 0.1
}
provider = OpenAIProvider(config)

# Generate saidata
context = GenerationContext(
    software_name="nginx",
    target_providers=["apt", "brew"]
)
response = await provider.generate_saidata(context)
```

### Prompt Templates

```python
from saigen.llm.prompts import PromptManager, PromptTemplate

# Get template manager
manager = PromptManager()

# Get generation template
template = manager.get_template("generation")

# Render prompt
context = GenerationContext(software_name="nginx")
prompt = template.render(context)
```