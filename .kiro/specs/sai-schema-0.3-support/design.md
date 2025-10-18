# Design Document

## Overview

This design document outlines the implementation approach for updating the SAI CLI tool to support the saidata schema version 0.3. The update introduces new installation methods (sources, binaries, scripts), changes the package structure to distinguish between logical names and actual package names, and enhances provider configurations.

**Note**: Backward compatibility with schema 0.2 is not required. All implementation will focus solely on schema 0.3 support.

The design follows a layered approach:
1. **Data Layer**: Update Pydantic models to support new schema fields
2. **Validation Layer**: Update schema validation to use 0.3 schema
3. **Template Layer**: Enhance template engine with new functions and field support
4. **Provider Layer**: Ensure source, binary, and script providers are functional
5. **Testing Layer**: Comprehensive test coverage for new features

## Architecture

### Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        SAI CLI                               │
├─────────────────────────────────────────────────────────────┤
│  sai/cli/main.py - Command-line interface                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Core Components                            │
├─────────────────────────────────────────────────────────────┤
│  sai/core/saidata_loader.py - Load & validate saidata       │
│  sai/core/action_executor.py - Execute provider actions     │
│  sai/core/execution_engine.py - Orchestrate execution       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Data Models (0.2)                          │
├─────────────────────────────────────────────────────────────┤
│  sai/models/saidata.py - SaiData, Package, Service, etc.    │
│  - Package: name, version, alternatives, ...                │
│  - No package_name field                                    │
│  - No Source, Binary, Script models                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                Template Engine (0.2)                         │
├─────────────────────────────────────────────────────────────┤
│  sai/providers/template_engine.py                           │
│  - sai_package(context, provider, index) -> name            │
│  - No field parameter support                               │
│  - No sai_source, sai_binary, sai_script functions          │
└─────────────────────────────────────────────────────────────┘


### Architecture with Schema 0.3

```
┌─────────────────────────────────────────────────────────────┐
│                        SAI CLI                               │
├─────────────────────────────────────────────────────────────┤
│  sai/cli/main.py - Command-line interface (no changes)      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Core Components                            │
├─────────────────────────────────────────────────────────────┤
│  sai/core/saidata_loader.py                                 │
│    - Update schema path to saidata-0.3-schema.json          │
│    - Add validation for new fields                          │
│  sai/core/action_executor.py (no changes)                   │
│  sai/core/execution_engine.py (no changes)                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Data Models (0.3)                          │
├─────────────────────────────────────────────────────────────┤
│  sai/models/saidata.py                                      │
│  - Package: name, package_name (NEW), version, ...          │
│  - Source (NEW): name, url, build_system, ...               │
│  - Binary (NEW): name, url, platform, architecture, ...     │
│  - Script (NEW): name, url, interpreter, checksum, ...      │
│  - ProviderConfig: add sources, binaries, scripts           │
│  - Repository: add sources, binaries, scripts               │
│  - SaiData: add sources, binaries, scripts                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                Template Engine (0.3)                         │
├─────────────────────────────────────────────────────────────┤
│  sai/providers/template_engine.py                           │
│  - sai_package(context, index, field, provider) (UPDATED)   │
│    - Add field parameter (default: 'package_name')          │
│    - Support 'name' and 'package_name' fields               │
│  - sai_source(context, index, field, provider) (NEW)        │
│  - sai_binary(context, index, field, provider) (NEW)        │
│  - sai_script(context, index, field, provider) (NEW)        │
│  - Update context builder to include new arrays             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                Provider YAML Files                           │
├─────────────────────────────────────────────────────────────┤
│  providers/*.yaml - Updated to use new function signature   │
│  - sai_package('*', 'package_name', 'apt')                  │
│  - sai_package(0, 'package_name', 'apt')                    │
│  providers/source.yaml - Source build provider              │
│  providers/binary.yaml - Binary download provider           │
│  providers/script.yaml - Script installation provider       │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Data Models (sai/models/saidata.py)

#### Package Model

```python
class Package(BaseModel):
    """Package definition."""
    
    name: str  # Logical name for cross-referencing
    package_name: str  # Actual package name used by package managers
    version: Optional[str] = None
    alternatives: Optional[List[str]] = None
    install_options: Optional[str] = None
    repository: Optional[str] = None
    checksum: Optional[str] = None
    signature: Optional[str] = None
    download_url: Optional[str] = None
