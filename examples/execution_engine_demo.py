#!/usr/bin/env python3
"""Demo script for ExecutionEngine functionality."""

import logging
import sys
from pathlib import Path

# Add the parent directory to the path so we can import sai modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sai.core.execution_engine import ExecutionEngine, ExecutionContext
from sai.providers.base import ProviderFactory
from sai.providers.loader import ProviderLoader
from sai.core.saidata_loader import SaidataLoader
from sai.models.saidata import SaiData, Metadata


def setup_logging():
    """Set up logging for the demo."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_sample_saidata() -> SaiData:
    """Create sample saidata for demonstration."""
    return SaiData(
        version="0.2",
        metadata=Metadata(
            name="curl",
            display_name="cURL",
            description="Command line tool for transferring data with URLs"
        )
    )


def main():
    """Main demo function."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("=== SAI ExecutionEngine Demo ===\n")
    
    try:
        # Create provider factory and load providers
        print("1. Loading providers...")
        factory = ProviderFactory.create_default_factory()
        providers = factory.create_available_providers()
        
        if not providers:
            print("❌ No providers available on this system")
            print("   Make sure you have package managers like apt, brew, or dnf installed")
            return
        
        print(f"✅ Found {len(providers)} available providers:")
        for provider in providers:
            actions = ", ".join(provider.get_supported_actions())
            print(f"   - {provider.display_name} ({provider.name}): {actions}")
        
        # Create execution engine
        print("\n2. Creating execution engine...")
        engine = ExecutionEngine(providers)
        print(f"✅ ExecutionEngine initialized with {len(engine.get_available_providers())} providers")
        
        # Create sample saidata
        print("\n3. Creating sample saidata...")
        saidata = create_sample_saidata()
        print(f"✅ Created saidata for: {saidata.metadata.display_name}")
        
        # Demonstrate dry run execution
        print("\n4. Demonstrating dry-run execution...")
        context = ExecutionContext(
            action="install",
            software="curl",
            saidata=saidata,
            dry_run=True,
            verbose=True
        )
        
        result = engine.execute_action(context)
        
        print(f"📋 Dry Run Result:")
        print(f"   Success: {result.success}")
        print(f"   Status: {result.status}")
        print(f"   Provider: {result.provider_used}")
        print(f"   Commands that would be executed:")
        for cmd in result.commands_executed:
            print(f"     {cmd}")
        print(f"   Message: {result.message}")
        
        # Demonstrate provider selection
        print("\n5. Demonstrating provider selection...")
        supported_actions = engine.get_supported_actions()
        
        print("📊 Supported actions by provider:")
        for provider_name, actions in supported_actions.items():
            print(f"   {provider_name}: {', '.join(actions)}")
        
        # Try with specific provider if available
        if len(providers) > 1:
            print(f"\n6. Demonstrating specific provider selection...")
            specific_provider = providers[1].name  # Use second provider
            
            context_specific = ExecutionContext(
                action="install",
                software="curl",
                saidata=saidata,
                provider=specific_provider,
                dry_run=True
            )
            
            result_specific = engine.execute_action(context_specific)
            print(f"✅ Forced provider '{specific_provider}': {result_specific.success}")
        
        # Demonstrate unsupported action
        print(f"\n7. Demonstrating unsupported action handling...")
        context_unsupported = ExecutionContext(
            action="nonexistent-action",
            software="curl",
            saidata=saidata,
            dry_run=True
        )
        
        result_unsupported = engine.execute_action(context_unsupported)
        print(f"❌ Unsupported action result: {result_unsupported.success}")
        print(f"   Message: {result_unsupported.message}")
        
        print("\n🎉 Demo completed successfully!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"❌ Demo failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())