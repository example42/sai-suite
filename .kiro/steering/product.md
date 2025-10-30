# Product Overview

The SAI Software Management Suite consists of three complementary tools:

## SAI (Software Action Interface)
A lightweight CLI tool for executing software management actions using provider-based configurations.

## SAIGEN (SAI data Generation) 
A comprehensive Python tool for generating, validating, and managing software metadata in YAML format following the saidata json schema specification.

## SAITEST (SAI Testing and Verification)
An agent-based verification tool using LangGraph that automatically generates and validates saidata by testing software installations across multiple platforms and providers.

## Core Purpose

### SAI Core Purpose
- Executes software management actions using provider-based configurations
- Supports multi-platform software installation, configuration, and management
- Provides consistent interface across different package managers and platforms
- Enables automation of software deployment and system administration tasks

### SAIGEN Core Purpose
- Automates creation of software metadata YAML files (saidata) following schema 0.3
- Caches package information from multiple repositories (apt, dnf, brew, winget, etc.)
- Uses repository data and LLMs to generate saidata with sources, binaries, and scripts
- Validates generated files against official schema (saidata-0.3-schema.json)
- Tests saidata using mcp servers
- Supports URL templating with version, platform, and architecture placeholders

### SAITEST Core Purpose
- Automatically verifies software installations across multiple platforms using Docker containers
- Generates saidata by observing actual installation behavior and filesystem changes
- Tests multiple provider combinations (apt, dnf, brew, etc.) for comprehensive coverage
- Creates OS-specific overrides based on platform-specific observations
- Uses LangGraph agents for intelligent workflow orchestration
- Validates generated saidata against schema 0.3 with confidence scoring

## Key Features

### SAI Features
- Provider-based action execution system
- Multi-platform support (Linux, macOS, Windows)
- Extensible provider architecture
- Configuration management with YAML/JSON support
- Dry-run mode for safe testing
- Concurrent action execution with timeout controls

### SAIGEN Features
- Multi-provider package repository integration
- Schema 0.3 validation and quality assessment
- Support for multiple installation methods (packages, sources, binaries, scripts)
- Batch processing capabilities
- AI-enhanced metadata generation with RAG (Retrieval-Augmented Generation)
- URL templating with platform/architecture detection
- Security features (checksum validation, vulnerability metadata)
- CLI and programmatic API interfaces
- Docker containerization support

### SAITEST Features
- LangGraph-based agent workflow for intelligent verification
- Docker container management for isolated testing environments
- Filesystem monitoring to capture installation changes
- Providerdata integration for executing installation commands
- Multi-platform testing (Ubuntu, Debian, CentOS, Rocky, Fedora, macOS, Windows)
- Multi-provider testing with automatic combination generation
- Observation-based analysis for pattern detection
- Automatic generation of default.yaml and OS-specific overrides
- Provider-specific override generation
- Confidence scoring and quality assessment
- Human review flagging for low-confidence results

## Target Users

### SAI Target Users
- System administrators managing software deployments
- DevOps engineers automating infrastructure setup
- CI/CD pipeline developers
- Platform engineers standardizing software management

### SAIGEN Target Users
- DevOps engineers and system administrators
- Software inventory management teams
- CI/CD pipeline integrators
- Developers working with package metadata automation

### SAITEST Target Users
- Saidata contributors and maintainers
- Quality assurance teams validating software metadata
- DevOps engineers testing cross-platform compatibility
- System administrators verifying installation procedures
- CI/CD pipeline developers automating saidata generation

## Distribution Methods
- PyPI package (recommended)
- Docker container
- Standalone binary releases
- Development installation from source


# Online references

Website: sai.software
Source: github.com/example42/sai
Saidata repo: github.com/example42/saidata