```

**Key Fields:**
- `name`: Logical identifier for cross-referencing (required)
- `package_name`: Actual package name used by package managers (required)
- Both fields are required in schema 0.3

#### New Source Model

```python
class BuildSystem(str, Enum):
    """Build system types."""
    AUTOTOOLS = "autotools"
    CMAKE = "cmake"
    MAKE = "make"
    MESON = "meson"
    NINJA = "ninja"
    CUSTOM = "custom"

class CustomCommands(BaseModel):
    """Custom commands for overriding default behavior."""
    download: Optional[str] = None
    extract: Optional[str] = None
    configure: Optional[str] = None
    build: Optional[str] = None
    install: Optional[str] = None
    uninstall: Optional[str] = None
    validation: Optional[str] = None
    version: Optional[str] = None

class Source(BaseModel):
    """Source build configuration."""
    
    name: str  # Logical name (e.g., 'main', 'stable', 'dev')
    url: str  # Download URL with template support
    build_system: BuildSystem
    version: Optional[str] = None
    build_dir: Optional[str] = None
    source_dir: Optional[str] = None
    install_prefix: Optional[str] = None
    configure_args: Optional[List[str]] = None
    build_args: Optional[List[str]] = None
    install_args: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    checksum: Optional[str] = None
    custom_commands: Optional[CustomCommands] = None
```


#### New Binary Model

```python
class ArchiveConfig(BaseModel):
    """Archive extraction configuration."""
    format: Optional[str] = None  # tar.gz, zip, etc.
    strip_prefix: Optional[str] = None
    extract_path: Optional[str] = None

class Binary(BaseModel):
    """Binary download configuration."""
    
    name: str  # Logical name (e.g., 'main', 'stable')
    url: str  # Download URL with template support
    version: Optional[str] = None
    architecture: Optional[str] = None  # amd64, arm64, etc.
    platform: Optional[str] = None  # linux, darwin, windows
    checksum: Optional[str] = None
    install_path: Optional[str] = None  # Default: /usr/local/bin
    executable: Optional[str] = None
    archive: Optional[ArchiveConfig] = None
    permissions: Optional[str] = None  # Octal format
    custom_commands: Optional[CustomCommands] = None
```

#### New Script Model

```python
class Script(BaseModel):
    """Script installation configuration."""
    
    name: str  # Logical name (e.g., 'official', 'convenience')
    url: str  # Script download URL
    version: Optional[str] = None
    interpreter: Optional[str] = None  # bash, sh, python, etc.
    checksum: Optional[str] = None
    arguments: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    working_dir: Optional[str] = None
    timeout: Optional[int] = None  # Seconds, default 300
    custom_commands: Optional[CustomCommands] = None
```

#### ProviderConfig Model

```python
class ProviderConfig(BaseModel):
    """Provider-specific configuration."""
    
    # Core fields
    prerequisites: Optional[List[str]] = None
    build_commands: Optional[List[str]] = None
    packages: Optional[List[Package]] = None
    package_sources: Optional[List[PackageSource]] = None
    repositories: Optional[List[Repository]] = None
    services: Optional[List[Service]] = None
    files: Optional[List[File]] = None
    directories: Optional[List[Directory]] = None
    commands: Optional[List[Command]] = None
    ports: Optional[List[Port]] = None
    containers: Optional[List[Container]] = None
    
    # Installation method fields
    sources: Optional[List[Source]] = None
    binaries: Optional[List[Binary]] = None
    scripts: Optional[List[Script]] = None
```

#### SaiData Model

```python
class SaiData(BaseModel):
    """Complete SaiData structure."""
    
    version: str = Field(pattern=r"^\d+\.\d+(\.\d+)?$")
    metadata: Metadata
    
    # Core resource arrays
    packages: Optional[List[Package]] = None
    services: Optional[List[Service]] = None
    files: Optional[List[File]] = None
    directories: Optional[List[Directory]] = None
    commands: Optional[List[Command]] = None
    ports: Optional[List[Port]] = None
    containers: Optional[List[Container]] = None
    
    # Installation method arrays
    sources: Optional[List[Source]] = None
    binaries: Optional[List[Binary]] = None
    scripts: Optional[List[Script]] = None
    
    providers: Optional[Dict[str, ProviderConfig]] = None
    compatibility: Optional[Compatibility] = None

    model_config = ConfigDict(use_enum_values=True)
