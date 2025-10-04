#!/usr/bin/env python3
"""Comprehensive analysis of unused methods with context."""

import subprocess
import re

# Methods identified as potentially unused
CANDIDATES = {
    "BaseRepositoryDownloader": ["extract_package_metadata", "normalize_package_name"],
    "ChecksumValidator": ["get_supported_algorithms", "is_valid_format", "verify_checksum"],
    "ConfigManager": ["replace_secret_str", "update_config"],
    "GenerationEngine": ["_generate_configure_args", "_get_available_providers"],
    "LLMProviderManager": ["get_cost_estimate", "get_provider_models", "set_provider_model"],
    "OllamaProvider": ["get_usage_stats"],
    "ParserRegistry": ["get_available_formats"],
    "SaigenConfig": ["validate_llm_providers"],
    "TemplateContext": ["auto_detect"],
    "URLTemplateProcessor": ["get_supported_placeholders", "render_template"],
    "module": [
        "config_init", "config_samples", "config_set", "config_show", "config_validate",
        "get_version_info", "integrate_v03_prompts", "list_repos", 
        "load_saidata_schema_v03", "stats", "validate_v03_templates"
    ]
}

def search_usage(method_name):
    """Search for method usage in codebase."""
    try:
        # Search in saigen and tests
        result = subprocess.run(
            ['grep', '-r', method_name, 'saigen/', 'tests/', '--include=*.py'],
            capture_output=True, text=True
        )
        lines = result.stdout.strip().split('\n') if result.stdout else []
        # Filter out the definition line
        usage_lines = [l for l in lines if l and 'def ' + method_name not in l]
        return len(usage_lines)
    except:
        return -1

def main():
    print("=" * 80)
    print("COMPREHENSIVE UNUSED METHOD ANALYSIS")
    print("=" * 80)
    print()
    
    truly_unused = []
    possibly_used = []
    
    for class_name, methods in CANDIDATES.items():
        for method in methods:
            usage_count = search_usage(method)
            
            if usage_count == 0:
                truly_unused.append((class_name, method))
            elif usage_count > 0:
                possibly_used.append((class_name, method, usage_count))
    
    print("TRULY UNUSED (no references found):")
    print("-" * 80)
    if truly_unused:
        for class_name, method in truly_unused:
            print(f"  {class_name}.{method}")
    else:
        print("  None")
    
    print(f"\nTotal: {len(truly_unused)}")
    
    print("\n" + "=" * 80)
    print("POSSIBLY USED (found references):")
    print("-" * 80)
    if possibly_used:
        for class_name, method, count in possibly_used:
            print(f"  {class_name}.{method} ({count} references)")
    else:
        print("  None")
    
    print(f"\nTotal: {len(possibly_used)}")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS:")
    print("=" * 80)
    print("\nSafe to remove (truly unused):")
    for class_name, method in truly_unused:
        print(f"  - {class_name}.{method}")
    
    print("\nReview before removing (has references):")
    for class_name, method, count in possibly_used:
        print(f"  - {class_name}.{method} (check if references are actual usage)")

if __name__ == "__main__":
    main()
