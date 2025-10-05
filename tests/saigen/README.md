# SAIGEN Tests

Tests for SAIGEN (SAI Data Generation) generation engine and features.

## Test Files

### CLI Tests
- `test_cli_batch.py` - Batch command tests
- `test_cli_completion.py` - CLI completion tests
- `test_cli_test.py` - Test command tests
- `test_cli_update.py` - Update command tests
- `test_saigen_cli_main.py` - Main CLI tests

### Generation Tests
- `test_generation_engine.py` - Generation engine tests
- `test_batch_engine.py` - Batch processing tests
- `test_update_engine.py` - Update engine tests

### LLM Tests
- `test_llm_providers.py` - LLM provider tests

### Repository Tests
- `test_repository_cache.py` - Repository cache tests
- `test_saigen_repository_manager.py` - Repository manager tests

### Validation Tests
- `test_advanced_validator.py` - Advanced validation tests
- `test_saidata_validator.py` - Saidata validator tests
- `test_saidata_tester.py` - Saidata tester tests

### Feature Tests
- `test_rag_indexer.py` - RAG indexer tests
- `test_refresh_versions.py` - Refresh versions tests
- `test_url_filter.py` - URL filter tests

## Running SAIGEN Tests

```bash
# Run all SAIGEN tests
pytest tests/saigen/

# Run specific test file
pytest tests/saigen/test_generation_engine.py

# Run with coverage
pytest tests/saigen/ --cov=saigen
```

## Test Coverage

SAIGEN tests cover:
- ✅ CLI commands and options
- ✅ Generation engine and AI integration
- ✅ LLM providers (OpenAI, Anthropic, Ollama)
- ✅ Repository management and caching
- ✅ Validation and testing framework
- ✅ Batch processing
- ✅ RAG features
- ✅ URL filtering and validation

## Test Documentation

See [SAIGEN_TEST_DOCUMENTATION.md](SAIGEN_TEST_DOCUMENTATION.md) for detailed test documentation.

## See Also

- [SAIGEN Documentation](../../saigen/docs/)
- [Main Test README](../README.md)
