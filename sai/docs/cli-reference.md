# SAI CLI Reference

Complete command-line reference for the SAI (Software Action Interface) tool.

## Overview

SAI is a cross-platform software management CLI tool that executes actions using provider-based configurations and saidata files.

**Schema Version:** 0.3 (supports packages, sources, binaries, and scripts)  
**Default Repository:** `https://github.com/example42/saidata`  
**Cache Location:** `~/.sai/cache/repositories/`

### What's New in Schema 0.3

Schema 0.3 introduces significant enhancements to saidata structure and capabilities:

#### Multiple Installation Methods

SAI now supports four distinct installation methods, each optimized for different use cases:

1. **Packages** - Traditional package manager installations (apt, brew, dnf, etc.)
2. **Sources** - Build software from source with support for:
   - autotools (./configure && make && make install)
   - cmake (cmake && make && make install)
   - make (make && make install)
   - meson (meson setup && ninja)
   - ninja (ninja && ninja install)
   - custom (user-defined build commands)
3. **Binaries** - Download and install pre-compiled binaries with:
   - Platform detection (linux, darwin, windows)
   - Architecture detection (amd64, arm64, x86, etc.)
   - Archive extraction (tar.gz, zip, etc.)
   - Automatic URL templating
4. **Scripts** - Execute installation scripts with:
   - Security validation (checksum verification)
   - Interpreter specification (bash, sh, python, etc.)
   - Timeout controls
   - Environment variable support

#### Enhanced Package Structure

**Package Name Distinction**: Schema 0.3 separates logical identifiers from actual package names:

- **`name`**: Logical identifier used for cross-referencing within saidata files
- **`package_name`**: Actual package name used by package managers

This distinction enables:
- Consistent logical naming across all providers
- Provider-specific package name overrides
- Better cross-platform compatibility
- Clearer saidata organization

**Example:**
```yaml
packages:
  - name: nginx          # Logical name - consistent across providers
    package_name: nginx  # Actual package name for most providers

providers:
  brew:
    packages:
      - name: nginx
        package_name: nginx-full  # Different package name for Homebrew
```

#### New Template Functions

Three new template functions provide access to installation method configurations:

- **`sai_source(index, field, provider)`** - Access source build configurations
- **`sai_binary(index, field, provider)`** - Access binary download configurations
- **`sai_script(index, field, provider)`** - Access script installation configurations

#### Field-Level Access

The `sai_package()` function now supports a `field` parameter for precise data access:

```yaml
# Old approach (schema 0.2) - returns package name only
{{sai_package(0, 'apt')}}

# New approach (schema 0.3) - specify which field to access
{{sai_package(0, 'package_name', 'apt')}}  # Package name
{{sai_package(0, 'name', 'apt')}}          # Logical name
{{sai_package(0, 'version', 'apt')}}       # Version
```

#### Provider Overrides

Provider-specific configurations now support all resource types:

```yaml
providers:
  apt:
    packages: [...]      # Provider-specific packages
    sources: [...]       # Provider-specific source builds
    binaries: [...]      # Provider-specific binaries
    scripts: [...]       # Provider-specific scripts
    services: [...]      # Provider-specific services
    files: [...]         # Provider-specific files
```

This enables fine-grained control over how software is installed and configured on different platforms.

## Global Options

```bash
sai [OPTIONS] COMMAND [ARGS]...
```

### Options

- `--version` - Show version and exit
- `--help` - Show help message and exit
- `--config PATH` - Path to configuration file
- `--dry-run` - Preview actions without executing
- `--verbose, -v` - Increase verbosity
- `--quiet, -q` - Decrease verbosity

## Commands

### Software Management

#### install
Install software using saidata.

```bash
sai install [OPTIONS] SOFTWARE...
```

**Options:**
- `--provider TEXT` - Specify provider (auto-detected if not specified)
- `--version TEXT` - Specific version to install
- `--config PATH` - Configuration file
- `--dry-run` - Preview without executing

**Examples:**
```bash
sai install nginx
sai install nginx --provider apt
sai install nginx --version 1.18.0
sai install nginx postgresql redis
```

#### configure
Configure installed software.

```bash
sai configure [OPTIONS] SOFTWARE
```

**Options:**
- `--config PATH` - Configuration file with settings
- `--dry-run` - Preview configuration changes

**Examples:**
```bash
sai configure nginx --config nginx.yaml
sai configure postgresql --config prod-db.yaml
```

#### start
Start software services.

```bash
sai start [OPTIONS] SOFTWARE...
```

