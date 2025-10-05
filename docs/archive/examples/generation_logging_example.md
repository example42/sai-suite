# Generation Logging Example

This example demonstrates how to use the new generation logging feature in saigen to capture detailed information about the generation process.

## Basic Usage

Generate saidata with automatic logging:

```bash
# Generate with automatic log file (saved to ~/.saigen/logs/)
saigen generate nginx --verbose

# Generate with custom log file location
saigen generate nginx --log-file ./nginx-generation.json --verbose

# Generate with multiple providers and logging
saigen generate --providers apt --providers brew --log-file ./multi-provider.json postgresql
```

## What Gets Logged

The generation logger captures comprehensive information about the entire process:

### 1. Session Information
- Unique session ID
- Software name being generated
- Start/end timestamps
- Total duration
- Success/failure status
- System information (OS, Python version, etc.)

### 2. Generation Request
- Software name
- Target providers
- LLM provider used
- RAG settings
- User hints
- Whether existing saidata was provided

### 3. Generation Context
- Repository data summary (packages found)
- Similar saidata examples used
- Sample saidata files referenced
- RAG query results

### 4. Process Steps
Each major step in the generation process is logged with:
- Step name and description
- Start/completion timestamps
- Duration
- Status (started/completed/failed)
- Additional metadata

### 5. LLM Interactions
Complete record of all LLM communications:
- Provider and model used
- Full prompt sent to LLM
- Complete response received
- Token usage and cost estimates
- Duration of interaction
- Success/failure status

### 6. Data Operations
All data processing operations:
- Repository queries
- RAG context building
- YAML parsing and validation
- File save operations
- Input/output data summaries

### 7. Errors and Warnings
- Detailed error messages with context
- Warning messages
- Validation failures
- Exception details

## Example Log Structure

```json
{
  "session_id": "nginx_1757064665",
  "software_name": "nginx",
  "start_time": "2025-09-05T11:31:05.470877",
  "end_time": "2025-09-05T11:31:05.909465",
  "total_duration_seconds": 2.438588,
  "success": true,
  "generation_request": {
    "software_name": "nginx",
    "target_providers": ["apt", "brew", "winget"],
    "llm_provider": "openai",
    "use_rag": true,
    "user_hints": null,
    "has_existing_saidata": false
  },
  "process_steps": [
    {
      "timestamp": "2025-09-05T11:31:05.803850",
      "step_name": "validate_request",
      "description": "Validating generation request",
      "status": "completed",
      "duration_seconds": 0.001234
    },
    {
      "timestamp": "2025-09-05T11:31:06.123456",
      "step_name": "build_context",
      "description": "Building generation context",
      "status": "completed",
      "duration_seconds": 0.456789
    }
  ],
  "llm_interactions": [
    {
      "timestamp": "2025-09-05T11:31:06.500000",
      "provider": "openai",
      "model": "gpt-4",
      "prompt": "You are an expert system administrator...",
      "response": "version: \"0.2\"\nmetadata:\n  name: nginx...",
      "tokens_used": 1250,
      "cost_estimate": 0.025,
      "duration_seconds": 3.2,
      "success": true
    }
  ],
  "data_operations": [
    {
      "timestamp": "2025-09-05T11:31:05.900000",
      "operation_type": "rag_query",
      "description": "Building RAG context for nginx",
      "output_data": {
        "similar_packages_count": 5,
        "similar_saidata_count": 3,
        "sample_saidata_count": 2
      },
      "duration_seconds": 0.234,
      "success": true
    }
  ],
  "final_result": {
    "success": true,
    "has_saidata": true,
    "validation_errors": [],
    "output_file": "nginx.yaml",
    "saidata_summary": {
      "name": "nginx",
      "version": "0.2",
      "category": "web-server",
      "providers": ["apt", "brew", "winget"],
      "package_count": 3,
      "service_count": 1
    }
  }
}
```

## Use Cases

### 1. Debugging Generation Issues
When generation fails, the log provides detailed information about:
- Which step failed
- Exact error messages
- LLM responses that caused validation failures
- Repository data that was available

### 2. Optimizing Prompts
The logs show:
- Complete prompts sent to LLMs
- Token usage patterns
- Cost analysis
- Response quality indicators

### 3. Performance Analysis
Track generation performance:
- Time spent in each step
- LLM response times
- RAG query performance
- Overall generation efficiency

### 4. Quality Assurance
Verify generation quality:
- Repository data coverage
- RAG context effectiveness
- Validation results
- Final saidata structure

### 5. Cost Monitoring
Monitor LLM usage costs:
- Token consumption per generation
- Cost estimates by provider
- Usage patterns over time

## Log File Locations

### Default Location
When no `--log-file` is specified, logs are saved to:
```
~/.saigen/logs/saigen_generate_<software_name>_<timestamp>.json
```

### Custom Location
Specify a custom path:
```bash
saigen generate nginx --log-file /path/to/my/logs/nginx.json
```

### Log File Naming
Auto-generated log files use the format:
```
saigen_generate_<software_name>_<YYYYMMDD_HHMMSS>.json
```

## Analyzing Logs

### Command Line Tools
Use standard JSON tools to analyze logs:

```bash
# Pretty print log file
cat nginx_generation.json | jq '.'

# Extract LLM interactions
cat nginx_generation.json | jq '.llm_interactions[]'

# Get generation summary
cat nginx_generation.json | jq '{
  software: .software_name,
  success: .success,
  duration: .total_duration_seconds,
  tokens: (.llm_interactions | map(.tokens_used // 0) | add),
  cost: (.llm_interactions | map(.cost_estimate // 0) | add)
}'

# Find errors
cat nginx_generation.json | jq '.errors[]'
```

### Python Analysis
```python
import json

# Load log file
with open('nginx_generation.json') as f:
    log_data = json.load(f)

# Analyze token usage
total_tokens = sum(
    interaction.get('tokens_used', 0) 
    for interaction in log_data['llm_interactions']
)

# Check for errors
if log_data['errors']:
    print("Errors found:")
    for error in log_data['errors']:
        print(f"- {error['error']}")

# Performance analysis
print(f"Total duration: {log_data['total_duration_seconds']:.2f}s")
print(f"LLM interactions: {len(log_data['llm_interactions'])}")
print(f"Process steps: {len(log_data['process_steps'])}")
```

## Best Practices

1. **Always use logging for production generations** to track quality and costs
2. **Store logs in a centralized location** for analysis and monitoring
3. **Review failed generation logs** to improve prompts and configurations
4. **Monitor token usage and costs** using log data
5. **Use logs for debugging** when generation doesn't meet expectations
6. **Archive logs periodically** to manage disk space

## Privacy Considerations

Generation logs contain:
- Complete LLM prompts and responses
- Repository data queries
- System information

Ensure logs are stored securely and access is controlled appropriately.