```

### 2. Schema Validation (sai/core/saidata_loader.py)

#### Update Schema Loading

```python
def _load_schema(self) -> None:
    """Load the JSON schema for saidata validation."""
    # Change from saidata-0.2-schema.json to saidata-0.3-schema.json
    schema_path = Path(__file__).parent.parent.parent / "schemas" / "saidata-0.3-schema.json"
    
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            self._schema_cache = json.load(f)
        logger.debug(f"Loaded saidata schema from: {schema_path}")
    except Exception as e:
        logger.error(f"Failed to load saidata schema: {e}")
        # Fallback schema updated for 0.3
        self._schema_cache = {
            "type": "object",
            "properties": {
                "version": {"type": "string"},
                "metadata": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            },
            "required": ["version", "metadata"],
        }
```

#### Add Validation for New Fields

```python
def _validate_packages(
    self, data: Dict[str, Any], errors: List[str], warnings: List[str]
) -> None:
    """Validate packages section."""
    packages = data.get("packages", [])

    if not packages:
        warnings.append("No packages defined")
        return

    for i, package in enumerate(packages):
        if not isinstance(package, dict):
            errors.append(f"Package {i} must be an object")
            continue

        # Schema 0.3 requires both name and package_name
        if not package.get("name"):
            errors.append(f"Package {i} must have a name field")
        
        if not package.get("package_name"):
            errors.append(f"Package {i} must have a package_name field")
```


### 3. Template Engine Updates (sai/providers/template_engine.py)

#### Update Context Builder

```python
def _build_saidata_context(self) -> Dict[str, Any]:
    """Build the saidata section of the context."""
    context = {
        "metadata": self._build_metadata_context(),
    }

    # Core resource collections
    context["packages"] = (
        [self._package_to_dict(pkg) for pkg in self.saidata.packages]
        if self.saidata.packages
        else []
    )
    context["services"] = (
        [self._service_to_dict(svc) for svc in self.saidata.services]
        if self.saidata.services
        else []
    )
    # ... other core collections ...
    
    # Installation method collections
    context["sources"] = (
        [self._source_to_dict(src) for src in self.saidata.sources]
        if self.saidata.sources
        else []
    )
    context["binaries"] = (
        [self._binary_to_dict(bin) for bin in self.saidata.binaries]
        if self.saidata.binaries
        else []
    )
    context["scripts"] = (
        [self._script_to_dict(scr) for scr in self.saidata.scripts]
        if self.saidata.scripts
        else []
    )

    # Add providers section
    if hasattr(self.saidata, "providers") and self.saidata.providers:
        context["providers"] = self._build_providers_context()
    else:
        context["providers"] = {}

    return context
```

#### Add Conversion Methods

```python
def _package_to_dict(self, package) -> Dict[str, Any]:
    """Convert Package model to dictionary."""
    return {
        "name": package.name,
        "package_name": package.package_name,
        "version": package.version,
        "alternatives": package.alternatives or [],
        "install_options": package.install_options,
        "repository": package.repository,
        "checksum": package.checksum,
        "signature": package.signature,
        "download_url": package.download_url,
    }

def _source_to_dict(self, source) -> Dict[str, Any]:
    """Convert Source model to dictionary."""
    return {
        "name": source.name,
        "url": source.url,
        "version": source.version,
        "build_system": source.build_system,
        "build_dir": source.build_dir,
        "source_dir": source.source_dir,
        "install_prefix": source.install_prefix,
        "configure_args": source.configure_args or [],
        "build_args": source.build_args or [],
        "install_args": source.install_args or [],
        "prerequisites": source.prerequisites or [],
        "environment": source.environment or {},
        "checksum": source.checksum,
        "custom_commands": source.custom_commands.__dict__ if source.custom_commands else {},
    }

def _binary_to_dict(self, binary) -> Dict[str, Any]:
    """Convert Binary model to dictionary."""
    return {
        "name": binary.name,
        "url": binary.url,
        "version": binary.version,
        "architecture": binary.architecture,
        "platform": binary.platform,
        "checksum": binary.checksum,
        "install_path": binary.install_path,
        "executable": binary.executable,
        "archive": binary.archive.__dict__ if binary.archive else {},
        "permissions": binary.permissions,
        "custom_commands": binary.custom_commands.__dict__ if binary.custom_commands else {},
    }

