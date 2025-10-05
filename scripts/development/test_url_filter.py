#!/usr/bin/env python3
"""Test script for URL validation filter."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from saigen.models.saidata import SaiData, Metadata, Urls, Source, Binary, Script
from saigen.core.url_filter import URLValidationFilter


async def test_url_filter():
    """Test URL validation filter with sample saidata."""
    
    # Create sample saidata with mix of valid and invalid URLs
    saidata = SaiData(
        version="0.3",
        metadata=Metadata(
            name="test-software",
            description="Test software for URL filtering",
            urls=Urls(
                website="https://www.google.com",  # Valid
                documentation="https://invalid-url-that-does-not-exist-12345.com",  # Invalid
                source="https://github.com/example42/sai",  # Valid
                issues="https://nonexistent-domain-xyz-123.org/issues"  # Invalid
            )
        ),
        sources=[
            Source(
                name="source1",
                url="https://github.com/example42/sai/archive/main.tar.gz",  # Valid
                build_system="cmake"
            ),
            Source(
                name="source2",
                url="https://fake-download-site-xyz.com/source.tar.gz",  # Invalid
                build_system="make"
            )
        ],
        binaries=[
            Binary(
                name="binary1",
                url="https://www.python.org/ftp/python/3.11.0/Python-3.11.0.tgz"  # Valid
            ),
            Binary(
                name="binary2",
                url="https://nonexistent-binary-host.com/binary.tar.gz"  # Invalid
            )
        ],
        scripts=[
            Script(
                name="script1",
                url="https://raw.githubusercontent.com/example42/sai/main/README.md"  # Valid
            ),
            Script(
                name="script2",
                url="https://fake-script-host-xyz.com/install.sh"  # Invalid
            )
        ]
    )
    
    print("=" * 80)
    print("Testing URL Validation Filter")
    print("=" * 80)
    print()
    
    print("Original saidata:")
    print(f"  - Website: {saidata.metadata.urls.website}")
    print(f"  - Documentation: {saidata.metadata.urls.documentation}")
    print(f"  - Source: {saidata.metadata.urls.source}")
    print(f"  - Issues: {saidata.metadata.urls.issues}")
    print(f"  - Sources: {len(saidata.sources)} items")
    for source in saidata.sources:
        print(f"    - {source.name}: {source.url}")
    print(f"  - Binaries: {len(saidata.binaries)} items")
    for binary in saidata.binaries:
        print(f"    - {binary.name}: {binary.url}")
    print(f"  - Scripts: {len(saidata.scripts)} items")
    for script in saidata.scripts:
        print(f"    - {script.name}: {script.url}")
    print()
    
    print("Validating URLs...")
    print()
    
    # Apply URL filter
    async with URLValidationFilter(timeout=5, max_concurrent=5) as url_filter:
        filtered_saidata = await url_filter.filter_saidata(saidata)
    
    print()
    print("Filtered saidata:")
    print(f"  - Website: {filtered_saidata.metadata.urls.website}")
    print(f"  - Documentation: {filtered_saidata.metadata.urls.documentation}")
    print(f"  - Source: {filtered_saidata.metadata.urls.source}")
    print(f"  - Issues: {filtered_saidata.metadata.urls.issues}")
    print(f"  - Sources: {len(filtered_saidata.sources)} items")
    for source in filtered_saidata.sources:
        print(f"    - {source.name}: {source.url}")
    print(f"  - Binaries: {len(filtered_saidata.binaries)} items")
    for binary in filtered_saidata.binaries:
        print(f"    - {binary.name}: {binary.url}")
    print(f"  - Scripts: {len(filtered_saidata.scripts)} items")
    for script in filtered_saidata.scripts:
        print(f"    - {script.name}: {script.url}")
    print()
    
    print("=" * 80)
    print("URL Filtering Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_url_filter())
