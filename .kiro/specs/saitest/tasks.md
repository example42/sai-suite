# Saitest Implementation Tasks

## Overview

This task list implements saitest, an agent-based verification tool using LangGraph. Tasks are organized by phase and build incrementally. Each task references specific requirements from requirements.md.

## Phase 1: Foundation and Core Infrastructure

- [x] 1. Set up saitest package structure in monorepo
  - Create saitest/ directory with cli/, core/, agents/, tools/, models/, utils/ subdirectories
  - Create __init__.py files for all packages
  - Add saitest to pyproject.toml with optional dependencies
  - _Requirements: 15_

- [x] 1.1 Configure optional dependencies in pyproject.toml
  - Add [project.optional-dependencies.saitest] section
  - Include langgraph, langchain-openai, langchain-anthropic, docker, watchdog
  - Test installation with `pip install -e .[saitest]`
  - _Requirements: 15_

- [x] 2. Implement core state models
  - Create saitest/models/observation.py with Observation Pydantic model
  - Create saitest/models/state.py with PlatformResult Pydantic model
  - Create saitest/core/state.py with VerificationState TypedDict
  - Include provider field in Observation and PlatformResult
  - _Requirements: 16_

- [x] 2.1 Add provider tracking to VerificationState
  - Add current_provider, provider_combinations, package_versions fields
  - Add expected_dependencies dictionary
  - Test state initialization and updates
  - _Requirements: 13, 16_

- [x] 3. Implement Docker container management
  - Create saitest/utils/docker_manager.py with ContainerManager class
  - Implement spawn_container context manager
  - Implement ContainerWrapper with exec, read_file, list_files methods
  - Add platform-to-image mapping
  - _Requirements: 4_

- [x] 3.1 Add container cleanup and error handling
  - Ensure containers are stopped and removed on exit
  - Handle Docker connection errors gracefully
  - Add timeout handling for container operations
  - _Requirements: 4, 12_

- [ ] 4. Implement filesystem monitoring
  - Create saitest/utils/fs_monitor.py with FilesystemMonitor class
  - Implement capture_baseline method
  - Implement capture_changes method
  - Implement get_service_files and get_binaries methods
  - _Requirements: 5_

## Phase 2: Providerdata Integration

- [ ] 5. Implement ProviderCommandExecutor
  - Create saitest/utils/provider_executor.py
  - Implement _load_providers method to scan providers/ directory
  - Implement get_install_command method
  - Implement get_test_command method
  - Use sai's template engine for variable substitution
  - _Requirements: 18, 20_

- [ ] 5.1 Add provider validation and error handling
  - Validate providerdata structure when loading
  - Handle missing providers gracefully
  - Log warnings for invalid providerdata
  - _Requirements: 18, 20_

- [ ] 6. Implement unified installation tool
  - Create saitest/tools/package.py
  - Implement install_package LangGraph tool using ProviderCommandExecutor
  - Execute install command from providerdata
  - Execute test command from providerdata if available
  - Monitor filesystem changes during installation
  - Return structured results with provider, success, observations
  - _Requirements: 17, 18_

- [ ] 7. Implement system inspection tools
  - Create saitest/tools/system.py
  - Implement inspect_service tool for systemd services
  - Implement check_listening_ports tool
  - Implement find_config_files tool
  - _Requirements: 17_

## Phase 3: Saigen Integration

- [ ] 8. Implement repository integration
  - Import RepositoryDownloader from saigen
  - Create helper function to query all repository types
  - Create helper function to scan providers/ directory
  - Cross-reference repository data with available providerdata
  - _Requirements: 14, 20_

- [ ] 8.1 Add provider discovery logic
  - Implement get_available_providers function
  - Validate providers have both repository data AND providerdata
  - Handle missing repository data gracefully
  - _Requirements: 14, 20_

## Phase 4: LangGraph Agents

- [ ] 9. Implement Discovery Agent
  - Create saitest/agents/discovery.py
  - Query saigen's RepositoryDownloader for package metadata
  - Scan providers/ directory for available providerdata
  - Cross-reference to find valid providers
  - Use LLM for research if no repository data
  - Update VerificationState with installation_methods, package_versions
  - _Requirements: 2, 14, 20_

- [ ] 10. Implement Platform Selection Agent
  - Create saitest/agents/platform.py
  - Use user-specified platforms if provided
  - Otherwise use LLM to select 2-4 representative platforms
  - Update VerificationState with selected_platforms
  - _Requirements: 3_

- [ ] 10.1 Implement provider combination logic
  - Create function to generate platform-provider combinations
  - Store combinations in VerificationState
  - _Requirements: 6, 13_

- [ ] 11. Implement Installation Agent
  - Create saitest/agents/installation.py
  - Bind install_package tool to LLM
  - Execute installation for current platform-provider combination
  - Create Observation objects from results
  - Create PlatformResult with provider field
  - Handle installation failures gracefully
  - _Requirements: 5, 6, 12, 13_

- [ ] 12. Implement Analysis Agent
  - Create saitest/agents/analysis.py
  - Aggregate observations by type and provider
  - Use LLM to identify common patterns across platforms
  - Use LLM to identify provider-specific variations
  - Calculate confidence scores
  - Update VerificationState with patterns, variations, confidence_scores
  - _Requirements: 7_

