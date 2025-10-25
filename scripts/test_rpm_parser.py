#!/usr/bin/env python3
"""Test script for RPM metadata parser."""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from saigen.repositories.universal_manager import UniversalRepositoryManager

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def test_dnf_repositories():
    """Test DNF repository parsing."""
    print("\n" + "="*80)
    print("Testing DNF Repository Parsing")
    print("="*80 + "\n")
    
    from pathlib import Path
    cache_dir = Path.home() / ".sai" / "cache" / "test_rpm"
    config_dirs = [Path(__file__).parent.parent / "saigen" / "repositories" / "configs"]
    
    manager = UniversalRepositoryManager(cache_dir=cache_dir, config_dirs=config_dirs)
    await manager.initialize()
    
    # Test a few DNF repositories
    test_repos = [
        "dnf-rocky-9",
        "dnf-alma-9",
        "dnf-centos-stream-9",
    ]
    
    for repo_name in test_repos:
        print(f"\n{'='*60}")
        print(f"Testing: {repo_name}")
        print(f"{'='*60}")
        
        try:
            # Download packages (use_cache=False to force fresh download)
            print(f"Downloading package list...")
            packages = await manager.get_packages(repo_name, use_cache=False)
            
            print(f"✅ Successfully downloaded {len(packages)} packages")
            
            # Show sample packages
            if packages:
                print(f"\nSample packages (first 5):")
                for pkg in packages[:5]:
                    print(f"  - {pkg.name} {pkg.version}")
                    if pkg.description:
                        desc = pkg.description[:60] + "..." if len(pkg.description) > 60 else pkg.description
                        print(f"    {desc}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.exception(f"Failed to test {repo_name}")
    
    await manager.close()


async def test_zypper_repositories():
    """Test Zypper repository parsing."""
    print("\n" + "="*80)
    print("Testing Zypper Repository Parsing")
    print("="*80 + "\n")
    
    from pathlib import Path
    cache_dir = Path.home() / ".sai" / "cache" / "test_rpm"
    config_dirs = [Path(__file__).parent.parent / "saigen" / "repositories" / "configs"]
    
    manager = UniversalRepositoryManager(cache_dir=cache_dir, config_dirs=config_dirs)
    await manager.initialize()
    
    # Test Zypper repositories
    test_repos = [
        "zypper-opensuse-leap-15",
        "zypper-opensuse-tumbleweed",
    ]
    
    for repo_name in test_repos:
        print(f"\n{'='*60}")
        print(f"Testing: {repo_name}")
        print(f"{'='*60}")
        
        try:
            # Download packages (use_cache=False to force fresh download)
            print(f"Downloading package list...")
            packages = await manager.get_packages(repo_name, use_cache=False)
            
            print(f"✅ Successfully downloaded {len(packages)} packages")
            
            # Show sample packages
            if packages:
                print(f"\nSample packages (first 5):")
                for pkg in packages[:5]:
                    print(f"  - {pkg.name} {pkg.version}")
                    if pkg.description:
                        desc = pkg.description[:60] + "..." if len(pkg.description) > 60 else pkg.description
                        print(f"    {desc}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.exception(f"Failed to test {repo_name}")
    
    await manager.close()


async def main():
    """Run all tests."""
    await test_dnf_repositories()
    await test_zypper_repositories()
    
    print("\n" + "="*80)
    print("Testing Complete")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
