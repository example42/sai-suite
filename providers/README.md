# Provider Data Collection

This directory contains 33 generic provider implementations that work with any saidata file. Each provider defines how to implement software management actions for a specific platform or deployment method.

## Available Providers

### Linux Package Managers

| Provider | Platforms | Description | Service Type |
|----------|-----------|-------------|--------------|
| **apt** | debian, ubuntu | Advanced Package Tool | systemd |
| **dnf** | fedora, rhel, centos, rocky, alma | Dandified YUM | systemd |
| **yum** | rhel, centos, scientific | Legacy YUM | sysv |
| **zypper** | opensuse, sles | openSUSE package manager | systemd |
| **pacman** | arch, manjaro, endeavouros | Arch Linux package manager | systemd |
| **apk** | alpine | Alpine Package Keeper | openrc |
| **emerge** | gentoo | Portage Emerge | openrc |
| **portage** | gentoo | Alternative Portage interface | openrc |
| **xbps** | void | X Binary Package System | runit |
| **slackpkg** | slackware | Slackware package manager | sysv |
| **opkg** | openwrt, embedded | OpenWrt package manager | procd |

### BSD Package Managers

| Provider | Platforms | Description | Service Type |
|----------|-----------|-------------|--------------|
| **pkg** | freebsd, dragonfly | FreeBSD package manager | rc |

### macOS Package Managers

| Provider | Platforms | Description | Service Type |
|----------|-----------|-------------|--------------|
| **brew** | macos | Homebrew | launchd |

### Windows Package Managers

| Provider | Platforms | Description | Service Type |
|----------|-----------|-------------|--------------|
| **winget** | windows | Windows Package Manager | windows_service |
| **choco** | windows | Chocolatey | windows_service |
| **scoop** | windows | Scoop | application |

### Universal/Cross-Platform

| Provider | Platforms | Description | Service Type |
|----------|-----------|-------------|--------------|
| **flatpak** | linux | Universal Linux packages | flatpak |
| **snap** | ubuntu, fedora, debian, opensuse, arch | Universal Linux packages | snap |

### Functional/Declarative

| Provider | Platforms | Description | Service Type |
|----------|-----------|-------------|--------------|
| **nix** | nixos, linux, macos | Nix package manager | systemd |
| **nixpkgs** | nixos, linux, macos | Nix packages collection | systemd |
| **guix** | guix, linux | GNU Guix | shepherd |

### Scientific/HPC

| Provider | Platforms | Description | Service Type |
|----------|-----------|-------------|--------------|
| **spack** | linux, macos | Scientific computing packages | application |

### Language-Specific

| Provider | Platforms | Description | Service Type |
|----------|-----------|-------------|--------------|
| **npm** | linux, macos, windows | Node.js packages | nodejs |
| **pypi** | linux, macos, windows | Python packages | python |
| **cargo** | linux, macos, windows | Rust packages | rust |
| **gem** | linux, macos, windows | Ruby packages | ruby |
| **go** | linux, macos, windows | Go modules | go |
| **composer** | linux, macos, windows | PHP packages | php |
| **nuget** | linux, macos, windows | .NET packages | dotnet |
| **maven** | linux, macos, windows | Java packages | java |
| **gradle** | linux, macos, windows | Java/Kotlin packages | java |

### Container/Orchestration

| Provider | Platforms | Description | Service Type |
|----------|-----------|-------------|--------------|
| **docker** | linux, macos, windows | Container platform | docker |
| **helm** | linux, macos, windows | Kubernetes package manager | kubernetes |

## Provider Capabilities

### Common Actions
All providers support these core actions:
- ✅ `install` - Install software
- ✅ `uninstall` - Remove software
- ✅ `info` - Show software information
- ✅ `list` - List installed software

### Service Management
Most providers support service management:
- ✅ `start` - Start services
- ✅ `stop` - Stop services
- ✅ `restart` - Restart services
- ✅ `status` - Check service status
- ✅ `enable` - Enable auto-start
- ✅ `disable` - Disable auto-start

### Advanced Features
Many providers offer additional capabilities:
- 🔍 `search` - Search for software
- 📈 `upgrade` - Update software
- 📋 `logs` - View service logs

## How Providers Work

### 1. Generic Templates
Providers use generic command templates with saidata variable substitution:

```yaml
actions:
  install:
    template: \"apt-get install -y {{saidata.packages.*.name}}\"
```

### 2. Mapping Rules
Providers define how logical saidata components map to provider-specific implementations:

```yaml
mappings:
  packages:
    server:
      name: \"{{saidata.metadata.name}}-server\"
  services:
    main:
      name: \"{{saidata.metadata.name}}\"
```

