# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **RAG (Retrieval-Augmented Generation) System**: Complete implementation of semantic search and context building
  - RAGIndexer class with vector embedding support using sentence-transformers and FAISS
  - RAGContextBuilder for intelligent prompt context injection
  - Semantic search for repository packages and existing saidata files
  - Index management commands for building, rebuilding, and clearing indices
  - Support for similarity search with configurable thresholds and limits
- **Enhanced Prompt Template System**: Improved prompt generation with better context formatting
  - Repository data grouping by provider for better organization
  - Enhanced similar saidata examples with comprehensive metadata display
  - Improved template variable substitution with compiled template caching
  - Better handling of large repository datasets with intelligent truncation
- **SAI Output Formatting System**: Comprehensive output formatting improvements
  - OutputFormatter class with consistent styling across all commands
  - Provider-specific output sections with success/failure indicators
  - Color-coded output (stdout, stderr, success, error, warning, info)
  - Mode-responsive formatting (quiet, verbose, normal)
  - Command sanitization with automatic sensitive data redaction
  - Execution summary with statistics and timing information
- **Repository Management System**: Complete repository configuration and caching framework for SAIGEN
  - Configurable repository downloaders supporting multiple formats (JSON, YAML, XML, text)
  - Advanced caching system with TTL management and concurrent access safety
  - Repository configuration management with validation and security features
  - Generic repository downloader with customizable parsing rules
  - Support for multiple repository types (apt, brew, winget, dnf, generic)
  - Repository cache statistics and maintenance operations
- **Enhanced Security Features**:
  - URL scheme validation for repository configurations
  - Cache key sanitization to prevent path traversal attacks
  - Secure file permissions (0o600) for cache files
  - HTTP request size limits and SSL verification enforcement
  - Input validation and sanitization throughout repository system
- **Performance Optimizations**:
  - HTTP connection pooling for repository downloads
  - Memory-efficient cache loading for large files
  - Concurrent repository updates with proper error handling
  - Streaming package processing for memory efficiency
- **Enhanced CLI Security**: Added input validation and sanitization for software names in generate command
- **CLI Command Structure**: Complete CLI command framework with config, generate, and validate commands
- **Generation Engine Core Implementation**: Complete GenerationEngine class with LLM orchestration, validation, and metrics tracking
- **Advanced Validation System**: Comprehensive SaidataValidator with JSON schema validation, custom rules, cross-reference checking, and detailed error reporting
- **LLM Provider Framework**: Extensible provider system with OpenAI integration, async support, and cost estimation
- **Sophisticated Prompt Templates**: Context-aware prompt generation with conditional sections and variable substitution
- **Comprehensive Saidata Validation System**: Complete validation framework with JSON schema validation, custom rules, and cross-reference checking
- **Validation CLI Command**: New `saigen validate` command with multiple output formats and detailed error reporting
- **LLM Provider Framework**: Extensible LLM provider system with OpenAI integration and prompt template engine
- **Advanced Prompt Templates**: Sophisticated prompt generation system with conditional sections and context-aware rendering
- **Validation Error Reporting**: Detailed validation reports with severity levels, suggestions, and context information
- **Schema Compliance Validation**: Full JSON schema validation against saidata-0.2-schema.json with helpful error messages
- **Custom Validation Rules**: Additional validation beyond schema including port ranges, file paths, and package name validation
- **Cross-Reference Validation**: Validation of internal references like repository names and service dependencies
- **Version Command**: New `sai version <software>` command to show software version information
- **Enhanced Provider Selection UI**: Provider selection now displays package names and version availability for better user experience
- **Version Action Support**: Added version action support to multiple providers (apt, brew, gem, npm, pypi)
- **Complete SAI CLI Implementation**: Full-featured CLI tool with all planned commands implemented
- **Execution History Tracking**: Complete execution history system with metrics, filtering, and cleanup commands
- **Shell Completion**: Auto-completion support for bash, zsh, and fish shells with install/uninstall commands
- **Enhanced CLI Interface**: Added `sai history`, `sai completion`, `sai config`, and comprehensive provider management commands
- **Configuration Management**: Complete configuration system with show, set, reset, validate, and paths commands
- **Provider Cache Management**: Advanced caching system with status, clear, and refresh operations
- **SAI CLI Tool**: Complete implementation of sai CLI tool with provider-based software management
- **Comprehensive Logging System**: Structured logging with configurable levels and execution result tracking
- **Enhanced Security**: Comprehensive command injection prevention and secure subprocess execution
- **Execution Engine**: Robust execution engine with timeout handling, privilege escalation, and process isolation
- **Security Validation**: Multi-layer command validation with dangerous pattern detection
- **Resource Management**: Process resource limits and secure environment variable handling
- **CLI Commands**: Implemented `sai stats`, `sai config-show`, and `sai version` commands
- **Advanced Security Features**: 
  - Command argument sanitization with length limits
  - Executable safety validation with allowlist/blocklist
  - Root command safety checks for privileged operations
  - Secure environment variable handling with minimal attack surface
  - Process isolation with new session groups and resource limits
