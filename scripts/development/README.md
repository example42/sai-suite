# Development Scripts

This directory contains development tools and demonstration scripts for the SAI Software Management Suite.

## Code Analysis Tools

### find_truly_unused.py
Comprehensive analysis tool that finds truly unused methods by checking all usage across the codebase including tests. Uses AST parsing to detect method definitions and calls, including attribute access and property usage.

**Usage:**
```bash
./scripts/development/find_truly_unused.py
```

**Features:**
- Analyzes both source code and test files
- Detects method calls, attribute access, and property usage
- Filters out common patterns (main, test methods, etc.)
- Groups results by class/module context

**Use case:** Identify dead code for cleanup and refactoring.

## Package-Specific Demo Scripts

Demo scripts are organized by package to showcase internal APIs and components.

### SAI Demos (`sai/`)

Demonstration scripts for SAI execution engine features:

- **execution_engine_demo.py** - Action execution and provider system
- **saidata_loader_demo.py** - Loading and parsing saidata files
- **template_engine_demo.py** - Dynamic configuration templating
- **security_demo.py** - Security features and credential management
- **hierarchical_saidata_demo.py** - Hierarchical saidata structure

**Usage:**
```bash
# Install SAI in development mode first
pip install -e ./sai[dev]

# Run any demo
python scripts/development/sai/execution_engine_demo.py
```

See [sai/README.md](sai/README.md) for detailed documentation.

### SAIGEN Demos (`saigen/`)

Demonstration scripts for SAIGEN generation engine features:

- **generation_engine_demo.py** - Core generation engine functionality
- **llm_provider_demo.py** - LLM provider integrations (OpenAI, Anthropic, Ollama)
- **advanced_validation_demo.py** - Advanced saidata validation
- **retry_generation_example.py** - Retry logic for failed generations
- **saidata_validation_demo.py** - Schema validation
- **output_formatting_demo.py** - Output formatting and logging
- **sample_data_demo.py** - Working with sample data and fixtures
- **start-vllm-dgx.sh** - Start vLLM server for NVIDIA GB10 systems
- **test-vllm-provider.py** - Test vLLM provider integration

**Usage:**
```bash
# Install SAIGEN in development mode with all features
pip install -e ./saigen[dev,llm,rag]

# Set API keys if needed
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"

# Run any demo
python scripts/development/saigen/generation_engine_demo.py
```

See [saigen/README.md](saigen/README.md) for detailed documentation.

## Testing vs Demo Scripts

**Important:** These are demo/development scripts, not tests.

- **Demo scripts** (here) - Show how to use internal APIs, for learning and development
- **Test scripts** (in `tests/`) - Automated test suite with pytest, for CI/CD

If you need to test functionality:
```bash
# Run the proper test suite
pytest tests/

# Run specific test file
pytest tests/saigen/test_url_filter.py
pytest tests/saigen/test_llm_providers.py
```

## Removed Scripts

The following scripts were removed as they're now covered by the proper test suite:

- `test_config_init.py` - Config tests in `tests/saigen/test_config.py`
- `test_deduplication.py` - Should be in proper test suite
- `test_url_filter.py` - Tests in `tests/saigen/test_url_filter.py`
- `test_prompt_improvements.py` - Tests in `tests/saigen/test_llm_providers.py`
- `test_url_prompt_enhancement.py` - Tests in `tests/saigen/test_llm_providers.py`
- `analyze_unused_methods.py` - Superseded by `find_truly_unused.py`
- `comprehensive_unused_analysis.py` - Hardcoded candidates, not maintainable
- `setup-test-runner.sh` - No self-hosted runners configured

## Quick Reference

**Analyze code for unused methods:**
```bash
./scripts/development/find_truly_unused.py
```

**Run SAI demos:**
```bash
pip install -e ./sai[dev]
python scripts/development/sai/execution_engine_demo.py
```

**Run SAIGEN demos:**
```bash
pip install -e ./saigen[dev,llm]
python scripts/development/saigen/generation_engine_demo.py
```

**Run actual tests:**
```bash
pytest tests/
```

## Contributing

When adding new demo scripts:

1. Place them in the appropriate package subdirectory (`sai/` or `saigen/`)
2. Add documentation to the package-specific README
3. Include usage examples and requirements
4. Keep demos focused on showcasing specific features

When adding new tests:

1. Add them to the `tests/` directory, not here
2. Follow pytest conventions
3. Ensure they run in CI/CD
