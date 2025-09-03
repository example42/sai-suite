# Product Overview

The SAI Software Management Suite consists of two complementary tools:

## SAI (Software Action Interface)
A lightweight CLI tool for executing software management actions using provider-based configurations.

## SAIGEN (SAI data Generation) 
A comprehensive Python tool for generating, validating, and managing software metadata in YAML format following the saidata json schema specification.

## Core Purpose

### SAI Core Purpose
- Executes software management actions using provider-based configurations
- Supports multi-platform software installation, configuration, and management
- Provides consistent interface across different package managers and platforms
- Enables automation of software deployment and system administration tasks

### SAIGEN Core Purpose
- Automates creation of software metadata YAML files (saidata)
- Caches package information from multiple repositories (apt, dnf, brew, winget, etc.)
- Uses repository data and LLMs to generate saidata
- Validates generated files against official schema
- Tests saidata using mcp servers

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
- Schema validation and quality assessment
- Batch processing capabilities
- AI-enhanced metadata generation with RAG (Retrieval-Augmented Generation)
- CLI and programmatic API interfaces
- Docker containerization support

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

## Distribution Methods
- PyPI package (recommended)
- Docker container
- Standalone binary releases
- Development installation from source


# Online references

Website: sai.software
Source: github.com/example42/sai
Saidata repo: github.com/example42/saidata
