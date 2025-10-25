# Design Document: Provider Version Refresh Enhancement

## Overview

This document describes the architectural design for enhancing the `saigen refresh-versions` command to support OS-specific saidata files and comprehensive repository configurations. The enhancement enables accurate package name and version updates from package providers across different operating system versions without LLM inference.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLI Command Layer                            │
│  refresh-versions [file/dir] [--all-variants] [--create-missing]│
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Refresh Orchestration Layer                     │
│  • File/Directory Detection                                      │
│  • OS Context Extraction                                         │
│  • Multi-file Processing                                         │
│  • Result Aggregation                                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   OS Path   │  │  Codename   │  │ Repository  │
│   Parser    │  │  Resolver   │  │  Selector   │
└─────────────┘  └─────────────┘  └─────────────┘
         │               │               │
         └───────────────┼───────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Repository Manager Layer                        │
│  • Repository Configuration Loading                              │
│  • Package Query (Bulk Download & API-based)                     │
│  • Cache Management                                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Provider-Specific Repository Configs                │
│  apt.yaml | dnf.yaml | brew.yaml | choco.yaml | winget.yaml    │
│  Each contains: endpoints, version_mapping, parsing rules       │
└─────────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
User Input (file/directory path)
    │
    ▼
[Path Parser] → Extract OS info (os, version, is_default)
    │
    ▼
[Codename Resolver] → Map version to codename using repository config
    │
    ▼
[Repository Selector] → Build repository name: {provider}-{os}-{codename}
    │
    ▼
[Repository Manager] → Query package info (name, version)
    │
    ▼
[Package Comparator] → Compare with current saidata
    │
    ▼
[Saidata Updater] → Update package_name and version
    │
    ▼
[Validator] → Validate against schema
    │
    ▼
[File Writer] → Save updated saidata
```

## Components and Interfaces

### 1. Path Parser (`saigen/utils/saidata_path.py`)

**Purpose:** Extract OS and version information from saidata file paths.

**Interface:**
```python
def extract_os_info(file_path: Path) -> Dict[str, Optional[str]]:
    """
    Extract OS information from saidata file path.
    
    Args:
        file_path: Path to saidata file
        
    Returns:
        Dict with keys:
        - 'os': OS name (ubuntu, debian, fedora, etc.) or None
        - 'version': OS version (22.04, 11, 39, etc.) or None
        - 'is_default': True if default.yaml, False otherwise
        
    Examples:
        ng/nginx/ubuntu/22.04.yaml → {'os': 'ubuntu', 'version': '22.04', 'is_default': False}
        ng/nginx/default.yaml → {'os': None, 'version': None, 'is_default': True}
    """
```

**Implementation Details:**
- Use regex pattern to match `{prefix}/{software}/{os}/{version}.yaml`
- Detect `default.yaml` as special case
- Handle edge cases: missing directories, invalid paths
- Return structured data for downstream components

### 2. Codename Resolver (`saigen/repositories/codename_resolver.py`)

**Purpose:** Resolve OS version to codename using repository configuration.

**Interface:**
```python
def resolve_codename(repository_info: RepositoryInfo, version: str) -> Optional[str]:
    """
    Resolve OS version to codename from repository's version_mapping.
    
    Args:
        repository_info: Repository configuration with version_mapping
        version: OS version (e.g., "22.04", "11", "39")
        
    Returns:
        Codename string (e.g., "jammy", "bullseye", "f39") or None if not found
    """

def resolve_repository_name(
    provider: str,
    os: Optional[str],
    version: Optional[str],
    repositories: Dict[str, RepositoryInfo]
) -> str:
    """
    Build repository name from provider, OS, and version.
    
    Args:
        provider: Provider name (apt, dnf, brew, etc.)
        os: OS name (ubuntu, debian, etc.) or None
        version: OS version (e.g., "22.04", "11") or None
        repositories: Available repository configurations
        
    Returns:
        Repository name (e.g., "apt-ubuntu-jammy", "apt", "brew-macos")
        
    Logic:
        1. If os and version provided:
           - Iterate through all repositories
           - Find repos matching: type==provider AND distribution contains os
           - Check each repo's version_mapping for the given version
           - If found, extract codename and return "{provider}-{os}-{codename}"
        2. If only provider: return provider name
        3. If no match: return provider name (fallback)
        
    Example:
        provider="apt", os="ubuntu", version="22.04"
        → Finds repo with version_mapping: {"22.04": "jammy"}
        → Returns "apt-ubuntu-jammy"
    """
