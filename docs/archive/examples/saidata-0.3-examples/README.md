# SaiData 0.3 Schema Examples

This directory contains comprehensive examples showcasing the new features and capabilities of the saidata 0.3 schema format.

## New Features in 0.3

### Installation Methods
- **Sources**: Build software from source code with various build systems (autotools, cmake, make, meson, ninja, custom)
- **Binaries**: Download and install pre-compiled binaries with platform/architecture templating
- **Scripts**: Execute installation scripts with security measures and environment controls

### Enhanced Security
- Security metadata with CVE exceptions, security contacts, and vulnerability disclosure
- Checksum validation for sources, binaries, and scripts
- SBOM (Software Bill of Materials) support

### URL Templating
- Dynamic URL generation with `{{version}}`, `{{platform}}`, and `{{architecture}}` placeholders
- Cross-platform binary downloads with automatic platform detection

### Enhanced Provider Configuration
- Provider-specific overrides for all resource types including new installation methods
- Package sources with priority and recommendation settings
- Repository configurations with enhanced metadata

### Compatibility Matrix
- Comprehensive compatibility tracking across providers, platforms, and architectures
- Version tracking with latest, minimum, LTS, and latest_minimum versions

## Examples

### Basic Examples
- `terraform.yaml` - Binary downloads with URL templating
- `nginx-source.yaml` - Source compilation with autotools
- `docker-script.yaml` - Script installation with security measures

### Advanced Examples
- `kubernetes-comprehensive.yaml` - Multi-method installation (packages, binaries, scripts)
- `nodejs-cross-platform.yaml` - Cross-platform support with provider overrides
- `security-focused.yaml` - Security-focused configuration with comprehensive metadata

### Real-World Examples
- `prometheus.yaml` - Monitoring system with multiple installation options
- `postgresql.yaml` - Database with source, binary, and package options
- `redis.yaml` - In-memory database with comprehensive provider support

Each example demonstrates specific aspects of the 0.3 schema and can be used as templates for creating new saidata files.