### 3. Runtime Resolution
Tools combine saidata + providerdata at runtime:

1. Load `software/re/redis/default.yaml` from repository cache (software metadata)
2. Load `providerdata/apt.yaml` (provider implementation)
3. Resolve variables: `{{saidata.metadata.name}}` → `redis`
4. Execute: `apt-get install -y redis-server`

## Platform Support Matrix

| Provider | Linux | macOS | Windows | Containers |
|----------|-------|-------|---------|------------|
| apt | ✅ | ❌ | ❌ | ❌ |
| dnf | ✅ | ❌ | ❌ | ❌ |
| yum | ✅ | ❌ | ❌ | ❌ |
| zypper | ✅ | ❌ | ❌ | ❌ |
| pacman | ✅ | ❌ | ❌ | ❌ |
| apk | ✅ | ❌ | ❌ | ❌ |
| emerge | ✅ | ❌ | ❌ | ❌ |
| portage | ✅ | ❌ | ❌ | ❌ |
| xbps | ✅ | ❌ | ❌ | ❌ |
| slackpkg | ✅ | ❌ | ❌ | ❌ |
| opkg | ✅ | ❌ | ❌ | ❌ |
| pkg | ❌ | ❌ | ❌ | ❌ |
| brew | ❌ | ✅ | ❌ | ❌ |
| winget | ❌ | ❌ | ✅ | ❌ |
| choco | ❌ | ❌ | ✅ | ❌ |
| scoop | ❌ | ❌ | ✅ | ❌ |
| flatpak | ✅ | ❌ | ❌ | ❌ |
| snap | ✅ | ❌ | ❌ | ❌ |
| nix | ✅ | ✅ | ❌ | ❌ |
| nixpkgs | ✅ | ✅ | ❌ | ❌ |
| guix | ✅ | ❌ | ❌ | ❌ |
| spack | ✅ | ✅ | ❌ | ❌ |
| npm | ✅ | ✅ | ✅ | ❌ |
| pypi | ✅ | ✅ | ✅ | ❌ |
| cargo | ✅ | ✅ | ✅ | ❌ |
| gem | ✅ | ✅ | ✅ | ❌ |
| go | ✅ | ✅ | ✅ | ❌ |
| composer | ✅ | ✅ | ✅ | ❌ |
| nuget | ✅ | ✅ | ✅ | ❌ |
| maven | ✅ | ✅ | ✅ | ❌ |
| gradle | ✅ | ✅ | ✅ | ❌ |
| docker | ✅ | ✅ | ✅ | ✅ |
| helm | ✅ | ✅ | ✅ | ✅ |

## Usage Examples

### Installing Redis via Different Providers

**Same saidata file (`software/re/redis/default.yaml`):**
```yaml
metadata:
  name: \"redis\"
software:
  packages:
    - name: \"server\"
      required: true
```

**Different provider implementations:**

```bash
# Ubuntu/Debian
sai install redis --provider apt
# → apt-get install -y redis-server

# RHEL/Fedora
sai install redis --provider dnf
# → dnf install -y redis

# macOS
sai install redis --provider brew
# → brew install redis

# Container
sai install redis --provider docker
# → docker run -d --name redis-container redis:latest

# Kubernetes
sai install redis --provider helm
# → helm install redis-release redis-repo/redis
```

## Service Type Coverage

The providers support various service management systems:

- **systemd**: 8 providers (modern Linux)
- **sysv**: 2 providers (legacy Linux)
- **openrc**: 3 providers (Alpine, Gentoo)
- **runit**: 1 provider (Void Linux)
- **rc**: 1 provider (FreeBSD)
- **procd**: 1 provider (OpenWrt)
- **launchd**: 1 provider (macOS)
- **windows_service**: 2 providers (Windows)
- **container**: 2 providers (Docker, Kubernetes)
- **application**: 2 providers (Scoop, Spack)
- **language-specific**: 9 providers (npm, pypi, cargo, etc.)

## Validation

All 33 provider files validate successfully against the [`providerdata-0.1-schema.json`](/schemas/providerdata-0.1-schema.json-schema.json) schema and work with any compliant saidata file.

## Benefits

- ✅ **Comprehensive Coverage**: 33 providers across all major platforms
- ✅ **Reusable**: One provider works with all software
- ✅ **Maintainable**: Provider updates don't affect software definitions
- ✅ **Extensible**: Easy to add new providers
- ✅ **Consistent**: Same interface across all providers
- ✅ **Generic**: No software-specific code in providers
- ✅ **Platform Native**: Uses each platform's preferred tools and conventions