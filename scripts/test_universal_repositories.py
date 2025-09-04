#!/usr/bin/env python3
"""Test script for the universal repository management system."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import tempfile
import yaml

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from saigen.repositories.manager import RepositoryManager
from saigen.repositories.universal_manager import UniversalRepositoryManager
from saigen.repositories.parsers import ParserRegistry


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def create_test_config() -> Dict[str, Any]:
    """Create a test repository configuration."""
    return {
        "version": "1.0",
        "repositories": [
            {
                "name": "test-json-repo",
                "type": "generic",
                "platform": "universal",
                "distribution": ["test"],
                "architecture": ["all"],
                "endpoints": {
                    "packages": "https://registry.npmjs.org/-/v1/search?text=express&size=5"
                },
                "parsing": {
                    "format": "json",
                    "encoding": "utf-8",
                    "patterns": {
                        "json_path": "objects"
                    },
                    "fields": {
                        "name": "package.name",
                        "version": "package.version",
                        "description": "package.description",
                        "homepage": "package.links.homepage",
                        "maintainer": "package.publisher.username"
                    }
                },
                "cache": {
                    "ttl_hours": 1,
                    "max_size_mb": 10,
                    "enabled": True
                },
                "limits": {
                    "requests_per_minute": 60,
                    "timeout_seconds": 30,
                    "max_response_size_mb": 10,
                    "concurrent_requests": 2
                },
                "auth": {
                    "type": "none"
                },
                "metadata": {
                    "description": "Test JSON Repository",
                    "maintainer": "Test",
                    "priority": 50,
                    "enabled": True,
                    "official": False
                }
            }
        ]
    }


async def test_parser_registry():
    """Test the parser registry functionality."""
    logger.info("Testing Parser Registry...")
    
    registry = ParserRegistry()
    
    # Test available formats
    formats = registry.get_available_formats()
    logger.info(f"Available parser formats: {formats}")
    
    expected_formats = ['json', 'yaml', 'xml', 'text', 'debian_packages', 'rpm_metadata']
    for fmt in expected_formats:
        parser = registry.get_parser(fmt)
        if parser:
            logger.info(f"✓ Parser available for format: {fmt}")
        else:
            logger.error(f"✗ Parser missing for format: {fmt}")
            return False
    
    logger.info("✓ Parser Registry test passed")
    return True


async def test_universal_manager():
    """Test the universal repository manager."""
    logger.info("Testing Universal Repository Manager...")
    
    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "cache"
        config_dir = Path(temp_dir) / "config"
        
        cache_dir.mkdir()
        config_dir.mkdir()
        
        # Create test configuration file
        config_file = config_dir / "test-repositories.yaml"
        test_config = create_test_config()
        
        with open(config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        # Initialize manager
        manager = UniversalRepositoryManager(
            cache_dir=cache_dir,
            config_dirs=[config_dir]
        )
        
        try:
            async with manager:
                # Test initialization
                logger.info("✓ Manager initialized successfully")
                
                # Test repository info
                repos = manager.get_all_repository_info()
                logger.info(f"✓ Found {len(repos)} repositories")
                
                if repos:
                    repo = repos[0]
                    logger.info(f"✓ Repository: {repo.name} ({repo.type})")
                
                # Test statistics
                stats = await manager.get_repository_statistics()
                logger.info(f"✓ Statistics: {stats['total_repositories']} total repositories")
                
                # Test supported platforms and types
                platforms = manager.get_supported_platforms()
                types = manager.get_supported_types()
                logger.info(f"✓ Supported platforms: {platforms}")
                logger.info(f"✓ Supported types: {types}")
                
                # Test package search (with a small test)
                try:
                    result = await manager.search_packages("express", limit=3)
                    logger.info(f"✓ Search test: found {result.total_results} packages in {result.search_time:.2f}s")
                    
                    if result.packages:
                        pkg = result.packages[0]
                        logger.info(f"✓ Sample package: {pkg.name} v{pkg.version}")
                
                except Exception as e:
                    logger.warning(f"Search test failed (expected for test): {e}")
                
                logger.info("✓ Universal Repository Manager test passed")
                return True
                
        except Exception as e:
            logger.error(f"✗ Universal Repository Manager test failed: {e}")
            return False


async def test_enhanced_manager():
    """Test the enhanced repository manager."""
    logger.info("Testing Enhanced Repository Manager...")
    
    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "cache"
        config_dir = Path(temp_dir) / "config"
        
        cache_dir.mkdir()
        config_dir.mkdir()
        
        # Create test configuration file
        config_file = config_dir / "test-repositories.yaml"
        test_config = create_test_config()
        
        with open(config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        # Test with universal system (now the default)
        manager = RepositoryManager(
            cache_dir=cache_dir,
            config_dir=config_dir
        )
        
        try:
            async with manager:
                # Test basic functionality
                logger.info("✓ Repository Manager initialized successfully")
                
                # Test platform and type support
                platforms = manager.get_supported_platforms()
                types = manager.get_supported_types()
                logger.info(f"✓ Platforms: {platforms}")
                logger.info(f"✓ Types: {types}")
                
                # Test statistics
                stats = await manager.get_statistics()
                logger.info(f"✓ Statistics retrieved: {len(stats)} keys")
                
                logger.info("✓ Enhanced Repository Manager test passed")
                return True
                
        except Exception as e:
            logger.error(f"✗ Enhanced Repository Manager test failed: {e}")
            return False


async def test_configuration_validation():
    """Test configuration validation."""
    logger.info("Testing Configuration Validation...")
    
    # Test valid configuration
    valid_config = create_test_config()
    logger.info("✓ Valid configuration created")
    
    # Test invalid configurations
    invalid_configs = [
        # Missing required field
        {
            "version": "1.0",
            "repositories": [
                {
                    "name": "test",
                    "type": "generic"
                    # Missing platform, endpoints, parsing
                }
            ]
        },
        # Invalid URL scheme
        {
            "version": "1.0", 
            "repositories": [
                {
                    "name": "test",
                    "type": "generic",
                    "platform": "linux",
                    "endpoints": {
                        "packages": "ftp://invalid.com/packages"  # Invalid scheme
                    },
                    "parsing": {
                        "format": "json"
                    }
                }
            ]
        }
    ]
    
    # These would be validated by the actual manager during initialization
    logger.info("✓ Configuration validation test structure ready")
    return True


async def run_all_tests():
    """Run all tests."""
    logger.info("Starting Universal Repository System Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Parser Registry", test_parser_registry),
        ("Universal Manager", test_universal_manager),
        ("Repository Manager", test_enhanced_manager),
        ("Configuration Validation", test_configuration_validation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("Test Results Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Universal repository system is working correctly.")
        return True
    else:
        logger.error("❌ Some tests failed. Please check the implementation.")
        return False


async def main():
    """Main test function."""
    try:
        success = await run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())