**Examples:**
```bash
sai start nginx
sai start nginx postgresql
```

#### stop
Stop software services.

```bash
sai stop [OPTIONS] SOFTWARE...
```

**Examples:**
```bash
sai stop nginx
sai stop nginx postgresql
```

#### restart
Restart software services.

```bash
sai restart [OPTIONS] SOFTWARE...
```

**Examples:**
```bash
sai restart nginx
sai restart nginx postgresql
```

#### remove
Remove/uninstall software.

```bash
sai remove [OPTIONS] SOFTWARE...
```

**Options:**
- `--purge` - Remove configuration files too
- `--dry-run` - Preview removal

**Examples:**
```bash
sai remove nginx
sai remove nginx --purge
```

#### update
Update software to latest version.

```bash
sai update [OPTIONS] [SOFTWARE...]
```

**Options:**
- `--all` - Update all installed software

**Examples:**
```bash
sai update nginx
sai update --all
```

### Batch Operations

#### apply
Apply configuration from a file.

```bash
sai apply [OPTIONS] --config PATH
```

**Options:**
- `--config PATH` - Configuration file (required)
- `--dry-run` - Preview actions
- `--continue-on-error` - Continue if one action fails

**Examples:**
```bash
sai apply --config infrastructure.yaml
sai apply --config infrastructure.yaml --dry-run
```

See [sai-apply-command.md](sai-apply-command.md) for detailed documentation.

### Information Commands

#### list
List software.

```bash
sai list [OPTIONS] [CATEGORY]
```

**Categories:**
- `installed` - Show installed software
- `available` - Show available software in repository
- `all` - Show all software

**Examples:**
```bash
sai list installed
sai list available
sai list
```

#### info
Show information about software.

```bash
sai info [OPTIONS] SOFTWARE
```

**Examples:**
```bash
sai info nginx
sai info postgresql
```

#### search
Search for software in repository.

```bash
sai search [OPTIONS] QUERY
```

**Examples:**
```bash
sai search web server
sai search database
```

### Repository Management

#### repo update
Update saidata repository cache.

```bash
sai repo update [OPTIONS]
```

**Examples:**
```bash
sai repo update
```

#### repo list
List configured repositories.

```bash
sai repo list
```

#### repo info
Show repository information.

```bash
sai repo info [REPO_NAME]
```

## Configuration

See [examples/sai-config-sample.yaml](examples/sai-config-sample.yaml) for configuration examples.

## Exit Codes

- `0` - Success
- `1` - General error
- `2` - Command-line usage error
- `3` - Configuration error
- `4` - Execution error

## Environment Variables

- `SAI_CONFIG` - Path to configuration file
- `SAI_CACHE_DIR` - Override cache directory
- `SAI_REPO_URL` - Override default repository URL
- `SAI_LOG_LEVEL` - Set log level (DEBUG, INFO, WARNING, ERROR)

## Package Name vs Package_Name

Schema 0.3 introduces an important distinction between logical names and actual package names:

### Understanding the Distinction

**`name` (Logical Name)**
- Internal identifier used for cross-referencing within saidata files
- Consistent across all providers and platforms
- Used for organizing and referencing software
- Example: `nginx`, `postgresql`, `redis`

**`package_name` (Actual Package Name)**
- The actual package name used by package managers
- May vary across different providers
- What gets passed to `apt install`, `brew install`, etc.
- Example: `nginx`, `nginx-full`, `nginx-mainline`

### Why This Matters

Different package managers may use different names for the same software:

```yaml
# Base definition
packages:
  - name: nginx                    # Logical name - always "nginx"
    package_name: nginx            # Default package name

# Homebrew uses a different package name
providers:
  brew:
    packages:
      - name: nginx                # Same logical name
        package_name: nginx-full   # Different actual package name

# APT uses the default
providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx        # Standard package name
```

### Usage in Templates

Always use `package_name` field when installing packages:

```yaml
# Correct - uses actual package name
command: "apt-get install -y {{sai_package(0, 'package_name', 'apt')}}"

# Incorrect - uses logical name (may not match actual package)
command: "apt-get install -y {{sai_package(0, 'name', 'apt')}}"
```

Use `name` field for display, logging, or cross-referencing:

```yaml
# Display logical name to user
command: "echo Installing {{sai_package(0, 'name')}}..."

# Then install using actual package name
command: "apt-get install -y {{sai_package(0, 'package_name', 'apt')}}"
```

### Real-World Examples