```

**Implementation Details:**
- Load version_mapping from RepositoryInfo
- Perform lookup: version → codename
- Handle missing mappings gracefully (log warning, return None)
- Cache resolved mappings for performance

### 3. Repository Configuration Model Updates

**Update `saigen/models/repository.py`:**

```python
class RepositoryInfo(BaseModel):
    """Repository information and metadata."""
    
    name: str
    url: Optional[str] = None
    type: str  # apt, dnf, brew, winget, etc.
    platform: str  # linux, macos, windows
    architecture: Optional[List[str]] = None
    description: Optional[str] = None
    maintainer: Optional[str] = None
    last_sync: Optional[datetime] = None
    package_count: Optional[int] = None
    enabled: bool = True
    priority: int = 1
    
    # NEW FIELDS
    version_mapping: Optional[Dict[str, str]] = None  # version → codename
    eol: bool = False  # End-of-life status
    query_type: str = "bulk_download"  # or "api"
```

### 4. Repository Configuration Files

**New Structure:**

```
saigen/repositories/configs/
├── apt.yaml          # All apt-based repositories
├── dnf.yaml          # All dnf/yum-based repositories
├── brew.yaml         # macOS Homebrew
├── choco.yaml        # Windows Chocolatey
├── winget.yaml       # Windows winget
├── zypper.yaml       # SUSE-based
├── pacman.yaml       # Arch-based
├── apk.yaml          # Alpine
├── emerge.yaml       # Gentoo
├── npm.yaml          # Node.js packages
├── pip.yaml          # Python packages
├── cargo.yaml        # Rust packages
└── ...
```

**Example: apt.yaml**

```yaml
version: "1.0"
repositories:
  # Ubuntu 20.04 (Focal) repository
  - name: "apt-ubuntu-focal"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    version_mapping:
      "20.04": "focal"  # Single mapping: this repo is for Ubuntu 20.04 only
    endpoints:
      packages: "http://archive.ubuntu.com/ubuntu/dists/focal/main/binary-{arch}/Packages.gz"
    # ... rest of config
    
  # Ubuntu 22.04 (Jammy) repository - separate repo entry
  - name: "apt-ubuntu-jammy"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    version_mapping:
      "22.04": "jammy"  # Single mapping: this repo is for Ubuntu 22.04 only
    endpoints:
      packages: "http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-{arch}/Packages.gz"
    # ... rest of config
    
  # Ubuntu 24.04 (Noble) repository - separate repo entry
  - name: "apt-ubuntu-noble"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    version_mapping:
      "24.04": "noble"  # Single mapping: this repo is for Ubuntu 24.04 only
    endpoints:
      packages: "http://archive.ubuntu.com/ubuntu/dists/noble/main/binary-{arch}/Packages.gz"
    # ... rest of config
    
  # Debian 11 (Bullseye) repository - separate repo entry
  - name: "apt-debian-bullseye"
    type: "apt"
    platform: "linux"
    distribution: ["debian"]
    version_mapping:
      "11": "bullseye"  # Single mapping: this repo is for Debian 11 only
    endpoints:
      packages: "http://deb.debian.org/debian/dists/bullseye/main/binary-{arch}/Packages.gz"
    # ... rest of config
```

**Key Point:** Each repository configuration represents ONE specific OS version. The `version_mapping` field contains a single entry that maps that OS version to its codename. This allows the codename resolver to look up the codename when given an OS and version.

### 5. Enhanced Refresh Command

**Modified `saigen/cli/commands/refresh_versions.py`:**

**New CLI Options:**
```python
@click.option("--all-variants", is_flag=True, 
              help="Process all saidata files in directory (default.yaml + OS-specific)")