def _script_to_dict(self, script) -> Dict[str, Any]:
    """Convert Script model to dictionary."""
    return {
        "name": script.name,
        "url": script.url,
        "version": script.version,
        "interpreter": script.interpreter,
        "checksum": script.checksum,
        "arguments": script.arguments or [],
        "environment": script.environment or {},
        "working_dir": script.working_dir,
        "timeout": script.timeout,
        "custom_commands": script.custom_commands.__dict__ if script.custom_commands else {},
    }
```

#### Update sai_package Function

```python
def _sai_package_global(
    self, 
    saidata_context: Dict[str, Any], 
    index_or_wildcard: Union[int, str] = 0,
    field: str = "package_name",  # NEW: default to package_name
    provider_name: Optional[str] = None
) -> str:
    """Global function to get package field with provider fallback.
    
    Args:
        saidata_context: The saidata context dictionary
        index_or_wildcard: Index (int) or '*' for all packages
        field: Field to extract ('name', 'package_name', 'version', etc.)
        provider_name: Provider name for provider-specific lookup
    
    Returns:
        Package field value(s) as string
    
    Usage:
        {{sai_package(saidata, 0, 'package_name', 'apt')}}  # First package name for apt
        {{sai_package(saidata, '*', 'package_name', 'apt')}} # All package names for apt
        {{sai_package(saidata, 0, 'name')}}                  # Logical name
    """
    # Handle case where saidata_context is the actual SaiData object
    if hasattr(saidata_context, "metadata"):
        context_builder = SaidataContextBuilder(saidata_context)
        saidata_context = context_builder.build_context()
    
    # Determine if we want all packages or a single one
    if index_or_wildcard == '*':
        index = -1  # Signal to return all
    else:
        index = int(index_or_wildcard)
    
    return self._sai_lookup_filter(
        saidata_context, 
        "packages", 
        field,  # Use the specified field
        index, 
        provider_name
    )
```


#### Add New Template Functions

```python
def _sai_source_global(
    self,
    saidata_context: Dict[str, Any],
    index: int = 0,
    field: str = "url",
    provider_name: Optional[str] = None
) -> str:
    """Global function to get source configuration field.
    
    Args:
        saidata_context: The saidata context dictionary
        index: Index of source to retrieve
        field: Field to extract ('name', 'url', 'version', 'build_system', etc.)
        provider_name: Provider name for provider-specific lookup
    
    Returns:
        Source field value as string
    
    Usage:
        {{sai_source(saidata, 0, 'url')}}           # First source URL
        {{sai_source(saidata, 0, 'version')}}       # First source version
        {{sai_source(saidata, 0, 'url', 'source')}} # Provider-specific source URL
    """
    if hasattr(saidata_context, "metadata"):
        context_builder = SaidataContextBuilder(saidata_context)
        saidata_context = context_builder.build_context()
    
    return self._sai_lookup_filter(
        saidata_context,
        "sources",
        field,
        index,
        provider_name
    )

def _sai_binary_global(
    self,
    saidata_context: Dict[str, Any],
    index: int = 0,
    field: str = "url",
    provider_name: Optional[str] = None
) -> str:
    """Global function to get binary configuration field.
    
    Args:
        saidata_context: The saidata context dictionary
        index: Index of binary to retrieve
        field: Field to extract ('name', 'url', 'version', 'platform', etc.)
        provider_name: Provider name for provider-specific lookup
    
    Returns:
        Binary field value as string
    
    Usage:
        {{sai_binary(saidata, 0, 'url')}}            # First binary URL
        {{sai_binary(saidata, 0, 'platform')}}       # First binary platform
        {{sai_binary(saidata, 0, 'url', 'binary')}}  # Provider-specific binary URL
    """
    if hasattr(saidata_context, "metadata"):
        context_builder = SaidataContextBuilder(saidata_context)
        saidata_context = context_builder.build_context()
    
    return self._sai_lookup_filter(
        saidata_context,
        "binaries",
        field,
        index,
        provider_name
    )

def _sai_script_global(
    self,
    saidata_context: Dict[str, Any],
    index: int = 0,
    field: str = "url",
    provider_name: Optional[str] = None
) -> str:
    """Global function to get script configuration field.
    
    Args:
        saidata_context: The saidata context dictionary
        index: Index of script to retrieve
        field: Field to extract ('name', 'url', 'interpreter', etc.)
        provider_name: Provider name for provider-specific lookup
    
    Returns:
        Script field value as string
    
    Usage:
        {{sai_script(saidata, 0, 'url')}}            # First script URL
        {{sai_script(saidata, 0, 'interpreter')}}    # First script interpreter
        {{sai_script(saidata, 0, 'url', 'script')}}  # Provider-specific script URL
    """
    if hasattr(saidata_context, "metadata"):
        context_builder = SaidataContextBuilder(saidata_context)
        saidata_context = context_builder.build_context()
    
    return self._sai_lookup_filter(
        saidata_context,
        "scripts",
        field,
        index,
        provider_name
    )
