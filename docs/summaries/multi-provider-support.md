# Multi-Provider Instance Support Implementation

## Summary

Implemented support for multiple instances of the same LLM provider type (e.g., multiple Ollama models) with different configurations. Users can now configure multiple providers of the same type by using unique names in their configuration.

## Problem

Previously, the system only supported one instance per provider type (openai, anthropic, ollama, vllm). Users couldn't configure multiple Ollama models or multiple OpenAI endpoints with different settings. The code tried to convert provider names directly to the `LLMProvider` enum, which failed for names like `ollama_qwen3`.

## Solution

### 1. Provider Type Extraction

Added logic to extract the base provider type from provider names or configuration:
- Provider names like `ollama_qwen3` are split to extract `ollama` as the type
- The `provider` field in configuration explicitly specifies the type
- New helper methods in `LLMProviderManager`:
  - `extract_provider_type()`: Extracts base provider type from name/config
  - `validate_provider_name()`: Validates provider names against configuration

### 2. Provider Name Handling

Updated all CLI commands to use provider names as strings instead of converting to enum:
- `batch.py`: Validates provider names against config keys
- `generate.py`: Uses provider names directly
- `update.py`: Uses provider names directly
- Better error messages showing available configured providers

### 3. Model Updates

Changed `GenerationRequest` and `BatchGenerationRequest` models:
- `llm_provider` field changed from `LLMProvider` enum to `str`
- Maintains backward compatibility with existing code
- Generation engine already handled both string and enum values

### 4. Validation Improvements

Updated configuration validation:
- Ollama and vLLM providers no longer require API keys
- Validation checks provider existence in configuration
- Clear error messages with list of available providers

### 5. Documentation Updates

Updated documentation to explain multi-provider support:
- `README.md`: Added example with multiple Ollama instances
- `saigen/docs/configuration-guide.md`: Added dedicated section on multi-provider instances
- `saigen/docs/examples/saigen-config-sample.yaml`: Updated with multiple Ollama examples
- CLI help text updated to reflect provider name usage

## Configuration Example

```yaml
llm_providers:
  openai:
    provider: openai
    model: gpt-4o-mini
    enabled: true
  
  # Multiple Ollama instances with different models
  ollama_qwen3:
    provider: ollama
    api_base: http://localhost:11434
    model: qwen3-coder:30b
    enabled: true
  
  ollama_deepseek:
    provider: ollama
    api_base: http://localhost:11434
    model: deepseek-r1:8b
    enabled: true
  
  ollama_phi3:
    provider: ollama
    api_base: http://localhost:11434
    model: phi3:latest
    enabled: true
```

## Usage

```bash
# Use specific provider
saigen generate nginx --llm-provider ollama_qwen3

# Use different provider
saigen batch software-list.txt --llm-provider ollama_deepseek

# Use default (first enabled provider)
saigen generate nginx
```

## Files Modified

### Core Implementation
- `saigen/llm/provider_manager.py`: Added provider type extraction logic
- `saigen/models/generation.py`: Changed llm_provider field to string
- `saigen/core/update_engine.py`: Updated method signature

### CLI Commands
- `saigen/cli/main.py`: Updated help text
- `saigen/cli/commands/batch.py`: Provider name validation
- `saigen/cli/commands/generate.py`: Provider name validation
- `saigen/cli/commands/update.py`: Provider name validation

### Configuration & Validation
- `saigen/utils/config.py`: Skip API key validation for ollama/vllm

### Documentation
- `README.md`: Added multi-provider example
- `saigen/docs/configuration-guide.md`: Added multi-provider section
- `saigen/docs/examples/saigen-config-sample.yaml`: Updated examples

## Testing

All existing tests pass. The implementation:
- Maintains backward compatibility with existing configurations
- Handles both string and enum provider values in generation engine
- Validates provider names against actual configuration
- Provides clear error messages when invalid providers are specified

## Benefits

1. **Flexibility**: Users can configure multiple models of the same provider type
2. **Model Comparison**: Easy to compare different models by switching providers
3. **Resource Management**: Different models can use different endpoints/servers
4. **Clear Naming**: Descriptive names like `ollama_qwen3` make it obvious which model is being used
5. **Backward Compatible**: Existing single-provider configurations continue to work
