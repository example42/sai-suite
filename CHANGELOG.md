# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **SAI CLI Tool**: Complete implementation of sai CLI tool with provider-based software management
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
- Comprehensive test suite with basic model validation
- API reference documentation
- Configuration guide with examples and troubleshooting
- SAI CLI tool with Click-based interface and provider management
- ProviderData models with comprehensive action and mapping support

### Changed
- Project structure follows modular architecture principles
- Configuration system supports multiple file locations and formats
- Optimized environment variable loading with mapping-based approach
- Enhanced error handling for configuration file parsing

### Security
- API keys are stored as SecretStr and masked in configuration display
- Environment variable support for sensitive configuration data
- Configuration files saved with secure permissions (0o600)
- Enhanced input validation with proper encoding handling
- YAML safe_load prevents code execution vulnerabilities

### Fixed
- Configuration file encoding issues with explicit UTF-8 handling
- Improved error messages for invalid configuration formats

## [0.1.0] - Initial Release

### Added
- Initial project structure and core models
- Basic CLI framework with Click
- Pydantic-based data validation
- Configuration management foundation