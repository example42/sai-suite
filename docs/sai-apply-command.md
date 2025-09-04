# SAI Apply Command

The `sai apply` command allows you to execute multiple software management actions from a single YAML or JSON file. This is useful for automating complex deployment scenarios, setting up development environments, or managing multiple software packages at once.

## Usage

```bash
sai apply <action_file> [OPTIONS]
```

### Options

- `--parallel` - Execute actions in parallel when possible (experimental)
- `--continue-on-error` - Continue executing remaining actions if one fails
- `--timeout <seconds>` - Default timeout for all actions in seconds

All global SAI options are also supported:
- `--verbose, -v` - Enable verbose output
- `--dry-run` - Show what would be done without executing
- `--yes, -y` - Assume yes for all prompts
- `--quiet, -q` - Suppress non-essential output
- `--provider, -p` - Force specific provider for all actions
- `--json` - Output results in JSON format

## Action File Format

Action files can be written in YAML or JSON format and must contain:

1. **config** (optional) - Configuration options for execution
2. **actions** (required) - Software management actions to perform

### Basic Structure

```yaml
---
config:
  verbose: true
  dry_run: false
  continue_on_error: true

actions:
  install:
    - nginx
    - curl
    - git
  start:
    - nginx
```

### Configuration Options

The `config` section supports the following options:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `verbose` | boolean | false | Enable verbose output |
| `dry_run` | boolean | false | Show what would be done without executing |
| `yes` | boolean | false | Assume yes for all prompts |
| `quiet` | boolean | false | Suppress non-essential output |
| `timeout` | integer | null | Default timeout in seconds |
| `provider` | string | null | Force specific provider for all actions |
| `parallel` | boolean | false | Execute actions in parallel when possible |
| `continue_on_error` | boolean | false | Continue executing remaining actions if one fails |

### Action Types

The `actions` section supports the following action types:

- **install** - Install software packages
- **uninstall** - Uninstall software packages  
- **start** - Start services
- **stop** - Stop services
- **restart** - Restart services

### Action Items

Each action type accepts a list of items that can be either:

1. **Simple string** - Just the software/service name
2. **Object with options** - Name with additional configuration

#### Simple Format
```yaml
actions:
  install:
    - nginx
    - curl
    - git
```

#### Advanced Format
```yaml
actions:
  install:
    - name: nginx
      provider: apt
      timeout: 300
    - name: docker
      provider: snap
      timeout: 600
```

#### Object Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | Software or service name (required) |
| `provider` | string | Specific provider to use for this item |
| `timeout` | integer | Timeout in seconds for this specific action |

## Examples

### Simple Installation

```yaml
---
config:
  verbose: true

actions:
  install:
    - nginx
    - curl
    - git
```

### Complex Deployment

```yaml
---
config:
  verbose: true
  continue_on_error: true
  timeout: 300

actions:
  install:
    - nginx
    - name: docker
      provider: apt
      timeout: 600
    - name: nodejs
      provider: snap
    - postgresql
    - redis

  start:
    - nginx
    - docker
    - postgresql
    - redis

  # Optional: Clean up old packages
  uninstall:
    - apache2
    - old-nodejs
```

### Development Environment Setup

```yaml
---
config:
  verbose: true
  parallel: false
  continue_on_error: false

actions:
  install:
    # Development tools
    - git
    - curl
    - wget
    - vim
    
    # Programming languages
    - name: python3
      provider: apt
    - name: nodejs
      provider: snap
    - name: go
      provider: snap
    
    # Databases
    - postgresql
    - redis
    - mongodb
    
    # Containers
    - name: docker
      provider: apt
      timeout: 600

  start:
    - postgresql
    - redis
    - docker
```

### JSON Format Example

```json
{
  "config": {
    "verbose": true,
    "dry_run": false,
    "continue_on_error": true
  },
  "actions": {
    "install": [
      "nginx",
      "curl",
      {
        "name": "docker",
        "provider": "apt",
        "timeout": 600
      }
    ],
    "start": [
      "nginx",
      "docker"
    ]
  }
}
```

## Execution Behavior

### Sequential Execution (Default)

By default, actions are executed sequentially:
1. All `install` actions are executed in order
2. Then all `uninstall` actions
3. Then all `start` actions
4. Then all `stop` actions  
5. Finally all `restart` actions

Within each action type, items are processed in the order they appear in the file.

### Parallel Execution

When `--parallel` is specified or `parallel: true` is set in config:
- Actions of the same type can be executed in parallel
- Different action types are still executed in sequence
- Maximum of 4 concurrent operations

### Error Handling

By default, execution stops on the first error. With `continue_on_error: true`:
- Failed actions are logged but don't stop execution
- Remaining actions continue to execute
- Final result shows success/failure summary

### Configuration Precedence

Configuration options are applied in this order (highest to lowest precedence):

1. Command-line options (`--verbose`, `--dry-run`, etc.)
2. Action file `config` section
3. Global SAI configuration
4. Default values

## Output Formats

### Human-Readable Output (Default)

```
✓ Successfully executed 4/5 actions (1 failed)
Execution time: 45.2s
Success rate: 80.0%
  ✓ install nginx
  ✓ install curl
  ✗ install docker: Provider 'apt' cannot handle 'docker'
  ✓ start nginx
  ✓ start curl
```

### JSON Output

Use `--json` flag for machine-readable output:

```json
{
  "success": true,
  "total_actions": 3,
  "successful_actions": 3,
  "failed_actions": 0,
  "success_rate": 100.0,
  "execution_time": 12.5,
  "results": [
    {
      "action_type": "install",
      "software": "nginx",
      "success": true,
      "provider_used": "apt",
      "commands_executed": ["apt install -y nginx"],
      "execution_time": 5.2
    }
  ]
}
```

## Best Practices

1. **Use dry-run first** - Always test with `--dry-run` before actual execution
2. **Group related actions** - Keep related software installations together
3. **Set appropriate timeouts** - Some packages take longer to install
4. **Use continue-on-error for optional packages** - Don't let optional packages break the entire deployment
5. **Specify providers when needed** - Use specific providers for better control
6. **Version control your action files** - Keep action files in version control for reproducible deployments

## Troubleshooting

### Common Issues

1. **No providers found** - Ensure package managers are installed and available
2. **Permission denied** - Run with appropriate privileges or use `sudo`
3. **Timeout errors** - Increase timeout values for slow operations
4. **Provider conflicts** - Specify explicit providers to avoid conflicts

### Debugging

Use these options for debugging:
- `--verbose` - See detailed execution information
- `--dry-run` - Preview what would be executed
- `--json` - Get structured output for analysis

### Validation

Validate your action file before execution:
```bash
# The apply command will validate the file before execution
sai apply my-actions.yaml --dry-run
```