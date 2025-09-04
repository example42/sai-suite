# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
- **CLI Version Command**: Replaced global version command with software-specific version command that shows version information for installed packages
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
- Configuration file encoding issues with explicit UTF-8 handling
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