```

#### Register New Functions

```python
def __init__(self):
    """Initialize the template engine."""
    # ... existing initialization ...
    
    # Add global functions for easier template access
    self.env.globals["sai_packages"] = self._sai_packages_global
    self.env.globals["sai_package"] = self._sai_package_global
    self.env.globals["sai_service"] = self._sai_service_global
    self.env.globals["sai_file"] = self._sai_file_global
    self.env.globals["sai_port"] = self._sai_port_global
    self.env.globals["sai_command"] = self._sai_command_global
    
    # Installation method functions
    self.env.globals["sai_source"] = self._sai_source_global
    self.env.globals["sai_binary"] = self._sai_binary_global
    self.env.globals["sai_script"] = self._sai_script_global
    
    logger.debug("Template engine initialized")
```

### 4. Provider YAML Updates

The provider YAML files have already been updated in commit 9fb7a22. The function signature is:

**Example:**
```yaml
command: "apt-get install -y {{sai_package('*', 'package_name', 'apt')}}"
```

**Function Signature:**
```
sai_package(index_or_wildcard, field, provider_name)
```

Where:
- `index_or_wildcard`: `0`, `1`, `2`, ... or `'*'` for all
- `field`: `'package_name'`, `'name'`, `'version'`, etc.
- `provider_name`: `'apt'`, `'brew'`, `'dnf'`, etc.

## Data Models

### Package Name vs Logical Name

**Package Structure:**
```yaml
packages:
  - name: nginx          # Logical name for cross-referencing
    package_name: nginx  # Actual package name for package managers
```

**Provider-Specific Override:**
```yaml
providers:
  brew:
    packages:
      - name: nginx
        package_name: nginx-full  # Different package name for brew
```

This allows the same logical name to map to different actual package names across providers.


### Installation Method Models

#### Source Build

```yaml
sources:
  - name: main
    url: "https://nginx.org/download/nginx-{{version}}.tar.gz"
    version: "1.24.0"
    build_system: autotools
    configure_args:
      - "--with-http_ssl_module"
      - "--with-http_v2_module"
    prerequisites:
      - build-essential
      - libssl-dev
    checksum: "sha256:abc123..."
```

#### Binary Download

```yaml
binaries:
  - name: main
    url: "https://releases.example.com/{{version}}/app_{{version}}_{{platform}}_{{architecture}}.zip"
    version: "1.5.0"
    checksum: "sha256:def456..."
    install_path: "/usr/local/bin"
    executable: "app"
    archive:
      format: zip
      strip_prefix: "app-1.5.0/"
```

#### Script Installation

```yaml
scripts:
  - name: official
    url: "https://get.example.com/install.sh"
    checksum: "sha256:ghi789..."
    interpreter: bash
    timeout: 600
    arguments:
      - "--channel"
      - "stable"
```

## Error Handling

### Schema Validation Errors

When loading a saidata file with missing required fields:

```
Error: Saidata validation failed for nginx:
  - Package 0 must have a package_name field
  
Suggestion: Ensure all packages have both 'name' and 'package_name' fields:

packages:
  - name: nginx
    package_name: nginx
```

### Template Resolution Errors

When template function has incorrect syntax:

```
Error: Template resolution failed for '{{sai_package(0, 'invalid_field', 'apt')}}':
  Field 'invalid_field' not found in package

Valid fields: name, package_name, version, alternatives, install_options, 
              repository, checksum, signature, download_url
```

### Missing Field Errors

When accessing non-existent field:

```
Error: Template resolution failed for '{{sai_package(0, 'invalid_field', 'apt')}}':
  Field 'invalid_field' not found in package

Valid fields: name, package_name, version, alternatives, install_options, 
              repository, checksum, signature, download_url
