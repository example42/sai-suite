# Tests Directory Reorganization Plan

**Date:** May 10, 2025

## Current State

The `tests/` directory contains 60+ test files mixed together:
- SAI-specific tests
- SAIGEN-specific tests
- Shared/integration tests
- Obsolete/duplicate tests
- Test documentation

## Issues

1. **Mixed tests** - SAI and SAIGEN tests all together
2. **Hard to run** - Can't easily run just SAI or SAIGEN tests
3. **Unclear ownership** - Not obvious which tests belong to which package
4. **Duplicates** - Some tests appear to be duplicates or obsolete

## New Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared pytest configuration
├── README.md                      # Test suite overview
├── fixtures/                      # Shared fixtures
│   ├── __init__.py
│   └── test_repositories.py
├── sai/                          # SAI-specific tests
│   ├── __init__.py
│   ├── conftest.py              # SAI-specific fixtures
│   ├── test_cli_apply.py
│   ├── test_cli_main.py
│   ├── test_core_action_loader.py
│   ├── test_execution_engine.py
│   ├── test_git_repository_handler.py
│   ├── test_provider_loader.py
│   ├── test_providers_template_engine.py
│   ├── test_saidata_loader.py
│   ├── test_saidata_path.py
│   ├── test_saidata_repository_manager.py
│   ├── test_tarball_repository_handler.py
│   ├── test_template_engine.py
│   └── test_utils_*.py
├── saigen/                       # SAIGEN-specific tests
│   ├── __init__.py
│   ├── conftest.py              # SAIGEN-specific fixtures
│   ├── test_advanced_validator.py
│   ├── test_batch_engine.py
│   ├── test_cli_batch.py
│   ├── test_cli_test.py
│   ├── test_cli_update.py
│   ├── test_generation_engine.py
│   ├── test_llm_providers.py
│   ├── test_rag_indexer.py
│   ├── test_refresh_versions.py
│   ├── test_repository_*.py
│   ├── test_saidata_tester.py
│   ├── test_saidata_validator.py
│   ├── test_saigen_*.py
│   ├── test_update_engine.py
│   └── test_url_filter.py
├── integration/                  # Integration tests (both packages)
│   ├── __init__.py
│   ├── test_complete_workflows.py
│   ├── test_git_integration.py
│   ├── test_hierarchical_integration.py
│   ├── test_provider_template_integration.py
│   ├── test_saigen_integration.py
│   ├── test_tarball_integration.py
│   ├── test_template_integration.py
│   └── test_update_integration.py
└── archive/                      # Obsolete tests
    ├── test_click.py            # Obsolete
    ├── test_hierarchical_path_edge_cases.py  # Covered elsewhere
    ├── test_llm_providers_extended.py  # Duplicate
    ├── test_performance_benchmarks.py  # Outdated
    ├── test_provider_availability.py  # Obsolete
    ├── test_provider_filtering.py  # Obsolete
    ├── test_provider_mapping.py  # Obsolete
    ├── test_repository_caching_advanced.py  # Duplicate
    ├── test_repository_components_comprehensive.py  # Duplicate
    ├── test_repository_error_handling.py  # Covered elsewhere
    ├── test_repository_integration_e2e.py  # Duplicate
    ├── test_runner.py  # Obsolete
    ├── test_saigen_runner.py  # Obsolete
    ├── test_utils_cache_simple.py  # Duplicate
    ├── test_validate_providers.py  # Obsolete
    └── test_validate.py  # Obsolete
```

## Categorization

### SAI Tests (Core execution)
- test_cli_apply.py
- test_cli_main.py
- test_core_action_loader.py
- test_execution_engine.py
- test_git_repository_handler.py
- test_provider_loader.py
- test_providers_template_engine.py
- test_saidata_loader.py
- test_saidata_loader_hierarchical.py
- test_saidata_path.py
- test_saidata_repository_manager.py
- test_tarball_repository_handler.py
- test_template_engine.py
- test_utils_cache.py
- test_utils_errors.py
- test_utils_logging.py
- test_utils_system.py

### SAIGEN Tests (Generation)
- test_advanced_validator.py
- test_batch_engine.py
- test_cli_batch.py
- test_cli_completion.py
- test_cli_test.py
- test_cli_update.py
- test_generation_engine.py
- test_llm_providers.py
- test_rag_indexer.py
- test_refresh_versions.py
- test_repository_cache.py
- test_saidata_tester.py
- test_saidata_validator.py
- test_saigen_batch_engine.py
- test_saigen_cli_main.py
- test_saigen_repository_manager.py
- test_update_engine.py
- test_url_filter.py

### Integration Tests (Both)
- test_complete_workflows.py
- test_git_integration.py
- test_hierarchical_integration.py
- test_provider_template_integration.py
- test_saigen_integration.py
- test_tarball_integration.py
- test_template_integration.py
- test_update_integration.py

### Shared Tests (Models, Config)
- test_config.py
- test_models.py
- test_models_actions.py
- test_output_formatter.py

### Obsolete/Duplicate Tests (Archive)
- test_click.py
- test_hierarchical_path_edge_cases.py
- test_llm_providers_extended.py
- test_performance_benchmarks.py
- test_provider_availability.py
- test_provider_filtering.py
- test_provider_mapping.py
- test_repository_caching_advanced.py
- test_repository_components_comprehensive.py
- test_repository_error_handling.py
- test_repository_integration_e2e.py
- test_runner.py
- test_saigen_runner.py
- test_utils_cache_simple.py
- test_validate_providers.py
- test_validate.py

### Test Documentation
- SAIGEN_TEST_DOCUMENTATION.md → saigen/
- TEST_SUMMARY.md → archive/

### Test Runners (Keep in root)
- run_basic_tests.py
- run_integration_tests.py
- pytest_integration.ini

## Benefits

✅ **Clear separation** - SAI vs SAIGEN tests  
✅ **Easy to run** - `pytest tests/sai/` or `pytest tests/saigen/`  
✅ **Better organization** - Tests match code structure  
✅ **Faster CI** - Can run package-specific tests  
✅ **Maintainable** - Clear ownership  
✅ **Clean** - Obsolete tests archived  

## Actions

1. Create new directory structure
2. Move SAI tests to tests/sai/
3. Move SAIGEN tests to tests/saigen/
4. Keep integration tests in tests/integration/
5. Archive obsolete tests
6. Update conftest.py for new structure
7. Create README files
8. Update pytest configuration
9. Update CI/CD workflows

## Note

**Not fixing tests** - Just organizing them. Fixing broken tests is a separate task.
