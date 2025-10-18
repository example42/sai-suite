git ad# Generation Process Logging

The saigen generate command now supports comprehensive logging of the generation process through the `--log-file` option. This feature captures detailed information about every aspect of saidata generation, making it invaluable for debugging, optimization, and monitoring.

## Quick Start

```bash
# Generate with automatic logging
saigen generate nginx --verbose

# Generate with custom log file
saigen generate nginx --log-file ./nginx-generation.json

# View log summary after generation
cat ~/.saigen/logs/saigen_generate_nginx_*.json | jq '.final_result'
```

## What Gets Logged

### Process Tracking
- **Process Steps**: Each major step (validation, context building, LLM generation, etc.) with timing
- **Data Operations**: Repository queries, RAG operations, file I/O with input/output summaries
- **Error Handling**: Complete error messages with context and stack traces

### LLM Interactions
- **Complete Prompts**: Full text sent to LLM providers
- **Complete Responses**: Full text received from LLM providers  
- **Usage Metrics**: Token counts, cost estimates, response times
- **Provider Details**: Which provider and model was used
- **Retry Attempts**: Automatic retry attempts with validation feedback are marked with `retry_attempt: true` metadata

### Generation Context
- **Repository Data**: Summary of packages found in repositories
- **RAG Context**: Similar saidata and sample files used for context
- **Configuration**: All generation parameters and settings

### Results
- **Final Saidata**: Summary of generated saidata structure
- **Validation Results**: Schema validation details and any errors
- **File Operations**: Details about saving the output file

## Automatic Retry Mechanism

When the first LLM generation attempt fails validation, saigen automatically retries with enhanced feedback:

### Retry Process Logging
- **Validation Errors**: Detailed capture of what went wrong in the first attempt
- **Enhanced Context**: The retry prompt includes specific validation feedback
- **Retry Identification**: All retry attempts are clearly marked in logs
- **Success Tracking**: Whether the retry succeeded or also failed

### Example Retry Log Entry
```json
{
  "process_steps": [
    {
      "step_name": "retry_generation",
      "description": "Retrying generation with validation feedback",
      "status": "completed",
      "duration_seconds": 2.1
    }
  ],
  "llm_interactions": [
    {
      "timestamp": "2025-01-09T14:30:15",
      "provider": "openai",
      "success": true,
      "metadata": {}
    },
    {
      "timestamp": "2025-01-09T14:30:45", 
      "provider": "openai",
      "success": true,
      "metadata": {"retry_attempt": true}
    }
  ]
}
```

## Log File Structure

```json
{
  "session_id": "nginx_1757064665",
  "software_name": "nginx", 
  "start_time": "2025-09-05T11:31:05.470877",
  "end_time": "2025-09-05T11:31:08.909465",
  "total_duration_seconds": 3.438588,
  "success": true,
  "generation_request": { /* request parameters */ },
  "generation_context": { /* context data summary */ },
  "process_steps": [ /* step-by-step execution log */ ],
  "llm_interactions": [ /* complete LLM conversations */ ],
  "data_operations": [ /* all data processing operations */ ],
  "final_result": { /* generation outcome */ },
  "errors": [ /* any errors encountered */ ],
  "warnings": [ /* any warnings generated */ ],
  "metadata": { /* system and version info */ }
}
```

## Use Cases

### Debugging Failed Generations
When generation fails, logs provide:
- Exact point of failure
- Complete error context
- LLM responses that caused issues
- Available repository data

### Cost and Performance Monitoring
Track resource usage:
- Token consumption per generation
- Cost estimates by provider
- Time spent in each generation phase
- RAG query performance

### Quality Assurance
Verify generation quality:
- Repository data coverage
- RAG context effectiveness  
- Validation success rates
- Output consistency

### Prompt Optimization
Improve LLM interactions:
- Analyze prompt effectiveness
- Review response quality
- Optimize token usage
- Test different approaches

## Configuration

### Default Behavior
- Logs are automatically created for all non-dry-run generations
- Default location: `~/.saigen/logs/saigen_generate_<software>_<timestamp>.json`
- Includes both JSON structured data and text logs

### Custom Log Files
```bash
# Specify custom location
saigen generate nginx --log-file /path/to/custom.json

# Use relative paths
saigen generate nginx --log-file ./logs/nginx.json

# Disable logging (dry-run only)
saigen generate nginx --dry-run  # No log file created
```

### Log File Naming
Auto-generated files use the pattern:
```
saigen_generate_<software_name>_<YYYYMMDD_HHMMSS>.json
```

Special characters in software names are sanitized to filesystem-safe equivalents.

## Privacy and Security

### Sensitive Data
Generation logs contain:
- Complete LLM prompts and responses
- Repository query results
- System information
- Configuration details

### Best Practices
- Store logs in secure locations with appropriate access controls
- Consider log retention policies for compliance
- Review logs before sharing to ensure no sensitive data exposure
- Use log rotation to manage disk space

### Data Minimization
The logger automatically:
- Truncates very long responses to prevent excessive log sizes
- Sanitizes file paths to relative references where possible
- Excludes sensitive configuration values (API keys, etc.)

## Analysis Tools

### Command Line
```bash
# View generation summary
jq '.final_result' generation.json

# Extract all LLM interactions
jq '.llm_interactions[]' generation.json

# Calculate total cost
jq '[.llm_interactions[].cost_estimate // 0] | add' generation.json

# Find errors
jq '.errors[]' generation.json
```

### Python Analysis
```python
import json
from pathlib import Path

def analyze_generation_log(log_file):
    with open(log_file) as f:
        data = json.load(f)
    
    return {
        'success': data['success'],
        'duration': data['total_duration_seconds'],
        'tokens_used': sum(i.get('tokens_used', 0) for i in data['llm_interactions']),
        'cost_estimate': sum(i.get('cost_estimate', 0) for i in data['llm_interactions']),
        'error_count': len(data['errors']),
        'warning_count': len(data['warnings'])
    }
```

## Integration

### CI/CD Pipelines
```bash
# Generate with logging in CI
saigen generate $SOFTWARE --log-file ./artifacts/generation.json

# Upload logs as build artifacts
# Analyze logs for quality gates
```

### Monitoring Systems
- Parse JSON logs for metrics collection
- Set up alerts for generation failures
- Track cost trends over time
- Monitor generation performance

## Troubleshooting

### Common Issues

**Log file not created**
- Check directory permissions
- Verify disk space availability
- Ensure parent directories exist

**Large log files**
- Very long LLM responses are automatically truncated
- Consider log rotation for high-volume usage
- Archive old logs periodically

**Missing data in logs**
- Some operations may not be logged in test/mock environments
- Ensure logger is properly initialized
- Check for exceptions during logging

### Debug Mode
Use `--verbose` flag for additional console output that complements the log file:

```bash
saigen generate nginx --log-file ./debug.json --verbose
```

This provides real-time feedback while comprehensive details are saved to the log file.

## Future Enhancements

Planned improvements to generation logging:
- Log aggregation and analysis dashboard
- Integration with monitoring systems
- Automated log analysis and recommendations
- Performance benchmarking tools
- Cost optimization suggestions

For more examples and detailed usage, see the examples directory in the saigen documentation.