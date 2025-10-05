# SAI Test Suite

Comprehensive test suite for the SAI Software Management Suite.

## Structure

```
tests/
├── sai/              # SAI-specific tests
├── saigen/           # SAIGEN-specific tests
├── shared/           # Shared tests (models, config)
├── integration/      # Integration tests (both packages)
├── fixtures/         # Shared test fixtures
└── archive/          # Obsolete tests
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run SAI Tests Only
```bash
pytest tests/sai/
```

### Run SAIGEN Tests Only
```bash
pytest tests/saigen/
```

### Run Integration Tests
```bash
pytest tests/integration/
```

### Run Shared Tests
```bash
pytest tests/shared/
```

### Run with Coverage
```bash
pytest --cov=sai --cov=saigen --cov-report=html
```

### Run Specific Test File
```bash
pytest tests/sai/test_execution_engine.py
```

### Run with Verbose Output
```bash
pytest -v
```

## Test Organization

### SAI Tests (`tests/sai/`)
Tests for SAI execution engine, providers, and core functionality:
- CLI tests
- Execution engine tests
- Provider tests
- Template engine tests
- Saidata loader tests
- Utility tests

### SAIGEN Tests (`tests/saigen/`)
Tests for SAIGEN generation engine and features:
- Generation engine tests
- LLM provider tests
- Repository management tests
- Validation tests
- Batch processing tests
- URL filter tests

### Shared Tests (`tests/shared/`)
Tests for shared components:
- Configuration tests
- Model tests
- Output formatter tests

### Integration Tests (`tests/integration/`)
End-to-end integration tests:
- Complete workflow tests
- Cross-component integration
- Git integration tests
- Template integration tests

## Test Fixtures

Shared fixtures are in `tests/fixtures/` and `tests/conftest.py`.

## Test Runners

- `run_basic_tests.py` - Run basic test suite
- `run_integration_tests.py` - Run integration tests

## Configuration

- `conftest.py` - Shared pytest configuration
- `pytest_integration.ini` - Integration test configuration

## CI/CD

Tests are automatically run in CI/CD pipelines:
- On pull requests
- On main branch commits
- Separate jobs for SAI and SAIGEN tests

## Writing Tests

### Test File Naming
- Prefix with `test_`
- Use descriptive names
- Place in appropriate directory (sai/, saigen/, shared/, integration/)

### Test Function Naming
- Prefix with `test_`
- Use descriptive names
- Follow pattern: `test_<what>_<condition>_<expected>`

### Example
```python
def test_execution_engine_install_action_succeeds():
    """Test that execution engine successfully executes install action."""
    # Test implementation
```

## Archived Tests

Obsolete and duplicate tests are in `tests/archive/` for reference.

## See Also

- [SAI Documentation](../sai/docs/)
- [SAIGEN Documentation](../saigen/docs/)
- [SAIGEN Test Documentation](saigen/SAIGEN_TEST_DOCUMENTATION.md)