- [ ] 13. Implement Generation Agent
  - Create saitest/agents/generation.py
  - Use LLM to generate default.yaml with common configuration
  - Use LLM to generate OS-specific override files
  - Include provider-specific overrides for all tested providers
  - Parse YAML and store in VerificationState
  - _Requirements: 8, 19_

- [ ] 13.1 Implement saidata file writing
  - Create function to write default.yaml
  - Create function to write OS-specific overrides (os/version.yaml)
  - Organize files in proper directory structure
  - _Requirements: 19_

- [ ] 14. Implement Quality Check Agent
  - Create saitest/agents/quality.py
  - Validate generated saidata against schema 0.3 using jsonschema
  - Use LLM to assess completeness and accuracy
  - Calculate completeness_score, accuracy_score, overall_confidence
  - Set needs_human_review flag based on confidence threshold
  - _Requirements: 9_

## Phase 5: LangGraph Workflow Orchestration

- [ ] 15. Implement workflow orchestrator
  - Create saitest/core/orchestrator.py
  - Implement create_verification_workflow function
  - Add all agent nodes to StateGraph
  - Set entry point to discovery agent
  - _Requirements: 1_

- [ ] 15.1 Implement workflow routing logic
  - Implement route_to_platforms function
  - Implement check_more_combinations function (for platform-provider pairs)
  - Implement route_after_quality_check function
  - Add conditional edges to workflow
  - _Requirements: 1, 6, 12_

- [ ] 15.2 Add checkpointing and state persistence
  - Configure SqliteSaver for checkpointing
  - Compile workflow with checkpointer
  - _Requirements: 1_

- [ ] 16. Implement run_verification function
  - Initialize VerificationState with input parameters
  - Invoke workflow with initial state
  - Return final VerificationState with results
  - _Requirements: 1_

## Phase 6: CLI Interface

- [ ] 17. Implement main CLI structure
  - Create saitest/cli/main.py
  - Set up Click CLI with main group
  - Add version option
  - _Requirements: 10_

- [ ] 17.1 Implement verify command
  - Create verify command with software argument
  - Add --platforms, --output-dir, --format, --verbose options
  - Call run_verification function
  - Display results (confidence, platform count, errors)
  - Write saidata files to output directory
  - _Requirements: 10_

- [ ] 17.2 Add Docker availability check
  - Check if Docker is available before running
  - Display helpful error message if Docker not found
  - Provide installation instructions
  - _Requirements: 15_

- [ ] 18. Implement test command
  - Create test command with saidata_file argument
  - Load existing saidata
  - Extract software name from metadata
  - Run verification workflow
  - Compare results with existing saidata
  - Display match confidence
  - _Requirements: 11_

## Phase 7: Configuration and Documentation

- [ ] 19. Create configuration file
  - Create saitest/config.yaml with default settings
  - Include LLM provider, model, temperature settings
  - Include platform defaults
  - Include container settings (timeout, max_concurrent)
  - Include verification settings (max_retries, confidence_threshold)
  - _Requirements: 1_

- [ ] 20. Create saitest documentation
  - Create saitest/docs/README.md with overview
  - Create saitest/docs/architecture.md with design details
  - Create saitest/docs/cli-reference.md with command documentation
  - Create saitest/docs/examples/ with usage examples
  - _Requirements: 15_

## Phase 8: Testing and Quality Assurance

- [ ] 21. Create unit tests for core components
  - Create tests/saitest/unit/test_state.py
  - Create tests/saitest/unit/test_container_manager.py
  - Create tests/saitest/unit/test_fs_monitor.py
  - Create tests/saitest/unit/test_provider_executor.py
  - Mock external dependencies (Docker, LLM)
  - _Requirements: All_

- [ ] 22. Create integration tests
  - Create tests/saitest/integration/test_workflow.py
  - Test full workflow with real containers
  - Test with known software (nginx as example)
  - Verify generated saidata structure
  - Test error scenarios
  - _Requirements: All_

- [ ] 23. Create test fixtures
  - Create tests/saitest/fixtures/sample_states.py
  - Create tests/saitest/fixtures/sample_observations.py
  - Create tests/saitest/fixtures/sample_saidata.yaml
  - Create tests/saitest/fixtures/mock_llm_responses.json
  - _Requirements: All_

## Phase 9: Integration and Polish

- [ ] 24. Integrate with existing sai-suite
  - Update root pyproject.toml with saitest entry point
  - Ensure imports from saigen work correctly
  - Ensure providerdata loading works correctly
  - Test optional dependency installation
  - _Requirements: 14, 15, 18_

- [ ] 25. Add error handling and logging
  - Add comprehensive error handling throughout
  - Add logging for debugging
  - Add progress indicators for long-running operations
  - _Requirements: 12_

- [ ] 26. Performance optimization
  - Add caching for Docker images
  - Optimize filesystem scanning
  - Add timeout controls
  - _Requirements: 4, 5_

- [ ] 27. Create example workflows
  - Create scripts/development/saitest/demo_verify.py
  - Create scripts/development/saitest/demo_multi_provider.py
  - Create scripts/development/saitest/demo_os_overrides.py
  - _Requirements: All_

## Success Criteria

- All 20 requirements implemented
- Unit tests pass with >80% coverage
- Integration tests pass with real containers
- CLI commands work as documented
- Generated saidata validates against schema 0.3
- Providerdata integration works for all available providers
- OS-specific overrides generated correctly
- Documentation complete and accurate
