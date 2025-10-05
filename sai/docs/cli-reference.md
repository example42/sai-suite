# SAI CLI Reference

Complete command-line reference for the SAI (Software Action Interface) tool.

## Overview

SAI is a cross-platform software management CLI tool that executes actions using provider-based configurations and saidata files.

**Default Repository:** `https://github.com/example42/saidata`  
**Cache Location:** `~/.sai/cache/repositories/`

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

## See Also

- [sai-apply-command.md](sai-apply-command.md) - Detailed apply command documentation
- [template-engine.md](template-engine.md) - Template engine documentation
- [examples/](examples/) - Configuration examples