@click.option("--skip-default", is_flag=True,
              help="Skip default.yaml when processing directory")
@click.option("--create-missing", is_flag=True,
              help="Create OS-specific files that don't exist")
@click.option("--interactive", is_flag=True,
              help="Show diff and prompt before applying changes")
```

**Enhanced Processing Flow:**

```python
def refresh_versions(ctx, saidata_file, ...):
    # 1. Detect if input is file or directory
    if saidata_file.is_dir():
        if not all_variants:
            raise click.ClickException("Use --all-variants for directory processing")
        files_to_process = _scan_directory(saidata_file, skip_default, create_missing)
    else:
        files_to_process = [saidata_file]
    
    # 2. Process each file
    results = []
    for file_path in files_to_process:
        # Extract OS context
        os_info = extract_os_info(file_path)
        
        # Load saidata
        saidata = _load_saidata(file_path)
        
        # Refresh versions with OS context
        result = await _refresh_versions(
            saidata=saidata,
            os_context=os_info,
            ...
        )
        
        results.append((file_path, result))
    
    # 3. Display results
    if len(results) > 1:
        _display_multi_file_results(results)
    else:
        _display_results(results[0][1])
```

### 6. Package Query Enhancement

**Modified `_query_package_version()`:**

```python
async def _query_package_version(
    repo_manager: RepositoryManager,
    package_name: str,
    provider: str,
    os_context: Optional[Dict[str, str]],  # NEW
    use_cache: bool,
    verbose: bool,
) -> Optional[Dict[str, str]]:  # Returns {'name': str, 'version': str}
    """
    Query repository for package name and version.
    
    Args:
        os_context: Dict with 'os' and 'version' keys, or None for default
        
    Returns:
        Dict with 'name' and 'version', or None if not found
    """
    # Resolve repository name based on OS context
    if os_context and os_context['os'] and os_context['version']:
        repo_name = resolve_repository_name(
            provider=provider,
            os=os_context['os'],
            version=os_context['version'],
            repositories=repo_manager.repositories
        )
    else:
        repo_name = provider
    
    # Check if repository exists
    if not repo_manager.has_repository(repo_name):
        if verbose:
            click.echo(f"  Warning: Repository {repo_name} not configured")
        return None
    
    # Query repository
    search_result = await repo_manager.search_packages(
        query=package_name,
        repository_names=[repo_name]
    )
    
    if search_result.packages:
        pkg = search_result.packages[0]  # Exact match logic
        return {
            'name': pkg.name,
            'version': pkg.version
        }
    
    return None
```

### 7. Package Update Logic

**Modified `_update_package_version()`:**

```python
def _update_package_version(
    saidata: SaiData,
    pkg_info: Dict[str, Any],
    new_version: str,
    new_package_name: Optional[str] = None  # NEW
) -> None:
    """
    Update package version and optionally package name in saidata.
    
    Args:
        new_package_name: New package name if it differs, or None to keep current
    """
    pkg_obj = pkg_info["object"]
    pkg_obj.version = new_version
    
    if new_package_name and new_package_name != pkg_obj.package_name:
        pkg_obj.package_name = new_package_name
        # Note: pkg_obj.name (logical name) is never changed