- **Comprehensive Statistics**: Detailed provider and action coverage analysis with multiple view options
- **Provider Statistics**: Comprehensive statistics system with detailed provider and action analysis
- **Template Engine**: Advanced Jinja2-based template resolution engine with array expansion support
- **Provider System**: Comprehensive provider loading, caching, and availability detection
- **System Utilities**: Cross-platform system detection and executable management
- **Statistics Command**: Detailed provider and action statistics with multiple view options
- **Specialized Providers**: 32 new specialized provider configurations for system tools
- Core data models for SaiData, configuration, and generation requests
- Pydantic models with comprehensive validation and type safety
- Configuration management system with environment variable support
- Multi-format configuration file support (YAML/JSON)
- Secure API key handling with masking in configuration display
- Basic CLI interface with generate and config commands
- Support for multiple LLM providers (OpenAI, Anthropic, Ollama)
- Repository package data models for caching system
- RAG (Retrieval-Augmented Generation) configuration support
- Comprehensive validation and generation result tracking
- Batch processing configuration and models
- Cache management with TTL and size limits
- Comprehensive test suite with 82 tests covering all components
- API reference documentation
- Configuration guide with examples and troubleshooting
- SAI CLI tool with Click-based interface and provider management
- ProviderData models with comprehensive action and mapping support
- **Provider Loading System**: Complete YAML-based provider loading with validation
- **Provider Caching**: File-based caching system with modification time tracking for improved performance
- **Variable Mapping Support**: Enhanced variable mappings to support both string and object formats
- **Security Enhancements**: File size limits for provider YAML files to prevent DoS attacks

### Changed
- **Repository Architecture**: Implemented comprehensive repository management system with async-first design
- **Configuration System**: Enhanced configuration management to support repository-specific settings
- **CLI Interface**: Updated SAIGEN CLI to include repository management commands (list, update, stats, clear)
- **Generation Architecture**: Implemented async-first generation engine with comprehensive error handling and metrics tracking
- **CLI Implementation Status**: Generate command currently provides stub implementation pending repository downloader framework (Task 6)
- **Validation Architecture**: Enhanced validation system with multiple severity levels, detailed error context, and helpful suggestions
- **LLM Integration**: Added structured LLM provider framework with template-based prompt generation and response validation
- **CLI Version Command**: Replaced global version command with software-specific version command that shows version information for installed packages
- **Validation Architecture**: Implemented comprehensive validation system with multiple severity levels and detailed error context
- **LLM Integration**: Added structured LLM provider framework with async support and cost estimation
- **Prompt Engineering**: Enhanced prompt template system with conditional sections and context-aware variable substitution
- **Provider Selection Interface**: Enhanced provider selection UI to show package names and version command availability
- Project structure follows modular architecture principles
- Configuration system supports multiple file locations and formats
- Optimized environment variable loading with mapping-based approach
- Enhanced error handling for configuration file parsing
- **Provider Data Models**: Updated VariableMapping to support Union[VariableMapping, str] for flexible variable definitions
- **Performance Optimization**: Added caching layer to provider loading system reducing file I/O operations
- **Template Engine**: Implemented efficient array expansion with custom Jinja2 filters
- **Provider Detection**: Enhanced executable detection with caching and priority-based selection
- **CLI Interface**: Expanded CLI with stats, config-show, and version commands

