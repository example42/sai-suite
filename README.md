# SAI Software Management Suite

This repository contains two complementary tools for software metadata management:

## 🔧 SAI - Software Action Interface CLI Tool

A lightweight CLI tool for executing software management actions using provider-based configurations.

**Key Features:**
- **Provider-based Actions**: Execute install, configure, start, stop, and other actions
- **Multi-platform Support**: Works across Linux, macOS, and Windows
- **Extensible Providers**: Support for package managers, containers, and custom providers
- **Configuration Management**: Flexible YAML/JSON configuration system
- **Dry-run Mode**: Preview actions before execution

## 🤖 SAIGEN - AI-Powered Saidata Generation Tool

An AI-enhanced tool for generating, validating, and managing software metadata in YAML format with universal repository support.

**Key Features:**
- **Universal Repository Support**: 50+ package managers including apt, dnf, brew, winget, npm, pypi, cargo, and more
- **YAML-Driven Configuration**: Add new repositories without code changes using simple YAML configs
- **AI-Enhanced Generation**: Uses LLMs (OpenAI, Anthropic, Ollama) for intelligent metadata creation
- **Advanced Repository Management**: Concurrent operations, intelligent caching, and real-time statistics
- **Schema Validation**: Validates generated files against official saidata schema
- **RAG Support**: Retrieval-Augmented Generation for improved accuracy
- **Batch Processing**: Generate metadata for multiple software packages efficiently
- **Comprehensive CLI**: Full-featured repository management and package search capabilities

## Installation

### Install Both Tools
```bash
pip install sai  # Installs both sai and saigen
```

### Development Installation

It's recommended to use a virtual environment for development:

```bash
git clone https://github.com/example42/sai.git
cd sai

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Upgrade pip to latest version (required for pyproject.toml editable installs)
pip install --upgrade pip

# Install in development mode with all dependencies
pip install -e ".[dev,llm,rag]"
```

To deactivate the virtual environment when done:
```bash
deactivate
```

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

## Quick Start

### SAI CLI Tool

1. Execute software actions using providers:
```bash
# Install nginx using available providers
sai install nginx

# Start a service
sai start nginx

# Dry run to preview actions
sai install nginx --dry-run
```

2. Execute multiple actions from a file:
```bash
# Apply actions from a YAML file
sai apply actions.yaml

# Apply with parallel execution
sai apply actions.yaml --parallel

# Apply and continue on errors
sai apply actions.yaml --continue-on-error
```

2. View available providers and statistics:
```bash
sai providers list
sai actions nginx
sai stats --detailed
sai config-show
```

### SAIGEN AI Generation Tool

1. **Explore Available Repositories** (50+ supported):
```bash
# List all repositories
saigen repositories list-repos

# Filter by platform
saigen repositories list-repos --platform linux

# Filter by type
saigen repositories list-repos --type npm
```

2. **Search Packages Across All Repositories**:
```bash
# Search across all 50+ repositories
saigen repositories search "redis"

# Search with platform filter
saigen repositories search "nginx" --platform linux --limit 10

# Get detailed package information
saigen repositories info "docker" --platform linux
```

3. **Repository Statistics and Management**:
```bash
# Show comprehensive statistics
saigen repositories stats

# Update repository caches (concurrent operations)
saigen repositories update-cache

# JSON output for automation
saigen repositories stats --format json
```

4. **Configure LLM Provider**:
```bash
export OPENAI_API_KEY="your-api-key"
# or
export ANTHROPIC_API_KEY="your-api-key"
```

5. **Generate Saidata with Repository Data**:
```bash
# Generate using repository data + AI
saigen generate nginx

# Generate with specific providers
saigen generate nginx --llm-provider openai --providers apt brew --output nginx.yaml

# View current configuration
saigen config --show
```

6. **Validate Generated Files**:
```bash
saigen validate nginx.yaml
saigen validate --show-context --format json nginx.yaml
```

## Commands

### SAI Commands

