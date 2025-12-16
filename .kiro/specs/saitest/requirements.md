# Saitest Requirements Document

## Introduction

Saitest is an agent-based verification tool that installs software in containerized environments, observes system changes, and generates validated saidata using AI-powered analysis with LangGraph. It will be part of the sai-suite monorepo alongside sai and saigen, providing a complete workflow: `saigen generate` → `saitest verify` → `sai install`.

## Glossary

- **Saitest**: Agent-based verification tool for generating and validating saidata
- **LangGraph**: Graph-based agent orchestration framework from LangChain
- **Agent**: AI-powered component that performs specific verification tasks
- **Observation**: Data point collected during software installation (file, service, port, etc.)
- **Platform**: Operating system and version combination (e.g., ubuntu:22.04)
- **Container**: Isolated Docker environment for testing installations
- **Saidata**: YAML configuration file following schema 0.3 specification
- **Confidence Score**: Numerical measure (0-1) of verification result reliability
- **Verification State**: LangGraph state object tracking workflow progress
- **Tool**: LangGraph tool that performs system operations (install, inspect, monitor)

## Requirements

### Requirement 1: Agent-Based Verification Workflow

**User Story:** As a DevOps engineer, I want an automated tool that verifies software installations across multiple platforms, so that I can generate accurate saidata without manual testing.

#### Acceptance Criteria

1. WHEN the user invokes saitest with a software name, THE Saitest System SHALL execute a multi-agent workflow using LangGraph
2. WHEN the workflow starts, THE Saitest System SHALL initialize a VerificationState object with software name and configuration
3. WHILE the workflow executes, THE Saitest System SHALL maintain state across all agent nodes
4. WHEN an agent completes its task, THE Saitest System SHALL update the VerificationState and route to the next agent
5. WHEN the workflow completes, THE Saitest System SHALL return generated saidata with confidence scores

### Requirement 2: Discovery Agent

**User Story:** As a system administrator, I want the tool to automatically research software installation methods, so that I don't need to manually specify how to install each package.

#### Acceptance Criteria

1. WHEN the Discovery Agent executes, THE Saitest System SHALL query saigen's repository cache for package metadata
2. WHEN repository data exists, THE Saitest System SHALL identify available providers from repository information
3. WHEN repository data is missing, THE Saitest System SHALL use an LLM to research available installation providers
4. WHEN identifying providers, THE Saitest System SHALL check which providers have providerdata definitions
5. WHEN researching software, THE Saitest System SHALL predict expected services, files, ports, and configuration locations
6. WHEN research completes, THE Saitest System SHALL store findings in VerificationState with discovery_complete flag set to true
7. IF the LLM returns invalid JSON, THEN THE Saitest System SHALL set discovery_complete to false and log an error message

### Requirement 3: Platform Selection Agent

**User Story:** As a quality engineer, I want the tool to intelligently select test platforms, so that I get good coverage without testing every possible OS combination.

#### Acceptance Criteria

1. WHERE the user specifies target platforms, THE Saitest System SHALL use those platforms for testing
2. WHERE the user does not specify platforms, THE Saitest System SHALL use an LLM to select 2-4 representative platforms
3. WHEN selecting platforms, THE Saitest System SHALL consider different package managers and popular distributions
4. WHEN platform selection completes, THE Saitest System SHALL store selected_platforms in VerificationState
5. IF the LLM fails to select platforms, THEN THE Saitest System SHALL default to ubuntu:22.04 and debian:12

### Requirement 4: Container Management

**User Story:** As a developer, I want installations to run in isolated containers, so that testing doesn't affect my local system.

#### Acceptance Criteria

1. WHEN spawning a container, THE Saitest System SHALL pull the Docker image if not already cached
2. WHEN spawning a container, THE Saitest System SHALL create a privileged container with TTY enabled
3. WHILE a container is active, THE Saitest System SHALL track it in active_containers dictionary
4. WHEN container operations complete, THE Saitest System SHALL stop and remove the container automatically
5. WHEN executing commands in a container, THE Saitest System SHALL return exit code, output, and success status

### Requirement 5: Installation Agent with Monitoring

**User Story:** As a software packager, I want to observe all system changes during installation, so that I can accurately document what files and services are created.

