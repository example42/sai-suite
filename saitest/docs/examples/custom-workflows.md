# Custom Workflows Example

This example demonstrates advanced usage patterns and custom workflows for saitest.

## Python API Integration

### Programmatic Verification

```python
from saitest.core.orchestrator import run_verification
from pathlib import Path
import yaml

def verify_software(software, platforms, output_dir):
    """Verify software and save results"""
    
    # Run verification
    result = run_verification(
        software=software,
        platforms=platforms,
        config={
            "llm": {"model": "gpt-4o", "temperature": 0.0},
            "containers": {"timeout": 600}
        }
    )
    
    # Check confidence
    confidence = result["overall_confidence"]
    print(f"Confidence: {confidence:.2f}")
    
    if confidence >= 0.8:
        # Save saidata
        output_path = Path(output_dir) / software
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Write default.yaml
        with open(output_path / "default.yaml", 'w') as f:
            yaml.dump(result["generated_saidata"]["default"], f)
        
        # Write OS-specific overrides
        for os_name, versions in result["generated_saidata"]["overrides"].items():
            os_dir = output_path / os_name
            os_dir.mkdir(exist_ok=True)
            
            for version, override_data in versions.items():
                with open(os_dir / f"{version}.yaml", 'w') as f:
                    yaml.dump(override_data, f)
        
        print(f"✅ Saidata saved to {output_path}")
        return True
    else:
        print(f"⚠️  Low confidence - manual review required")
        return False

# Usage
if __name__ == "__main__":
    success = verify_software(
        software="nginx",
        platforms=["ubuntu:22.04", "debian:12"],
        output_dir="./saidata"
    )
    
    exit(0 if success else 1)
```

### Batch Processing

```python
from saitest.core.orchestrator import run_verification
from concurrent.futures import ThreadPoolExecutor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_single(software, platforms):
    """Verify single software"""
    try:
        logger.info(f"Verifying {software}...")
        result = run_verification(software=software, platforms=platforms)
        
        confidence = result["overall_confidence"]
        logger.info(f"{software}: confidence={confidence:.2f}")
        
        return {
            "software": software,
            "success": True,
            "confidence": confidence,
            "result": result
        }
    except Exception as e:
        logger.error(f"{software}: {e}")
        return {
            "software": software,
            "success": False,
            "error": str(e)
        }

def batch_verify(software_list, platforms, max_workers=4):
    """Verify multiple software in parallel"""
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(verify_single, software, platforms)
            for software in software_list
        ]
        
        results = [f.result() for f in futures]
    
    # Summary
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"\n{'='*50}")
    print(f"Batch Verification Summary")
    print(f"{'='*50}")
    print(f"Total: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if successful:
        avg_confidence = sum(r["confidence"] for r in successful) / len(successful)
        print(f"Average confidence: {avg_confidence:.2f}")
    
    return results

# Usage
if __name__ == "__main__":
    software_list = ["nginx", "apache", "postgresql", "redis", "mysql"]
    platforms = ["ubuntu:22.04", "debian:12"]
    
    results = batch_verify(software_list, platforms, max_workers=2)
```

### Custom Analysis

```python
from saitest.core.orchestrator import run_verification
from saitest.models.observation import Observation
from collections import defaultdict

def analyze_observations(result):
    """Analyze observations from verification"""
    
    observations_by_type = defaultdict(list)
    observations_by_platform = defaultdict(list)
    observations_by_provider = defaultdict(list)
    
    for platform_result in result["platform_results"]:
        platform = platform_result.platform
        provider = platform_result.provider
        
        for obs in platform_result.observations:
            observations_by_type[obs.type].append(obs)
            observations_by_platform[platform].append(obs)
            observations_by_provider[provider].append(obs)
    
    # Print analysis
    print("\n=== Observation Analysis ===\n")
    
    print("By Type:")
    for obs_type, obs_list in observations_by_type.items():
        print(f"  {obs_type}: {len(obs_list)}")
    
    print("\nBy Platform:")
    for platform, obs_list in observations_by_platform.items():
        print(f"  {platform}: {len(obs_list)}")
    
    print("\nBy Provider:")
    for provider, obs_list in observations_by_provider.items():
        print(f"  {provider}: {len(obs_list)}")
    
    return {
        "by_type": observations_by_type,
        "by_platform": observations_by_platform,
        "by_provider": observations_by_provider
    }

# Usage
result = run_verification(
    software="nginx",
    platforms=["ubuntu:22.04", "debian:12"]
)

analysis = analyze_observations(result)
```

## Custom Configuration

### Configuration File

**saitest-config.yaml:**