#### Software Management
- `sai install <software>` - Install software using available providers
- `sai uninstall <software>` - Uninstall software using available providers
- `sai start <software>` - Start software/service
- `sai stop <software>` - Stop software/service
- `sai restart <software>` - Restart software/service
- `sai status <software>` - Show software service status
- `sai info <software>` - Show software information
- `sai search <term>` - Search for available software
- `sai list` - List installed software managed through sai
- `sai logs <software>` - Show software service logs
- `sai version <software>` - Show software version information
- `sai apply <action_file>` - Apply multiple actions from a YAML/JSON file

#### Provider Management
- `sai providers list` - List available providers
- `sai providers detect` - Detect and refresh provider availability
- `sai providers info <provider>` - Show detailed provider information
- `sai providers clear-cache` - Clear provider detection cache
- `sai providers cache-status` - Show provider cache status
- `sai providers refresh-cache` - Refresh provider detection cache

#### Configuration Management
- `sai config show` - Display current SAI configuration
- `sai config set <key> <value>` - Set configuration value
- `sai config reset [key]` - Reset configuration to defaults
- `sai config validate` - Validate configuration file
- `sai config paths` - Show configuration file search paths

#### History and Analytics
- `sai history list` - Show execution history
- `sai history metrics` - Show execution metrics and statistics
- `sai history clear` - Clear execution history

#### Shell Integration
- `sai completion install` - Install shell completion
- `sai completion uninstall` - Uninstall shell completion

#### Specialized Tool Actions
- `sai scan <software>` - Scan for packages/vulnerabilities (syft, grype)
- `sai generate <software>` - Generate SBOM or reports (syft)
- `sai debug <software>` - Start debugging session (gdb)
- `sai attach <software>` - Attach debugger to running process (gdb)
- `sai report <software>` - Generate vulnerability/security reports (grype)
- `sai export <software>` - Export data in multiple formats (syft, grype)
- `sai update <software>` - Update databases/signatures (grype)
- `sai convert <software>` - Convert between formats (syft)
- `sai validate <software>` - Validate generated files (syft)
- `sai filter <software>` - Apply filters to scan results (grype)
- `sai check <software>` - Check for specific issues/CVEs (grype)

#### Service Management (systemd-based systems)
- `sai enable <software>` - Enable service auto-start
- `sai disable <software>` - Disable service auto-start

#### Utilities
- `sai stats` - Show comprehensive statistics about providers and actions
- `sai validate <saidata-file>` - Validate a saidata file against the schema
- `sai --version` - Show sai version information

### SAIGEN Commands

#### Generation and Validation
- `saigen generate <software>` - Generate saidata for software with AI assistance
- `saigen validate <file>` - Validate saidata file against schema with detailed reporting

#### Configuration Management
- `saigen config show` - Display current configuration including LLM providers
- `saigen config set <key> <value>` - Set configuration values with dot notation
- `saigen config validate` - Validate configuration file syntax and settings
- `saigen config init` - Initialize new configuration file with defaults

#### Universal Repository Management
- `saigen repositories list-repos` - List all 50+ supported repositories with filtering
- `saigen repositories search <query>` - Search packages across all repositories
- `saigen repositories info <package>` - Get detailed package information
- `saigen repositories stats` - Show comprehensive repository statistics and health
- `saigen repositories update-cache` - Update repository caches with concurrent operations

#### Repository Filtering and Search
- `--platform <linux|macos|windows|universal>` - Filter by platform
- `--type <apt|brew|npm|pypi|cargo|...>` - Filter by repository type
- `--limit <number>` - Limit search results
- `--format <table|json|yaml>` - Choose output format

#### Help and Information
- `saigen --help` - Show all available commands and options
- `saigen --version` - Show version information

#### Generation Options
- `--llm-provider` - Choose LLM provider (openai, anthropic, ollama)
- `--providers` - Target package providers (50+ supported)
- `--output` - Output file path
- `--dry-run` - Preview generation without making API calls
- `--verbose` - Enable detailed logging

