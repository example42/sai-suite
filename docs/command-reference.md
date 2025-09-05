# SAI & SAIGEN Command Reference

This document provides a comprehensive reference for all available commands in both SAI and SAIGEN tools.

## Table of Contents

- [SAI Commands](#sai-commands)
  - [Software Management](#software-management)
  - [Batch Operations](#batch-operations)
  - [System Management](#system-management)
- [SAIGEN Commands](#saigen-commands)
  - [Generation Commands](#generation-commands)
  - [Validation Commands](#validation-commands)
  - [Repository Management](#repository-management)
  - [Configuration Management](#configuration-management)
  - [Cache Management](#cache-management)
  - [Utility Commands](#utility-commands)

---

## SAI Commands

SAI (Software Action Interface) is a cross-platform software management CLI tool that executes actions using provider-based configurations.

### Global Options

All SAI commands support these global options:

```bash
sai [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGUMENTS]
```

**Global Options:**
- `--config, -c PATH` - Path to configuration file
- `--provider, -p NAME` - Force specific provider (apt, brew, winget, etc.)
- `--verbose, -v` - Enable verbose output
- `--dry-run` - Show what would be done without executing
- `--yes, -y` - Assume yes for all prompts
- `--quiet, -q` - Suppress non-essential output
- `--json` - Output in JSON format
- `--version` - Show version and exit
- `--help` - Show help message

### Software Management

#### install
Install software using the best available provider.

```bash
sai install SOFTWARE [OPTIONS]
```

**Options:**
- `--timeout SECONDS` - Command timeout in seconds
- `--no-cache` - Skip cache and perform fresh operations

**Examples:**
```bash
sai install nginx
sai install --provider apt nginx
sai install --timeout 300 docker
sai --dry-run install postgresql
```

#### uninstall
Uninstall software using the best available provider.

```bash
sai uninstall SOFTWARE [OPTIONS]
```

**Options:**
- `--timeout SECONDS` - Command timeout in seconds
- `--no-cache` - Skip cache and perform fresh operations

**Examples:**
```bash
sai uninstall nginx
sai uninstall --provider brew nodejs
sai --yes uninstall old-package
```

#### start
Start software service.

```bash
sai start SOFTWARE [OPTIONS]
```

**Options:**
- `--timeout SECONDS` - Command timeout in seconds
- `--no-cache` - Skip cache and perform fresh operations

**Examples:**
```bash
sai start nginx
sai start --provider systemd postgresql
```

#### stop
Stop software service.

```bash
sai stop SOFTWARE [OPTIONS]
```

**Options:**
- `--timeout SECONDS` - Command timeout in seconds
- `--no-cache` - Skip cache and perform fresh operations

**Examples:**
```bash
sai stop nginx
sai stop --provider systemd apache2
```

#### restart
Restart software service.

```bash
sai restart SOFTWARE [OPTIONS]
```

**Options:**
- `--timeout SECONDS` - Command timeout in seconds
- `--no-cache` - Skip cache and perform fresh operations

**Examples:**
```bash
sai restart nginx
sai restart --provider systemd mysql
```

#### status
Show software service status.

```bash
sai status SOFTWARE [OPTIONS]
```

**Options:**
- `--timeout SECONDS` - Command timeout in seconds
- `--no-cache` - Skip cache and perform fresh operations

**Examples:**
```bash
sai status nginx
sai status --json docker
sai --quiet status apache2
```

#### info
Show software information.

```bash
sai info SOFTWARE [OPTIONS]
```

**Options:**
- `--timeout SECONDS` - Command timeout in seconds
- `--no-cache` - Skip cache and perform fresh operations

**Examples:**
```bash
sai info nginx
sai info --json postgresql
sai info --provider apt docker
```

#### search
Search for available software.

```bash
sai search TERM [OPTIONS]
```

**Options:**
- `--timeout SECONDS` - Command timeout in seconds
- `--no-cache` - Skip cache and perform fresh operations

**Examples:**
```bash
sai search nginx
sai search --provider brew "web server"
sai search --json database
```

#### list
List installed software managed through sai.

```bash
sai list [OPTIONS]
```

**Options:**
- `--timeout SECONDS` - Command timeout in seconds
- `--no-cache` - Skip cache and perform fresh operations

**Examples:**
```bash
sai list
sai list --json
sai list --provider apt
```

#### logs
Show software service logs.

```bash
sai logs SOFTWARE [OPTIONS]
```

**Options:**
- `--timeout SECONDS` - Command timeout in seconds
- `--no-cache` - Skip cache and perform fresh operations

**Examples:**
```bash
sai logs nginx
sai logs --provider systemd postgresql
```

#### version
Show software version information.

```bash
sai version SOFTWARE [OPTIONS]
```

**Options:**
- `--timeout SECONDS` - Command timeout in seconds
- `--no-cache` - Skip cache and perform fresh operations

**Examples:**
```bash
sai version nginx
sai version --json docker
```

### Batch Operations

#### apply
Apply multiple actions from an action file.

```bash
sai apply ACTION_FILE [OPTIONS]
```

**Options:**
- `--parallel` - Execute actions in parallel when possible
- `--continue-on-error` - Continue executing remaining actions if one fails
- `--timeout SECONDS` - Default timeout for all actions in seconds

**Action File Format (YAML):**
```yaml
---
config:
  verbose: true
  dry_run: false
actions:
  install:
    - nginx
    - name: docker
      provider: apt
  start:
    - nginx
    - docker
  status:
    - nginx
```

**Action File Format (JSON):**
```json
{
  "config": {
    "verbose": true,
    "dry_run": false
  },
  "actions": {
    "install": [
      "nginx",
      {"name": "docker", "provider": "apt"}
    ],
    "start": ["nginx", "docker"]
  }
}
```

**Examples:**
```bash
sai apply deployment.yaml
sai apply --parallel --continue-on-error setup.yaml
sai --dry-run apply production.yaml
```

### System Management

#### cache
Manage SAI cache system.

##### cache status
Show cache status and statistics.

```bash
sai cache status [OPTIONS]
```

**Examples:**
```bash
sai cache status
sai cache status --json
```

##### cache clear
Clear cache data.

```bash
sai cache clear [OPTIONS]
```

**Options:**
- `--provider, -p NAME` - Clear cache for specific provider only
- `--saidata, -s NAME` - Clear cache for specific saidata only
- `--all` - Clear all cache data

**Examples:**
```bash
sai cache clear --all
sai cache clear --provider apt
sai cache clear --saidata nginx
```

##### cache cleanup
Clean up expired cache entries.

```bash
sai cache cleanup
```

**Examples:**
```bash
sai cache cleanup
```

---

## SAIGEN Commands

SAIGEN (SAI data Generation) is a comprehensive tool for generating, validating, and managing software metadata in YAML format.

### Global Options

All SAIGEN commands support these global options:

```bash
saigen [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGUMENTS]
```

**Global Options:**
- `--config PATH` - Configuration file path
- `--llm-provider NAME` - LLM provider to use (openai, anthropic, ollama)
- `--verbose, -v` - Enable verbose output
- `--dry-run` - Show what would be done without executing
- `--version` - Show version and exit
- `--help` - Show help message

### Generation Commands

#### generate
Generate saidata for a software package.

```bash
saigen generate SOFTWARE_NAME [OPTIONS]
```

**Options:**
- `--output, -o PATH` - Output file path (default: `<software_name>.yaml`)
- `--providers PROVIDER` - Target providers for saidata (can be specified multiple times)
- `--no-rag` - Disable RAG context injection
- `--force` - Overwrite existing files
- `--log-file PATH` - Log file path for detailed generation process logging (default: auto-generated)

**Examples:**
```bash
saigen generate nginx
saigen generate --providers apt --providers brew --output custom.yaml nginx
saigen generate --no-rag --dry-run postgresql
saigen generate --force --verbose docker
saigen generate --log-file ./nginx-generation.json nginx
```

**Automatic Retry Mechanism:**
The generate command includes an intelligent retry system that automatically attempts a second LLM query when the first generation fails validation:
- Captures detailed validation errors from the first attempt
- Provides specific feedback to the LLM about what needs to be fixed
- Uses enhanced prompts designed for error correction
- Significantly improves success rates for complex saidata generation
- All retry attempts are logged for monitoring and debugging

**Generation Logging:**
The `--log-file` option enables comprehensive logging of the generation process, capturing:
- All LLM interactions (prompts sent and responses received)
- Repository data operations and RAG queries
- Validation steps and results
- Retry attempts with validation feedback
- File operations and timing information
- Error details and debugging information

If no log file is specified, logs are automatically saved to `~/.saigen/logs/` with timestamped filenames.

#### batch
Generate saidata for multiple software packages in batch.

```bash
saigen batch [OPTIONS]
```

**Options:**
- `--input-file, -f PATH` - Input file containing software names (one per line)
- `--software-list, -s NAME` - Software names to process (can be specified multiple times)
- `--output-dir, -o PATH` - Output directory for generated saidata files
- `--providers PROVIDER` - Target providers for saidata (can be specified multiple times)
- `--category-filter, -c PATTERN` - Filter by category using regex pattern
- `--max-concurrent, -j NUMBER` - Maximum number of concurrent generations (default: 3)
- `--no-rag` - Disable RAG context injection
- `--stop-on-error` - Stop processing on first error
- `--force` - Overwrite existing files
- `--preview` - Preview what would be processed without generating

**Examples:**
```bash
# Generate from file
saigen batch -f software_list.txt -o output/

# Generate specific software
saigen batch -s nginx -s postgresql -s redis -o output/

# Filter by category
saigen batch -f web_tools.txt -c "database|cache" -o output/

# Control concurrency
saigen batch -f large_list.txt -j 5 -o output/

# Preview mode
saigen batch -f software_list.txt --preview
```

### Validation Commands

#### validate
Validate a saidata YAML file against the schema.

```bash
saigen validate FILE_PATH [OPTIONS]
```

**Options:**
- `--schema PATH` - Path to custom saidata schema file
- `--show-context` - Show detailed context information for errors
- `--format FORMAT` - Output format for validation results (text, json)

**Examples:**
```bash
saigen validate nginx.yaml
saigen validate --schema custom-schema.json software.yaml
saigen validate --show-context --format json software.yaml
```

#### test
Test saidata files using MCP servers.

```bash
saigen test [OPTIONS]
```

**Options:**
- `--file, -f PATH` - Specific saidata file to test
- `--directory, -d PATH` - Directory containing saidata files to test
- `--mcp-server NAME` - Specific MCP server to use for testing
- `--timeout SECONDS` - Test timeout in seconds
- `--parallel` - Run tests in parallel

**Examples:**
```bash
saigen test -f nginx.yaml
saigen test -d saidata/ --parallel
saigen test --mcp-server local-server nginx.yaml
```

### Repository Management

#### repositories
Manage 50+ package repositories across all platforms.

##### repositories list-repos
List available repositories from 50+ supported package managers.

```bash
saigen repositories list-repos [OPTIONS]
```

**Options:**
- `--platform PLATFORM` - Filter by platform (linux, macos, windows, universal)
- `--type TYPE` - Filter by repository type (apt, brew, npm, pypi, cargo, etc.)
- `--format FORMAT` - Output format (table, json, yaml)
- `--cache-dir PATH` - Cache directory path
- `--config-dir PATH` - Configuration directory path

**Examples:**
```bash
saigen repositories list-repos
saigen repositories list-repos --platform linux
saigen repositories list-repos --type npm --format json
```

##### repositories search
Search for packages across all 50+ repositories concurrently.

```bash
saigen repositories search QUERY [OPTIONS]
```

**Options:**
- `--platform PLATFORM` - Filter by platform (linux, macos, windows, universal)
- `--type TYPE` - Filter by repository type (apt, brew, npm, pypi, etc.)
- `--limit NUMBER` - Maximum number of results (default: 20)
- `--format FORMAT` - Output format (table, json, yaml)
- `--cache-dir PATH` - Cache directory path
- `--config-dir PATH` - Configuration directory path

**Examples:**
```bash
saigen repositories search "redis"
saigen repositories search "nginx" --platform linux --limit 10
saigen repositories search "react" --type npm --format json
```

##### repositories info
Get detailed information about a package.

```bash
saigen repositories info PACKAGE_NAME [OPTIONS]
```

**Options:**
- `--version VERSION` - Specific version to get details for
- `--platform PLATFORM` - Filter by platform
- `--format FORMAT` - Output format (table, json, yaml)
- `--cache-dir PATH` - Cache directory path
- `--config-dir PATH` - Configuration directory path

**Examples:**
```bash
saigen repositories info nginx
saigen repositories info --version 1.20.1 nginx
saigen repositories info --platform linux --format json postgresql
```

##### repositories stats
Show comprehensive repository statistics and health information.

```bash
saigen repositories stats [OPTIONS]
```

**Options:**
- `--platform PLATFORM` - Filter by platform (linux, macos, windows, universal)
- `--type TYPE` - Filter by repository type (apt, brew, npm, etc.)
- `--format FORMAT` - Output format (table, json, yaml)
- `--cache-dir PATH` - Cache directory path
- `--config-dir PATH` - Configuration directory path

**Examples:**
```bash
saigen repositories stats
saigen repositories stats --platform linux
saigen repositories stats --format json
```

##### repositories update-cache
Update repository cache.

```bash
saigen repositories update-cache [OPTIONS]
```

**Options:**
- `--repository NAME` - Specific repository to update
- `--force` - Force update even if cache is valid
- `--cache-dir PATH` - Cache directory path
- `--config-dir PATH` - Configuration directory path

**Examples:**
```bash
saigen repositories update-cache
saigen repositories update-cache --repository apt-main
saigen repositories update-cache --force
```

### Configuration Management

#### config
Manage saigen configuration.

##### config show
Show current configuration.

```bash
saigen config show [OPTIONS]
```

**Options:**
- `--format FORMAT` - Output format (yaml, json)
- `--section SECTION` - Show only specific configuration section

**Examples:**
```bash
saigen config show
saigen config show --format json
saigen config show --section llm_providers
```

##### config set
Set a configuration value.

```bash
saigen config set KEY VALUE [OPTIONS]
```

**Options:**
- `--type TYPE` - Value type for proper conversion (string, int, float, bool)

**Examples:**
```bash
saigen config set generation.default_providers "apt,brew"
saigen config set cache.max_size_mb 2000 --type int
saigen config set rag.enabled true --type bool
saigen config set llm_providers.openai.model gpt-4
```

##### config validate
Validate current configuration.

```bash
saigen config validate
```

**Examples:**
```bash
saigen config validate
```

##### config init
Initialize a new configuration file.

```bash
saigen config init [OPTIONS]
```

**Options:**
- `--force` - Overwrite existing configuration

**Examples:**
```bash
saigen config init
saigen config init --force
```

##### config samples
Configure sample saidata directory for LLM examples.

```bash
saigen config samples [OPTIONS]
```

**Options:**
- `--directory, -d PATH` - Set custom sample directory path
- `--auto-detect` - Auto-detect sample directory
- `--disable` - Disable use of sample data

**Examples:**
```bash
saigen config samples --auto-detect
saigen config samples --directory /path/to/samples
saigen config samples --disable
```

### Cache Management

#### cache
Manage saigen cache system.

##### cache status
Show cache status and statistics.

```bash
saigen cache status [OPTIONS]
```

**Options:**
- `--format FORMAT` - Output format (text, json)

**Examples:**
```bash
saigen cache status
saigen cache status --format json
```

##### cache clear
Clear cache data.

```bash
saigen cache clear [OPTIONS]
```

**Options:**
- `--type TYPE` - Cache type to clear (repository, rag, all)
- `--repository NAME` - Clear cache for specific repository
- `--force` - Force clear without confirmation

**Examples:**
```bash
saigen cache clear --type all
saigen cache clear --type repository --repository apt-main
saigen cache clear --force
```

##### cache cleanup
Clean up expired cache entries.

```bash
saigen cache cleanup
```

**Examples:**
```bash
saigen cache cleanup
```

### Utility Commands

#### update
Update saigen components.

```bash
saigen update [OPTIONS]
```

**Options:**
- `--component COMPONENT` - Specific component to update (schema, samples, repositories)
- `--force` - Force update even if current version is latest

**Examples:**
```bash
saigen update
saigen update --component schema
saigen update --force
```

#### index
Manage RAG index for enhanced generation.

```bash
saigen index [OPTIONS]
```

**Options:**
- `--rebuild` - Rebuild the entire index
- `--add PATH` - Add files to the index
- `--remove PATH` - Remove files from the index
- `--status` - Show index status

**Examples:**
```bash
saigen index --status
saigen index --rebuild
saigen index --add /path/to/samples/
```

---

## Environment Variables

### SAI Environment Variables
- `SAI_LOG_LEVEL` - Override log level (debug, info, warning, error)
- `SAI_CACHE_DIR` - Override cache directory
- `SAI_CONFIG_PATH` - Override config file path

### SAIGEN Environment Variables
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `SAIGEN_LOG_LEVEL` - Override log level (debug, info, warning, error)
- `SAIGEN_CACHE_DIR` - Override cache directory
- `SAIGEN_OUTPUT_DIR` - Override output directory

---

## Exit Codes

Both tools use standard exit codes:
- `0` - Success
- `1` - General error
- `2` - Misuse of shell command (invalid arguments)
- `130` - Script terminated by Control-C

---

## Configuration Files

### SAI Configuration Locations
1. `~/.sai/config.yaml`
2. `~/.sai/config.json`
3. `./.sai.yaml`
4. `./.sai.json`
5. `./sai.yaml`
6. `./sai.json`

### SAIGEN Configuration Locations
1. `~/.saigen/config.yaml`
2. `~/.saigen/config.json`
3. `./.saigen.yaml`
4. `./.saigen.json`
5. `./saigen.yaml`
6. `./saigen.json`

---

## Examples and Use Cases

### Common SAI Workflows

```bash
# Install and start a web server
sai install nginx
sai start nginx
sai status nginx

# Batch deployment
sai apply deployment.yaml --parallel

# Search and install with specific provider
sai search "web server" --provider apt
sai install --provider apt apache2
```

### Common SAIGEN Workflows

```bash
# Generate saidata for a single package
saigen generate nginx --providers apt --providers brew

# Batch generate from file
saigen batch -f software_list.txt -o output/ -j 5

# Validate generated files
saigen validate output/nginx.yaml --show-context

# Search repositories for packages
saigen repositories search "database" --limit 5

# Configure and test
saigen config samples --auto-detect
saigen test -d output/ --parallel
```

For more detailed information about specific commands, use the `--help` option with any command:

```bash
sai --help
sai install --help
saigen --help
saigen generate --help
```