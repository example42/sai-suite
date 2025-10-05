# Batch Command Configuration Fix

## Issue
The `saigen batch` command was not honoring the same configuration settings as the `generate` command, specifically:
1. **Output directory**: Not using the configured `generation.output_directory` when `--output-dir` was not specified
2. **LLM provider**: Defaulting to `openai` instead of using the first enabled provider from config

## Root Cause
The batch command implementation had two issues:

1. When `--output-dir` was not provided, it passed `None` to the batch engine instead of falling back to `config.generation.output_directory`
2. When no `--llm-provider` was specified globally, it hardcoded `LLMProvider.OPENAI` instead of checking the config for enabled providers

## Solution
Modified `saigen/cli/commands/batch.py` to:

1. **Use configured output directory**: Added logic to use `config.generation.output_directory` when `--output-dir` is not specified:
```python
# Use configured output directory if not specified
if not output_dir:
    output_dir = config.generation.output_directory
    if verbose:
        click.echo(f"Using configured output directory: {output_dir}")
```

2. **Use configured LLM provider**: Changed the LLM provider selection logic to match the `generate` command:
```python
# Use default from config or fallback
if hasattr(config, 'llm_providers') and config.llm_providers:
    # Get first enabled provider from config
    first_provider = None
    for provider_name, provider_config in config.llm_providers.items():
        if provider_config.enabled:
            first_provider = provider_name
            break
    
    if not first_provider:
        # No enabled providers, use first one anyway
        first_provider = next(iter(config.llm_providers.keys()), 'openai')
    
    try:
        llm_provider = LLMProvider(first_provider)
    except ValueError:
        llm_provider = LLMProvider.OPENAI  # Fallback
else:
    llm_provider = LLMProvider.OPENAI  # Fallback
```

3. **Updated preview output**: Modified the preview mode to always show the output directory (whether configured or specified)

## Testing
Verified the fix with:
```bash
saigen batch -f docs/software_lists/test_sets/test_current.txt --preview
```

Output now correctly shows:
- LLM Provider: `anthropic` (from config)
- Output directory: `/Users/al/Documents/GITHUB/saidata/software` (from config)

## Impact
- The `batch` command now behaves consistently with the `generate` command
- Users no longer need to specify `--output-dir` for every batch operation
- The configured LLM provider is respected, avoiding unexpected costs or behavior
- Both commands now follow the same configuration precedence: CLI args > config file > defaults