```

## Testing Strategy

### Unit Tests

1. **Model Tests** (`tests/sai/models/test_saidata_03.py`)
   - Test Package model with name and package_name
   - Test Source, Binary, Script models
   - Test ProviderConfig with new fields
   - Test SaiData with new top-level arrays

2. **Loader Tests** (`tests/sai/core/test_saidata_loader_03.py`)
   - Test loading 0.3 schema files
   - Test validation with new fields
   - Test error messages for missing fields
   - Test backward compatibility warnings

3. **Template Engine Tests** (`tests/sai/providers/test_template_engine_03.py`)
   - Test sai_package with field parameter
   - Test sai_source, sai_binary, sai_script functions
   - Test context builder with new arrays
   - Test provider-specific lookups

### Integration Tests

1. **End-to-End Tests** (`tests/integration/test_sai_03_integration.py`)
   - Test loading 0.3 saidata and executing actions
   - Test source provider with real build
   - Test binary provider with download and install
   - Test script provider with execution

2. **Provider Tests** (`tests/sai/providers/test_providers_03.py`)
   - Test apt provider with new function signature
   - Test brew provider with new function signature
   - Test source, binary, script providers

### Test Data

Create test saidata files in `tests/fixtures/`:

1. `nginx.yaml` - Complete example with all features
2. `simple-package.yaml` - Minimal package example
3. `source-build.yaml` - Source build example
4. `binary-download.yaml` - Binary download example
5. `script-install.yaml` - Script installation example

## Saidata File Examples

### Basic Package Definition
```yaml
version: "0.3"
metadata:
  name: nginx

packages:
  - name: nginx
    package_name: nginx
```

### With Installation Methods
```yaml
version: "0.3"
metadata:
  name: nginx

packages:
  - name: nginx
    package_name: nginx

# Source build configuration
sources:
  - name: main
    url: "https://nginx.org/download/nginx-{{version}}.tar.gz"
    build_system: autotools

# Binary download configuration
binaries:
  - name: main
    url: "https://releases.example.com/{{version}}/app_{{platform}}_{{architecture}}.zip"

# Script installation configuration
scripts:
  - name: official
    url: "https://get.example.com/install.sh"
```

### Provider YAML Template Functions
```yaml
# Package installation
command: "apt-get install -y {{sai_package('*', 'package_name', 'apt')}}"

# Source builds
command: "wget {{sai_source(0, 'url', 'source')}}"

# Binary downloads
command: "curl -L {{sai_binary(0, 'url', 'binary')}} -o app.zip"

# Script installations
command: "bash {{sai_script(0, 'url', 'script')}}"
```

## Implementation Phases

### Phase 1: Data Models (Priority: High)
- Update Package model with package_name
- Add Source, Binary, Script models
- Add CustomCommands, ArchiveConfig models
- Update ProviderConfig and SaiData models
- Add BuildSystem enum

### Phase 2: Schema Validation (Priority: High)
- Update schema path to 0.3
- Add validation for new fields
- Update error messages
- Test validation with 0.3 files

### Phase 3: Template Engine (Priority: High)
- Update sai_package function signature
- Add sai_source, sai_binary, sai_script functions
- Update context builder
- Add conversion methods for new models
- Register new functions

### Phase 4: Provider Support (Priority: Medium)
- Verify source provider works
- Verify binary provider works
- Verify script provider works
- Test with real saidata files

### Phase 5: Testing (Priority: High)
- Write unit tests for models
- Write unit tests for loader
- Write unit tests for template engine
- Write integration tests
- Create test fixtures

### Phase 6: Documentation (Priority: Medium)
- Update README with 0.3 changes
- Create migration guide
- Update CLI documentation
- Add examples

## Dependencies

- **pydantic**: For data model validation
- **jsonschema**: For schema validation
- **jinja2**: For template resolution
- **PyYAML**: For YAML parsing

No new dependencies required.

## Performance Considerations

1. **Schema Validation**: Minimal impact, same validation approach
2. **Template Resolution**: Slight increase due to new functions, but negligible
3. **Memory Usage**: Minimal increase from new model fields
4. **Loading Time**: No significant impact on saidata loading performance

## Security Considerations

1. **Checksum Validation**: New checksum fields for sources, binaries, scripts
2. **Script Execution**: Timeout limits and checksum verification
3. **URL Templating**: Validate template variables to prevent injection
4. **File Permissions**: Validate octal format for binary permissions

## Rollout Plan

1. **Development**: Implement all phases in feature branch
2. **Testing**: Comprehensive test coverage
3. **Documentation**: Update all documentation
4. **Release**: Version 0.3.0 with schema 0.3 support
5. **Validation**: Ensure all saidata files use schema 0.3
