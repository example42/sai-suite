# SAI Tests

Tests for SAI (Software Action Interface) execution engine and core functionality.

## Test Files

### CLI Tests
- `test_cli_apply.py` - Apply command tests
- `test_cli_main.py` - Main CLI tests

### Core Tests
- `test_core_action_loader.py` - Action loader tests
- `test_execution_engine.py` - Execution engine tests

### Provider Tests
- `test_provider_loader.py` - Provider loader tests
- `test_providers_template_engine.py` - Provider template engine tests

### Saidata Tests
- `test_saidata_loader.py` - Saidata loader tests
- `test_saidata_loader_hierarchical.py` - Hierarchical saidata tests
- `test_saidata_path.py` - Saidata path tests
- `test_saidata_repository_manager.py` - Repository manager tests

### Repository Tests
- `test_git_repository_handler.py` - Git repository handler tests
- `test_tarball_repository_handler.py` - Tarball repository handler tests

### Template Tests
- `test_template_engine.py` - Template engine tests

### Utility Tests
- `test_utils_cache.py` - Cache utility tests
- `test_utils_errors.py` - Error handling tests
- `test_utils_logging.py` - Logging utility tests
- `test_utils_system.py` - System utility tests

## Running SAI Tests

```bash
# Run all SAI tests
pytest tests/sai/

# Run specific test file
pytest tests/sai/test_execution_engine.py

# Run with coverage
pytest tests/sai/ --cov=sai
```

## Test Coverage

SAI tests cover:
- ✅ CLI commands and options
- ✅ Execution engine and action execution
- ✅ Provider system and loading
- ✅ Saidata loading and parsing
- ✅ Repository handling (git, tarball)
- ✅ Template engine
- ✅ Utility functions

## See Also

- [SAI Documentation](../../sai/docs/)
- [Main Test README](../README.md)