```

### 8. OS-Specific File Creation

**New Function:**

```python
def _create_os_specific_file(
    software_dir: Path,
    os: str,
    version: str,
    default_saidata: SaiData,
    repo_manager: RepositoryManager,
    providers: List[str],
    verbose: bool
) -> None:
    """
    Create OS-specific saidata file with minimal overrides.
    
    Args:
        software_dir: Base directory (e.g., ng/nginx/)
        os: OS name (ubuntu, debian, etc.)
        version: OS version (22.04, 11, etc.)
        default_saidata: Loaded default.yaml for comparison
        repo_manager: Repository manager for queries
        providers: List of providers to query
        
    Creates:
        {software_dir}/{os}/{version}.yaml with minimal structure:
        
        version: "0.3"
        providers:
          apt:
            packages:
              - name: nginx
                package_name: nginx-full  # Only if differs from default
                version: "1.18.0"  # Always included
    """
    # 1. Create directory structure
    os_dir = software_dir / os
    os_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Query repositories for OS-specific data
    os_context = {'os': os, 'version': version, 'is_default': False}
    provider_data = {}
    
    for provider in providers:
        packages = []
        for pkg in default_saidata.packages:
            result = await _query_package_version(
                repo_manager=repo_manager,
                package_name=pkg.package_name,
                provider=provider,
                os_context=os_context,
                use_cache=True,
                verbose=verbose
            )
            
            if result:
                pkg_data = {'name': pkg.name, 'version': result['version']}
                
                # Only include package_name if it differs
                if result['name'] != pkg.package_name:
                    pkg_data['package_name'] = result['name']
                
                packages.append(pkg_data)
        
        if packages:
            provider_data[provider] = {'packages': packages}
    
    # 3. Build minimal YAML structure
    os_specific_data = {
        'version': '0.3',
        'providers': provider_data
    }
    
    # 4. Write file
    output_path = os_dir / f"{version}.yaml"
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(os_specific_data, f, default_flow_style=False, sort_keys=False, indent=2)
    
    if verbose:
        click.echo(f"Created OS-specific file: {output_path}")
```

### 9. Override Validation

**New Module: `saigen/core/override_validator.py`:**

```python
def compare_saidata_files(
    os_specific_path: Path,
    default_path: Path
) -> Dict[str, List[str]]:
    """
    Compare OS-specific saidata with default.yaml to find duplicates.
    
    Returns:
        Dict with:
        - 'identical_fields': List of field paths that are identical
        - 'different_fields': List of field paths that differ
        - 'os_only_fields': List of fields only in OS-specific file
    """
    os_data = _load_saidata(os_specific_path)
    default_data = _load_saidata(default_path)
    
    identical = []
    different = []
    os_only = []
    
    # Deep comparison logic
    _compare_recursive(os_data, default_data, "", identical, different, os_only)
    
    return {
        'identical_fields': identical,
        'different_fields': different,
        'os_only_fields': os_only
    }

def remove_duplicate_fields(
    os_specific_path: Path,
    identical_fields: List[str],
    backup: bool = True
) -> None:
    """
    Remove fields from OS-specific file that are identical to default.yaml.
    """
    if backup:
        _create_backup(os_specific_path)
    
    # Load, remove fields, save
    # Implementation details...
```

## Data Models

### Repository Configuration Schema Updates

The repository configuration schema already exists at `schemas/repository-config-schema.json` and needs to be updated to support the new fields.

**Required Schema Changes:**

Add three new optional properties to the `Repository` definition in `schemas/repository-config-schema.json`:

```json
{
  "definitions": {
    "Repository": {
      "type": "object",
      "properties": {
        // ... existing properties ...
        
        // NEW PROPERTIES TO ADD:
        "version_mapping": {
          "type": "object",
          "description": "Maps OS version string to distribution codename for this specific repository",
          "patternProperties": {
            "^[0-9.]+$": {
              "type": "string",
              "pattern": "^[a-z0-9-]+$"
            }
          },
          "additionalProperties": false,
          "examples": [
            {"22.04": "jammy"},
            {"11": "bullseye"},
            {"39": "f39"}
          ]
        },
        "eol": {
          "type": "boolean",
          "description": "Indicates if this is an end-of-life OS version/repository",
          "default": false
        },
        "query_type": {
          "type": "string",
          "description": "Method for querying packages from this repository",
          "enum": ["bulk_download", "api"],
          "default": "bulk_download"
        }
      },
      "required": [
        "name",
        "type",
        "platform",
        "endpoints",
        "parsing"
      ],
      "additionalProperties": false
    }
  }
}
```

**Field Specifications:**

1. **version_mapping** (optional)
   - Type: Object with string keys and string values
   - Contains: Single key-value pair mapping this repository's OS version to its codename
   - Example: `{"22.04": "jammy"}` for apt-ubuntu-jammy repository
   - Pattern: Keys must match `^[0-9.]+$`, values must match `^[a-z0-9-]+$`
   - Purpose: Allows codename resolver to find the codename for a given OS version
   - Note: Each repository has ONE version mapping since each repo is version-specific

2. **eol** (optional, default: false)
   - Type: Boolean
   - Purpose: Marks end-of-life repositories for informational warnings
   - When true: Log informational message when querying this repository

3. **query_type** (optional, default: "bulk_download")
   - Type: String enum
   - Values: "bulk_download" or "api"
   - Purpose: Determines how packages are queried
     - "bulk_download": Download full package list (apt, dnf, etc.)
     - "api": Query per-package via API (npm, pip, cargo, winget, etc.)

**Validation Implementation:**

The schema validation will be handled automatically by the JSON schema validator when loading repository configurations. Additional runtime validation can be added:

```python
# In saigen/repositories/universal_manager.py

