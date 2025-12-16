# Repository Configuration Reorganization

## Problem Statement

Current repository configuration files are organized by platform (linux, macos, windows), which creates several issues:

### Current Structure Issues

```
saigen/repositories/configs/
  linux-repositories.yaml      # Contains apt, dnf, zypper, pacman, apk, emerge, etc.
  macos-repositories.yaml       # Contains brew
  windows-repositories.yaml     # Contains choco, winget
  language-repositories.yaml    # Contains npm, pip, cargo, etc.
```

**Problems**:
1. **Mixed Provider Types**: `linux-repositories.yaml` contains multiple unrelated providers (apt, dnf, zypper, pacman)
2. **Hard to Find**: Finding apt configs requires searching through large linux file
3. **Difficult to Maintain**: Adding new OS versions means editing large files
4. **Unclear Organization**: Not obvious where to add new repositories
5. **Scalability**: As we add 33+ repositories, files become unwieldy

## Proposed Solution

Reorganize by **provider type** instead of platform:

### New Structure

```
saigen/repositories/configs/
  # Package Managers
  apt.yaml          # All apt-based repositories
  dnf.yaml          # All dnf/yum-based repositories
  zypper.yaml       # All zypper-based repositories
  pacman.yaml       # Arch Linux repositories
  apk.yaml          # Alpine Linux repositories
  emerge.yaml       # Gentoo repositories
  brew.yaml         # Homebrew (macOS)
  choco.yaml        # Chocolatey (Windows)
  winget.yaml       # Winget (Windows)
  nix.yaml          # NixOS repositories
  
  # Language Package Managers
  npm.yaml          # Node.js packages
  pip.yaml          # Python packages
  cargo.yaml        # Rust packages
  gem.yaml          # Ruby packages
  maven.yaml        # Java packages
  nuget.yaml        # .NET packages
  
  # Container/Universal
  flatpak.yaml      # Flatpak repositories
  snap.yaml         # Snap repositories
  appimage.yaml     # AppImage repositories
```

### Benefits

1. **Clear Organization**: Each provider has its own file
2. **Easy to Find**: Want apt configs? Open `apt.yaml`
3. **Easy to Maintain**: Adding Ubuntu 26.04? Just edit `apt.yaml`
4. **Logical Grouping**: All related repositories together
5. **Scalability**: Each file stays manageable size
6. **Parallel Development**: Multiple people can work on different providers

## Example: apt.yaml Structure

```yaml
version: "1.0"
provider: "apt"
description: "APT package manager repositories for Debian-based distributions"

repositories:
  # Ubuntu Repositories
  - name: "apt-ubuntu-focal"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    os_version: "20.04"
    codename: "focal"
    version_mapping:
      "20.04": "focal"
    architecture: ["amd64", "arm64", "armhf"]
    endpoints:
      packages: "http://archive.ubuntu.com/ubuntu/dists/focal/main/binary-{arch}/Packages.gz"
    parsing:
      format: "debian_packages"
      compression: "gzip"
      encoding: "utf-8"
    cache:
      ttl_hours: 24
    metadata:
      description: "Ubuntu 20.04 LTS (Focal Fossa) Main Repository"
      priority: 90
      enabled: true
      official: true
      eol: false

  - name: "apt-ubuntu-jammy"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    os_version: "22.04"
    codename: "jammy"
    version_mapping:
      "22.04": "jammy"
    # ... similar structure

  - name: "apt-ubuntu-noble"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    os_version: "24.04"
    codename: "noble"
    version_mapping:
      "24.04": "noble"
    # ... similar structure

  - name: "apt-ubuntu-oracular"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    os_version: "26.04"
    codename: "oracular"
    version_mapping:
      "26.04": "oracular"
    # ... similar structure

  # Debian Repositories
  - name: "apt-debian-buster"
    type: "apt"
    platform: "linux"
    distribution: ["debian"]
    os_version: "10"
    codename: "buster"
    version_mapping:
      "10": "buster"
    # ... similar structure

  - name: "apt-debian-bullseye"
    type: "apt"
    platform: "linux"
    distribution: ["debian"]
    os_version: "11"
    codename: "bullseye"
    version_mapping:
      "11": "bullseye"
    # ... similar structure

  # ... more Debian versions

  # Linux Mint Repositories
  - name: "apt-mint-22"
    type: "apt"
    platform: "linux"
    distribution: ["mint"]
    os_version: "22"
    codename: "wilma"
    version_mapping:
      "22": "wilma"
    # ... similar structure

  # Upstream Vendor Repositories
  - name: "apt-hashicorp-ubuntu"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    vendor: "hashicorp"
    endpoints:
      packages: "https://apt.releases.hashicorp.com/dists/jammy/main/binary-{arch}/Packages.gz"
    metadata:
      description: "HashiCorp Official APT Repository"
      vendor_specific: true
    # ... similar structure
```

