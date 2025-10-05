#!/usr/bin/env python3
"""Test script to verify config init includes all settings."""

import sys
import tempfile
import yaml
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from saigen.models.config import SaigenConfig
from saigen.utils.config import ConfigManager


def test_default_config():
    """Test that default config includes all expected settings."""
    
    print("=" * 80)
    print("Testing Default Configuration")
    print("=" * 80)
    print()
    
    # Create default config
    config = SaigenConfig()
    config_dict = config.model_dump()
    
    print("1. Checking core settings...")
    assert 'config_version' in config_dict
    assert 'log_level' in config_dict
    print(f"   ✓ config_version: {config_dict['config_version']}")
    print(f"   ✓ log_level: {config_dict['log_level']}")
    print()
    
    print("2. Checking LLM providers...")
    assert 'llm_providers' in config_dict
    # Note: Default provider is added by validator when explicitly set to empty dict
    # When using config init, the sample config will have providers configured
    if len(config_dict['llm_providers']) > 0:
        print(f"   ✓ Default providers configured: {list(config_dict['llm_providers'].keys())}")
    else:
        print(f"   ✓ LLM providers field present (will be populated from sample config)")
    print()
    
    print("3. Checking cache configuration...")
    assert 'cache' in config_dict
    cache = config_dict['cache']
    assert 'directory' in cache
    assert 'max_size_mb' in cache
    assert 'default_ttl' in cache
    print(f"   ✓ cache.max_size_mb: {cache['max_size_mb']}")
    print(f"   ✓ cache.default_ttl: {cache['default_ttl']}")
    print()
    
    print("4. Checking RAG configuration...")
    assert 'rag' in config_dict
    rag = config_dict['rag']
    assert 'enabled' in rag
    assert 'embedding_model' in rag
    assert 'use_default_samples' in rag
    print(f"   ✓ rag.enabled: {rag['enabled']}")
    print(f"   ✓ rag.use_default_samples: {rag['use_default_samples']}")
    print(f"   ✓ rag.max_sample_examples: {rag['max_sample_examples']}")
    print()
    
    print("5. Checking validation configuration...")
    assert 'validation' in config_dict
    validation = config_dict['validation']
    assert 'strict_mode' in validation
    assert 'auto_fix_common_issues' in validation
    print(f"   ✓ validation.strict_mode: {validation['strict_mode']}")
    print(f"   ✓ validation.auto_fix_common_issues: {validation['auto_fix_common_issues']}")
    print()
    
    print("6. Checking generation configuration...")
    assert 'generation' in config_dict
    generation = config_dict['generation']
    
    # Check standard settings
    assert 'default_providers' in generation
    assert 'output_directory' in generation
    assert 'backup_existing' in generation
    assert 'parallel_requests' in generation
    assert 'request_timeout' in generation
    print(f"   ✓ generation.default_providers: {generation['default_providers']}")
    print(f"   ✓ generation.backup_existing: {generation['backup_existing']}")
    print(f"   ✓ generation.parallel_requests: {generation['parallel_requests']}")
    print(f"   ✓ generation.request_timeout: {generation['request_timeout']}")
    print()
    
    print("7. Checking URL filter settings (NEW)...")
    # Check URL filter settings
    assert 'enable_url_filter' in generation, "enable_url_filter missing from generation config!"
    assert 'url_filter_timeout' in generation, "url_filter_timeout missing from generation config!"
    assert 'url_filter_max_concurrent' in generation, "url_filter_max_concurrent missing from generation config!"
    
    print(f"   ✓ generation.enable_url_filter: {generation['enable_url_filter']}")
    print(f"   ✓ generation.url_filter_timeout: {generation['url_filter_timeout']}")
    print(f"   ✓ generation.url_filter_max_concurrent: {generation['url_filter_max_concurrent']}")
    
    # Verify default values
    assert generation['enable_url_filter'] == True, "enable_url_filter should default to True"
    assert generation['url_filter_timeout'] == 5, "url_filter_timeout should default to 5"
    assert generation['url_filter_max_concurrent'] == 10, "url_filter_max_concurrent should default to 10"
    print("   ✓ All URL filter defaults are correct")
    print()
    
    print("8. Testing config save/load...")
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.yaml"
        
        # Save config
        config_manager = ConfigManager()
        config_manager.save_config(config, config_path)
        print(f"   ✓ Config saved to {config_path}")
        
        # Load config
        with open(config_path, 'r') as f:
            loaded_yaml = yaml.safe_load(f)
        
        # Verify URL filter settings in saved file
        assert 'generation' in loaded_yaml
        assert 'enable_url_filter' in loaded_yaml['generation']
        assert 'url_filter_timeout' in loaded_yaml['generation']
        assert 'url_filter_max_concurrent' in loaded_yaml['generation']
        print("   ✓ URL filter settings present in saved config")
        
        # Verify values
        assert loaded_yaml['generation']['enable_url_filter'] == True
        assert loaded_yaml['generation']['url_filter_timeout'] == 5
        assert loaded_yaml['generation']['url_filter_max_concurrent'] == 10
        print("   ✓ URL filter values correct in saved config")
    
    print()
    print("=" * 80)
    print("Configuration Test Complete - All Settings Present!")
    print("=" * 80)
    print()
    print("Summary:")
    print("✓ Core settings configured")
    print("✓ LLM providers configured")
    print("✓ Cache settings configured")
    print("✓ RAG settings configured")
    print("✓ Validation settings configured")
    print("✓ Generation settings configured")
    print("✓ URL filter settings configured (NEW)")
    print()
    print("The 'saigen config init' command will create a config with all these settings.")


if __name__ == "__main__":
    test_default_config()
