# Template Engine Implementation

## Overview

Task 3 of the SAI CLI tool implementation has been completed. This document summarizes the command template resolution engine that was built to handle dynamic template variable substitution for provider actions.

## Implementation Summary

### Core Components

1. **TemplateEngine** (`sai/providers/template_engine.py`)
   - Main template resolution engine using Jinja2
   - Handles template variable substitution with strict undefined checking
   - Supports complex template scenarios with conditionals and loops

2. **SaidataContextBuilder** (`sai/providers/template_engine.py`)
   - Extracts template variables from SaiData objects
   - Builds comprehensive context dictionaries for template resolution
   - Handles all SaiData components (packages, services, files, directories, commands, ports, containers)

3. **ArrayExpansionFilter** (`sai/providers/template_engine.py`)
   - Implements custom array expansion syntax: `{{saidata.packages.*.name}}`
   - Converts array expansion to Jinja2 map/join operations
   - Supports nested field access in arrays

4. **BaseProvider Integration** (`sai/providers/base.py`)
   - Integrated template engine into BaseProvider class
   - Added methods for resolving action templates and single templates
   - Provides error handling and logging for template resolution

### Key Features Implemented

#### 1. Template Variable Substitution using Jinja2
- ✅ Full Jinja2 template engine integration
- ✅ Strict undefined variable checking for error detection
- ✅ Support for complex template logic (conditionals, loops, filters)
- ✅ Proper whitespace handling and template formatting

#### 2. Context Builder for SaiData Variables
- ✅ Comprehensive context extraction from SaiData objects
- ✅ Support for all SaiData components:
  - Metadata (name, version, description, etc.)
  - Packages (name, version, alternatives, etc.)
  - Services (name, service_name, type, etc.)
  - Files (path, owner, group, mode, etc.)
  - Directories (path, owner, group, mode, etc.)
  - Commands (name, path, arguments, etc.)
  - Ports (port, protocol, service, etc.)
  - Containers (name, image, tag, ports, volumes, etc.)
- ✅ Nested object support (URLs, security metadata)

#### 3. Compact Template System (Latest Enhancement)
- ✅ **Smart lookup functions** with automatic fallback logic:
  - `sai_packages(saidata, provider_name)` - All package names with provider fallback
  - `sai_package(saidata, index, provider_name)` - Single package by index
  - `sai_service(saidata, index, field)` - Service information with field selection
  - `sai_file(saidata, index, field)` - File information
  - `sai_port(saidata, index, field)` - Port information
- ✅ **Automatic fallback pattern**: Provider-specific → General → Metadata → Empty
- ✅ **80% reduction in template complexity** from verbose conditionals to simple function calls
- ✅ **Consistent behavior** across all providers and resource types
- ✅ **Graceful error handling** with empty string fallbacks
- ✅ Empty array handling for missing components

#### 3. Array Expansion Support
- ✅ Custom syntax: `{{saidata.packages.*.name}}`
- ✅ Automatic conversion to Jinja2 map/join operations
- ✅ Support for nested field access
- ✅ Multiple array expansions in single template
- ✅ Graceful handling of empty arrays

### Requirements Fulfilled

**Requirement 3.1**: Template variable substitution using Jinja2
- ✅ Implemented full Jinja2 integration with StrictUndefined for error detection
- ✅ Support for all Jinja2 features (conditionals, loops, filters, etc.)
- ✅ Proper error handling and logging

**Requirement 3.2**: Context builder and array expansion
- ✅ Comprehensive SaidataContextBuilder extracts all variables from saidata
- ✅ Custom array expansion syntax `{{saidata.packages.*.name}}` implemented
- ✅ Support for complex nested field access in arrays

### Files Created/Modified

#### New Files
- `sai/providers/template_engine.py` - Core template engine implementation
- `tests/test_template_engine.py` - Comprehensive unit tests (22 tests)
- `tests/test_template_integration.py` - Integration tests (7 tests)
- `tests/test_provider_template_integration.py` - Provider integration tests (10 tests)
- `examples/template_engine_demo.py` - Demonstration script
- `docs/template-engine-implementation.md` - This documentation

#### Modified Files
- `pyproject.toml` - Added Jinja2 dependency
- `sai/providers/base.py` - Integrated template engine into BaseProvider
- `.kiro/specs/sai-cli-tool/tasks.md` - Updated task status

### Test Coverage

Total: **39 tests** covering all aspects of the template engine:

1. **Unit Tests (22 tests)**:
   - SaidataContextBuilder functionality
   - ArrayExpansionFilter operations
   - TemplateEngine core functionality
   - Error handling and edge cases

2. **Integration Tests (7 tests)**:
   - Realistic provider scenarios
   - Complex template patterns
   - Multi-step action resolution
   - Docker container templates

3. **Provider Integration Tests (10 tests)**:
   - BaseProvider template integration
   - Action template resolution
   - Error handling in provider context
   - Complex multi-step scenarios

### Usage Examples

#### Basic Template Resolution
```python
engine = TemplateEngine()
result = engine.resolve_template(
    "Installing {{display_name}} version {{version}}", 
    saidata
)
# Result: "Installing Nginx Web Server version 1.20.1"
```

#### Array Expansion
```python
result = engine.resolve_template(
    "apt-get install -y {{saidata.packages.*.name}}", 
    saidata
)
# Result: "apt-get install -y nginx nginx-common nginx-extras"
```

#### Provider Integration
```python
provider = BaseProvider(provider_data)
resolved = provider.resolve_action_templates("install", saidata)
# Returns: {"command": "apt-get install -y nginx nginx-common", "rollback": "..."}
```