**Example 1: Python**
```yaml
packages:
  - name: python3
    package_name: python3

providers:
  apt:
    packages:
      - name: python3
        package_name: python3.11    # Specific version on Ubuntu
  brew:
    packages:
      - name: python3
        package_name: python@3.11   # Homebrew naming convention
```

**Example 2: Node.js**
```yaml
packages:
  - name: nodejs
    package_name: nodejs

providers:
  apt:
    packages:
      - name: nodejs
        package_name: nodejs        # Standard name
  brew:
    packages:
      - name: nodejs
        package_name: node          # Homebrew uses "node"
```

## Template Functions (Schema 0.3)

SAI uses template functions in provider configurations to access saidata fields dynamically.

### Package Functions

**`sai_package(index, field, provider)`** - Get package field value

```yaml
# Get first package name for apt
command: "apt-get install -y {{sai_package(0, 'package_name', 'apt')}}"

# Get all package names for apt (space-separated)
command: "apt-get install -y {{sai_package('*', 'package_name', 'apt')}}"

# Get logical name
command: "echo Installing {{sai_package(0, 'name')}}"

# Get version
command: "apt-get install -y {{sai_package(0, 'package_name', 'apt')}}={{sai_package(0, 'version')}}"
```

**Parameters:**
- `index`: `0`, `1`, `2`, ... or `'*'` for all packages
- `field`: `'package_name'`, `'name'`, `'version'`, `'alternatives'`, etc.
- `provider`: `'apt'`, `'brew'`, `'dnf'`, etc. (optional, for provider-specific lookup)

### Installation Method Functions

#### sai_source() - Source Build Configuration

**`sai_source(index, field, provider)`** - Access source build configurations

**Common Use Cases:**

```yaml
# Download source tarball
command: "wget {{sai_source(0, 'url', 'source')}} -O source.tar.gz"

# Extract and build
command: |
  tar xzf source.tar.gz
  cd source-dir
  ./configure {{sai_source(0, 'configure_args', 'source')}}
  make {{sai_source(0, 'build_args', 'source')}}
  make install {{sai_source(0, 'install_args', 'source')}}

# Get build system type
command: "echo Build system: {{sai_source(0, 'build_system')}}"

# Verify checksum
command: "echo '{{sai_source(0, 'checksum')}}  source.tar.gz' | sha256sum -c"
```

**Available Fields:**
- `name` - Logical name (e.g., 'main', 'stable', 'dev')
- `url` - Download URL (supports `{{version}}`, `{{platform}}`, `{{architecture}}` placeholders)
- `version` - Source version
- `build_system` - Build system (autotools, cmake, make, meson, ninja, custom)
- `build_dir` - Build directory path
- `source_dir` - Source directory path
- `install_prefix` - Installation prefix (e.g., /usr/local)
- `configure_args` - Configuration arguments (array)
- `build_args` - Build arguments (array)
- `install_args` - Installation arguments (array)
- `prerequisites` - Required packages (array)
- `checksum` - Source checksum for verification

#### sai_binary() - Binary Download Configuration

**`sai_binary(index, field, provider)`** - Access binary download configurations

**Common Use Cases:**

```yaml
# Download binary with platform/architecture detection
command: "curl -L {{sai_binary(0, 'url', 'binary')}} -o app.tar.gz"

# Extract and install
command: |
  tar xzf app.tar.gz
  install -m {{sai_binary(0, 'permissions')}} {{sai_binary(0, 'executable')}} {{sai_binary(0, 'install_path')}}

# Verify checksum before installation
command: "echo '{{sai_binary(0, 'checksum')}}  app.tar.gz' | sha256sum -c"

# Platform-specific installation
command: |
  if [ "{{sai_binary(0, 'platform')}}" = "linux" ]; then
    install -m 755 app /usr/local/bin/
  fi
```

**Available Fields:**
- `name` - Logical name
- `url` - Download URL (supports placeholders)
- `version` - Binary version
- `platform` - Target platform (linux, darwin, windows)
- `architecture` - Target architecture (amd64, arm64, x86, etc.)
- `checksum` - Binary checksum
- `install_path` - Installation directory (e.g., /usr/local/bin)
- `executable` - Executable filename
- `permissions` - File permissions (octal format, e.g., 755)
- `archive.format` - Archive format (tar.gz, zip, etc.)
- `archive.strip_prefix` - Prefix to strip during extraction
- `archive.extract_path` - Extraction path

#### sai_script() - Script Installation Configuration

**`sai_script(index, field, provider)`** - Access script installation configurations

