# SAI Software Management Suite

> A comprehensive monorepo containing two complementary Python tools for software management and metadata generation.

**Repository:** [github.com/example42/sai-suite](https://github.com/example42/sai-suite)  
**Website:** [sai.software](https://sai.software)  
**Saidata Repository:** [github.com/example42/saidata](https://github.com/example42/saidata)

---

## 📑 Table of Contents

- [Two Packages, One Repository](#two-packages-one-repository)
- [Quick Start](#quick-start)
- [Documentation Hub](#documentation-hub)
- [Quick Examples](#quick-examples)
- [Configuration](#configuration)
- [Commands Overview](#commands-overview)
- [Supported Package Managers](#supported-package-managers)
- [Repository Structure](#repository-structure)
- [Development](#development)
- [Use Cases](#use-cases)
- [Troubleshooting & Support](#troubleshooting--support)
- [License](#license)

---

## 📦 Two Packages, One Repository

This repository provides **separate pip packages**. Installing SAI also installs SAIGEN because SAI imports its saidata model:

### 🔧 SAI - Software Action Interface

**Lightweight CLI for executing software management actions**

```bash
pip install sai
```

**Key Features:**
- Provider-based action execution (install, configure, start, stop, etc.)
- Multi-platform support (Linux, macOS, Windows)
- **Schema 0.3 support** with multiple installation methods:
  - **Packages**: Traditional package manager installations
  - **Sources**: Build software from source with autotools, cmake, make, meson, ninja
  - **Binaries**: Download and install pre-compiled binaries with platform/architecture detection
  - **Scripts**: Execute installation scripts with security validation
- Enhanced template functions for flexible configuration
- **Package name distinction**: Separate logical names (`name`) from actual package names (`package_name`)
- SAIGEN is a required runtime dependency; its AI/ML integrations remain optional
- Dry-run mode for safe testing
- Works with existing saidata from the [saidata repository](https://github.com/example42/saidata)

**Use SAI when you need to:**
- Deploy software using existing saidata
- Execute software management in production
- Run automated deployments in CI/CD pipelines
- Build software from source or install pre-compiled binaries

### 🤖 SAIGEN - SAI Data Generation

**AI-powered tool for generating and managing software metadata**

```bash
pip install saigen
```

**Key Features:**
- Generate saidata files for 50+ package managers (apt, dnf, brew, winget, npm, pypi, cargo, etc.)
- AI-enhanced generation with LLM support (OpenAI, Anthropic, Ollama)
- Schema validation and quality assessment
- Batch processing capabilities
- RAG (Retrieval-Augmented Generation) support
- Comprehensive repository management

**Use SAIGEN when you need to:**
- Create new saidata files
- Validate and test metadata
- Contribute to the saidata repository
- Build software catalogs

## 🚀 Quick Start

### Choose Your Installation

> **Note:** PyPI packages are coming soon. For now, use the development installation below.

```bash
# Clone the repository
git clone https://github.com/example42/sai-suite.git
cd sai-suite

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install both packages in editable mode
make install-both
# Or: ./scripts/install-local.sh both

# Verify installation
sai --version
saigen --version
```

**Future PyPI Installation (coming soon):**
```bash
# Install SAI for execution (includes SAIGEN)
pip install sai

# Install SAIGEN only (for metadata generation)
pip install saigen

# Install SAIGEN with all features (LLM + RAG)
pip install saigen[all]
```

**Not sure which to install?** See [When to Use What](docs/when-to-use-what.md)

### Quick Command Examples

**SAI (Execution):**
```bash
# Install software
sai install nginx

# Execute multiple actions
sai apply infrastructure.yaml

# View available providers
sai providers list
```

**SAIGEN (Generation):**
```bash
# Generate saidata
saigen generate nginx --providers apt brew

# Search across 50+ repositories
saigen repositories search redis

# Validate saidata
saigen validate nginx.yaml

# Test saidata
saigen test-system nginx.yaml
```

## 📖 Documentation Hub

### 🚀 Getting Started
- **[Quick Start Guide](QUICK-START.md)** - Get up and running in 5 minutes
- **[When to Use What](docs/when-to-use-what.md)** - Choose the right tool for your needs
- **[Installation Guide](docs/installation.md)** - Detailed installation instructions for all scenarios

### 📚 Core Documentation
- **[Documentation Index](docs/README.md)** - Complete documentation overview
- **[Monorepo Structure](MONOREPO.md)** - Understanding the repository architecture
- **[Architecture Diagram](docs/architecture-diagram.md)** - Visual guide to the system

### 🔧 SAI Documentation
- **[SAI README](sai/README.md)** - SAI package overview
- **[SAI CLI Reference](sai/docs/cli-reference.md)** - Complete command reference
- **[SAI Apply Command](sai/docs/sai-apply-command.md)** - Batch action execution
- **[Template Engine](sai/docs/template-engine.md)** - Configuration templating
- **[SAI Examples](sai/docs/examples/)** - Usage examples and patterns

### 🤖 SAIGEN Documentation
- **[SAIGEN README](saigen/README.md)** - SAIGEN package overview
- **[SAIGEN CLI Reference](saigen/docs/cli-reference.md)** - Complete command reference
- **[Generation Engine](saigen/docs/generation-engine.md)** - How generation works
- **[Repository Management](saigen/docs/repository-management.md)** - Working with 50+ repositories
- **[Configuration Guide](saigen/docs/configuration-guide.md)** - Advanced configuration
- **[Testing Guide](saigen/docs/testing-guide.md)** - Testing saidata files
- **[RAG Indexing Guide](saigen/docs/rag-indexing-guide.md)** - AI-enhanced generation
- **[SAIGEN Examples](saigen/docs/examples/)** - Generation examples and patterns

### 🛠️ Development & Contributing
- **[Tests Organization](tests/README.md)** - Test suite structure and guidelines
- **[Development Scripts](scripts/development/)** - Demo and development tools
- **[Documentation Quick Reference](DOCS-QUICK-REFERENCE.md)** - Find docs fast

## 🛠️ Development

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/example42/sai-suite.git
cd sai-suite

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install both packages in editable mode
make install-both
# Or: ./scripts/install-local.sh both

# Verify installation
sai --version
saigen --version
```

### Common Development Tasks

```bash
# Run tests
make test                    # All tests
make test-sai                # SAI tests only
make test-saigen             # SAIGEN tests only

# Code quality
make format                  # Format code
make lint                    # Run linters

# Build and publish
make build                   # Build both packages
make publish-test            # Publish to TestPyPI
make publish-prod            # Publish to PyPI

# Utilities
make clean                   # Clean build artifacts
make help                    # See all commands
```

**See [MONOREPO.md](MONOREPO.md) for complete development guide.**



## Supported Package Managers

SAIGEN now supports 50+ package managers across all major platforms:

### Linux Package Managers
- **Debian/Ubuntu**: apt
- **Red Hat/Fedora**: dnf, yum
- **SUSE**: zypper
- **Arch Linux**: pacman
- **Alpine**: apk
- **Gentoo**: emerge, portage
- **Void Linux**: xbps
- **Universal**: flatpak, snap

### macOS Package Managers
- **Homebrew**: brew (formulae and casks)
- **MacPorts**: macports
- **Nix**: nix, nixpkgs

### Windows Package Managers
- **Microsoft**: winget
- **Community**: chocolatey, scoop

### Language Ecosystems
- **JavaScript**: npm, yarn, pnpm
- **Python**: pypi, conda
- **Rust**: cargo (crates.io)
- **Ruby**: gem (rubygems)
- **Go**: go modules
- **PHP**: composer (packagist)
- **Java**: maven, gradle
- **C#/.NET**: nuget

### Container & Cloud
- **Containers**: docker hub
- **Kubernetes**: helm charts
- **Scientific**: spack, conda-forge

## 🆕 Schema 0.3 Features

SAI now supports the saidata schema version 0.3, which introduces powerful new capabilities:

### Multiple Installation Methods

**Packages** - Traditional package manager installations:
```yaml
packages:
  - name: nginx          # Logical name for cross-referencing
    package_name: nginx  # Actual package name for package managers
    version: "1.24.0"
```

**Sources** - Build from source with multiple build systems:
```yaml
sources:
  - name: main
    url: "https://nginx.org/download/nginx-{{version}}.tar.gz"
    build_system: autotools  # autotools, cmake, make, meson, ninja, custom
    configure_args:
      - "--with-http_ssl_module"
    checksum: "sha256:abc123..."
```

**Binaries** - Pre-compiled downloads with platform detection:
```yaml
binaries:
  - name: main
    url: "https://releases.example.com/{{version}}/app_{{platform}}_{{architecture}}.tar.gz"
    platform: linux      # linux, darwin, windows
    architecture: amd64  # amd64, arm64, etc.
    install_path: "/usr/local/bin"
    checksum: "sha256:def456..."
```

**Scripts** - Installation scripts with security validation:
```yaml
scripts:
  - name: official
    url: "https://get.example.com/install.sh"
    interpreter: bash
    checksum: "sha256:ghi789..."
    timeout: 600
```

### Enhanced Template Functions

Access saidata fields with precision using the new template functions:

```yaml
# Package management - specify which field to access
command: "apt-get install -y {{sai_package(0, 'package_name', 'apt')}}"
command: "echo Installing {{sai_package(0, 'name')}}"

# Source builds - access build configurations
command: "wget {{sai_source(0, 'url', 'source')}}"
command: "{{sai_source(0, 'build_system')}} build"

# Binary downloads - platform-aware installations
command: "curl -L {{sai_binary(0, 'url', 'binary')}} -o app.tar.gz"

# Script installations - secure script execution
command: "curl -fsSL {{sai_script(0, 'url', 'script')}} | {{sai_script(0, 'interpreter')}}"
```

### Package Name Distinction

Schema 0.3 distinguishes between logical names and actual package names:

- **`name`**: Logical identifier for cross-referencing (e.g., "nginx")
- **`package_name`**: Actual package name used by package managers (e.g., "nginx-full" for brew)

This allows the same software to have different package names across providers:

```yaml
packages:
  - name: nginx
    package_name: nginx

providers:
  brew:
    packages:
      - name: nginx
        package_name: nginx-full  # Different package name for brew
```

## 💡 Key Features at a Glance

### SAI Features
✅ Execute software actions across platforms  
✅ Multi-provider support (apt, brew, winget, etc.)  
✅ **Schema 0.3 support** with multiple installation methods:
  - Packages (traditional package managers)
  - Sources (build from source with autotools, cmake, make, meson, ninja)
  - Binaries (pre-compiled downloads with platform/architecture detection)
  - Scripts (installation scripts with security validation)
✅ Enhanced template functions with field-level access:
  - `sai_package(index, field, provider)` - Access package fields
  - `sai_source(index, field, provider)` - Access source configurations
  - `sai_binary(index, field, provider)` - Access binary configurations
  - `sai_script(index, field, provider)` - Access script configurations
✅ **Package name distinction**: Logical names vs actual package names  
✅ Batch action execution with `sai apply`  
✅ Dry-run mode for safe testing  
✅ Provider auto-detection and caching  
✅ Comprehensive history and metrics  
✅ Shell completion support  

### SAIGEN Features
✅ Generate saidata for 50+ package managers  
✅ AI-powered metadata generation (OpenAI, Anthropic, Ollama)  
✅ Search across all repositories simultaneously  
✅ Schema validation and quality assessment  
✅ Batch processing with concurrent operations  
✅ RAG (Retrieval-Augmented Generation) support  
✅ Comprehensive testing framework for saidata  
✅ Repository cache management  

## 🎯 Quick Examples

### SAI: Execute Software Actions

```bash
# Install software using available providers
sai install nginx

# Execute multiple actions from a file
sai apply infrastructure.yaml --parallel

# View available providers and statistics
sai providers list
sai stats --detailed

# Dry run to preview actions
sai install postgresql --dry-run
```

### SAIGEN: Generate & Validate Metadata

```bash
# Generate saidata with AI assistance
saigen generate nginx --providers apt brew

# Search across 50+ repositories
saigen repositories search redis --platform linux

# Validate and test saidata
saigen validate nginx.yaml
saigen test-system nginx.yaml

# Batch generate multiple packages
saigen batch --software-list "nginx,redis,postgresql"
```

## ⚙️ Configuration

### SAI Configuration

SAI looks for configuration files in:
- `~/.sai/config.yaml` or `~/.sai/config.json`
- `.sai.yaml` or `.sai.json` (in current directory)
- `sai.yaml` or `sai.json` (in current directory)

Example SAI configuration:
```yaml
config_version: "0.1.0"
log_level: info

# Saidata search paths (repository cache has highest priority)
saidata_paths:
  - "~/.sai/cache/repositories/saidata-main"
  - "~/.sai/saidata"
  - "/usr/local/share/sai/saidata"

provider_paths:
  - "providers"
  - "~/.sai/providers"
  - "/usr/local/share/sai/providers"

# Provider priorities (lower number = higher priority)
provider_priorities:
  apt: 1
  brew: 2
  winget: 3

# Execution settings
max_concurrent_actions: 3
action_timeout: 300
require_confirmation: true
dry_run_default: false
```

### SAIGEN Configuration

SAIGEN looks for configuration files in:
- `~/.saigen/config.yaml` or `~/.saigen/config.json`
- `.saigen.yaml` or `.saigen.json` (in current directory)
- `saigen.yaml` or `saigen.json` (in current directory)

Configuration can also be set via environment variables:
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `SAIGEN_LOG_LEVEL` - Logging level (debug, info, warning, error)
- `SAIGEN_CACHE_DIR` - Cache directory path
- `SAIGEN_OUTPUT_DIR` - Output directory path

Example SAIGEN configuration:
```yaml
config_version: "0.1.0"
log_level: info

llm_providers:
  openai:
    provider: openai
    model: gpt-4o-mini
    max_tokens: 4000
    temperature: 0.1
    timeout: 30
    max_retries: 3
    enabled: true
  anthropic:
    provider: anthropic
    model: claude-3-sonnet-20240229
    enabled: false

repositories:
  apt:
    type: apt
    enabled: true
    cache_ttl: 3600
    priority: 1

cache:
  directory: ~/.saigen/cache
  max_size_mb: 1000
  default_ttl: 3600

rag:
  enabled: true
  index_directory: ~/.saigen/rag_index
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
  max_context_items: 5

generation:
  default_providers: [apt, brew, winget]
  output_directory: ./saidata
  parallel_requests: 3
  request_timeout: 120

validation:
  strict_mode: true
  auto_fix_common_issues: true
```

## 📋 Commands Overview

### SAI Commands

**Software Management**
```bash
sai install <software>        # Install software
sai uninstall <software>      # Uninstall software
sai start|stop|restart <sw>   # Service management
sai status <software>         # Check status
sai apply <file>              # Batch actions
```

**Provider Management**
```bash
sai providers list            # List providers
sai providers detect          # Detect available providers
sai providers info <name>     # Provider details
```

**Configuration & Utilities**
```bash
sai config show               # Show configuration
sai stats                     # Show statistics
sai history list              # Execution history
sai completion install        # Shell completion
```

**📖 Full command reference:** [SAI CLI Reference](sai/docs/cli-reference.md)

### SAIGEN Commands

**Generation & Validation**
```bash
saigen generate <software>    # Generate saidata
saigen validate <file>        # Validate saidata
saigen quality <file>         # Quality assessment
saigen batch                  # Batch generation
saigen test-system <file>     # Test saidata
```

**Repository Management**
```bash
saigen repositories list-repos      # List all repositories
saigen repositories search <query>  # Search packages
saigen repositories info <package>  # Package details
saigen repositories stats           # Repository statistics
saigen repositories update-cache    # Update caches
```

**Configuration**
```bash
saigen config show            # Show configuration
saigen config set <key> <val> # Set configuration
saigen config init            # Initialize config
```

**📖 Full command reference:** [SAIGEN CLI Reference](saigen/docs/cli-reference.md)

## 🔍 Troubleshooting & Support

- **Repository Issues:** [Repository Troubleshooting](saigen/docs/repository-troubleshooting.md)
- **Bug Reports:** [Open an issue](https://github.com/example42/sai-suite/issues)
- **Questions:** [GitHub Discussions](https://github.com/example42/sai-suite/discussions)
- **Documentation:** See [Documentation Hub](#documentation-hub) above

## 📁 Repository Structure

```
sai-suite/
├── sai/                          # SAI package (lightweight execution)
│   ├── pyproject.toml            # Package configuration
│   ├── __init__.py               # Package root
│   ├── cli/                      # CLI interface and commands
│   ├── core/                     # Core execution engine
│   ├── models/                   # Data models
│   ├── providers/                # Provider implementations
│   ├── utils/                    # Utilities
│   └── docs/                     # SAI-specific documentation
│       └── examples/             # SAI usage examples
│   │   └── cli-reference.md      # Command reference
│   └── pyproject.toml            # SAI package configuration
│
├── saigen/                       # SAIGEN package (generation tool)
│   ├── saigen/                   # Source code
│   │   ├── cli/                  # CLI interface and commands
│   │   ├── core/                 # Generation engine
│   │   ├── llm/                  # LLM provider integrations
│   │   ├── models/               # Data models
│   │   ├── repositories/         # 50+ repository integrations
│   │   ├── testing/              # Testing framework
│   │   └── utils/                # Utilities
│   ├── docs/                     # SAIGEN-specific documentation
│   │   ├── examples/             # Generation examples
│   │   ├── cli-reference.md      # Command reference
│   │   ├── repository-management.md
│   │   └── testing-guide.md
│   └── pyproject.toml            # SAIGEN package configuration
│
├── docs/                         # Shared documentation
│   ├── summaries/                # Implementation summaries
│   ├── archive/                  # Archived documentation
│   ├── TODO/                     # Pending tasks
│   ├── installation.md
│   ├── when-to-use-what.md
│   └── MIGRATION.md
│
├── tests/                        # Comprehensive test suite
│   ├── sai/                      # SAI-specific tests
│   ├── saigen/                   # SAIGEN-specific tests
│   ├── shared/                   # Shared component tests
│   └── integration/              # Integration tests
│
├── scripts/                      # Build and utility scripts
│   └── development/              # Development scripts
│       ├── sai/                  # SAI demo scripts
│       └── saigen/               # SAIGEN demo scripts
│
├── examples/                     # Shared examples (CI/CD)
├── schemas/                      # JSON schema definitions
├── providers/                    # Provider data files
├── pyproject.toml                # Workspace configuration
├── README.md                     # This file
├── QUICK-START.md                # Quick start guide
├── MONOREPO.md                   # Monorepo architecture
└── DOCS-QUICK-REFERENCE.md       # Documentation index
```

**See [MONOREPO.md](MONOREPO.md) for detailed architecture information.**

## 🔄 How SAI and SAIGEN Work Together

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   SAIGEN    │ creates │   Saidata    │  used   │     SAI     │
│ (Generator) │────────>│    Files     │────────>│ (Executor)  │
└─────────────┘         └──────────────┘   by    └─────────────┘
      │                                               │
      │ AI + Repository Data                          │ Provider-based
      │ Schema Validation                             │ Action Execution
      │ Quality Assessment                            │ Multi-platform
      └───────────────────────────────────────────────┘
                    Independent but Complementary
```

- **SAI** consumes saidata files to execute software management actions
- **SAIGEN** generates saidata files using AI and repository data
- Both share common schemas and data formats but operate independently
- SAI focuses on execution and action management
- SAIGEN focuses on metadata generation and validation

## 🛡️ Specialized Providers

SAI includes specialized providers for security, debugging, and analysis:

- **Network Security (nmap)**: Port scanning, service discovery, vulnerability detection
- **SBOM Generation (syft)**: Package scanning, SBOM generation, format conversion
- **Vulnerability Scanning (grype)**: Security scanning, CVE checking, report generation
- **Debugging (gdb)**: Interactive debugging, process attachment, core dump analysis

**📖 See:** [Specialized Providers Roadmap](sai/docs/specialized-providers-roadmap.md)

## Use Cases

### SAI Use Cases
- Automated software deployment and configuration
- Cross-platform software management
- Infrastructure as Code implementations
- CI/CD pipeline integrations
- System administration automation

### SAIGEN Use Cases
- Generating metadata for new software packages
- Updating existing saidata with latest information
- Bulk metadata generation for software catalogs
- AI-assisted software documentation
- Repository data analysis and enrichment

## 📄 License

Apache License 2.0 - see [LICENSE](LICENSE) file for details.

---

## 🔗 Quick Links

| Resource | Link |
|----------|------|
| **Website** | [sai.software](https://sai.software) |
| **Repository** | [github.com/example42/sai-suite](https://github.com/example42/sai-suite) |
| **Saidata Repo** | [github.com/example42/saidata](https://github.com/example42/saidata) |
| **Issues** | [Report a bug](https://github.com/example42/sai-suite/issues) |
| **Discussions** | [Ask questions](https://github.com/example42/sai-suite/discussions) |
| **SAI on PyPI** | [pypi.org/project/sai](https://pypi.org/project/sai/) |
| **SAIGEN on PyPI** | [pypi.org/project/saigen](https://pypi.org/project/saigen/) |

---

**Made with ❤️ by the SAI team**

*Star ⭐ this repository if you find it useful!*