### Security
- **Enhanced Command Sanitization**: Improved sensitive data redaction in output formatter
  - Regex-based pattern matching for better detection of sensitive arguments
  - Comprehensive patterns for passwords, tokens, keys, and authentication data
  - Fallback word-based sanitization for additional protection
- **Repository Security**: Added comprehensive security measures for repository operations
  - URL scheme validation (only http/https/ftp/ftps allowed)
  - Cache key sanitization prevents directory traversal attacks
  - Secure file permissions for cache files (owner read/write only)
  - HTTP response size limits to prevent DoS attacks
  - SSL certificate verification enforcement for HTTPS requests
- API keys are stored as SecretStr and masked in configuration display
- Environment variable support for sensitive configuration data
- Configuration files saved with secure permissions (0o600)
- Enhanced input validation with proper encoding handling
- YAML safe_load prevents code execution vulnerabilities
- **Provider File Security**: Added 10MB file size limit for provider YAML files to prevent resource exhaustion attacks
- **Command Execution Security**: Enhanced subprocess execution with argument validation and minimal environment
- **Template Security**: Jinja2 StrictUndefined prevents template injection and silent failures
- **Input Sanitization**: Comprehensive validation of command arguments and template variables
- **Process Isolation**: New process groups with resource limits (CPU time, memory usage)
- **Privilege Escalation**: Secure sudo handling with non-interactive mode and argument separation
- **Command Injection Prevention**: Multi-layer validation against dangerous patterns and executables
- **Environment Hardening**: Minimal secure environment variables, removal of dangerous PATH entries

### Fixed
- **Test Class Naming Conflicts**: Renamed test-related classes to avoid pytest collection conflicts:
  - `TestResult` → `SaidataTestResult`
  - `TestSuite` → `SaidataTestSuite` 
  - `TestType` → `SaidataTestType`
  - `TestSeverity` → `SaidataTestSeverity`
- **CLI Test Command**: Fixed remaining class name references in test command implementation
- **Repository Index Command**: Improved TODO comment with clearer implementation guidance
- **JSON Serialization**: Fixed datetime serialization issues in repository cache metadata
- **Cache Corruption Handling**: Enhanced error handling for corrupted cache files with automatic cleanup
- **Configuration Loading**: Improved error handling for invalid repository configurations
- **Memory Management**: Optimized cache loading for large repository data files
- **Ollama Provider Cost Estimation**: Fixed missing `estimate_cost` method implementation to return 0.0 for local models
- **Generation Engine Stability**: Enhanced error handling and validation in generation workflow
- **Template Performance**: Optimized prompt template rendering with compiled template caching
- **Validation Accuracy**: Improved schema validation with better error messages and suggestions
- **LLM Provider Reliability**: Added proper connection validation and retry logic for OpenAI provider
- Configuration file encoding issues with explicit UTF-8 handling
- **Template Caching**: Optimized prompt template rendering with compiled template caching for better performance
- **Schema Loading**: Enhanced schema loading with proper error handling and validation
- **Import Issues**: Fixed module import paths in demo scripts for proper execution
- Improved error messages for invalid configuration formats
- **Provider Validation**: Fixed Pydantic model validation errors for providers with string-based variable mappings (npm, cargo, etc.)
- **Schema Compliance**: Aligned Pydantic models with JSON schema definitions for variable mappings
- **Test Suite**: Fixed configuration tests to match actual implementation behavior
- **Template Resolution**: Improved error handling and context building for complex scenarios
- **Provider Availability**: Enhanced executable detection with proper platform support checking
- **Pydantic V2 Migration**: Completed migration of all Pydantic models to V2 ConfigDict syntax, eliminating all 14 deprecation warnings across both sai and saigen packages
- **CLI Documentation**: Updated README.md to reflect all available CLI commands including new provider management and validation commands
- **Test Cache Issues**: Fixed provider availability tests to bypass cache during testing for accurate mocking behavior

## [0.1.0] - Initial Release

### Added
- Initial project structure and core models
- Basic CLI framework with Click
- Pydantic-based data validation
- Configuration management foundation