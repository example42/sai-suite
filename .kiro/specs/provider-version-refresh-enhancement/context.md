# Context: Provider Version Refresh Enhancement

## Executive Summary

This specification enhances the existing `saigen refresh-versions` command to support OS-specific saidata files and comprehensive repository configurations. The enhancement enables accurate package name and version updates across different operating system versions without LLM inference.

## Background

### Current Implementation Status

SAIGEN already has a `refresh-versions` command (`saigen/cli/commands/refresh_versions.py`) that:
- ✅ Loads saidata files and extracts packages
- ✅ Queries repositories for version information
- ✅ Updates version fields in various saidata locations
- ✅ Creates backups and validates changes
- ✅ Supports check-only mode and selective provider targeting

**What's Missing:**
- ❌ OS-specific repository configurations (only Ubuntu 22.04, Debian 12 configured)
- ❌ OS version detection from file paths
- ❌ Directory-wide refresh for multiple OS variants
- ❌ Package name updates (currently only updates versions)
- ❌ Codename-to-version mapping system

### Saidata File Structure

Saidata follows a hierarchical override pattern:

```
software/ng/nginx/
  default.yaml           # Base configuration with upstream defaults
  ubuntu/
    22.04.yaml          # Ubuntu 22.04 specific overrides
    24.04.yaml          # Ubuntu 24.04 specific overrides
  debian/
    11.yaml             # Debian 11 specific overrides
    12.yaml             # Debian 12 specific overrides
```

**Merge Behavior**: When SAI loads saidata for Ubuntu 22.04:
1. Load `default.yaml`
2. Merge with `ubuntu/22.04.yaml` (OS-specific values take precedence)

### Default.yaml Version Policy

**Key Decision**: `default.yaml` should contain **upstream/official versions** and **common provider package names**.

**Rationale**:
- Top-level version represents the canonical software version
- Provider package names should be included if consistent across OS versions
- Only OS-specific files override when package names differ
- Versions are always OS-specific, never in default.yaml providers

**Example 1: Apache (package name differs across OS versions)**
```yaml
# default.yaml
metadata:
  name: apache
packages:
  - name: main
    package_name: httpd  # Generic upstream name
    version: "2.4.58"    # Latest official Apache release

providers:
  apt:
    packages:
      - name: main
        package_name: apache2  # Common name for apt across most OS versions
        # NO version here - versions are OS-specific
  dnf:
    packages:
      - name: main
        package_name: httpd    # Common name for dnf
        # NO version here
```

```yaml
# ubuntu/22.04.yaml
providers:
  apt:
    packages:
      - name: main
        # package_name: apache2 inherited from default.yaml
        version: "2.4.52"  # Ubuntu 22.04 specific version
```

```yaml
# debian/9.yaml (if package name differs)
providers:
  apt:
    packages:
      - name: main
        package_name: apache2-bin  # ONLY override because it differs on Debian 9
        version: "2.4.25"
```

**Example 2: Nginx (package name varies by OS)**
```yaml
# default.yaml
metadata:
  name: nginx
packages:
  - name: main
    package_name: nginx
    version: "1.25.3"  # Latest official nginx release

providers:
  apt:
    packages:
      - name: main
        package_name: nginx  # Common name across most apt-based systems
        # NO version here
```

```yaml
# ubuntu/22.04.yaml
providers:
  apt:
    packages:
      - name: main
        package_name: nginx-core  # Override because Ubuntu uses different name
        version: "1.18.0"
```

```yaml
# debian/11.yaml
providers:
  apt:
    packages:
      - name: main
        # package_name: nginx inherited from default.yaml (same as common)
        version: "1.18.0"
```

### Repository Configuration Structure

**Current Structure** (Platform-based):
```
saigen/repositories/configs/
  linux-repositories.yaml      # All Linux repos mixed together
  macos-repositories.yaml       # macOS repos
  windows-repositories.yaml     # Windows repos
  language-repositories.yaml    # Language package managers
```

**Problems**:
- Mixed provider types in single files
- Hard to find specific provider configs
- Difficult to maintain as repos grow

**New Structure** (Provider-based - RECOMMENDED):
```
saigen/repositories/configs/
  apt.yaml          # All apt repositories (Ubuntu, Debian, Mint)
  dnf.yaml          # All dnf repositories (Fedora, RHEL, Rocky, Alma, CentOS)
  brew.yaml         # Homebrew for macOS
  choco.yaml        # Chocolatey for Windows
  winget.yaml       # Winget for Windows
  pacman.yaml       # Arch Linux
  zypper.yaml       # SUSE/openSUSE
  apk.yaml          # Alpine Linux
  emerge.yaml       # Gentoo
  nix.yaml          # NixOS
  npm.yaml          # Node.js packages
  pip.yaml          # Python packages
  cargo.yaml        # Rust packages
  # ... other providers
```

