# Retry Generation Feature

## Overview

The saigen generate command now includes an intelligent retry mechanism that automatically attempts a second LLM query when the first generation fails validation. This significantly improves the success rate of saidata generation by providing detailed validation feedback to the LLM for correction.

## How It Works

### First Generation Attempt
1. The LLM generates saidata YAML based on the initial prompt
2. The generated content is parsed and validated against the saidata schema
3. If validation passes, the process completes successfully

### Automatic Retry on Validation Failure
1. If validation fails, the system captures detailed error information:
   - Validation error summary
   - Specific error messages
   - Failed YAML excerpt
   - Retry instructions

2. A second LLM query is made with enhanced context including:
   - Original generation context (repository data, examples, etc.)
   - Detailed validation feedback from the first attempt
   - Specific instructions on what needs to be fixed
   - Schema requirements and examples

3. The retry uses a specialized prompt template that emphasizes fixing validation errors

### Benefits

- **Higher Success Rate**: Automatically recovers from common validation failures
- **Better Error Handling**: Provides specific feedback about what went wrong
- **Cost Effective**: Only retries when necessary, avoiding unnecessary API calls
- **Detailed Logging**: All retry attempts are logged for debugging and monitoring

## Example Scenarios

### Scenario 1: Schema Validation Error
```
First attempt generates:
version: "invalid-version"  # Invalid semantic version
metadata:
  name: "nginx"

Retry receives feedback:
- "Schema validation failed: version must be semantic version"
- Generates corrected version: "0.2"
```

### Scenario 2: Missing Required Fields
```
First attempt generates:
version: "0.2"
metadata:
  description: "Web server"  # Missing required 'name' field

Retry receives feedback:
- "Model validation failed: name is required"
- Generates corrected metadata with name field
```

### Scenario 3: YAML Syntax Error
```
First attempt generates:
version: "0.2"
metadata: [unclosed bracket

Retry receives feedback:
- "Invalid YAML syntax: expected ']'"
- Generates properly formatted YAML
```

## Logging and Monitoring

The retry mechanism is fully integrated with the generation logging system:

- **Process Steps**: Retry attempts are logged as separate process steps
- **LLM Interactions**: Both original and retry LLM calls are recorded
- **Metadata**: Retry attempts are marked with `retry_attempt: true` metadata
- **Validation Feedback**: The validation errors that triggered the retry are logged

### Example Log Entry
```json
{
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
  ],
  "process_steps": [
    {
      "step_name": "retry_generation",
      "description": "Retrying generation with validation feedback",
      "status": "completed"
    }
  ]
}
```

## Configuration

The retry mechanism is enabled by default and requires no additional configuration. It:

- Only triggers on validation failures (not on other errors)
- Uses the same LLM provider as the original attempt
- Prevents infinite loops by marking retry attempts
- Maintains all original context and preferences

## Error Handling

If both the original and retry attempts fail:
- The final validation errors from the retry attempt are returned
- Both LLM interactions are logged for debugging
- The generation is marked as failed with detailed error information

## Performance Impact

- **Minimal Overhead**: Only activates when validation fails
- **Smart Retry**: Uses enhanced prompts specifically designed for error correction
- **Single Retry**: Prevents infinite loops with a maximum of one retry attempt
- **Efficient Logging**: All interactions are logged for cost monitoring and debugging

## Future Enhancements

Potential improvements to the retry mechanism:
- Configurable retry count
- Different retry strategies based on error type
- Learning from common validation patterns
- Integration with quality scoring for retry decisions