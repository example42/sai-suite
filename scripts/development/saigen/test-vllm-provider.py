#!/usr/bin/env python3
"""Test script for vLLM provider integration."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from saigen.llm.providers.vllm import VLLMProvider
from saigen.models.generation import GenerationContext


async def test_connection():
    """Test vLLM server connection."""
    print("Testing vLLM connection...")
    
    config = {
        "base_url": "http://localhost:8000/v1",
        "model": "meta-llama/Meta-Llama-3-70B-Instruct",
        "temperature": 0.1,
        "max_tokens": 500
    }
    
    try:
        provider = VLLMProvider(config)
        print(f"✓ Provider initialized")
        
        # Check if available
        if not provider.is_available():
            print("✗ Provider not available (configuration issue)")
            return False
        print(f"✓ Provider available")
        
        # Validate connection
        connected = await provider.validate_connection()
        if not connected:
            print("✗ Cannot connect to vLLM server")
            print("  Make sure vLLM is running at http://localhost:8000")
            return False
        print(f"✓ Connected to vLLM server")
        
        # Get model info
        model_info = provider.get_model_info()
        print(f"\nModel Information:")
        print(f"  Name: {model_info.name}")
        print(f"  Provider: {model_info.provider}")
        print(f"  Max Tokens: {model_info.max_tokens}")
        print(f"  Context Window: {model_info.context_window}")
        print(f"  Capabilities: {[c.value for c in model_info.capabilities]}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_generation():
    """Test saidata generation."""
    print("\n" + "="*60)
    print("Testing saidata generation...")
    print("="*60)
    
    config = {
        "base_url": "http://localhost:8000/v1",
        "model": "meta-llama/Meta-Llama-3-70B-Instruct",
        "temperature": 0.1,
        "max_tokens": 1000
    }
    
    try:
        provider = VLLMProvider(config)
        
        # Create a simple generation context
        context = GenerationContext(
            software_name="nginx",
            repository_data=[],
            similar_saidata=[],
            sample_saidata=[],
            target_providers=["apt", "brew"]
        )
        
        print(f"\nGenerating saidata for: {context.software_name}")
        print("This may take 30-60 seconds...")
        
        response = await provider.generate_saidata(context)
        
        print(f"\n✓ Generation successful!")
        print(f"  Tokens used: {response.tokens_used}")
        print(f"  Cost: ${response.cost_estimate:.4f}")
        print(f"  Model: {response.model_used}")
        print(f"  Finish reason: {response.finish_reason}")
        
        print(f"\nGenerated content (first 500 chars):")
        print("-" * 60)
        print(response.content[:500])
        if len(response.content) > 500:
            print(f"... ({len(response.content) - 500} more characters)")
        print("-" * 60)
        
        return True
        
    except Exception as e:
        print(f"✗ Generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_model_requirements():
    """Test model requirements lookup."""
    print("\n" + "="*60)
    print("Model Requirements")
    print("="*60)
    
    config = {
        "base_url": "http://localhost:8000/v1",
        "model": "meta-llama/Meta-Llama-3-70B-Instruct"
    }
    
    provider = VLLMProvider(config)
    
    print("\nAvailable models:")
    for model in provider.get_available_models():
        reqs = provider.get_model_requirements(model)
        if reqs:
            print(f"\n  {model}")
            print(f"    GPU Memory: {reqs['gpu_memory_gb']}GB")
            print(f"    Recommended GPUs: {reqs['recommended_tensor_parallel']}")
            print(f"    Context Window: {reqs['context_window']}")


async def main():
    """Run all tests."""
    print("="*60)
    print("vLLM Provider Test Suite")
    print("="*60)
    
    # Test connection
    connection_ok = await test_connection()
    if not connection_ok:
        print("\n✗ Connection test failed")
        print("\nTo start vLLM server, run:")
        print("  ./scripts/development/saigen/start-vllm-dgx.sh")
        return 1
    
    # Test generation
    generation_ok = await test_generation()
    if not generation_ok:
        print("\n✗ Generation test failed")
        return 1
    
    # Show model requirements
    await test_model_requirements()
    
    print("\n" + "="*60)
    print("✓ All tests passed!")
    print("="*60)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
