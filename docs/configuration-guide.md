# Configuration Guide

## Configuration File Locations

saigen searches for configuration files in the following order:

1. `~/.saigen/config.yaml` or `~/.saigen/config.json`
2. `.saigen.yaml` or `.saigen.json` (in current directory)
3. `saigen.yaml` or `saigen.json` (in current directory)

## Configuration Format

Configuration files can be in YAML or JSON format. YAML is recommended for readability.

### Complete Configuration Example

```yaml
# Configuration version
config_version: "0.1.0"

# Logging configuration
log_level: info  # debug, info, warning, error
log_file: ~/.saigen/logs/saigen.log  # Optional log file

# LLM Provider Configuration
llm_providers:
  openai:
    provider: openai
    model: gpt-3.5-turbo
    max_tokens: 4000
    temperature: 0.1
    timeout: 30
    max_retries: 3
    enabled: true
    # api_key: set via OPENAI_API_KEY environment variable
  
  anthropic:
    provider: anthropic
    model: claude-3-sonnet-20240229
    max_tokens: 4000
    temperature: 0.1
    timeout: 30
    max_retries: 3
    enabled: false
    # api_key: set via ANTHROPIC_API_KEY environment variable
  
  ollama:
    provider: ollama
    api_base: http://localhost:11434
    model: llama2
    enabled: false

# Repository Configuration
repositories:
  apt:
    type: apt
    enabled: true
    cache_ttl: 3600  # 1 hour
    priority: 1
  
  brew:
    type: brew
    enabled: true
    cache_ttl: 7200  # 2 hours
    priority: 2
  
  winget:
    type: winget
    enabled: true
    cache_ttl: 3600
    priority: 3

# Cache Configuration
cache:
  directory: ~/.saigen/cache
  max_size_mb: 1000
  default_ttl: 3600  # 1 hour
  cleanup_interval: 86400  # 24 hours

# RAG (Retrieval-Augmented Generation) Configuration
rag:
  enabled: true
  index_directory: ~/.saigen/rag_index
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
  max_context_items: 5
  similarity_threshold: 0.7
  rebuild_on_startup: false

# Validation Configuration
validation:
  schema_path: null  # Use built-in schema
  strict_mode: true
  auto_fix_common_issues: true
  validate_repository_accuracy: true

# Generation Configuration
generation:
  default_providers: [apt, brew, winget]
  output_directory: ./saidata
  backup_existing: true
  parallel_requests: 3
  request_timeout: 120

# Advanced Settings
user_agent: "saigen/0.1.0"
max_concurrent_requests: 5
request_timeout: 30
```

## Environment Variables

Environment variables override configuration file settings:

### Required for LLM Providers
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key

### Optional Overrides
- `SAIGEN_LOG_LEVEL` - Override log level
- `SAIGEN_CACHE_DIR` - Override cache directory
- `SAIGEN_OUTPUT_DIR` - Override output directory

### Example
```bash
export OPENAI_API_KEY="sk-..."
export SAIGEN_LOG_LEVEL="debug"
export SAIGEN_CACHE_DIR="/tmp/saigen-cache"

saigen generate nginx
```

## Configuration Management Commands

### View Current Configuration
```bash
saigen config --show
```

### Validate Configuration
```bash
saigen config --validate
```

## Security Best Practices

1. **API Keys**: Never store API keys in configuration files. Use environment variables.

2. **File Permissions**: Configuration files are automatically saved with secure permissions (0o600).

3. **Cache Directory**: Ensure cache directory has appropriate permissions.

4. **Log Files**: Be careful with log file locations and permissions if logging sensitive data.

## Troubleshooting

### Configuration Not Found
If saigen can't find a configuration file, it will create a default configuration. Check the search paths above.

### Invalid Configuration
Use `saigen config --validate` to check for configuration errors.

### API Key Issues
Ensure environment variables are set correctly:
```bash
echo $OPENAI_API_KEY  # Should show your API key
```

### Permission Errors
Ensure saigen can write to cache and output directories:
```bash
ls -la ~/.saigen/
```

## Migration from Previous Versions

When upgrading saigen, configuration files are automatically migrated to the latest format. Backup your configuration before upgrading:

```bash
cp ~/.saigen/config.yaml ~/.saigen/config.yaml.backup
```