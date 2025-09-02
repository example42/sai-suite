# Design Document

## Overview

The `sai` CLI tool is designed as a modular, extensible software management interface that abstracts provider-specific operations through a unified command structure. The architecture emphasizes clean separation of concerns, provider pluggability, and robust error handling while maintaining high performance through intelligent caching and lazy loading.

## Architecture

### Core Components

```
sai/
├── cli/                    # Command-line interface layer
│   ├── commands/          # Individual command implementations
│   ├── parser.py          # Argument parsing and validation
│   └── output.py          # Formatted output and logging
├── core/                  # Core business logic
│   ├── engine.py          # Main execution engine
│   ├── provider_manager.py # Provider detection and management
│   ├── saidata_loader.py  # Saidata file loading and validation
│   └── config.py          # Configuration management
├── providers/             # Provider system
│   ├── base.py           # Base provider class and factory
│   ├── loader.py         # Provider YAML file loader
│   └── executor.py       # Command template execution engine
├── models/               # Data models and schemas
│   ├── saidata.py        # Saidata structure models
│   ├── provider_data.py  # Provider YAML structure models
│   └── config.py         # Configuration models
└── utils/                # Utility functions
    ├── system.py         # System detection utilities
    ├── validation.py     # Schema validation
    └── cache.py          # Caching mechanisms
```

### Design Patterns

- **Strategy Pattern**: Provider implementations follow a common interface
- **Factory Pattern**: Provider creation based on system detection
- **Command Pattern**: CLI commands as discrete, testable units
- **Observer Pattern**: Event-driven logging and progress reporting

## Components and Interfaces

### Provider Interface

```python
class BaseProvider:
    def __init__(self, provider_data: ProviderData):
        """Initialize provider with data from YAML file"""
        self.provider_data = provider_data
        self.name = provider_data.name
        
    def is_available(self) -> bool:
        """Check if provider executable is available on system"""
        return self._check_executable_exists()
        
    def get_supported_actions(self) -> List[str]:
        """Return actions defined in provider YAML"""
        return list(self.provider_data.actions.keys())
        
    def execute_action(self, action: str, software: str, saidata: SaiData) -> ExecutionResult:
        """Execute action using command template from provider YAML"""
        return self._execute_template_command(action, software, saidata)
        
    def get_priority(self) -> int:
        """Return provider priority from YAML or default"""
        return self.provider_data.priority or 50

class ProviderFactory:
    @staticmethod
    def create_providers() -> List[BaseProvider]:
        """Dynamically create providers from YAML files in providers/ directory"""
        providers = []
        for yaml_file in Path("providers").glob("*.yaml"):
            provider_data = ProviderData.from_yaml(yaml_file)
            providers.append(BaseProvider(provider_data))
        return providers
```

### Saidata Loader Interface

```python
class SaidataLoader:
    def load_saidata(self, software_name: str) -> Optional[SaiData]:
        """Load and validate saidata for software"""
        
    def get_search_paths(self) -> List[Path]:
        """Return ordered list of saidata search paths"""
        
    def validate_saidata(self, data: dict) -> ValidationResult:
        """Validate saidata against schema"""
```

### Configuration System

```python
class Config:
    provider_priorities: Dict[str, int]
    saidata_paths: List[str]
    provider_paths: List[str]  # Additional provider YAML directories
    log_level: str
    cache_enabled: bool
    default_provider: Optional[str]
```

### Command Template System

The provider YAML files define command templates that are resolved at runtime:

```yaml
# Example: providers/apt.yaml
name: apt
executable: apt-get
platforms: [debian, ubuntu]
actions:
  install:
    command: "apt-get"
    args: ["install", "-y", "{{saidata.packages.*.name}}"]
    requires_sudo: true
  uninstall:
    command: "apt-get" 
    args: ["remove", "-y", "{{saidata.packages.*.name}}"]
    requires_sudo: true
  status:
    command: "systemctl"
    args: ["status", "{{saidata.services.*.service_name}}"]
```

Template variables are resolved using saidata context:
- `{{saidata.metadata.name}}` → software name
- `{{saidata.packages.*.name}}` → package names
- `{{saidata.services.*.service_name}}` → service names

## Data Models

### Provider Data Model

```python
@dataclass
class ProviderData:
    name: str
    executable: str
    platforms: List[str]
    actions: Dict[str, ActionTemplate]
    priority: Optional[int] = None
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> 'ProviderData':
        """Load provider data from YAML file"""

@dataclass
class ActionTemplate:
    command: str
    args: List[str]
    requires_sudo: bool = False
    timeout: Optional[int] = None
```

