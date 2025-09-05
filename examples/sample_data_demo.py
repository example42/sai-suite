#!/usr/bin/env python3
"""
Demo script showing how sample data improves LLM prompts.

This script demonstrates the difference between LLM prompts with and without
sample data optimization.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from saigen.models.generation import GenerationContext
from saigen.llm.prompts import PromptManager
from saigen.repositories.indexer import RAGContextBuilder
from saigen.models.saidata import SaiData


class MockRAGIndexer:
    """Mock RAG indexer for demonstration."""
    
    async def search_similar_packages(self, query, limit=5):
        return []
    
    async def find_similar_saidata(self, query, limit=3):
        return []


async def demo_prompt_comparison():
    """Demonstrate the difference in prompts with and without sample data."""
    
    print("Sample Data Optimization Demo")
    print("=" * 50)
    
    # Create prompt manager
    prompt_manager = PromptManager()
    template = prompt_manager.get_template("generation")
    
    # Demo 1: Without sample data
    print("\n1. PROMPT WITHOUT SAMPLE DATA:")
    print("-" * 30)
    
    context_without_samples = GenerationContext(
        software_name="nginx",
        target_providers=["apt", "brew", "winget"],
        repository_data=[],
        similar_saidata=[],
        sample_saidata=[],  # No samples
        user_hints=None,
        existing_saidata=None
    )
    
    prompt_without = template.render(context_without_samples)
    print(prompt_without[:800] + "..." if len(prompt_without) > 800 else prompt_without)
    
    # Demo 2: With sample data
    print("\n\n2. PROMPT WITH SAMPLE DATA:")
    print("-" * 30)
    
    # Load sample data
    config = {
        'use_default_samples': True,
        'default_samples_directory': Path('docs/saidata_samples'),
        'max_sample_examples': 2
    }
    
    indexer = MockRAGIndexer()
    context_builder = RAGContextBuilder(indexer, config)
    
    # Load samples
    sample_data = await context_builder._load_default_sample_saidata()
    
    context_with_samples = GenerationContext(
        software_name="nginx",
        target_providers=["apt", "brew", "winget"],
        repository_data=[],
        similar_saidata=[],
        sample_saidata=sample_data[:2],  # Include samples
        user_hints=None,
        existing_saidata=None
    )
    
    prompt_with = template.render(context_with_samples)
    print(prompt_with[:800] + "..." if len(prompt_with) > 800 else prompt_with)
    
    # Show statistics
    print("\n\n3. COMPARISON STATISTICS:")
    print("-" * 30)
    print(f"Prompt without samples: {len(prompt_without):,} characters")
    print(f"Prompt with samples:    {len(prompt_with):,} characters")
    print(f"Difference:             +{len(prompt_with) - len(prompt_without):,} characters")
    print(f"Sample files included:  {len(sample_data)}")
    
    # Show sample content preview
    if sample_data:
        print(f"\n4. SAMPLE DATA INCLUDED:")
        print("-" * 30)
        for i, saidata in enumerate(sample_data[:2], 1):
            print(f"Sample {i}: {saidata.metadata.name}")
            print(f"  Category: {saidata.metadata.category}")
            print(f"  Providers: {', '.join(saidata.providers.keys())}")
            if saidata.providers:
                first_provider = list(saidata.providers.items())[0]
                provider_name, provider_config = first_provider
                if provider_config.packages:
                    pkg_names = [pkg.name for pkg in provider_config.packages[:2]]
                    print(f"  {provider_name} packages: {', '.join(pkg_names)}")
            print()


async def demo_context_building():
    """Demonstrate how context is built with sample data."""
    
    print("\n5. CONTEXT BUILDING PROCESS:")
    print("-" * 30)
    
    config = {
        'use_default_samples': True,
        'default_samples_directory': Path('docs/saidata_samples'),
        'max_sample_examples': 3
    }
    
    indexer = MockRAGIndexer()
    context_builder = RAGContextBuilder(indexer, config)
    
    # Build context
    context = await context_builder.build_context(
        software_name="redis",
        target_providers=["apt", "brew", "winget"],
        max_packages=5,
        max_saidata=3
    )
    
    print(f"Software: redis")
    print(f"Similar packages found: {len(context['similar_packages'])}")
    print(f"Similar saidata found: {len(context['similar_saidata'])}")
    print(f"Sample saidata loaded: {len(context['sample_saidata'])}")
    print(f"Context summary: {context['context_summary']}")
    
    if context['sample_saidata']:
        print(f"\nSample files used as examples:")
        for saidata in context['sample_saidata']:
            print(f"  - {saidata.metadata.name} ({saidata.metadata.category})")


def show_configuration_example():
    """Show configuration examples."""
    
    print("\n6. CONFIGURATION EXAMPLES:")
    print("-" * 30)
    
    print("Enable sample data (auto-detect):")
    print("  saigen config samples --auto-detect")
    
    print("\nUse custom sample directory:")
    print("  saigen config samples --directory /path/to/samples")
    
    print("\nDisable sample data:")
    print("  saigen config samples --disable")
    
    print("\nView current configuration:")
    print("  saigen config samples")
    
    print("\nGenerate with verbose output:")
    print("  saigen generate --verbose nginx")


async def main():
    """Run the demo."""
    try:
        await demo_prompt_comparison()
        await demo_context_building()
        show_configuration_example()
        
        print("\n" + "=" * 50)
        print("Demo completed successfully!")
        print("\nKey Benefits of Sample Data Optimization:")
        print("• Provides high-quality examples to the LLM")
        print("• Improves consistency and structure of generated saidata")
        print("• Reduces errors and validation failures")
        print("• Shows best practices for multi-provider configurations")
        print("• Configurable and easy to customize")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)