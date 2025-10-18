# SAIGEN Test Fixes - May 10, 2025

## Summary
Fixed 15 out of 35 failing saigen tests by updating test code to match recent schema changes and fixing deprecated API usage.

## Changes Made

### 1. Package Model Schema Update
**Issue**: The `Package` model now requires both `name` and `package_name` fields (schema 0.3).
- `name`: Logical identifier for OS overrides and provider-specific configurations
- `package_name`: Actual package name used by package managers

**Files Fixed**:
- `tests/saigen/test_advanced_validator.py` - Updated all Package instantiations
- `tests/saigen/test_saidata_tester.py` - Fixed Package fixtures
- `tests/saigen/test_batch_engine.py` - Updated YAML package definitions
- `tests/saigen/test_update_engine.py` - Fixed both fixtures and inline YAML
- `tests/saigen/test_saigen_cli_main.py` - Updated YAML test data
- `tests/saigen/test_saidata_validator.py` - Fixed valid_saidata fixture
- `tests/saigen/test_cli_update.py` - Updated sample_saidata_file fixture

**Example Fix**:
```python
# Before
Package(name="nginx", version="1.18.0")

# After
Package(name="nginx", package_name="nginx", version="1.18.0")
```

### 2. pytest.mock Import Error
**Issue**: Tests were using `pytest.mock.AsyncMock()` which doesn't exist.

**Files Fixed**:
- `tests/saigen/test_url_filter.py` - Changed to use `AsyncMock` from `unittest.mock`

**Fix**:
```python
# Before
semaphore = pytest.mock.AsyncMock()

# After  
semaphore = AsyncMock()  # Already imported from unittest.mock
```

### 3. datetime.utcnow() Deprecation
**Issue**: `datetime.utcnow()` is deprecated in Python 3.13+.

**Files Fixed**:
- `tests/saigen/test_advanced_validator.py` - Updated to use `datetime.now(timezone.utc)`

**Fix**:
```python
# Before
from datetime import datetime
generated_at=datetime.utcnow()

# After
from datetime import datetime, timezone
generated_at=datetime.now(timezone.utc)
```

### 4. CLI Help Text Update
**Issue**: Batch command help text was updated but test still checked for old text.

**Files Fixed**:
- `tests/saigen/test_cli_batch.py` - Made assertion more flexible

**Fix**:
```python
# Before
assert "Generate saidata for multiple software packages" in result.output

# After
assert "Generate saidata" in result.output
assert "multiple software packages" in result.output
```

## Test Results

### Before
```
35 failed, 227 passed, 2 skipped, 29468 warnings
```

### After
```
20 failed, 257 passed, 2 skipped, 23473 warnings
```

### Improvement
- **15 tests fixed** (43% reduction in failures)
- **30 additional tests passing** (13% increase)
- **6000 fewer warnings** (20% reduction)

## Remaining Issues (20 failures)

The remaining 20 failures appear to be related to:

1. **CLI Integration Tests** (9 failures in `test_saigen_cli_main.py`)
   - Tests expecting specific CLI behavior that may have changed
   - Mock setup issues with generation engine

2. **Batch Processing Tests** (5 failures in `test_cli_batch.py`)
   - Preview mode tests
   - Category filtering tests
   - Partial failure handling

3. **Generation Engine Tests** (5 failures in `test_generation_engine.py`)
   - LLM provider initialization
   - YAML parsing and validation
   - Integration tests

4. **Update Engine Test** (1 failure in `test_update_engine.py`)
   - Full update workflow integration test

These remaining failures likely require deeper investigation into:
- Changes in CLI command structure
- Mock setup for async operations
- Generation engine initialization logic
- RAG availability checks

## Recommendations

1. **Continue fixing remaining tests** - Focus on CLI integration tests next
2. **Update source code deprecations** - Fix `datetime.utcnow()` usage in source files (not just tests)
3. **Schema migration guide** - Document the 0.2 → 0.3 schema changes for users
4. **Test maintenance** - Consider adding schema version fixtures to make future updates easier

## Notes

- All fixes maintain backward compatibility where possible
- No changes were made to production code, only test files
- The schema changes are intentional and align with saidata 0.3 specification