#### Validation Options  
- `--format` - Output format (text, json, yaml)
- `--show-context` - Include detailed error context
- `--strict` - Enable strict validation mode

## Troubleshooting

For common issues and solutions, see the [Troubleshooting Guide](docs/troubleshooting.md).

## Configuration

### SAI Configuration

SAI looks for configuration files in:
- `~/.sai/config.yaml` or `~/.sai/config.json`
- `.sai.yaml` or `.sai.json` (in current directory)
- `sai.yaml` or `sai.json` (in current directory)

Example SAI configuration:
```yaml
config_version: "0.1.0"
log_level: info

# Provider search paths
saidata_paths:
  - "."
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
    model: gpt-3.5-turbo
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

## Repository Structure

```
├── sai/                    # SAI CLI Tool
│   ├── cli/               # CLI interface and commands
│   ├── models/            # Data models (config, provider data)
│   └── utils/             # Utilities (config management)
├── saigen/                # SAIGEN AI Generation Tool
│   ├── cli/               # CLI interface and commands
│   ├── core/              # Core generation engine
│   ├── llm/               # LLM provider integrations
│   ├── models/            # Data models (saidata, generation)
│   ├── repositories/      # Package repository integrations
│   └── utils/             # Utilities and helpers
├── saidata/               # Generated saidata files
├── providers/             # Provider data files
├── schemas/               # JSON schema definitions
├── docs/                  # Documentation
├── tests/                 # Test suite
└── examples/              # Usage examples
```

## Project Relationship

- **SAI** consumes saidata files and provider configurations to execute software management actions
- **SAIGEN** generates saidata files using AI and repository data that SAI can then use
- Both tools share common schemas and data formats but operate independently
- SAI focuses on execution and action management
- SAIGEN focuses on metadata generation and validation

## Specialized Providers

SAI includes specialized providers for security, debugging, and analysis tools:

### Network Security (nmap)
- **Port scanning**: `sai search <target>` - Scan ports on target hosts
- **Service discovery**: `sai info <target>` - Detect services and versions
- **Script scanning**: `sai logs <target>` - Run NSE scripts
- **Performance tuning**: `sai list <target>` - Optimized timing scans
- **Version detection**: `sai version <target>` - Detect service versions on target

### SBOM Generation (syft)
- **Package scanning**: `sai scan <path>` - Scan directories/images for packages
- **SBOM generation**: `sai generate <image>` - Generate SBOM from container images
- **Format conversion**: `sai convert <sbom>` - Convert between SBOM formats
- **Multi-format export**: `sai export <target>` - Export to SPDX, CycloneDX, table formats
- **SBOM validation**: `sai validate <sbom>` - Validate SBOM format compliance
- **SBOM comparison**: `sai diff <baseline> <current>` - Compare two SBOMs

### Vulnerability Scanning (grype)
- **Security scanning**: `sai scan <target>` - Scan for vulnerabilities
- **Report generation**: `sai report <target>` - Generate vulnerability reports
- **Severity filtering**: `sai filter <target>` - Filter by vulnerability severity
- **Multi-format export**: `sai export <target>` - Export to JSON, SARIF, table formats
- **Database updates**: `sai update` - Update vulnerability database
- **CVE checking**: `sai check <target>` - Check for specific CVEs

### Debugging (gdb)
- **Interactive debugging**: `sai debug <binary>` - Start debugging session
- **Process attachment**: `sai attach <process>` - Attach to running process
- **Core dump analysis**: `sai core_dump <binary>` - Analyze core dumps
- **Stack traces**: `sai backtrace <process>` - Get stack trace from running process
- **Breakpoint debugging**: `sai breakpoint <binary>` - Set breakpoints and debug
- **Variable watching**: `sai watch <binary>` - Watch variable changes
- **Memory inspection**: `sai inspect <process>` - Inspect memory and variables
- **Execution profiling**: `sai profile <binary>` - Profile application execution

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

## License

MIT License - see LICENSE file for details.