#### Acceptance Criteria

1. WHEN the Installation Agent executes, THE Saitest System SHALL capture a filesystem baseline before installation
2. WHEN installing software, THE Saitest System SHALL use LangGraph tools to execute package manager commands
3. WHILE installation runs, THE Saitest System SHALL monitor filesystem changes, service registrations, and binary creation
4. WHEN installation completes, THE Saitest System SHALL create Observation objects for each detected change
5. WHEN installation completes, THE Saitest System SHALL store PlatformResult with observations, errors, and duration

### Requirement 6: Multi-Platform Testing

**User Story:** As a release manager, I want to test software on multiple platforms in parallel, so that I can quickly identify platform-specific differences.

#### Acceptance Criteria

1. WHEN multiple platforms are selected, THE Saitest System SHALL test each platform sequentially through the workflow
2. WHEN testing a platform, THE Saitest System SHALL set current_platform in VerificationState
3. WHEN a platform test completes, THE Saitest System SHALL check if more platforms remain
4. IF more platforms remain, THEN THE Saitest System SHALL route back to the Installation Agent with the next platform
5. IF all platforms are tested, THEN THE Saitest System SHALL route to the Analysis Agent

### Requirement 7: Analysis Agent

**User Story:** As a data analyst, I want the tool to identify patterns across platforms, so that I can understand what's common versus platform-specific.

#### Acceptance Criteria

1. WHEN the Analysis Agent executes, THE Saitest System SHALL aggregate observations by type across all platforms
2. WHEN analyzing observations, THE Saitest System SHALL use an LLM to identify common patterns
3. WHEN analyzing observations, THE Saitest System SHALL identify platform-specific variations
4. WHEN analysis completes, THE Saitest System SHALL calculate confidence scores for each finding
5. WHEN analysis completes, THE Saitest System SHALL store patterns, variations, and confidence_scores in VerificationState

### Requirement 8: Saidata Generation Agent

**User Story:** As a configuration manager, I want the tool to generate valid saidata YAML, so that I can immediately use it with sai and saigen.

#### Acceptance Criteria

1. WHEN the Generation Agent executes, THE Saitest System SHALL use an LLM to generate saidata following schema 0.3
2. WHEN generating saidata, THE Saitest System SHALL include metadata, packages, services, files, commands, and ports
3. WHEN generating saidata, THE Saitest System SHALL create provider overrides for platform-specific variations
4. WHEN generation completes, THE Saitest System SHALL parse the YAML and store in generated_saidata
5. IF YAML parsing fails, THEN THE Saitest System SHALL set generated_saidata to None and log the error

### Requirement 9: Quality Check Agent

**User Story:** As a quality assurance engineer, I want automated quality assessment, so that I know when generated saidata needs human review.

#### Acceptance Criteria

1. WHEN the Quality Check Agent executes, THE Saitest System SHALL validate generated saidata against schema 0.3
2. WHEN validating saidata, THE Saitest System SHALL use jsonschema to check structural compliance
3. WHEN assessing quality, THE Saitest System SHALL use an LLM to evaluate completeness and accuracy
4. WHEN quality check completes, THE Saitest System SHALL calculate completeness_score, accuracy_score, and overall_confidence
5. IF overall_confidence is below 0.7 or validation errors exist, THEN THE Saitest System SHALL set needs_human_review to true

### Requirement 10: CLI Interface

**User Story:** As a command-line user, I want a simple CLI to verify software, so that I can integrate saitest into my workflows.

#### Acceptance Criteria

1. WHEN the user runs `saitest verify <software>`, THE Saitest System SHALL execute the verification workflow
2. WHERE the user specifies `--platforms`, THE Saitest System SHALL use those platforms for testing
3. WHERE the user specifies `--output`, THE Saitest System SHALL save generated saidata to the specified file
4. WHERE the user specifies `--verbose`, THE Saitest System SHALL display detailed progress messages
5. WHEN verification completes, THE Saitest System SHALL display confidence score and platform count

### Requirement 11: Testing Existing Saidata

**User Story:** As a maintainer, I want to test existing saidata files, so that I can verify they're still accurate.

#### Acceptance Criteria