**Benefits**:
- Clear organization by provider type
- Easy to find and maintain provider-specific configs
- Logical grouping of related repositories
- Scales better as more OS versions are added

### Repository Types: Bulk Download vs API-Based

**Two Types of Repositories**:

1. **Bulk Download Repositories** (apt, dnf, zypper, pacman)
   - Download complete package lists
   - Parse locally
   - Cache entire list
   - Fast for multiple queries
   - Examples: apt, dnf, zypper, pacman, apk

2. **API-Based Repositories** (npm, pip, cargo, winget)
   - Query per package via HTTP API
   - No bulk download available
   - Cache individual results
   - Requires rate limiting
   - Examples: npm, pip, cargo, winget, rubygems, maven, nuget

**Configuration Differences**:

```yaml
# Bulk Download Repository (apt)
- name: "apt-ubuntu-jammy"
  type: "apt"
  query_type: "bulk_download"  # Downloads full package list
  endpoints:
    packages: "http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-{arch}/Packages.gz"
  parsing:
    format: "debian_packages"
    compression: "gzip"
  cache:
    ttl_hours: 24  # Cache full list for 24 hours

# API-Based Repository (npm)
- name: "npm-registry"
  type: "npm"
  query_type: "api"  # Queries per package
  endpoints:
    search: "https://registry.npmjs.org/-/v1/search?text={query}"
    info: "https://registry.npmjs.org/{package}"
  parsing:
    format: "json"
  cache:
    ttl_hours: 1  # Cache individual package results for 1 hour
  rate_limiting:
    requests_per_minute: 60
    concurrent_requests: 5
```

**Implications for Refresh Command**:

**Bulk Download Repositories**:
- Download once, query many times
- Efficient for multiple packages
- Slower initial download
- Works offline after download

**API-Based Repositories**:
- Query each package individually
- Slower for multiple packages
- Requires network for each query
- Respects rate limits
- Needs authentication for some (npm tokens, PyPI API keys)

**Current Gap**: Only one repository per OS type (e.g., "ubuntu-main" for jammy only)

**Needed**: Multiple repositories per provider for different OS versions:

**apt.yaml** should contain:
- `apt-ubuntu-focal` (20.04)
- `apt-ubuntu-jammy` (22.04)
- `apt-ubuntu-noble` (24.04)
- `apt-ubuntu-oracular` (26.04)
- `apt-debian-stretch` (9)
- `apt-debian-buster` (10)
- `apt-debian-bullseye` (11)
- `apt-debian-bookworm` (12)
- `apt-debian-trixie` (13)
- `apt-mint-22`

**dnf.yaml** should contain:
- `dnf-fedora-38`, `dnf-fedora-39`, `dnf-fedora-40`, `dnf-fedora-41`, `dnf-fedora-42`
- `dnf-rocky-8`, `dnf-rocky-9`, `dnf-rocky-10`
- `dnf-alma-8`, `dnf-alma-9`, `dnf-alma-10`
- `dnf-rhel-7`, `dnf-rhel-8`, `dnf-rhel-9`, `dnf-rhel-10`
- `dnf-centos-8`, `dnf-centos-9`, `dnf-centos-10`

### Codename Mapping Challenge

Different distributions use different naming schemes:

| OS | Version | Codename | Repository Name |
|----|---------|----------|-----------------|
| **Windows** | - | - | choco-windows, winget-windows |
| **macOS** | - | - | brew-macos |
| **Ubuntu** | 20.04 | focal | apt-ubuntu-focal |
| **Ubuntu** | 22.04 | jammy | apt-ubuntu-jammy |
| **Ubuntu** | 24.04 | noble | apt-ubuntu-noble |
| **Ubuntu** | 26.04 | oracular | apt-ubuntu-oracular |
| **Debian** | 9 | stretch | apt-debian-stretch |
| **Debian** | 10 | buster | apt-debian-buster |
| **Debian** | 11 | bullseye | apt-debian-bullseye |
| **Debian** | 12 | bookworm | apt-debian-bookworm |
| **Debian** | 13 | trixie | apt-debian-trixie |
| **Fedora** | 38 | f38 | dnf-fedora-38 |
| **Fedora** | 39 | f39 | dnf-fedora-39 |
| **Fedora** | 40 | f40 | dnf-fedora-40 |
| **Fedora** | 41 | f41 | dnf-fedora-41 |
| **Fedora** | 42 | f42 | dnf-fedora-42 |
| **Rocky** | 8 | 8 | dnf-rocky-8 |
| **Rocky** | 9 | 9 | dnf-rocky-9 |
| **Rocky** | 10 | 10 | dnf-rocky-10 |
| **Alma** | 8 | 8 | dnf-alma-8 |
| **Alma** | 9 | 9 | dnf-alma-9 |
| **Alma** | 10 | 10 | dnf-alma-10 |
| **RHEL** | 7-10 | - | dnf-rhel-{version} |
| **CentOS Stream** | 8-10 | - | dnf-centos-{version} |
| **SLES** | 12, 15 | - | zypper-sles-{version} |
| **openSUSE Leap** | 15 | - | zypper-opensuse-leap-15 |
| **openSUSE Tumbleweed** | rolling | - | zypper-opensuse-tumbleweed |
| **Arch** | rolling | - | pacman-arch |
| **Gentoo** | rolling | - | emerge-gentoo |
| **Mint** | 22 | wilma | apt-mint-22 |
| **NixOS** | unstable | - | nix-nixos |

