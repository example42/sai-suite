# Implementation Plan

- [x] 1. Update data models for schema 0.3 support
  - Update Package model to include both name and package_name fields
  - Create new Source model with build system support
  - Create new Binary model with platform/architecture support
  - Create new Script model with security features
  - Update ProviderConfig to include sources, binaries, scripts
  - Update SaiData to include top-level sources, binaries, scripts arrays
  - _Requirements: 1.2, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3_

- [x] 1.1 Update Package model in sai/models/saidata.py
  - Add package_name field as required string
  - Keep name field as logical identifier
  - Update docstrings to explain the distinction
  - _Requirements: 1.2, 2.1_

- [x] 1.2 Create Source model in sai/models/saidata.py
  - Define BuildSystem enum with autotools, cmake, make, meson, ninja, custom
  - Create CustomCommands model for overriding default behavior
  - Create Source model with all required fields from schema
  - Add validation for checksum format
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 1.3 Create Binary model in sai/models/saidata.py
  - Create ArchiveConfig model for extraction configuration
  - Create Binary model with platform/architecture support
  - Add URL templating field support
  - Add permissions field with octal format validation
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 1.4 Create Script model in sai/models/saidata.py
  - Create Script model with security features
  - Add checksum field for verification
  - Add timeout field with validation (1-3600 seconds)
  - Add interpreter and arguments fields
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 1.5 Update ProviderConfig and SaiData models
  - Add sources, binaries, scripts arrays to ProviderConfig
  - Add sources, binaries, scripts arrays to SaiData top-level
  - Update model_config to handle new enums
  - _Requirements: 5.2, 5.3_

- [x] 2. Update schema validation for 0.3 format
  - Change schema file path from 0.2 to 0.3
  - Update validation methods for new fields
  - Add validation for package_name requirement
  - Update error messages for 0.3 schema
  - _Requirements: 1.1, 1.3, 1.4, 1.5, 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 2.1 Update schema loading in sai/core/saidata_loader.py
  - Change _load_schema() to use saidata-0.3-schema.json
  - Update fallback schema for 0.3 format
  - Add logging for schema version
  - _Requirements: 1.1, 8.1_

- [x] 2.2 Update package validation in sai/core/saidata_loader.py
  - Modify _validate_packages() to check for package_name field
  - Add clear error messages when package_name is missing
  - Validate both name and package_name are present
  - _Requirements: 1.2, 8.2_

- [x] 2.3 Add validation for new resource types
  - Add _validate_sources() method for source configurations
  - Add _validate_binaries() method for binary configurations
  - Add _validate_scripts() method for script configurations
  - Validate checksum format, URL templates, and required fields
  - _Requirements: 8.3, 8.4, 8.5_

- [x] 3. Update template engine for new function signatures
  - Update sai_package function to support field parameter
  - Add sai_source, sai_binary, sai_script template functions
  - Update context builder to include new arrays
  - Add conversion methods for new models
  - Register new functions in template engine
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 3.1 Update sai_package function signature
  - Modify _sai_package_global() to accept field parameter
  - Default field to 'package_name' for backward compatibility
  - Support 'name', 'package_name', 'version', and other fields
  - Handle wildcard '*' for all packages
  - Update function docstring with examples
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 3.2 Update context builder for new arrays
  - Add _source_to_dict() conversion method
  - Add _binary_to_dict() conversion method
  - Add _script_to_dict() conversion method
  - Update _build_saidata_context() to include sources, binaries, scripts
  - Update _package_to_dict() to include package_name field
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 3.3 Add new template functions
  - Implement _sai_source_global() function
  - Implement _sai_binary_global() function
  - Implement _sai_script_global() function
  - Register functions in __init__() method
  - Add comprehensive docstrings with usage examples
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 3.4 Update _sai_lookup_filter for new resource types
  - Ensure lookup filter works with sources, binaries, scripts
  - Test provider-specific lookups for new types
  - Handle missing resources gracefully
  - _Requirements: 7.4, 7.5_

- [x] 4. Verify provider implementations
  - Verify source provider is functional
  - Verify binary provider is functional
  - Verify script provider is functional
  - Test provider YAML files with new syntax
  - _Requirements: 8.1, 8.2, 8.3_

- [x] 4.1 Check source provider implementation
  - Review providers/source.yaml for correct syntax
  - Verify source provider actions use sai_source() function
  - Test source provider with sample saidata
  - _Requirements: 8.1_

- [x] 4.2 Check binary provider implementation
  - Review providers/binary.yaml for correct syntax
  - Verify binary provider actions use sai_binary() function
  - Test binary provider with sample saidata
  - _Requirements: 8.2_

- [x] 4.3 Check script provider implementation
  - Review providers/script.yaml for correct syntax
  - Verify script provider actions use sai_script() function
  - Test script provider with sample saidata
  - _Requirements: 8.3_

- [x] 5. Create comprehensive test suite
  - Write unit tests for new models
  - Write unit tests for schema validation
  - Write unit tests for template engine updates
  - Write integration tests for end-to-end workflows
  - Create test fixtures for 0.3 saidata files
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 5.1 Write model unit tests
  - Create tests/sai/models/test_saidata_03.py
  - Test Package model with name and package_name
  - Test Source model with all fields
  - Test Binary model with archive configuration
  - Test Script model with security features
  - Test ProviderConfig and SaiData with new arrays
  - _Requirements: 9.1_

- [x] 5.2 Write loader unit tests
  - Create tests/sai/core/test_saidata_loader_03.py
  - Test loading 0.3 schema files successfully
  - Test validation errors for missing package_name
  - Test validation for new resource types
  - Test error messages are clear and helpful
  - _Requirements: 9.1, 9.5_

- [x] 5.3 Write template engine unit tests
  - Create tests/sai/providers/test_template_engine_03.py
  - Test sai_package with field parameter
  - Test sai_source, sai_binary, sai_script functions
  - Test context builder includes new arrays
  - Test provider-specific lookups
  - _Requirements: 9.2, 9.3_

- [x] 5.4 Write integration tests
  - Create tests/integration/test_sai_03_integration.py
  - Test loading 0.3 saidata and executing actions
  - Test source provider end-to-end
  - Test binary provider end-to-end
  - Test script provider end-to-end
  - _Requirements: 9.4_

- [x] 5.5 Create test fixtures
  - Create test fixtures in tests/fixtures/
  - Create nginx.yaml with complete example
  - Create simple-package.yaml with minimal example
  - Create source-build.yaml for source builds
  - Create binary-download.yaml for binary downloads
  - Create script-install.yaml for script installations
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 6. Update documentation
  - Update README with schema 0.3 information
  - Update CLI documentation
  - Add examples for new features
  - Document template functions
  - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [x] 6.1 Update main documentation
  - Update README.md with schema 0.3 information
  - Update sai/docs/cli-reference.md with new features
  - Document package name vs package_name distinction
  - Document new template functions with examples
  - _Requirements: 10.1, 10.2, 10.4_

- [x] 6.2 Create example saidata files
  - Create examples in sai/docs/examples/
  - Add complete schema 0.3 saidata example
  - Add source build example
  - Add binary download example
  - Add script installation example
  - _Requirements: 10.3, 10.4_