**Common Use Cases:**

```yaml
# Download and execute installation script
command: "curl -fsSL {{sai_script(0, 'url', 'script')}} | {{sai_script(0, 'interpreter')}}"

# Download, verify, then execute
command: |
  curl -fsSL {{sai_script(0, 'url', 'script')}} -o install.sh
  echo '{{sai_script(0, 'checksum')}}  install.sh' | sha256sum -c
  {{sai_script(0, 'interpreter')}} install.sh {{sai_script(0, 'arguments')}}

# Execute with timeout
command: "timeout {{sai_script(0, 'timeout')}} bash install.sh"

# Execute with environment variables
command: |
  export INSTALL_DIR={{sai_script(0, 'environment.INSTALL_DIR')}}
  bash install.sh
```

**Available Fields:**
- `name` - Logical name (e.g., 'official', 'convenience')
- `url` - Script download URL
- `version` - Script version
- `interpreter` - Script interpreter (bash, sh, python, perl, etc.)
- `checksum` - Script checksum for security validation
- `arguments` - Script arguments (array)
- `environment` - Environment variables (object)
- `working_dir` - Working directory for execution
- `timeout` - Execution timeout in seconds (default: 300)

### Common Fields

**Package Fields:**
- `name` - Logical name for cross-referencing
- `package_name` - Actual package name for package managers
- `version` - Package version
- `alternatives` - Alternative package names
- `repository` - Repository name
- `checksum` - Package checksum

**Source Fields:**
- `name` - Logical name (e.g., 'main', 'stable')
- `url` - Download URL (supports `{{version}}`, `{{platform}}`, `{{architecture}}` placeholders)
- `version` - Source version
- `build_system` - Build system type (autotools, cmake, make, meson, ninja, custom)
- `build_dir` - Build directory
- `install_prefix` - Installation prefix
- `checksum` - Source checksum

**Binary Fields:**
- `name` - Logical name
- `url` - Download URL (supports placeholders)
- `version` - Binary version
- `platform` - Target platform (linux, darwin, windows)
- `architecture` - Target architecture (amd64, arm64, etc.)
- `install_path` - Installation path
- `executable` - Executable name
- `checksum` - Binary checksum

**Script Fields:**
- `name` - Logical name
- `url` - Script URL
- `version` - Script version
- `interpreter` - Script interpreter (bash, sh, python, etc.)
- `checksum` - Script checksum
- `timeout` - Execution timeout in seconds

### Template Resolution Order

Template functions follow a hierarchical resolution order:
1. **OS-specific provider overrides**: `saidata.providers.{provider}.{resource_type}` from OS override file
2. **Default provider overrides**: `saidata.providers.{provider}.{resource_type}` from default file
3. **OS-specific defaults**: `saidata.{resource_type}` from OS override file
4. **Base defaults**: `saidata.{resource_type}` from default file

**Example:** `{{sai_package(0, 'package_name', 'apt')}}` on Ubuntu 22.04 will look for:
1. `software/ap/apache/ubuntu/22.04.yaml` → `providers.apt.packages[0].package_name`
2. `software/ap/apache/default.yaml` → `providers.apt.packages[0].package_name`
3. `software/ap/apache/ubuntu/22.04.yaml` → `packages[0].package_name`
4. `software/ap/apache/default.yaml` → `packages[0].package_name`

## Complete Examples

### Example 1: Package Installation with Multiple Providers

**Saidata (nginx.yaml):**
```yaml
version: "0.3"
metadata:
  name: nginx
  description: "High-performance HTTP server"

packages:
  - name: nginx
    package_name: nginx
    version: "1.24.0"

providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx
  brew:
    packages:
      - name: nginx
        package_name: nginx-full
```

**Provider Action (apt.yaml):**
```yaml
actions:
  install:
    command: "apt-get install -y {{sai_package('*', 'package_name', 'apt')}}"
```

**Usage:**
```bash
sai install nginx --provider apt   # Installs "nginx" on Ubuntu
sai install nginx --provider brew  # Installs "nginx-full" on macOS
```

### Example 2: Source Build Installation

**Saidata (redis.yaml):**
```yaml
version: "0.3"
metadata:
  name: redis
  description: "In-memory data structure store"

sources:
  - name: main
    url: "https://download.redis.io/releases/redis-{{version}}.tar.gz"
    version: "7.2.0"
    build_system: make
    checksum: "sha256:abc123..."
    build_args:
      - "-j4"
    install_prefix: "/usr/local"
```

