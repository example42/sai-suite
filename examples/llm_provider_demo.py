#!/usr/bin/env python3
"""Demo script showing LLM provider functionality."""

import asyncio
from typing import List

from saigen.llm.providers.base import ModelCapability
from saigen.llm.providers.openai import OpenAIProvider
from saigen.llm.prompts import PromptManager
from saigen.models.generation import GenerationContext
from saigen.models.repository import RepositoryPackage


def create_sample_context() -> GenerationContext:
    """Create a sample generation context for testing."""
    
    # Sample repository packages
    repository_packages = [
        RepositoryPackage(
            name="nginx",
            version="1.20.1",
            description="HTTP and reverse proxy server",
            repository_name="apt",
            platform="linux",
            homepage="https://nginx.org"
        ),
        RepositoryPackage(
            name="nginx",
            version="1.21.0",
            description="HTTP and reverse proxy server",
            repository_name="brew",
            platform="macos",
            homepage="https://nginx.org"
        )
    ]
    
    return GenerationContext(
        software_name="nginx",
        target_providers=["apt", "brew", "winget"],
        repository_data=repository_packages,
        user_hints={
            "category": "web-server",
            "include_ssl": True,
            "default_config": "/etc/nginx/nginx.conf"
        }
    )


def demo_prompt_generation():
    """Demonstrate prompt template functionality."""
    print("=== Prompt Generation Demo ===")
    
    # Create prompt manager
    manager = PromptManager()
    print(f"Available templates: {manager.list_templates()}")
    
    # Create sample context
    context = create_sample_context()
    
    # Generate prompt for saidata creation
    template = manager.get_template("generation")
    prompt = template.render(context)
    
    print(f"\nGenerated prompt length: {len(prompt)} characters")
    print("\nPrompt preview (first 500 chars):")
    print("-" * 50)
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    print("-" * 50)


def demo_openai_provider():
    """Demonstrate OpenAI provider functionality."""
    print("\n=== OpenAI Provider Demo ===")
    
    # Note: This demo uses a dummy API key for testing configuration
    # In real usage, you would use a valid OpenAI API key
    config = {
        "api_key": "sk-dummy-key-for-demo",
        "model": "gpt-3.5-turbo",
        "max_tokens": 4000,
        "temperature": 0.1
    }
    
    try:
        provider = OpenAIProvider(config)
        print("✓ Provider initialized successfully")
        
        # Get model information
        model_info = provider.get_model_info()
        print(f"✓ Model: {model_info.name}")
        print(f"✓ Provider: {model_info.provider}")
        print(f"✓ Max tokens: {model_info.max_tokens}")
        print(f"✓ Context window: {model_info.context_window}")
        print(f"✓ Capabilities: {[cap.value for cap in model_info.capabilities]}")
        
        # Test capability checking
        print(f"✓ Supports text generation: {provider.supports_capability(ModelCapability.TEXT_GENERATION)}")
        print(f"✓ Supports code generation: {provider.supports_capability(ModelCapability.CODE_GENERATION)}")
        print(f"✓ Supports function calling: {provider.supports_capability(ModelCapability.FUNCTION_CALLING)}")
        
        # Test cost estimation
        cost = provider.estimate_cost(1000)
        print(f"✓ Estimated cost for 1000 tokens: ${cost:.4f}")
        
        # List available models
        models = provider.get_available_models()
        print(f"✓ Available models: {models}")
        
        # Test model switching
        provider.set_model("gpt-4")
        print(f"✓ Switched to model: {provider.model}")
        
        print("\nNote: This demo uses a dummy API key.")
        print("To test actual generation, set a valid OpenAI API key in the config.")
        
    except Exception as e:
        print(f"✗ Error: {e}")


async def demo_generation_workflow():
    """Demonstrate the complete generation workflow (without API calls)."""
    print("\n=== Generation Workflow Demo ===")
    
    # Create context
    context = create_sample_context()
    print(f"Software: {context.software_name}")
    print(f"Target providers: {context.target_providers}")
    print(f"Repository packages: {len(context.repository_data)}")
    print(f"User hints: {context.user_hints}")
    
    # Generate prompt
    manager = PromptManager()
    template = manager.get_template("generation")
    prompt = template.render(context)
    
    print(f"\n✓ Generated prompt ({len(prompt)} chars)")
    
    # Show what would happen with a real API call
    print("\nWith a valid API key, the workflow would:")
    print("1. Send the prompt to OpenAI GPT model")
    print("2. Receive YAML saidata content")
    print("3. Validate the generated content")
    print("4. Return structured response with metadata")
    
    # Simulate response structure
    print("\nExpected response structure:")
    print("- content: Generated YAML saidata")
    print("- tokens_used: Number of tokens consumed")
    print("- cost_estimate: Estimated cost in USD")
    print("- model_used: Model that generated the content")
    print("- finish_reason: Completion reason (stop, length, etc.)")


def main():
    """Run all demos."""
    print("LLM Provider Functionality Demo")
    print("=" * 40)
    
    demo_prompt_generation()
    demo_openai_provider()
    
    # Run async demo
    asyncio.run(demo_generation_workflow())
    
    print("\n" + "=" * 40)
    print("Demo completed successfully!")
    print("\nNext steps:")
    print("1. Set up a valid OpenAI API key")
    print("2. Test actual saidata generation")
    print("3. Implement additional LLM providers (Anthropic, Ollama)")


if __name__ == "__main__":
    main()