# Saitest Specification Summary

## Overview

Saitest is an agent-based verification tool using LangGraph that installs software in Docker containers, observes system changes, and generates validated saidata. It integrates into the sai-suite monorepo.

## Key Design Principles

### 1. Providerdata-Driven Installation
- **Single Source of Truth**: All installation commands come from `providers/*.yaml` files
- **Consistency**: Saitest uses the same commands as sai
- **Extensibility**: New providers automatically supported when providerdata added
- **No Hardcoding**: No provider-specific code or commands

### 2. Saigen Repository Integration
- **Discovery Phase**: Query saigen's RepositoryDownloader for package metadata
- **Version Information**: Use cached repository data for versions and dependencies
- **Fallback**: Use LLM if repository data unavailable
- **Shared Code**: Import from saigen.repositories

### 3. Multi-Provider Testing
- **Platform-Provider Combinations**: Test each (platform, provider) pair
- **Fresh Containers**: Spawn new container for each test
- **Tagged Observations**: Each observation includes platform and provider
- **Provider Overrides**: Generated saidata includes provider-specific sections

### 4. LangGraph Workflow
- **7 Agents**: Discovery, Platform Selection, Installation, Inspection, Analysis, Generation, Quality Check
- **State Management**: VerificationState tracks entire workflow
- **Conditional Routing**: AI-driven decisions at each step
- **Checkpointing**: Resume failed workflows

## Core Components

### Unified Installation Tool
```python
@tool
def install_package(platform: str, provider: str, package: str) -> Dict:
    """Uses providerdata to install with any provider"""
    executor = ProviderCommandExecutor()
    install_cmd = executor.get_install_command(provider, package)
    # Execute and monitor...
```

### Provider Command Executor
```python
class ProviderCommandExecutor:
    """Loads and executes commands from providerdata"""
    def get_install_command(self, provider: str, package: str) -> str
    def get_test_command(self, provider: str, package: str) -> str
```

### Data Models
```python
class Observation(BaseModel):
    type: str  # file, service, port, command
    platform: str  # ubuntu:22.04
    provider: str  # apt, pip, gem
    timestamp: str
    data: Dict
    confidence: float

class PlatformResult(BaseModel):
    platform: str
    provider: str
    success: bool
    observations: List[Observation]
    errors: List[str]
    duration: float
```

## Workflow Example

```
User: saitest verify nginx --platforms ubuntu:22.04

1. Discovery Agent:
   - Scan providers/ directory → Find all available providerdata
   - Query saigen repos for nginx across all providers
   - Find: apt (nginx), snap (nginx), flatpak (org.nginx.nginx)
   - Validate: All three have providerdata definitions
   - Store: installation_methods = ['apt', 'snap', 'flatpak']

2. Platform Selection Agent:
   - Selected: ['ubuntu:22.04']

3. Create Combinations:
   - [('ubuntu:22.04', 'apt'), ('ubuntu:22.04', 'snap'), ('ubuntu:22.04', 'flatpak')]

4. Installation Agent (ubuntu:22.04, apt):
   - Load providers/apt.yaml
   - Execute install command from providerdata
   - Execute test command from providerdata
   - Observe: files, services, ports
   - Result: PlatformResult(platform='ubuntu:22.04', provider='apt', ...)

5. Installation Agent (ubuntu:22.04', snap):
   - Load providers/snap.yaml
   - Execute install command from providerdata
   - Execute test command from providerdata
   - Observe: files, services
   - Result: PlatformResult(platform='ubuntu:22.04', provider='snap', ...)

6. Installation Agent (ubuntu:22.04, flatpak):
   - Load providers/flatpak.yaml
   - Execute install command from providerdata
   - Execute test command from providerdata
   - Observe: files
   - Result: PlatformResult(platform='ubuntu:22.04', provider='flatpak', ...)

7. Analysis Agent:
   - Aggregate observations by type and provider
   - Identify common patterns
   - Identify provider-specific differences

8. Generation Agent:
   - Generate saidata with base configuration
   - Add provider sections for ALL tested providers (apt, snap, flatpak)
   - Each section contains provider-specific overrides

9. Quality Check Agent:
   - Validate against schema 0.3
   - Calculate confidence scores
   - Determine if human review needed

Output: Validated saidata with multi-provider support (apt, snap, flatpak, and any other tested providers)
```

## Generated Saidata Structure

```yaml
version: "0.3"
metadata:
  name: nginx
  description: "High-performance HTTP server"

# Base configuration (common)
packages:
  - name: nginx
    package_name: nginx

services:
  - name: nginx
    type: systemd

# Provider-specific overrides
providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx-full
        version: "1.24.0"
    services:
      - name: nginx
        enabled: true
  
  pip:
    packages:
      - name: nginx-config
        package_name: nginx-config-builder
        version: "0.5.0"
```

## Integration Points

### With Saigen
- Import: `from saigen.repositories import RepositoryDownloader`
- Import: `from saigen.models.saidata import SaidataModel`
- Import: `from saigen.utils.validation import validate_saidata`

### With Sai
- Read: `providers/*.yaml` files for command templates
- Import: `from sai.models.providerdata import ProviderData`
- Use: Same template engine for variable substitution

### With Shared
- Import: `from shared.models.saidata import SaidataBase` (if created)

## Requirements Summary

20 requirements covering:
1. Agent-based workflow
2. Discovery with saigen integration and providerdata scanning
3. Platform selection
4. Container management
5. Installation monitoring
6. Multi-platform and multi-provider testing
7. Analysis and pattern recognition
8. Saidata generation
9. Quality assessment
10. CLI interface
11. Testing existing saidata
12. Error handling and retry
13. Multi-provider support (ANY provider with providerdata)
14. Saigen repository integration
15. Monorepo integration
16. Observation data models
17. Unified installation tool using providerdata
18. Providerdata integration
19. OS-specific override generation
20. Provider extensibility (automatic support for new providers)

## Success Criteria

- **Accuracy**: Generated saidata matches manual verification >90%
- **Coverage**: Supports all providers with providerdata
- **Speed**: Complete verification in <5 minutes per platform-provider combination
- **Confidence**: Average confidence score >0.8
- **Consistency**: Uses same commands as sai (via providerdata)

## Next Steps

1. ✅ Requirements defined (18 requirements)
2. ✅ Design completed (architecture, components, integration)
3. ⏭️ Create implementation task list
4. ⏭️ Begin Phase 1 implementation (foundation)


## Provider Support

### Automatic Provider Detection

Saitest supports **ANY provider with providerdata** - no hardcoded provider list!

**How it works:**
1. Scan `providers/` directory for all `.yaml` files
2. Load providerdata for each provider
3. Extract install/test commands from providerdata
4. Execute commands with proper variable substitution

**Currently supported providers** (as of implementation):
- Package managers: apt, dnf, yum, zypper, pacman, brew, choco, winget, scoop, pkg, apk
- Language package managers: pip, gem, npm, cargo, go, composer
- And any future providers added to providerdata!

**Adding new provider support:**
1. Create `providers/new-provider.yaml` with install/test actions
2. Saitest automatically detects and uses it
3. No code changes needed!

**Example - Adding a new provider:**
```yaml
# providers/flatpak.yaml
metadata:
  name: flatpak
  type: package_manager

actions:
  - name: install
    command: "flatpak install -y {{sai_packages('flatpak')}}"
  
  - name: status
    command: "flatpak list | grep {{sai_packages('flatpak')}}"
```

Result: Saitest can now test flatpak installations!