1. WHEN the user runs `saitest test <saidata_file>`, THE Saitest System SHALL load the existing saidata
2. WHEN testing saidata, THE Saitest System SHALL extract the software name from metadata
3. WHEN testing saidata, THE Saitest System SHALL run verification workflow for that software
4. WHEN testing completes, THE Saitest System SHALL compare existing saidata with observed results
5. WHEN testing completes, THE Saitest System SHALL display match confidence score

### Requirement 12: Error Handling and Retry Logic

**User Story:** As a reliability engineer, I want the tool to handle failures gracefully, so that transient errors don't cause complete workflow failure.

#### Acceptance Criteria

1. WHEN an agent encounters an error, THE Saitest System SHALL log the error in VerificationState messages
2. WHEN installation fails on a platform, THE Saitest System SHALL create a PlatformResult with success=false and error details
3. WHEN overall_confidence is below 0.5, THE Saitest System SHALL retry installation if retry_count is below max_retries
4. WHEN retrying, THE Saitest System SHALL increment retry_count in VerificationState
5. WHEN max_retries is reached, THE Saitest System SHALL complete the workflow with current results

### Requirement 13: Multi-Provider Testing

**User Story:** As a package maintainer, I want to test different installation providers on the same platform, so that I can verify all available installation methods work correctly.

#### Acceptance Criteria

1. WHEN the Discovery Agent identifies multiple installation providers, THE Saitest System SHALL test each provider separately
2. WHEN testing a platform, THE Saitest System SHALL iterate through all discovered providers that have providerdata definitions
3. WHEN testing a provider, THE Saitest System SHALL spawn a fresh container for isolation
4. WHEN observations are collected, THE Saitest System SHALL tag each observation with the provider used
5. WHEN analyzing results, THE Saitest System SHALL create provider-specific overrides in generated saidata
6. WHEN a provider is not found in providerdata, THE Saitest System SHALL skip that provider and log a warning

### Requirement 14: Saigen Repository Integration

**User Story:** As a developer, I want saitest to leverage saigen's repository cache, so that I can use existing package metadata to inform verification.

#### Acceptance Criteria

1. WHEN the Discovery Agent executes, THE Saitest System SHALL query saigen's repository cache for package information
2. WHEN repository data exists, THE Saitest System SHALL use it to identify available versions and dependencies
3. WHEN repository data is missing, THE Saitest System SHALL fall back to LLM-based discovery
4. WHEN generating saidata, THE Saitest System SHALL include version information from repository cache
5. WHEN testing multiple providers, THE Saitest System SHALL use saigen's RepositoryDownloader to fetch package metadata

### Requirement 15: Monorepo Integration

**User Story:** As a contributor, I want saitest integrated into sai-suite, so that I can share code and maintain consistency.

#### Acceptance Criteria

1. WHEN installing sai-suite, THE Saitest System SHALL be available as an optional dependency
2. WHEN importing from saigen, THE Saitest System SHALL access SaidataModel, validation utilities, and RepositoryDownloader
3. WHEN importing from shared, THE Saitest System SHALL access common saidata models if they exist
4. WHERE the user installs `sai-suite[saitest]`, THE Saitest System SHALL install LangGraph, Docker, and monitoring dependencies
5. WHEN running saitest, THE Saitest System SHALL check for Docker availability and display helpful error if missing

### Requirement 14: Observation Data Models

**User Story:** As a data engineer, I want structured observation data, so that I can analyze and process verification results programmatically.

#### Acceptance Criteria

1. WHEN creating an Observation, THE Saitest System SHALL include type, platform, timestamp, data, and confidence fields
2. WHEN creating a PlatformResult, THE Saitest System SHALL include platform, success, observations, errors, and duration fields
3. WHEN storing observations, THE Saitest System SHALL use Pydantic models for type safety and validation
4. WHEN serializing observations, THE Saitest System SHALL support JSON and YAML output formats
5. WHEN aggregating observations, THE Saitest System SHALL group by type (file, service, port, command, package)

### Requirement 15: LangGraph Tools

**User Story:** As an agent developer, I want reusable tools for system operations, so that agents can perform installations and inspections.

#### Acceptance Criteria

