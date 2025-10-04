#!/usr/bin/env python3
"""
Test script to verify provider deduplication logic for all resource types.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from saigen.models.saidata import (
    SaiData, Metadata, Package, Service, File, Directory, Command, Port,
    ProviderConfig, ServiceType, FileType, Protocol
)
from saigen.core.generation_engine import GenerationEngine

def test_deduplication():
    """Test that duplicate provider resources are removed across all types."""
    
    print("Testing comprehensive provider deduplication...")
    
    # Create test saidata with duplicates across all resource types
    saidata = SaiData(
        version="0.3",
        metadata=Metadata(
            name="test-software",
            description="Test software"
        ),
        packages=[
            Package(name="main", package_name="test-software", version="1.0.0"),
        ],
        services=[
            Service(name="main", service_name="test-service", type=ServiceType.SYSTEMD),
        ],
        files=[
            File(name="config", path="/etc/test/config.conf", type=FileType.CONFIG),
        ],
        directories=[
            Directory(name="data", path="/var/lib/test", owner="root", group="root"),
        ],
        commands=[
            Command(name="test", path="/usr/bin/test"),
        ],
        ports=[
            Port(port=8080, protocol=Protocol.TCP, service="http"),
        ],
        providers={
            "apt": ProviderConfig(
                packages=[
                    # Exact duplicate - should be removed
                    Package(name="main", package_name="test-software"),
                    # Different version - should be kept
                    Package(name="main", package_name="test-software", version="2.0.0"),
                ],
                services=[
                    # Exact duplicate - should be removed
                    Service(name="main", service_name="test-service", type=ServiceType.SYSTEMD),
                ],
                files=[
                    # Exact duplicate - should be removed
                    File(name="config", path="/etc/test/config.conf", type=FileType.CONFIG),
                ],
                directories=[
                    # Exact duplicate - should be removed
                    Directory(name="data", path="/var/lib/test", owner="root", group="root"),
                ],
                commands=[
                    # Exact duplicate - should be removed
                    Command(name="test", path="/usr/bin/test"),
                ],
                ports=[
                    # Exact duplicate - should be removed
                    Port(port=8080, protocol=Protocol.TCP, service="http"),
                ]
            ),
            "dnf": ProviderConfig(
                packages=[
                    # Different package name - should be kept (Apache/httpd case)
                    Package(name="main", package_name="httpd"),
                ],
                services=[
                    # Different service name - should be kept
                    Service(name="main", service_name="httpd", type=ServiceType.SYSTEMD),
                ],
                files=[
                    # Different path - should be kept
                    File(name="config", path="/etc/httpd/conf/httpd.conf", type=FileType.CONFIG),
                ],
                directories=[
                    # Different path - should be kept
                    Directory(name="data", path="/var/lib/httpd", owner="root", group="root"),
                ],
            )
        }
    )
    
    print(f"\nBefore deduplication:")
    print(f"  apt: packages={len(saidata.providers['apt'].packages)}, services={len(saidata.providers['apt'].services)}, files={len(saidata.providers['apt'].files)}")
    print(f"  dnf: packages={len(saidata.providers['dnf'].packages)}, services={len(saidata.providers['dnf'].services)}, files={len(saidata.providers['dnf'].files)}")
    
    # Create engine and deduplicate
    engine = GenerationEngine()
    deduplicated = engine._deduplicate_provider_configs(saidata)
    
    print(f"\nAfter deduplication:")
    apt_pkg = len(deduplicated.providers['apt'].packages) if deduplicated.providers['apt'].packages else 0
    apt_svc = len(deduplicated.providers['apt'].services) if deduplicated.providers['apt'].services else 0
    apt_file = len(deduplicated.providers['apt'].files) if deduplicated.providers['apt'].files else 0
    apt_dir = len(deduplicated.providers['apt'].directories) if deduplicated.providers['apt'].directories else 0
    apt_cmd = len(deduplicated.providers['apt'].commands) if deduplicated.providers['apt'].commands else 0
    apt_port = len(deduplicated.providers['apt'].ports) if deduplicated.providers['apt'].ports else 0
    
    dnf_pkg = len(deduplicated.providers['dnf'].packages) if deduplicated.providers['dnf'].packages else 0
    dnf_svc = len(deduplicated.providers['dnf'].services) if deduplicated.providers['dnf'].services else 0
    dnf_file = len(deduplicated.providers['dnf'].files) if deduplicated.providers['dnf'].files else 0
    dnf_dir = len(deduplicated.providers['dnf'].directories) if deduplicated.providers['dnf'].directories else 0
    
    print(f"  apt: packages={apt_pkg}, services={apt_svc}, files={apt_file}, directories={apt_dir}, commands={apt_cmd}, ports={apt_port}")
    print(f"  dnf: packages={dnf_pkg}, services={dnf_svc}, files={dnf_file}, directories={dnf_dir}")
    
    # Verify results
    errors = []
    
    # apt should have 1 package (with different version), 0 of everything else
    if apt_pkg != 1:
        errors.append(f"apt should have 1 package (different version), got {apt_pkg}")
    if apt_svc != 0:
        errors.append(f"apt should have 0 services (duplicate), got {apt_svc}")
    if apt_file != 0:
        errors.append(f"apt should have 0 files (duplicate), got {apt_file}")
    if apt_dir != 0:
        errors.append(f"apt should have 0 directories (duplicate), got {apt_dir}")
    if apt_cmd != 0:
        errors.append(f"apt should have 0 commands (duplicate), got {apt_cmd}")
    if apt_port != 0:
        errors.append(f"apt should have 0 ports (duplicate), got {apt_port}")
    
    # dnf should keep all (different names/paths)
    if dnf_pkg != 1:
        errors.append(f"dnf should have 1 package (different name), got {dnf_pkg}")
    if dnf_svc != 1:
        errors.append(f"dnf should have 1 service (different name), got {dnf_svc}")
    if dnf_file != 1:
        errors.append(f"dnf should have 1 file (different path), got {dnf_file}")
    if dnf_dir != 1:
        errors.append(f"dnf should have 1 directory (different path), got {dnf_dir}")
    
    if errors:
        print("\n❌ ERRORS:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✅ Comprehensive deduplication test PASSED!")
        print("   - Exact duplicates removed")
        print("   - Resources with differences kept")
        print("   - All resource types handled correctly")
        return True

if __name__ == "__main__":
    success = test_deduplication()
    sys.exit(0 if success else 1)