**Solution**: Store version-to-codename mappings directly in repository YAML configuration files using a `version_mapping` field

## Key Design Decisions

### 1. Default.yaml Refresh Behavior

**Decision**: Do NOT refresh provider-specific versions in default.yaml

**Reasoning**:
- Provider versions are OS-specific
- Default.yaml should only contain upstream version
- Prevents confusion about which OS version is represented

**Implementation**:
- Only update `packages[].version` in default.yaml
- Skip `providers.{provider}.packages[].version` in default.yaml
- Provide `--skip-default` flag to skip default.yaml entirely

### 2. OS Detection Strategy

**Decision**: Extract OS information from file path

**Pattern**: `{software}/{os}/{version}.yaml`

**Examples**:
- `ng/nginx/ubuntu/22.04.yaml` → OS: ubuntu, Version: 22.04
- `ng/nginx/debian/11.yaml` → OS: debian, Version: 11
- `ng/nginx/default.yaml` → OS: none (generic)

**Fallback**: If path doesn't match pattern, treat as OS-agnostic

### 3. Repository Naming Convention

**Decision**: Use pattern `{provider}-{os}-{codename}`

**Examples**:
- `apt-ubuntu-jammy`
- `apt-debian-bookworm`
- `dnf-fedora-39`
- `dnf-rocky-9`

**Benefits**:
- Clear and consistent
- Easy to parse and generate
- Supports multiple versions per OS

### 4. Missing Repository Handling

**Decision**: Skip with warning, continue processing

**Behavior**:
```
⚠ No repository found for Ubuntu 20.04 (apt-ubuntu-focal)
⚠ Skipping ubuntu/20.04.yaml
✓ Processing ubuntu/22.04.yaml...
```

**Reasoning**:
- Graceful degradation
- Allows partial updates
- User can add missing repositories later

### 5. OS-Specific File Creation

**Decision**: Support creating OS-specific files when they don't exist

**Use Case**: When adding support for a new OS version (e.g., Ubuntu 26.04), automatically create the OS-specific file with version information.

**Behavior with `--create-missing` flag**:
```bash
saigen refresh-versions ng/nginx/ --all-variants --create-missing --providers apt

# Before:
ng/nginx/
  default.yaml
  ubuntu/
    22.04.yaml
    24.04.yaml

# After:
ng/nginx/
  default.yaml
  ubuntu/
    22.04.yaml
    24.04.yaml
    26.04.yaml  # ← Created with version info from apt-ubuntu-oracular
```

**Created File Structure** (minimal, only what differs):
```yaml
# ng/nginx/ubuntu/26.04.yaml (newly created)
providers:
  apt:
    packages:
      - name: main
        version: "1.26.0"  # Queried from apt-ubuntu-oracular
        # package_name inherited from default.yaml (not duplicated)
```

**Rules for Creation**:
1. Only create if `--create-missing` flag is used
2. Query appropriate repository for that OS version
3. Only include fields that differ from default.yaml
4. Always include version (OS-specific)
5. Only include package_name if it differs from default.yaml
6. Create directory structure if needed (e.g., `ubuntu/` folder)
7. Use minimal YAML (no unnecessary fields)

**Without `--create-missing` flag**:
```
⚠ File ubuntu/26.04.yaml does not exist, skipping (use --create-missing to create)
```

### 6. Package Name vs Version Updates

**Decision**: Update both package_name and version fields

**Reasoning**:
- Package names differ across OS versions (e.g., `nginx` vs `nginx-core`)
- Both fields need to be accurate for each OS
- Existing command only updates version - this is an enhancement

**Example Update**:
```
✓ apt/nginx: nginx 1.20.1 → nginx-core 1.18.0
  (package name changed: nginx → nginx-core)
```

## Implementation Phases

### Phase 1: Repository Configuration Expansion
**Goal**: Add all missing OS-version-specific repositories

