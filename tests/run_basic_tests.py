#!/usr/bin/env python3
"""Basic test runner for saigen models."""

import sys
import traceback
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_model_imports():
    """Test that all models can be imported."""
    try:
        from saigen.models.config import SaigenConfig, LLMConfig
        from saigen.models.saidata import SaiData, Metadata
        from saigen.models.generation import GenerationRequest, GenerationResult
        from saigen.models.repository import RepositoryPackage
        from saigen.utils.config import ConfigManager
        print("✓ All model imports successful")
        return True
    except Exception as e:
        print(f"✗ Model import failed: {e}")
        traceback.print_exc()
        return False

def test_basic_model_creation():
    """Test basic model creation and validation."""
    try:
        # Test SaiData creation
        from saigen.models.saidata import SaiData
        saidata = SaiData(
            version='0.2.0',
            metadata={'name': 'nginx', 'description': 'Web server'}
        )
        assert saidata.version == '0.2.0'
        assert saidata.metadata.name == 'nginx'
        
        # Test config creation
        from saigen.models.config import SaigenConfig
        config = SaigenConfig()
        assert config.config_version == '0.1.0'
        
        # Test generation request
        from saigen.models.generation import GenerationRequest
        request = GenerationRequest(software_name='nginx')
        assert request.software_name == 'nginx'
        
        print("✓ Basic model creation successful")
        return True
    except Exception as e:
        print(f"✗ Model creation failed: {e}")
        traceback.print_exc()
        return False

def test_config_manager():
    """Test configuration manager basic functionality."""
    try:
        from saigen.utils.config import ConfigManager
        manager = ConfigManager()
        config = manager._create_default_config()
        assert config is not None
        
        # Test masked config
        masked = config.get_masked_config()
        assert isinstance(masked, dict)
        
        print("✓ Configuration manager basic tests successful")
        return True
    except Exception as e:
        print(f"✗ Configuration manager test failed: {e}")
        traceback.print_exc()
        return False

def test_validation_errors():
    """Test that validation errors are properly caught."""
    try:
        from saigen.models.saidata import SaiData
        from pydantic import ValidationError
        
        # This should fail - invalid version format
        try:
            SaiData(version='invalid', metadata={'name': 'test'})
            print("✗ Validation should have failed for invalid version")
            return False
        except ValidationError:
            pass  # Expected
        
        # This should fail - missing required metadata.name
        try:
            SaiData(version='0.2.0', metadata={})
            print("✗ Validation should have failed for missing name")
            return False
        except ValidationError:
            pass  # Expected
        
        print("✓ Validation error handling successful")
        return True
    except Exception as e:
        print(f"✗ Validation test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all basic tests."""
    print("Running basic saigen tests...")
    print("=" * 50)
    
    tests = [
        test_model_imports,
        test_basic_model_creation,
        test_config_manager,
        test_validation_errors,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())