**Provider Action (source.yaml):**
```yaml
actions:
  install:
    steps:
      - name: "Download source"
        command: "wget {{sai_source(0, 'url', 'source')}} -O redis.tar.gz"
      - name: "Verify checksum"
        command: "echo '{{sai_source(0, 'checksum')}}  redis.tar.gz' | sha256sum -c"
      - name: "Extract"
        command: "tar xzf redis.tar.gz"
      - name: "Build"
        command: "cd redis-* && make {{sai_source(0, 'build_args', 'source')}}"
      - name: "Install"
        command: "cd redis-* && make install PREFIX={{sai_source(0, 'install_prefix')}}"
```

**Usage:**
```bash
sai install redis --provider source
```

### Example 3: Binary Download Installation

**Saidata (kubectl.yaml):**
```yaml
version: "0.3"
metadata:
  name: kubectl
  description: "Kubernetes command-line tool"

binaries:
  - name: main
    url: "https://dl.k8s.io/release/v{{version}}/bin/{{platform}}/{{architecture}}/kubectl"
    version: "1.28.0"
    platform: linux
    architecture: amd64
    checksum: "sha256:def456..."
    install_path: "/usr/local/bin"
    executable: "kubectl"
    permissions: "755"
```

**Provider Action (binary.yaml):**
```yaml
actions:
  install:
    steps:
      - name: "Download binary"
        command: "curl -L {{sai_binary(0, 'url', 'binary')}} -o kubectl"
      - name: "Verify checksum"
        command: "echo '{{sai_binary(0, 'checksum')}}  kubectl' | sha256sum -c"
      - name: "Install"
        command: "install -m {{sai_binary(0, 'permissions')}} kubectl {{sai_binary(0, 'install_path')}}/{{sai_binary(0, 'executable')}}"
```

**Usage:**
```bash
sai install kubectl --provider binary
```

### Example 4: Script Installation

**Saidata (docker.yaml):**
```yaml
version: "0.3"
metadata:
  name: docker
  description: "Container platform"

scripts:
  - name: official
    url: "https://get.docker.com"
    interpreter: bash
    checksum: "sha256:ghi789..."
    timeout: 600
    environment:
      CHANNEL: "stable"
```

**Provider Action (script.yaml):**
```yaml
actions:
  install:
    steps:
      - name: "Download script"
        command: "curl -fsSL {{sai_script(0, 'url', 'script')}} -o install.sh"
      - name: "Verify checksum"
        command: "echo '{{sai_script(0, 'checksum')}}  install.sh' | sha256sum -c"
      - name: "Execute"
        command: "CHANNEL={{sai_script(0, 'environment.CHANNEL')}} {{sai_script(0, 'interpreter')}} install.sh"
        timeout: "{{sai_script(0, 'timeout')}}"
```

**Usage:**
```bash
sai install docker --provider script
```

### Example 5: Multi-Method Installation

**Saidata (node.yaml):**
```yaml
version: "0.3"
metadata:
  name: nodejs
  description: "JavaScript runtime"

# Package manager installation
packages:
  - name: nodejs
    package_name: nodejs
    version: "20.0.0"

# Source build option
sources:
  - name: main
    url: "https://nodejs.org/dist/v{{version}}/node-v{{version}}.tar.gz"
    version: "20.0.0"
    build_system: custom
    checksum: "sha256:abc123..."

# Binary download option
binaries:
  - name: main
    url: "https://nodejs.org/dist/v{{version}}/node-v{{version}}-{{platform}}-{{architecture}}.tar.gz"
    version: "20.0.0"
    platform: linux
    architecture: x64
    checksum: "sha256:def456..."

# Script installation option
scripts:
  - name: nvm
    url: "https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh"
    interpreter: bash
    checksum: "sha256:ghi789..."

providers:
  apt:
    packages:
      - name: nodejs
        package_name: nodejs
  brew:
    packages:
      - name: nodejs
        package_name: node
```

**Usage:**
```bash
# Use package manager (fastest)
sai install nodejs --provider apt

# Build from source (most control)
sai install nodejs --provider source

# Download binary (no compilation)
sai install nodejs --provider binary

# Use installation script (automated setup)
sai install nodejs --provider script
```

## See Also

- [sai-apply-command.md](sai-apply-command.md) - Detailed apply command documentation
- [template-engine.md](template-engine.md) - Template engine documentation
- [schema-0.3-guide.md](schema-0.3-guide.md) - Complete schema 0.3 guide
- [examples/](examples/) - Configuration examples