1. WHEN an agent needs to install a package, THE Saitest System SHALL provide install_package tool
2. WHEN an agent needs to inspect a service, THE Saitest System SHALL provide inspect_service tool
3. WHEN an agent needs to check ports, THE Saitest System SHALL provide check_listening_ports tool
4. WHEN a tool executes, THE Saitest System SHALL return structured data with success status
5. WHEN a tool fails, THE Saitest System SHALL return error information without crashing the workflow


### Requirement 16: Observation Data Models

**User Story:** As a data engineer, I want structured observation data, so that I can analyze and process verification results programmatically.

#### Acceptance Criteria

1. WHEN creating an Observation, THE Saitest System SHALL include type, platform, provider, timestamp, data, and confidence fields
2. WHEN creating a PlatformResult, THE Saitest System SHALL include platform, provider, success, observations, errors, and duration fields
3. WHEN storing observations, THE Saitest System SHALL use Pydantic models for type safety and validation
4. WHEN serializing observations, THE Saitest System SHALL support JSON and YAML output formats
5. WHEN aggregating observations, THE Saitest System SHALL group by type and provider

### Requirement 17: LangGraph Tools Using Providerdata

**User Story:** As an agent developer, I want a unified tool that uses providerdata to install packages with any provider, so that I don't need provider-specific tools.

#### Acceptance Criteria

1. WHEN an agent needs to install a package, THE Saitest System SHALL provide a single install_package tool
2. WHEN the install_package tool executes, THE Saitest System SHALL load the provider's commands from providerdata
3. WHEN executing installation, THE Saitest System SHALL use the install action command template from providerdata
4. WHEN testing installation, THE Saitest System SHALL use the status/test action from providerdata if available
5. WHEN a tool executes, THE Saitest System SHALL return structured data with provider, success status, and observations
6. WHEN a provider is not found in providerdata, THE Saitest System SHALL return an error without crashing the workflow
7. WHEN a tool fails, THE Saitest System SHALL return error information without crashing the workflow


### Requirement 18: Providerdata Integration

**User Story:** As a maintainer, I want saitest to use the same provider commands as sai, so that verification matches actual installation behavior.

#### Acceptance Criteria

1. WHEN installing with a provider, THE Saitest System SHALL load providerdata for that provider from the providers/ directory
2. WHEN executing installation, THE Saitest System SHALL use the install action command template from providerdata
3. WHEN testing installation, THE Saitest System SHALL use the status/test action command from providerdata if available
4. WHEN substituting variables in command templates, THE Saitest System SHALL use the same template engine as sai
5. WHEN a provider is not found in providerdata, THE Saitest System SHALL log an error and skip that provider
6. WHEN providerdata is updated, THE Saitest System SHALL automatically use the new commands without code changes


### Requirement 19: OS-Specific Override Generation

**User Story:** As a package maintainer, I want saitest to generate OS-specific override files, so that I can handle platform differences like saigen does.

#### Acceptance Criteria

1. WHEN generating saidata, THE Saitest System SHALL create a default.yaml file with common configuration across all platforms
2. WHEN platform-specific differences are detected, THE Saitest System SHALL create OS-specific override files
3. WHEN creating override files, THE Saitest System SHALL organize them by OS and version (e.g., ubuntu/22.04.yaml, debian/12.yaml)
4. WHEN writing override files, THE Saitest System SHALL include only differences from default.yaml
5. WHEN the user specifies --output-dir, THE Saitest System SHALL write all files to that directory with proper structure (software/default.yaml, software/os/version.yaml)


### Requirement 20: Provider Extensibility

**User Story:** As a developer, I want saitest to automatically support new providers when providerdata is added, so that I don't need to modify saitest code for each new provider.

#### Acceptance Criteria

1. WHEN a new providerdata file is added to the providers/ directory, THE Saitest System SHALL automatically detect and support that provider
2. WHEN loading providers, THE Saitest System SHALL scan the providers/ directory for all available providerdata files
3. WHEN a provider is requested, THE Saitest System SHALL load its providerdata and extract install/test commands
4. WHEN executing provider commands, THE Saitest System SHALL use the same template substitution engine as sai
5. WHEN a provider's providerdata is updated, THE Saitest System SHALL use the new commands without code changes
6. WHEN listing available providers, THE Saitest System SHALL include all providers with valid providerdata definitions
