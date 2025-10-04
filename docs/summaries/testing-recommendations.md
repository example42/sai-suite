# Testing Recommendations for Prompt Improvements

## Quick Verification

Run the test scripts to verify prompt structure and deduplication:
```bash
# Test prompt structure
python scripts/development/test_prompt_improvements.py

# Test deduplication logic
python scripts/development/test_deduplication.py
```

Expected output: All checks should pass with ✅

## Manual Testing with Real Generation

### Test 1: Nginx (Web Server)
```bash
saigen generate nginx --output test-output/nginx.yaml
```

**Expected structure:**
- ✅ Top-level: packages, services, files, directories, commands, ports
- ✅ Provider sections: apt, dnf, brew, choco, docker
- ✅ Provider repositories only for upstream repos (nginx-official)
- ❌ Should NOT have invalid scripts section
- ❌ Should NOT have incomplete sources/binaries

**Compare with:** `docs/saidata_samples/ng/nginx/default.yaml`

### Test 2: Redis (Database)
```bash
saigen generate redis --output test-output/redis.yaml
```

**Expected structure:**
- ✅ Top-level: packages, services, files, directories, commands, ports
- ✅ Provider sections: apt, dnf, brew
- ✅ No upstream repositories (uses default OS repos)
- ❌ Should NOT have sources/binaries/scripts unless verified

**Compare with:** `docs/saidata_samples/re/redis/default.yaml`

### Test 3: Docker (Container Runtime)
```bash
saigen generate docker --output test-output/docker.yaml
```

**Expected structure:**
- ✅ Top-level: packages (multiple), services, files, directories, commands
- ✅ Provider repositories for upstream Docker repos
- ✅ Multiple packages (docker-ce, docker-ce-cli, docker-compose-plugin)

**Compare with:** `docs/saidata_samples/do/docker/default.yaml`

## Validation Checklist

For each generated file, verify:

### Structure
- [ ] Has `version: "0.3"`
- [ ] Has complete metadata section
- [ ] Has top-level packages section
- [ ] Has top-level services section (if applicable)
- [ ] Has top-level files section (if applicable)
- [ ] Has top-level directories section (if applicable)
- [ ] Has top-level commands section (if applicable)
- [ ] Has top-level ports section (if applicable)

### Provider Sections
- [ ] Provider packages reference logical names from top-level
- [ ] Provider repositories only included for upstream/third-party repos
- [ ] No unnecessary duplication of top-level data (deduplication working)
- [ ] Provider-specific overrides are appropriate
- [ ] Provider packages are empty/removed if they exactly match top-level

### Optional Sections
- [ ] sources section only present if build info is valid
- [ ] binaries section only present if download URLs are valid
- [ ] scripts section only present if install scripts are valid
- [ ] No placeholder or guessed data in these sections

### Quality
- [ ] All YAML syntax is valid
- [ ] Package names match repository data
- [ ] File paths are realistic
- [ ] Port numbers are correct
- [ ] Service names are accurate

## Comparison Script

Create a simple comparison to check structure:

```bash
# Compare structure of generated vs sample
python -c "
import yaml
import sys

with open('test-output/nginx.yaml') as f:
    generated = yaml.safe_load(f)
    
with open('docs/saidata_samples/ng/nginx/default.yaml') as f:
    sample = yaml.safe_load(f)

print('Generated top-level keys:', sorted(generated.keys()))
print('Sample top-level keys:', sorted(sample.keys()))

# Check for critical sections
critical = ['packages', 'services', 'files', 'directories', 'commands', 'ports']
missing = [k for k in critical if k not in generated]
if missing:
    print(f'❌ Missing critical sections: {missing}')
    sys.exit(1)
else:
    print('✅ All critical sections present')
"
```

## Regression Testing

Test with software that previously generated incorrectly:

1. **Software with services**: nginx, redis, postgresql, mysql
2. **CLI tools**: terraform, kubectl, helm
3. **Container platforms**: docker, kubernetes
4. **Monitoring tools**: prometheus, grafana

For each, verify:
- Top-level sections are complete
- Provider sections are appropriate
- No invalid optional sections

## Performance Testing

Check that the improved prompts don't significantly impact:
- Generation time
- Token usage
- LLM costs

Run batch generation and compare metrics:
```bash
saigen batch generate --file test-software-list.txt --output test-output/
```

## Success Criteria

The prompt improvements are successful if:

1. **Structure**: 100% of generated files have top-level packages, services, files, directories, commands, ports (when relevant)
2. **Quality**: Generated files match sample file structure and quality
3. **Accuracy**: Provider sections contain appropriate overrides, not duplicates
4. **Completeness**: Optional sections (sources/binaries/scripts) only present with valid data
5. **Validation**: All generated files pass schema validation
6. **Performance**: No significant increase in generation time or token usage

## Rollback Plan

If issues are found:
1. Document the specific problems
2. Check if it's a prompt issue or data issue
3. Revert changes to `saigen/llm/prompts.py` if needed
4. Investigate alternative prompt structures

## Reporting Issues

If you find problems, document:
- Software name being generated
- Command used
- Expected vs actual output
- Specific sections that are wrong
- LLM provider used
- Any error messages
