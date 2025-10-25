# Multi-Provider Configuration Guide

## Overview

SAIGEN supports configuring multiple instances of the same LLM provider type with different models or settings. This is particularly useful for:

- Comparing different models (e.g., different Ollama models)
- Using different endpoints for the same provider type
- Testing model performance across various configurations
- Load balancing across multiple instances

## Configuration

### Basic Structure

Each provider instance needs:
1. A unique name (e.g., `ollama_qwen3`, `ollama_deepseek`)
2. A `provider` field specifying the base type (`ollama`, `openai`, `anthropic`, `vllm`)
3. Provider-specific configuration (model, api_base, etc.)

### Example: Multiple Ollama Models

```yaml
llm_providers:
  # First Ollama instance with Qwen3 model
  ollama_qwen3:
    provider: ollama
    api_base: http://localhost:11434
    model: qwen3-coder:30b
    enabled: true
    timeout: 60
    max_retries: 3
  
  # Second Ollama instance with DeepSeek model
  ollama_deepseek:
    provider: ollama
    api_base: http://localhost:11434
    model: deepseek-r1:8b
    enabled: true
    timeout: 60
    max_retries: 3
  
  # Third Ollama instance with Phi3 model
  ollama_phi3:
    provider: ollama
    api_base: http://localhost:11434
    model: phi3:latest
    enabled: false  # Disabled by default
    timeout: 60
    max_retries: 3
```

### Example: Multiple OpenAI Endpoints

```yaml
llm_providers:
  # Official OpenAI
  openai:
    provider: openai
    model: gpt-4o-mini
    enabled: true
  
  # Azure OpenAI
  openai_azure:
    provider: openai
    api_base: https://your-resource.openai.azure.com
    model: gpt-4
    enabled: true
  
  # Local OpenAI-compatible server
  openai_local:
    provider: openai
    api_base: http://localhost:1234/v1
    api_key: not-needed
    model: local-model
    enabled: true
```

## Usage

### Command Line

Specify the exact provider name when running commands:

```bash
# Generate with Qwen3 model
saigen generate nginx --llm-provider ollama_qwen3

# Generate with DeepSeek model
saigen generate nginx --llm-provider ollama_deepseek

# Batch generation with specific provider
saigen batch software-list.txt --llm-provider ollama_qwen3

# Update existing saidata with specific provider
saigen update nginx.yaml --llm-provider ollama_deepseek
```

### Default Provider

If you don't specify a provider, SAIGEN uses the first enabled provider in your configuration:

```bash
# Uses first enabled provider (e.g., anthropic if it's first and enabled)
saigen generate nginx
```

## Naming Conventions

### Recommended Naming Pattern

Use descriptive names that indicate the provider type and model:

- `ollama_qwen3` - Ollama with Qwen3 model
- `ollama_deepseek` - Ollama with DeepSeek model
- `openai_azure` - OpenAI via Azure
- `openai_local` - Local OpenAI-compatible server

### Provider Type Extraction

The system extracts the provider type in two ways:

1. **From the `provider` field** (recommended):
   ```yaml
   ollama_qwen3:
     provider: ollama  # Explicitly set
   ```

2. **From the name prefix** (fallback):
   ```yaml
   ollama_qwen3:  # 'ollama' extracted from name
     model: qwen3-coder:30b
   ```

## Model Comparison Workflow

### 1. Configure Multiple Models

```yaml
llm_providers:
  ollama_qwen3:
    provider: ollama
    model: qwen3-coder:30b
    enabled: true
  
  ollama_deepseek:
    provider: ollama
    model: deepseek-r1:8b
    enabled: true
  
  ollama_phi3:
    provider: ollama
    model: phi3:latest
    enabled: true
```

### 2. Generate with Each Model

```bash
# Generate with each model
saigen generate nginx --llm-provider ollama_qwen3 -o nginx-qwen3.yaml
saigen generate nginx --llm-provider ollama_deepseek -o nginx-deepseek.yaml
saigen generate nginx --llm-provider ollama_phi3 -o nginx-phi3.yaml
```

### 3. Compare Results

```bash
# Validate each output
saigen validate nginx-qwen3.yaml
saigen validate nginx-deepseek.yaml
saigen validate nginx-phi3.yaml

# Compare quality scores
saigen quality nginx-qwen3.yaml
saigen quality nginx-deepseek.yaml
saigen quality nginx-phi3.yaml
```

## Troubleshooting

### Provider Not Found Error

```
Error: Invalid LLM provider: ollama_qwen3. Available providers: openai, anthropic
```

**Solution**: Check your configuration file and ensure the provider is defined:

```bash
# View current configuration
saigen config --show

# Check for validation issues
saigen config --validate
```

### Provider Type Mismatch

If you see errors about provider types, ensure the `provider` field matches the actual provider:

```yaml
# Correct
ollama_qwen3:
  provider: ollama  # Must be 'ollama'
  model: qwen3-coder:30b

# Incorrect
ollama_qwen3:
  provider: openai  # Wrong! Should be 'ollama'
  model: qwen3-coder:30b
```

### API Key Warnings

Ollama and vLLM don't require API keys. If you see warnings about missing API keys for these providers, they can be safely ignored.

## Best Practices

1. **Use Descriptive Names**: Make it clear which model each provider uses
2. **Set Appropriate Timeouts**: Local models may need longer timeouts
3. **Enable/Disable as Needed**: Use the `enabled` flag to control which providers are active
4. **Document Your Setup**: Add comments in your config explaining each provider's purpose
5. **Test Before Production**: Validate generated saidata before using in production

## Advanced Configuration

### Different Endpoints

```yaml
llm_providers:
  ollama_local:
    provider: ollama
    api_base: http://localhost:11434
    model: qwen3-coder:30b
    enabled: true
  
  ollama_remote:
    provider: ollama
    api_base: http://gpu-server:11434
    model: deepseek-r1:70b
    enabled: true
```

### Priority and Fallback

Configure multiple providers with different priorities:

```yaml
llm_providers:
  primary:
    provider: openai
    model: gpt-4o-mini
    enabled: true
    priority: high
  
  fallback:
    provider: ollama
    model: qwen3-coder:30b
    enabled: true
    priority: medium
```

## See Also

- [Configuration Guide](configuration-guide.md) - Complete configuration reference
- [CLI Reference](cli-reference.md) - All available commands
- [Generation Guide](generation-guide.md) - Saidata generation workflow