## Migration Strategy

### Clean Break Approach (No Backward Compatibility)

Since this is part of a major enhancement, we'll do a clean migration without maintaining backward compatibility.

**Phase 1: Reorganize Files**
1. Create new provider-specific files (apt.yaml, dnf.yaml, etc.)
2. Migrate all configurations from old files
3. Delete old platform-based files
4. Update all code references to use new structure

**Phase 2: Update Code**
1. Update repository loader to use new file structure
2. Update all imports and references
3. Update configuration schema if needed
4. Update tests to use new structure

**Phase 3: Validate**
1. Test that all repositories load correctly
2. Verify no broken references
3. Update documentation
4. Run full test suite

## Implementation Tasks

### Task 1.0: Reorganize Repository Configuration Files

**Subtasks**:

1. **Create new provider-specific files**
   - Create `apt.yaml` with all apt repositories
   - Create `dnf.yaml` with all dnf repositories  
   - Create `brew.yaml`, `choco.yaml`, `winget.yaml`
   - Create `zypper.yaml`, `pacman.yaml`, `apk.yaml`, `emerge.yaml`, `nix.yaml`
   - Create language package manager files (npm.yaml, pip.yaml, cargo.yaml, etc.)
   - Create universal package files (flatpak.yaml, snap.yaml)

2. **Migrate existing configurations**
   - Extract apt configs from `linux-repositories.yaml` → `apt.yaml`
   - Extract dnf configs from `linux-repositories.yaml` → `dnf.yaml`
   - Extract zypper configs from `linux-repositories.yaml` → `zypper.yaml`
   - Extract pacman configs from `linux-repositories.yaml` → `pacman.yaml`
   - Extract brew configs from `macos-repositories.yaml` → `brew.yaml`
   - Extract choco/winget configs from `windows-repositories.yaml` → `choco.yaml`, `winget.yaml`
   - Extract language managers from `language-repositories.yaml` → individual files
   - Preserve all existing functionality

3. **Delete old files**
   - Remove `linux-repositories.yaml`
   - Remove `macos-repositories.yaml`
   - Remove `windows-repositories.yaml`
   - Remove `language-repositories.yaml`

4. **Update repository loader**
   - Modify loader to scan for provider-specific files (*.yaml in configs/)
   - Update file discovery logic
   - Remove references to old file names
   - Update configuration loading logic

5. **Add provider-level metadata**
   - Add `provider` field to each file
   - Add `description` field
   - Document file purpose in header comments

6. **Update all code references**
   - Search codebase for references to old file names
   - Update imports and paths
   - Update configuration examples
   - Update tests to use new file names

7. **Update documentation**
   - Update configuration guide with new structure
   - Provide examples of new file organization
   - Document provider file format
   - Update README files

**Estimated Effort**: 4-6 hours

## File Organization Guidelines

### Provider File Template

```yaml
version: "1.0"
provider: "{provider_name}"  # apt, dnf, brew, etc.
description: "Description of provider and its repositories"

repositories:
  - name: "{provider}-{os}-{codename}"
    type: "{provider}"
    platform: "{platform}"
    distribution: ["{os}"]
    os_version: "{version}"
    codename: "{codename}"
    version_mapping:
      "{version}": "{codename}"
    # ... rest of configuration
```

### Naming Conventions

**File names**: `{provider}.yaml` (lowercase)
- `apt.yaml`, `dnf.yaml`, `brew.yaml`

**Repository names**: `{provider}-{os}-{codename}`
- `apt-ubuntu-jammy`, `dnf-fedora-39`, `brew-macos`

**Vendor-specific**: `{provider}-{vendor}-{os}`
- `apt-hashicorp-ubuntu`, `dnf-docker-fedora`

## Benefits Summary

| Aspect | Old Structure | New Structure |
|--------|--------------|---------------|
| **Organization** | By platform | By provider |
| **File Size** | Large (100+ repos) | Small (10-20 repos) |
| **Findability** | Search through file | Direct file access |
| **Maintenance** | Edit large file | Edit focused file |
| **Scalability** | Poor | Excellent |
| **Clarity** | Mixed providers | Single provider |
| **Parallel Work** | Conflicts likely | Independent files |

## Migration Checklist

- [ ] Create new provider-specific YAML files
- [ ] Migrate all existing configurations
- [ ] Delete old platform-based files
- [ ] Update repository loader to use new structure
- [ ] Add provider-level metadata
- [ ] Update all code references to new file names
- [ ] Update imports and paths
- [ ] Update tests to use new structure
- [ ] Test with existing functionality
- [ ] Update documentation
- [ ] Verify no broken references
- [ ] Run full test suite

## Conclusion

Reorganizing repository configurations by provider type creates a more maintainable, scalable, and intuitive structure. This clean break migration provides a better foundation for adding the 33+ repositories needed for this enhancement and improves long-term maintainability.