def _validate_version_mapping(version_mapping: Dict[str, str], repo_name: str) -> None:
    """Validate version_mapping field structure."""
    if not isinstance(version_mapping, dict):
        raise ValueError(f"Repository {repo_name}: version_mapping must be a dictionary")
    
    for version, codename in version_mapping.items():
        if not isinstance(version, str) or not isinstance(codename, str):
            raise ValueError(
                f"Repository {repo_name}: version_mapping entries must be string:string, "
                f"got {version}:{codename}"
            )
        if not re.match(r'^[0-9.]+$', version):
            raise ValueError(
                f"Repository {repo_name}: version_mapping key '{version}' "
                f"must match pattern ^[0-9.]+$"
            )
        if not re.match(r'^[a-z0-9-]+$', codename):
            raise ValueError(
                f"Repository {repo_name}: version_mapping value '{codename}' "
                f"must match pattern ^[a-z0-9-]+$"
            )
```

**Migration Notes:**

- Existing repository configurations without these fields will continue to work (all fields are optional)
- The schema change is backward compatible
- Repositories without `version_mapping` will not support OS-specific queries
- Default values: `eol=false`, `query_type="bulk_download"`

### Saidata Structure

**Default.yaml (Upstream/Generic):**
```yaml
version: "0.3"
metadata:
  name: "nginx"
  version: "1.24.0"  # Upstream version

packages:
  - name: "nginx"
    package_name: "nginx"  # Common name across OSes
    version: "1.24.0"  # Upstream version
```

**OS-Specific (ubuntu/22.04.yaml):**
```yaml
version: "0.3"
providers:
  apt:
    packages:
      - name: "nginx"
        package_name: "nginx-full"  # Ubuntu-specific package name
        version: "1.18.0"  # Ubuntu 22.04 packaged version
```

**Merge Result (when loaded on Ubuntu 22.04):**
```yaml
version: "0.3"
metadata:
  name: "nginx"
  version: "1.24.0"

packages:
  - name: "nginx"
    package_name: "nginx-full"  # From ubuntu/22.04.yaml
    version: "1.18.0"  # From ubuntu/22.04.yaml
```

### Repository Configuration Data Model

```yaml
version: "1.0"
repositories:
  - name: "apt-ubuntu-jammy"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    architecture: ["amd64", "arm64", "armhf"]
    
    # NEW: Version to codename mapping
    version_mapping:
      "22.04": "jammy"
    
    # NEW: EOL status
    eol: false
    
    # NEW: Query type
    query_type: "bulk_download"  # or "api"
    
    endpoints:
      packages: "http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-{arch}/Packages.gz"
      search: "https://packages.ubuntu.com/search?keywords={query}"
    
    parsing:
      format: "debian_packages"
      compression: "gzip"
      # ... rest of parsing config
    
    cache:
      ttl_hours: 24
      max_size_mb: 100
    
    limits:
      requests_per_minute: 60
      timeout_seconds: 300
    
    metadata:
      description: "Ubuntu 22.04 (Jammy) Main Repository"
      maintainer: "Ubuntu"
      priority: 90
      enabled: true
      official: true