```yaml
# LLM Configuration
llm:
  provider: openai
  model: gpt-4o
  temperature: 0.0
  max_tokens: 4000

# Container Configuration
containers:
  cpu_limit: 2
  memory_limit: 2g
  timeout: 600
  max_concurrent: 4
  cleanup: true

# Verification Configuration
verification:
  max_retries: 2
  confidence_threshold: 0.7
  default_platforms:
    - ubuntu:22.04
    - debian:12
  
  # Provider preferences
  preferred_providers:
    - apt
    - dnf
    - snap
  
  # Skip providers
  skip_providers:
    - source  # Skip source builds for faster testing

# Output Configuration
output:
  format: yaml
  include_metadata: true
  include_confidence_scores: true
  include_observations: false

# Logging Configuration
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: saitest.log
```

### Using Configuration

```bash
saitest verify nginx --config saitest-config.yaml
```

```python
from saitest.core.orchestrator import run_verification
import yaml

# Load config
with open("saitest-config.yaml") as f:
    config = yaml.safe_load(f)

# Run with config
result = run_verification(
    software="nginx",
    platforms=config["verification"]["default_platforms"],
    config=config
)
```

## Incremental Verification

### Update Existing Saidata

```python
from saitest.core.orchestrator import run_verification
from pathlib import Path
import yaml

def update_saidata(software, saidata_dir, new_platforms):
    """Update existing saidata with new platforms"""
    
    saidata_path = Path(saidata_dir) / software
    
    # Load existing saidata
    existing_platforms = []
    if saidata_path.exists():
        for os_dir in saidata_path.iterdir():
            if os_dir.is_dir():
                for version_file in os_dir.glob("*.yaml"):
                    os_name = os_dir.name
                    version = version_file.stem
                    existing_platforms.append(f"{os_name}:{version}")
    
    # Combine with new platforms
    all_platforms = list(set(existing_platforms + new_platforms))
    
    print(f"Existing platforms: {existing_platforms}")
    print(f"New platforms: {new_platforms}")
    print(f"Testing all platforms: {all_platforms}")
    
    # Run verification
    result = run_verification(
        software=software,
        platforms=all_platforms
    )
    
    # Save updated saidata
    # ... (save logic)
    
    return result

# Usage
update_saidata(
    software="nginx",
    saidata_dir="./saidata",
    new_platforms=["rockylinux:9", "fedora:40"]
)
```

## Comparison Workflows

### Compare Saidata Versions

```python
import yaml
from pathlib import Path
from deepdiff import DeepDiff

def compare_saidata(old_file, new_file):
    """Compare two saidata files"""
    
    with open(old_file) as f:
        old_data = yaml.safe_load(f)
    
    with open(new_file) as f:
        new_data = yaml.safe_load(f)
    
    # Compare
    diff = DeepDiff(old_data, new_data, ignore_order=True)
    
    if not diff:
        print("✅ No differences found")
        return True
    
    print("⚠️  Differences found:")
    print(diff.pretty())
    
    return False

# Usage
compare_saidata(
    "saidata/nginx/default.yaml",
    "updated/nginx/default.yaml"
)
```

### Compare Across Platforms

```python
from saitest.core.orchestrator import run_verification

def compare_platforms(software, platform1, platform2):
    """Compare software behavior across platforms"""
    
    # Verify on platform 1
    result1 = run_verification(software=software, platforms=[platform1])
    
    # Verify on platform 2
    result2 = run_verification(software=software, platforms=[platform2])
    
    # Compare observations
    obs1 = result1["platform_results"][0].observations
    obs2 = result2["platform_results"][0].observations
    
    print(f"\n=== Platform Comparison ===")
    print(f"{platform1}: {len(obs1)} observations")
    print(f"{platform2}: {len(obs2)} observations")
    
    # Find differences
    types1 = {obs.type for obs in obs1}
    types2 = {obs.type for obs in obs2}
    
    common = types1 & types2
    only1 = types1 - types2
    only2 = types2 - types1
    
    print(f"\nCommon: {common}")
    print(f"Only in {platform1}: {only1}")
    print(f"Only in {platform2}: {only2}")

# Usage
compare_platforms("nginx", "ubuntu:22.04", "debian:12")
```

## Validation Workflows

### Validate Before Commit

```python
from saitest.core.orchestrator import run_verification
from pathlib import Path
import yaml
import sys

def validate_saidata(saidata_file):
    """Validate saidata by testing it"""
    
    # Load saidata
    with open(saidata_file) as f:
        saidata = yaml.safe_load(f)
    
    software = saidata["metadata"]["name"]
    
    # Run verification
    result = run_verification(
        software=software,
        platforms=["ubuntu:22.04", "debian:12"]
    )
    
    # Compare with existing saidata
    confidence = result["overall_confidence"]
    
    if confidence >= 0.8:
        print(f"✅ Validation passed (confidence: {confidence:.2f})")
        return True
    else:
        print(f"❌ Validation failed (confidence: {confidence:.2f})")
        return False

# Usage in pre-commit hook
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: validate_saidata.py <saidata_file>")
        sys.exit(1)
    
    success = validate_saidata(sys.argv[1])
    sys.exit(0 if success else 1)
```

### Schema Validation

