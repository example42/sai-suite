# SAIGEN Development Scripts

Demo and development scripts for SAIGEN (SAI Data Generation).

## Scripts

### generation_engine_demo.py
Demonstrates the SAIGEN generation engine.

```bash
python scripts/development/saigen/generation_engine_demo.py
```

### llm_provider_demo.py
Shows how to use different LLM providers (OpenAI, Anthropic, Ollama).

```bash
python scripts/development/saigen/llm_provider_demo.py
```

### advanced_validation_demo.py
Demonstrates advanced saidata validation features.

```bash
python scripts/development/saigen/advanced_validation_demo.py
```

### retry_generation_example.py
Shows retry logic for failed generations.

```bash
python scripts/development/saigen/retry_generation_example.py
```

### saidata_validation_demo.py
Demonstrates saidata validation against schema.

```bash
python scripts/development/saigen/saidata_validation_demo.py
```

### output_formatting_demo.py
Shows output formatting and logging features.

```bash
python scripts/development/saigen/output_formatting_demo.py
```

### sample_data_demo.py
Demonstrates working with sample data and fixtures.

```bash
python scripts/development/saigen/sample_data_demo.py
```

### start-vllm-dgx.sh
Starts vLLM server optimized for NVIDIA GB10 (Grace Blackwell) systems.

```bash
# Start with default settings (Llama 3 8B on 1 GPU)
./scripts/development/saigen/start-vllm-dgx.sh

# Start with custom model
./scripts/development/saigen/start-vllm-dgx.sh mistralai/Mistral-7B-Instruct-v0.2

# Start with specific port
./scripts/development/saigen/start-vllm-dgx.sh meta-llama/Meta-Llama-3-8B-Instruct 1 8000
```

### test-vllm-provider.py
Tests vLLM provider integration and connection.

```bash
# Run full test suite
python scripts/development/saigen/test-vllm-provider.py

# Requires vLLM server to be running
```

## Usage

These scripts are for development and demonstration purposes. They show how to use SAIGEN's internal APIs and components.

## Requirements

```bash
# Install SAIGEN in development mode with all features
pip install -e ./saigen[dev,llm,rag]
```

## Environment Variables

Some scripts require API keys:

```bash
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
```

## See Also

- [SAIGEN Documentation](../../../saigen/docs/)
- [SAIGEN Examples](../../../saigen/docs/examples/)
- [Generation Engine Guide](../../../saigen/docs/generation-engine.md)