**Tasks**:
1. Add Ubuntu 20.04, 24.04 repositories
2. Add Debian 10, 11 repositories
3. Add Fedora 38, 40 repositories
4. Add Rocky/Alma 8, 9 repositories
5. Include codename mapping in metadata
6. Test repository connectivity

**Deliverable**: Complete repository configurations for all major OS versions

### Phase 2: Codename Mapping System
**Goal**: Implement OS version → codename resolution

**Tasks**:
1. Create codename mapping configuration
2. Implement mapping lookup function
3. Add validation for unknown versions
4. Document mapping maintenance process

**Deliverable**: Centralized codename mapping system

### Phase 3: OS Detection and Repository Selection
**Goal**: Detect OS from file paths and select appropriate repositories

**Tasks**:
1. Implement file path parsing for OS/version extraction
2. Implement repository name resolution (OS + version → repository name)
3. Add fallback logic for missing repositories
4. Add logging for OS detection and repository selection

**Deliverable**: OS-aware repository selection

### Phase 4: Package Name Updates
**Goal**: Update package_name field in addition to version

**Tasks**:
1. Modify query logic to retrieve package name
2. Update comparison logic to detect name changes
3. Update display logic to show name changes
4. Add tests for package name updates

**Deliverable**: Package name update capability

### Phase 5: Directory-Wide Refresh
**Goal**: Process multiple saidata files in one command

**Tasks**:
1. Implement directory scanning for YAML files
2. Add `--all-variants` flag
3. Implement per-file OS detection and processing
4. Add summary reporting for multi-file operations
5. Handle errors gracefully (continue on failure)

**Deliverable**: Directory-wide refresh capability

### Phase 6: Documentation and Testing
**Goal**: Complete documentation and comprehensive testing

**Tasks**:
1. Update command documentation
2. Add examples for all new features
3. Create integration tests
4. Test with real saidata files
5. Document default.yaml version policy

**Deliverable**: Complete documentation and test coverage

## Success Metrics

1. **Repository Coverage**: 
   - High Priority: Windows (2), macOS (1), Ubuntu (4), Debian (5), Rocky/Alma (6) = 18 repositories
   - Lower Priority: Fedora (5), RHEL (4), CentOS (3), SLES (2), openSUSE (2), Arch (1), Gentoo (1), Mint (1), NixOS (1) = 17 repositories
   - **Total Target**: 35+ repositories configured
2. **Accuracy**: 95%+ correct package name/version matches
3. **Performance**: <30s for directory with 10 files
4. **Reliability**: Graceful handling of missing repositories
5. **Usability**: Clear progress and error messages
6. **Validation**: Detect and report unnecessary OS-specific overrides

## Risk Mitigation

### Risk: Repository Endpoints Change
**Mitigation**: Regular testing, fallback to search endpoints, community contributions

### Risk: Codename Mapping Becomes Outdated
**Mitigation**: Centralized configuration, documentation for updates, validation on startup

### Risk: Package Names Don't Match
**Mitigation**: Fuzzy matching, logging of mismatches, manual override capability

### Risk: Breaking Changes to Existing Behavior
**Mitigation**: Backward compatibility, feature flags, comprehensive testing

## Design Questions - RESOLVED

### 1. Should we support custom codename mappings via configuration?
**RESOLVED**: Yes, but store mappings directly in repository YAML files using a `version_mapping` field, not in a separate configuration file. This keeps the mapping with the repository definition and allows for easier maintenance.

### 2. How should we handle EOL (end-of-life) OS versions?
**RESOLVED**: Keep repository configurations and relevant saidata files for EOL versions. Mark them as EOL in metadata but continue to support refresh operations if repositories remain accessible. This maintains historical compatibility.

### 3. Should we validate that OS-specific files only override necessary fields?
**RESOLVED**: Yes, provide validation to detect unnecessary duplications. OS-specific files should only contain fields that differ from default.yaml to avoid maintenance burden and confusion.

### 4. Do we need a command to list available repositories?
**RESOLVED**: Yes, `saigen repositories list-repos` already exists and should be enhanced to show OS version support and codename mappings. This helps users understand what repositories are available.

### 5. Should we support software-specific upstream repositories?
**RESOLVED**: Yes, support vendor-specific repositories (e.g., HashiCorp repo for Terraform/Vault). Allow multiple repositories per provider-OS combination to support both distribution and upstream vendor repositories.

## References

- Existing implementation: `saigen/cli/commands/refresh_versions.py`
- Repository configs: `saigen/repositories/configs/*.yaml`
- Documentation: `saigen/docs/refresh-versions-command.md`
- Saidata schema: `schemas/saidata-0.3-schema.json`
- Tech documentation: `.kiro/steering/tech.md`