```python
import yaml
import jsonschema
from pathlib import Path

def validate_schema(saidata_file, schema_file):
    """Validate saidata against schema"""
    
    # Load saidata
    with open(saidata_file) as f:
        saidata = yaml.safe_load(f)
    
    # Load schema
    with open(schema_file) as f:
        schema = yaml.safe_load(f)
    
    # Validate
    try:
        jsonschema.validate(saidata, schema)
        print("✅ Schema validation passed")
        return True
    except jsonschema.ValidationError as e:
        print(f"❌ Schema validation failed: {e.message}")
        return False

# Usage
validate_schema(
    "saidata/nginx/default.yaml",
    "schemas/saidata-0.3-schema.json"
)
```

## Reporting Workflows

### Generate Report

```python
from saitest.core.orchestrator import run_verification
import json
from datetime import datetime

def generate_report(software, platforms, output_file):
    """Generate verification report"""
    
    # Run verification
    result = run_verification(software=software, platforms=platforms)
    
    # Build report
    report = {
        "software": software,
        "timestamp": datetime.now().isoformat(),
        "platforms": platforms,
        "confidence": result["overall_confidence"],
        "platforms_tested": len(result["platform_results"]),
        "total_observations": sum(
            len(pr.observations) for pr in result["platform_results"]
        ),
        "needs_review": result["needs_human_review"],
        "platform_results": [
            {
                "platform": pr.platform,
                "provider": pr.provider,
                "success": pr.success,
                "observations": len(pr.observations),
                "duration": pr.duration
            }
            for pr in result["platform_results"]
        ]
    }
    
    # Save report
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Report saved to {output_file}")
    return report

# Usage
report = generate_report(
    software="nginx",
    platforms=["ubuntu:22.04", "debian:12"],
    output_file="nginx-report.json"
)
```

### HTML Report

```python
from jinja2 import Template

html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Saitest Report - {{ software }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 20px; }
        .metric { display: inline-block; margin: 10px; }
        .success { color: green; }
        .warning { color: orange; }
        .error { color: red; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Saitest Report: {{ software }}</h1>
        <p>Generated: {{ timestamp }}</p>
    </div>
    
    <div class="metrics">
        <div class="metric">
            <strong>Confidence:</strong>
            <span class="{{ 'success' if confidence >= 0.8 else 'warning' }}">
                {{ "%.2f"|format(confidence) }}
            </span>
        </div>
        <div class="metric">
            <strong>Platforms:</strong> {{ platforms_tested }}
        </div>
        <div class="metric">
            <strong>Observations:</strong> {{ total_observations }}
        </div>
    </div>
    
    <h2>Platform Results</h2>
    <table>
        <tr>
            <th>Platform</th>
            <th>Provider</th>
            <th>Status</th>
            <th>Observations</th>
            <th>Duration</th>
        </tr>
        {% for result in platform_results %}
        <tr>
            <td>{{ result.platform }}</td>
            <td>{{ result.provider }}</td>
            <td class="{{ 'success' if result.success else 'error' }}">
                {{ 'Success' if result.success else 'Failed' }}
            </td>
            <td>{{ result.observations }}</td>
            <td>{{ "%.1f"|format(result.duration) }}s</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

def generate_html_report(report_data, output_file):
    """Generate HTML report"""
    template = Template(html_template)
    html = template.render(**report_data)
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"HTML report saved to {output_file}")

# Usage
generate_html_report(report, "nginx-report.html")
```

## Integration with Other Tools

### Integration with Saigen

```python
from saigen.repositories import RepositoryDownloader
from saitest.core.orchestrator import run_verification

def verify_from_repository(software, repository_type):
    """Verify software using repository metadata"""
    
    # Query repository
    downloader = RepositoryDownloader()
    repo_info = downloader.query(repository_type, software)
    
    if not repo_info:
        print(f"Software {software} not found in {repository_type}")
        return None
    
    print(f"Found {software} version {repo_info.version}")
    
    # Run verification
    result = run_verification(
        software=software,
        platforms=["ubuntu:22.04", "debian:12"]
    )
    
    return result

# Usage
verify_from_repository("nginx", "apt")
```

### Integration with SAI

```python
from sai.core.execution_engine import ExecutionEngine
from saitest.core.orchestrator import run_verification

def verify_and_install(software, platform):
    """Verify saidata then install with sai"""
    
    # Verify
    result = run_verification(software=software, platforms=[platform])
    
    if result["overall_confidence"] >= 0.8:
        print("✅ Verification passed, installing...")
        
        # Install with sai
        engine = ExecutionEngine()
        engine.execute_action("install", software)
    else:
        print("⚠️  Low confidence, skipping installation")

# Usage
verify_and_install("nginx", "ubuntu:22.04")
```

## Next Steps

- [Basic Verification](basic-verification.md) - Simple verification workflow
- [Multi-Platform Testing](multi-platform-testing.md) - Test across platforms
- [Multi-Provider Testing](multi-provider-testing.md) - Test multiple providers
- [CI/CD Integration](ci-cd-integration.md) - Automate verification
- [CLI Reference](../cli-reference.md) - Complete command documentation