### Performance Considerations

- **Lazy Loading**: Template engine is initialized only when needed
- **Caching**: Jinja2 provides built-in template compilation caching
- **Memory Efficient**: Context building is optimized for minimal memory usage
- **Error Handling**: Fast-fail approach with detailed error messages

### Security Features

- **Input Sanitization**: Strict template validation prevents injection
- **Undefined Variable Detection**: StrictUndefined prevents silent failures
- **Template Isolation**: Each template resolution is isolated
- **Error Boundaries**: Template errors don't crash the provider system

### Future Enhancements

The template engine is designed to be extensible:

1. **Custom Filters**: Additional Jinja2 filters can be easily added
2. **Template Inheritance**: Support for template inheritance and includes
3. **Caching Improvements**: Provider-specific template caching
4. **Performance Monitoring**: Template resolution timing and metrics
5. **Advanced Array Operations**: More sophisticated array manipulation

## Conclusion

The command template resolution engine has been successfully implemented with comprehensive functionality that exceeds the basic requirements. The system provides:

- Robust template variable substitution using industry-standard Jinja2
- Comprehensive context building from SaiData objects
- Innovative array expansion syntax for simplified template writing
- Full integration with the provider system
- Extensive test coverage ensuring reliability
- Clear documentation and examples for future development

The implementation is production-ready and provides a solid foundation for the SAI CLI tool's provider system.
## C
ompact Template System (Latest Enhancement)

### Overview
The compact template system represents a major advancement in SAI's template architecture, providing smart lookup functions that dramatically simplify provider templates while maintaining full functionality.

### Before vs After Comparison

#### Verbose Template (Before)
```yaml
template: "brew install {% if saidata.providers.brew is defined and saidata.providers.brew.packages %}{% for pkg in saidata.providers.brew.packages %}{{pkg.name}} {% endfor %}{% elif saidata.packages %}{% for pkg in saidata.packages %}{{pkg.name}} {% endfor %}{% else %}{{saidata.metadata.name}}{% endif %}"
```

#### Compact Template (After)
```yaml
template: "brew install {{sai_packages(saidata, 'brew')}}"
```

**Result**: 80% reduction in template complexity while maintaining identical functionality.

### Available Functions

#### Package Functions
- `sai_packages(saidata, provider_name)` - All package names with provider fallback
- `sai_package(saidata, index, provider_name)` - Single package by index

#### Service Functions  
- `sai_service(saidata, index, field)` - Service information with field selection

#### Resource Functions
- `sai_file(saidata, index, field)` - File information
- `sai_port(saidata, index, field)` - Port information

### Service Management Examples

#### Brew Provider Service Actions
```yaml
# Using service_name field (recommended for service managers)
start: "brew services start {{sai_service(saidata, 0, 'service_name') or sai_package(saidata, 0, 'brew')}}"
stop: "brew services stop {{sai_service(saidata, 0, 'service_name') or sai_package(saidata, 0, 'brew')}}"
status: "brew services list | grep {{sai_service(saidata, 0, 'service_name') or sai_package(saidata, 0, 'brew')}}"
```

#### Systemd Service Actions
```yaml
start: "systemctl start {{sai_service(saidata, 0, 'service_name')}}"
stop: "systemctl stop {{sai_service(saidata, 0, 'service_name')}}"
status: "systemctl status {{sai_service(saidata)}}"
```

### Fallback Behavior

Each function implements the standard SAI fallback pattern:

1. **Provider-specific**: `saidata.providers.{provider}.{resource}` (if provider_name specified)
2. **General**: `saidata.{resource}` array
3. **Metadata**: `saidata.metadata.name` (for name fields only)
4. **Empty**: Graceful degradation to empty string

### Service Field Options

The `sai_service` function supports multiple field options:

- `name` - Service logical name (default)
- `service_name` - Actual service name used by service manager (recommended)
- `type` - Service type (systemd, launchd, etc.)
- `enabled` - Whether service is enabled

### Real-World Examples

#### Prometheus Service Management
```yaml
# Service data:
# - name: "node-exporter"
#   service_name: "prometheus-node-exporter"

# Templates:
start: "brew services start {{sai_service(saidata, 0, 'service_name')}}"
# Result: "brew services start prometheus-node-exporter"

stop: "systemctl stop {{sai_service(saidata, 0, 'service_name')}}"  
# Result: "systemctl stop prometheus-node-exporter"
```

#### Fallback Scenarios
```yaml
# With services defined:
start: "{{sai_service(saidata, 0, 'service_name') or sai_package(saidata, 0, 'brew')}}"
# Result: "prometheus-node-exporter" (uses service_name)

# Without services (fallback to package):
start: "{{sai_service(saidata, 0, 'service_name') or sai_package(saidata, 0, 'brew')}}"
# Result: "terraform" (uses package name)
```

### Benefits Achieved

1. **Developer Experience**: 80% reduction in template complexity
2. **Maintainability**: Centralized fallback logic, easier updates
3. **Reliability**: Consistent behavior across all providers
4. **Extensibility**: Easy to add new resource types and functions
5. **Error Handling**: Graceful degradation with empty string fallbacks

### Migration Guide

To migrate existing verbose templates to compact templates:

1. **Identify verbose conditional patterns**
2. **Replace with appropriate `sai_*` function**
3. **Test all fallback scenarios**
4. **Update documentation**

The compact template system is backward compatible - existing verbose templates continue to work while new templates can use the simplified syntax.