### Execution Context

```python
@dataclass
class ExecutionContext:
    action: str
    software: str
    provider: Optional[str]
    dry_run: bool
    verbose: bool
    saidata: SaiData
    selected_provider: BaseProvider
```

### Execution Result

```python
@dataclass
class ExecutionResult:
    success: bool
    message: str
    provider_used: str
    commands_executed: List[str]
    execution_time: float
    error_details: Optional[str] = None
```

### Provider Detection Result

```python
@dataclass
class ProviderInfo:
    name: str
    executable_path: str
    version: str
    available: bool
    priority: int
    supported_actions: List[str]
```

## Error Handling

### Error Hierarchy

```python
class SaiError(Exception):
    """Base exception for sai tool"""

class ProviderNotFoundError(SaiError):
    """No suitable provider found"""

class SaidataNotFoundError(SaiError):
    """Saidata file not found"""

class ValidationError(SaiError):
    """Schema validation failed"""

class ExecutionError(SaiError):
    """Command execution failed"""
```

### Error Recovery Strategies

1. **Provider Fallback**: Try alternative providers when primary fails
2. **Graceful Degradation**: Continue with limited functionality when possible
3. **Detailed Logging**: Capture full context for troubleshooting
4. **User Guidance**: Provide actionable error messages

## Testing Strategy

### Unit Testing

- **Provider Tests**: Mock system commands, test provider logic
- **Loader Tests**: Test saidata loading, validation, and merging
- **CLI Tests**: Test argument parsing and command routing
- **Configuration Tests**: Test config loading and validation

### Integration Testing

- **End-to-End Workflows**: Test complete action execution paths
- **Provider Integration**: Test with real package managers in containers
- **Cross-Platform Testing**: Validate behavior across OS platforms
- **Performance Testing**: Measure startup time and execution speed

### Test Structure

```
tests/
├── unit/
│   ├── test_providers/
│   ├── test_core/
│   └── test_cli/
├── integration/
│   ├── test_workflows/
│   └── test_providers/
├── fixtures/
│   ├── saidata/
│   └── configs/
└── conftest.py
```

## Performance Considerations

### Caching Strategy

1. **Provider Detection Cache**: Cache available providers between runs
2. **Saidata Cache**: Cache parsed and validated saidata files
3. **Command Result Cache**: Cache non-destructive command results
4. **Schema Cache**: Cache compiled JSON schemas

### Lazy Loading

- Load providers only when needed
- Parse saidata files on-demand
- Initialize logging subsystem lazily

### Optimization Points

- Parallel provider detection
- Efficient file system scanning
- Minimal memory footprint for CLI operations
- Fast startup time (< 100ms for cached operations)

## Security Considerations

### Command Injection Prevention

- Strict input validation and sanitization
- Use of parameterized commands where possible
- Whitelist approach for allowed characters in software names

### Privilege Management

- Run with minimal required privileges
- Clear documentation of required permissions
- Graceful handling of permission errors

### File System Security

- Validate file paths to prevent directory traversal
- Secure temporary file handling
- Proper file permission management

## Extensibility Design

### Dynamic Provider Loading

```python
class ProviderLoader:
    """Dynamically loads providers from YAML files"""
    
    def scan_provider_directory(self, path: Path) -> List[ProviderData]:
        """Scan directory for provider YAML files"""
        
    def validate_provider_data(self, data: dict) -> ValidationResult:
        """Validate provider YAML against schema"""
        
    def create_provider_instances(self) -> List[BaseProvider]:
        """Create provider instances from YAML data"""
```

### Configuration Extension Points

- Custom provider priority rules
- Additional saidata search paths
- Pluggable validation rules
- Custom output formatters

### Future Enhancement Hooks

- Remote provider repositories (download provider YAML files)
- Custom provider directories via configuration
- Provider YAML template inheritance
- Integration with external tools (MCP servers)
- Provider-specific configuration overrides

## CLI Design

### Command Structure

```bash
sai <action> <software> [options]
sai providers [list|detect|info <name>]
sai config [show|set <key> <value>]
sai validate <saidata-file>
```

### Global Options

- `--provider <name>`: Force specific provider
- `--dry-run`: Show what would be executed
- `--verbose`: Detailed output
- `--config <file>`: Use specific config file
- `--no-cache`: Disable caching

### Output Formats

- **Default**: Human-readable colored output
- **JSON**: Machine-readable structured output (`--json`)
- **Quiet**: Minimal output (`--quiet`)
- **Progress**: Progress bars for long operations (`--progress`)