```

## Error Handling

### Error Scenarios and Handling

1. **Missing Repository Configuration**
   - Detection: Repository name not found in loaded configs
   - Handling: Log warning, add to result.warnings, continue processing
   - User Message: "Repository apt-ubuntu-noble not configured. Skipping."

2. **Package Not Found in Repository**
   - Detection: search_packages returns empty list
   - Handling: Log warning, leave package unchanged, continue
   - User Message: "Package 'nginx' not found in apt-ubuntu-jammy"

3. **Invalid Saidata File**
   - Detection: YAML parsing error or schema validation failure
   - Handling: Skip file, log error, continue with other files
   - User Message: "Invalid saidata: {file_path}. Error: {details}"

4. **Network/Repository Access Errors**
   - Detection: RepositoryError exception
   - Handling: Retry with exponential backoff, then skip
   - User Message: "Failed to access repository: {repo_name}. Retrying..."

5. **Schema Validation Failure After Update**
   - Detection: Validator returns errors after save
   - Handling: Restore from backup, report error
   - User Message: "Updated saidata failed validation. Restored from backup."

6. **File Creation Failure**
   - Detection: IOError, PermissionError
   - Handling: Log error, continue with other files
   - User Message: "Failed to create {file_path}: {error}"

### Validation Strategy

```python
# Before saving
try:
    # Update saidata
    _save_saidata(saidata, output_path)
    
    # Validate against schema
    validator = SaidataValidator()
    validation_result = validator.validate(output_path)
    
    if not validation_result.is_valid:
        # Restore from backup
        if backup_path and backup_path.exists():
            shutil.copy2(backup_path, output_path)
        raise ValidationError(validation_result.errors)
        
except Exception as e:
    result.errors.append(f"Failed to save {output_path}: {e}")
    result.failed_packages += 1
