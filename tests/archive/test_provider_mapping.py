#!/usr/bin/env python3
"""Test script to verify provider mapping fixes."""

from saigen.models.saidata import Metadata, SaiData
from sai.utils.config import get_config
from sai.providers.loader import ProviderLoader
from sai.providers.base import BaseProvider
from sai.core.saidata_loader import SaidataLoader
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))


def test_provider_priority():
    """Test provider priority system."""
    print("Testing provider priority system...")

    # Load providers
    loader = ProviderLoader()
    providers = loader.load_all_providers()

    # Create provider instances
    provider_instances = []
    for name, provider_data in providers.items():
        provider_instance = BaseProvider(provider_data)
        if provider_instance.is_available():
            provider_instances.append(provider_instance)

    # Sort by priority
    provider_instances.sort(key=lambda p: p.get_priority(), reverse=True)

    print(f"Available providers (sorted by priority):")
    for provider in provider_instances:
        print(f"  {provider.name}: priority {provider.get_priority()}")

    return provider_instances


def test_template_resolution():
    """Test template resolution with terraform saidata."""
    print("\nTesting template resolution...")

    # Load terraform saidata
    try:
        config = get_config()
        saidata_loader = SaidataLoader(config)
        saidata = saidata_loader.load_saidata("terraform")
        print(f"Loaded saidata for terraform: {saidata.metadata.name}")
    except Exception as e:
        print(f"Failed to load terraform saidata: {e}")
        # Create minimal saidata for testing
        saidata = SaiData(version="0.2", metadata=Metadata(name="terraform"))
        print("Using minimal saidata for testing")

    # Test template resolution with brew provider
    loader = ProviderLoader()
    providers = loader.load_all_providers()

    if "brew" in providers:
        brew_provider = BaseProvider(providers["brew"])
        if brew_provider.is_available():
            try:
                resolved = brew_provider.resolve_action_templates("install", saidata, {})
                print(f"Brew install template resolved to: {resolved.get('command', 'No command')}")
            except Exception as e:
                print(f"Template resolution failed: {e}")
        else:
            print("Brew provider not available")
    else:
        print("Brew provider not found")


def test_provider_selection():
    """Test provider selection for terraform."""
    print("\nTesting provider selection for terraform...")

    provider_instances = test_provider_priority()

    # Filter providers that support install action
    install_providers = [p for p in provider_instances if p.has_action("install")]

    print(f"Providers supporting install action:")
    for i, provider in enumerate(install_providers, 1):
        priority = provider.get_priority()
        default_marker = " (default)" if i == 1 else ""
        print(f"  {i}. {provider.name} (priority: {priority}){default_marker}")


if __name__ == "__main__":
    print("SAI Provider Mapping Test")
    print("=" * 40)

    try:
        test_provider_priority()
        test_template_resolution()
        test_provider_selection()
        print("\n✓ All tests completed")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
