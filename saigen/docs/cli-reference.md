# SAIGEN CLI Reference

Complete command-line reference for the SAIGEN (SAI Data Generation) tool.

## Overview

SAIGEN is an AI-powered tool for generating, validating, and managing software metadata (saidata) files.

## Global Options

```bash
saigen [OPTIONS] COMMAND [ARGS]...
```

### Options

- `--version` - Show version and exit
- `--help` - Show help message and exit
- `--config PATH` - Path to configuration file
- `--verbose, -v` - Increase verbosity
- `--quiet, -q` - Decrease verbosity

## Commands

### Generation Commands

#### generate
Generate saidata for software.

```bash
saigen generate [OPTIONS] SOFTWARE
```

**Options:**
- `--provider TEXT` - Package manager provider (apt, dnf, brew, etc.)
- `--output PATH` - Output file path
- `--llm-provider TEXT` - LLM provider (openai, anthropic, ollama)
- `--model TEXT` - LLM model name
- `--use-rag` - Use RAG for enhanced generation
- `--force` - Overwrite existing file

**Examples:**
```bash
saigen generate nginx --provider apt
saigen generate docker --provider brew
saigen generate nginx --provider apt --use-rag
saigen generate nginx --llm-provider anthropic --model claude-4-sonnet
```

#### batch generate
Generate saidata for multiple packages.

```bash
saigen batch generate [OPTIONS]
```

**Options:**
- `--from PATH` - File with list of packages
- `--provider TEXT` - Package manager provider
- `--output-dir PATH` - Output directory
- `--parallel N` - Number of parallel generations
- `--continue-on-error` - Continue if one fails

**Examples:**
```bash
saigen batch generate --from packages.txt --provider apt
saigen batch generate --from packages.txt --provider apt --parallel 4
```

### Validation Commands

#### validate
Validate saidata file against schema.

```bash
saigen validate [OPTIONS] FILE
```

**Options:**
- `--schema PATH` - Custom schema file
- `--strict` - Strict validation mode

**Examples:**
```bash
saigen validate nginx.yaml
saigen validate nginx.yaml --strict
```

#### test
Test saidata file using MCP server.

```bash
saigen test [OPTIONS] FILE
```

**Options:**
- `--mcp-server TEXT` - MCP server to use
- `--action TEXT` - Specific action to test

**Examples:**
```bash
saigen test nginx.yaml
saigen test nginx.yaml --action install
```

See [testing-guide.md](testing-guide.md) for detailed testing documentation.

### Repository Management

#### repo update
Update package repository cache.

```bash
saigen repo update [OPTIONS] [PROVIDER]
```

**Options:**
- `--all` - Update all repositories
- `--force` - Force update even if cache is fresh

**Examples:**
```bash
saigen repo update apt
saigen repo update --all
```

#### repo list
List available repositories.

```bash
saigen repo list [OPTIONS]
```

**Options:**
- `--cached` - Show only cached repositories
- `--stats` - Show statistics

**Examples:**
```bash
saigen repo list
saigen repo list --stats
```

#### repo search
Search for packages in repositories.

```bash
saigen repo search [OPTIONS] QUERY
```

**Options:**
- `--provider TEXT` - Limit to specific provider
- `--limit N` - Limit results

**Examples:**
```bash
saigen repo search nginx
saigen repo search nginx --provider apt
```

#### repo info
Show repository information.

```bash
saigen repo info [OPTIONS] PROVIDER
```

**Examples:**
```bash
saigen repo info apt
saigen repo info brew
```

See [repository-management.md](repository-management.md) for detailed documentation.

### Update Commands

#### refresh-versions
Refresh version information in saidata.

```bash
saigen refresh-versions [OPTIONS] FILE
```

**Options:**
- `--provider TEXT` - Provider to check
- `--all-providers` - Check all providers
- `--dry-run` - Preview changes

**Examples:**
```bash
saigen refresh-versions nginx.yaml
saigen refresh-versions nginx.yaml --all-providers
```

See [refresh-versions-command.md](refresh-versions-command.md) for detailed documentation.

#### update
Update existing saidata file.

```bash
saigen update [OPTIONS] FILE
```

**Options:**
- `--refresh-urls` - Refresh download URLs
- `--refresh-versions` - Refresh version info
- `--add-action TEXT` - Add new action
- `--llm-provider TEXT` - LLM provider for enhancements

**Examples:**
```bash
saigen update nginx.yaml --refresh-urls
saigen update nginx.yaml --add-action configure
```

### Statistics Commands

#### stats
Show generation statistics.

```bash
saigen stats [OPTIONS]
```

**Options:**
- `--provider TEXT` - Filter by provider
- `--date-range TEXT` - Date range (e.g., "7d", "1m")

**Examples:**
```bash
saigen stats
saigen stats --provider apt
saigen stats --date-range 7d
```

See [stats-command.md](stats-command.md) for detailed documentation.

### Cache Management

#### cache clear
Clear repository cache.

```bash
saigen cache clear [OPTIONS] [PROVIDER]
```

**Options:**
- `--all` - Clear all caches

**Examples:**
```bash
saigen cache clear apt
saigen cache clear --all
```

#### cache info
Show cache information.

```bash
saigen cache info [OPTIONS]
```

**Examples:**
```bash
saigen cache info
```

### Configuration Commands

#### config show
Show current configuration.

```bash
saigen config show [OPTIONS]
```

**Examples:**
```bash
saigen config show
```

#### config validate
Validate configuration file.

```bash
saigen config validate [OPTIONS] [PATH]
```

**Examples:**
```bash
saigen config validate
saigen config validate ~/.saigen/config.yaml
```

## Configuration

See [configuration-guide.md](configuration-guide.md) for detailed configuration documentation.

## Exit Codes

- `0` - Success
- `1` - General error
- `2` - Command-line usage error
- `3` - Configuration error
- `4` - Validation error
- `5` - Generation error

## Environment Variables

- `SAIGEN_CONFIG` - Path to configuration file
- `SAIGEN_CACHE_DIR` - Override cache directory
- `SAIGEN_LOG_LEVEL` - Set log level (DEBUG, INFO, WARNING, ERROR)
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key

## See Also

- [generation-engine.md](generation-engine.md) - Generation engine documentation
- [repository-management.md](repository-management.md) - Repository management
- [testing-guide.md](testing-guide.md) - Testing documentation
- [configuration-guide.md](configuration-guide.md) - Configuration guide
- [examples/](examples/) - Configuration examples and samples