```

## Testing Strategy

### Unit Tests

1. **Path Parser Tests** (`tests/saigen/utils/test_saidata_path.py`)
   - Test Ubuntu path patterns
   - Test Debian path patterns
   - Test default.yaml detection
   - Test invalid paths
   - Test edge cases (missing directories, etc.)

2. **Codename Resolver Tests** (`tests/saigen/repositories/test_codename_resolver.py`)
   - Test version to codename mapping
   - Test repository name resolution
   - Test missing version handling
   - Test all OS/version combinations

3. **Repository Config Tests** (`tests/saigen/repositories/test_repository_configs.py`)
   - Test loading provider-specific files
   - Test version_mapping validation
   - Test all repository configurations
   - Test endpoint connectivity

4. **Package Query Tests** (`tests/saigen/cli/test_refresh_versions.py`)
   - Test OS-specific repository selection
   - Test package name and version retrieval
   - Test fallback to generic provider
   - Test missing repository handling

### Integration Tests

1. **Single File Refresh**
   - Test refreshing default.yaml
   - Test refreshing OS-specific file (ubuntu/22.04.yaml)
   - Test package name updates
   - Test version updates

2. **Directory Refresh**
   - Test --all-variants flag
   - Test processing multiple files
   - Test error handling (continue on failure)
   - Test summary reporting

3. **File Creation**
   - Test --create-missing flag
   - Test directory structure creation
   - Test minimal YAML generation
   - Test field comparison with default.yaml

4. **End-to-End Scenarios**
   - Test nginx saidata across multiple OS versions
   - Test with real repository data
   - Test with HashiCorp upstream repository
   - Test Windows/macOS repositories

### Performance Tests

1. **Single File Performance**
   - Target: < 5 seconds for single file refresh
   - Measure: Repository query time, file I/O time

2. **Directory Performance**
   - Target: < 30 seconds for 10 files
   - Measure: Total time, per-file time, concurrent queries

3. **Cache Effectiveness**
   - Measure: Cache hit rate, query time with/without cache
   - Target: > 80% cache hit rate for repeated queries

## Security Considerations

1. **Repository Endpoint Validation**
   - Validate URLs before making requests
   - Use HTTPS where available
   - Implement timeout and retry limits

2. **File System Operations**
   - Validate file paths to prevent directory traversal
   - Check permissions before writing
   - Create backups before modifications

3. **YAML Parsing**
   - Use yaml.safe_load() to prevent code execution
   - Validate schema after loading
   - Handle malformed YAML gracefully

4. **API Authentication**
   - Store API keys securely (not in repository configs)
   - Support environment variables for credentials
   - Implement rate limiting to avoid abuse

## Performance Optimizations

1. **Caching Strategy**
   - Cache repository data with appropriate TTL
   - Cache codename resolution results
   - Cache schema validation results

2. **Concurrent Processing**
   - Process multiple files concurrently (asyncio)
   - Batch repository queries where possible
   - Limit concurrent requests to avoid overwhelming servers

3. **Lazy Loading**
   - Load repository configs on-demand
   - Don't load all repositories at startup
   - Cache loaded configs in memory

4. **Incremental Updates**
   - Only query repositories for packages that need updates
   - Skip unchanged packages
   - Use conditional requests (ETags, Last-Modified)

## Migration Strategy

### Phase 0: Repository File Reorganization

1. **Create New Provider-Specific Files**
   - Create apt.yaml, dnf.yaml, brew.yaml, etc.
   - Migrate existing configurations
   - Add version_mapping fields to each repository entry
   - Add eol and query_type fields where appropriate

2. **Update Repository Configuration Validation**
   - Add validation for version_mapping field (Dict[str, str])
   - Add validation for eol field (boolean)
   - Add validation for query_type field (enum: bulk_download, api)
   - Implement validate_repository_config() function
   - Add validation to repository loader

3. **Update Repository Loader**
   - Modify universal_manager.py to load from new files
   - Support both old and new formats temporarily
   - Add deprecation warnings for old format
   - Load and validate new fields (version_mapping, eol, query_type)

4. **Update RepositoryInfo Model**
   - Add version_mapping: Optional[Dict[str, str]] field
   - Add eol: bool = False field
   - Add query_type: str = "bulk_download" field
   - Update model validation

5. **Test Compatibility**
   - Ensure existing functionality works
   - Test all repository queries
   - Validate configuration loading
   - Test new field validation

6. **Remove Old Files**
   - Delete linux-repositories.yaml, etc.
   - Update documentation
   - Remove compatibility code

### Backward Compatibility

- Existing refresh-versions command continues to work for single files
- New flags are optional (default behavior unchanged)
- Repository configs support both old and new formats during migration
- Clear deprecation warnings for old patterns

## Documentation Requirements

1. **Command Documentation**
   - Update CLI help text
   - Add examples for all new flags
   - Document OS detection behavior

2. **Repository Configuration Guide**
   - Document provider-specific file structure
   - Explain version_mapping field
   - Provide templates for new repositories

3. **Saidata Structure Guide**
   - Document default.yaml vs OS-specific files
   - Explain merge behavior
   - Provide examples of overrides

4. **Troubleshooting Guide**
   - Common issues and solutions
   - Debugging tips
   - Repository configuration validation

## Success Metrics

1. **Functionality**
   - All 33+ OS versions have repository configurations
   - Directory refresh processes 10 files in < 30 seconds
   - Package names and versions accurately updated
   - OS-specific files created successfully

2. **Reliability**
   - < 1% failure rate for repository queries
   - 100% backup creation before modifications
   - Schema validation catches all invalid updates

3. **Usability**
   - Clear error messages for all failure scenarios
   - Progress indicators for long operations
   - Comprehensive documentation with examples

4. **Performance**
   - Single file refresh < 5 seconds
   - Directory refresh (10 files) < 30 seconds
   - Cache hit rate > 80%

## Future Enhancements

1. **Automatic Repository Discovery**
   - Auto-detect available OS versions
   - Suggest missing repository configurations
   - Auto-generate repository configs from templates

2. **Diff Visualization**
   - Show visual diff before applying changes
   - Color-coded changes (additions, removals, modifications)
   - Interactive approval for each change

3. **Rollback Support**
   - Track all changes with timestamps
   - Support rollback to previous versions
   - Maintain change history

4. **Parallel Processing**
   - Process multiple files in parallel
   - Batch repository queries
   - Optimize for large directories

5. **Smart Caching**
   - Predictive cache warming
   - Intelligent cache invalidation
   - Distributed cache support
