#!/usr/bin/env python3
"""
Example demonstrating the retry generation feature in saigen.

This example shows how the generation engine automatically retries
when the first LLM response fails validation.
"""

import asyncio
from pathlib import Path
from unittest.mock import Mock

from saigen.core.generation_engine import GenerationEngine
from saigen.models.generation import GenerationRequest, LLMProvider
from saigen.llm.providers.base import LLMResponse


async def demonstrate_retry_generation():
    """Demonstrate the retry generation feature."""
    
    print("🔄 Retry Generation Feature Demo")
    print("=" * 50)
    
    # Create a generation engine
    config = {
        "llm_providers": {
            "openai": {
                "api_key": "demo-key",
                "model": "gpt-3.5-turbo"
            }
        }
    }
    
    engine = GenerationEngine(config)
    
    # Mock the LLM provider to simulate validation failure then success
    mock_provider = Mock()
    
    # First response: Invalid YAML (missing required fields)
    invalid_response = LLMResponse(
        content="""
version: "invalid-version"
metadata:
  description: "Web server"
  # Missing required 'name' field
providers:
  apt:
    packages: []
""",
        tokens_used=300,
        cost_estimate=0.0006
    )
    
    # Second response: Valid YAML (retry succeeds)
    valid_response = LLMResponse(
        content="""
version: "0.2"
metadata:
  name: "nginx"
  description: "High-performance web server and reverse proxy"
  category: "web-server"
  homepage: "https://nginx.org"
  license: "BSD-2-Clause"
providers:
  apt:
    packages:
      - name: "nginx"
        version: "latest"
  brew:
    packages:
      - name: "nginx"
        version: "latest"
  winget:
    packages:
      - name: "nginx.nginx"
        version: "latest"
""",
        tokens_used=450,
        cost_estimate=0.0009
    )
    
    # Set up mock to return invalid first, then valid on retry
    mock_provider.generate_saidata.side_effect = [invalid_response, valid_response]
    mock_provider.get_provider_name.return_value = "openai"
    
    # Add mock provider to engine
    engine._llm_providers["openai"] = mock_provider
    
    # Create generation request
    request = GenerationRequest(
        software_name="nginx",
        target_providers=["apt", "brew", "winget"],
        llm_provider=LLMProvider.OPENAI,
        use_rag=False
    )
    
    print(f"📝 Generating saidata for: {request.software_name}")
    print(f"🎯 Target providers: {', '.join(request.target_providers)}")
    print(f"🤖 LLM Provider: {request.llm_provider.value}")
    print()
    
    # Generate saidata (this will trigger the retry mechanism)
    result = await engine.generate_saidata(request)
    
    # Display results
    print("📊 Generation Results:")
    print(f"✅ Success: {result.success}")
    print(f"⏱️  Generation time: {result.generation_time:.2f}s")
    print(f"🔄 LLM calls made: {mock_provider.generate_saidata.call_count}")
    
    if result.success:
        print(f"📦 Generated saidata for: {result.saidata.metadata.name}")
        print(f"🏷️  Category: {result.saidata.metadata.category}")
        print(f"🔧 Providers: {', '.join(result.saidata.providers.keys())}")
        print(f"💰 Total cost estimate: ${result.cost_estimate:.4f}")
        print(f"🎫 Total tokens used: {result.tokens_used}")
        
        # Show that retry was successful
        print()
        print("🔄 Retry Mechanism Details:")
        print("1. First attempt failed validation (invalid version, missing name)")
        print("2. System automatically retried with validation feedback")
        print("3. Second attempt succeeded with corrected YAML")
        print("4. Final result contains valid saidata")
        
        # Save the result
        output_path = Path("nginx_retry_demo.yaml")
        await engine.save_saidata(result.saidata, output_path)
        print(f"💾 Saved to: {output_path}")
        
    else:
        print("❌ Generation failed even after retry")
        for error in result.validation_errors:
            print(f"   - {error.field}: {error.message}")
    
    print()
    print("🎉 Demo completed!")


async def demonstrate_retry_failure():
    """Demonstrate when both original and retry attempts fail."""
    
    print("\n🚫 Retry Failure Demo")
    print("=" * 30)
    
    # Create a generation engine
    engine = GenerationEngine({})
    
    # Mock provider that returns invalid YAML for both attempts
    mock_provider = Mock()
    
    invalid_response1 = LLMResponse(
        content="invalid: yaml: [unclosed",
        tokens_used=200,
        cost_estimate=0.0004
    )
    
    invalid_response2 = LLMResponse(
        content="still: invalid: yaml: {unclosed",
        tokens_used=250,
        cost_estimate=0.0005
    )
    
    mock_provider.generate_saidata.side_effect = [invalid_response1, invalid_response2]
    mock_provider.get_provider_name.return_value = "openai"
    engine._llm_providers["openai"] = mock_provider
    
    request = GenerationRequest(
        software_name="test-software",
        llm_provider=LLMProvider.OPENAI,
        use_rag=False
    )
    
    result = await engine.generate_saidata(request)
    
    print(f"❌ Success: {result.success}")
    print(f"🔄 LLM calls made: {mock_provider.generate_saidata.call_count}")
    print("📝 Both original and retry attempts failed validation")
    print("💡 This demonstrates the system's safety mechanism to prevent infinite retries")


if __name__ == "__main__":
    asyncio.run(demonstrate_retry_generation())
    asyncio.run(demonstrate_retry_failure())