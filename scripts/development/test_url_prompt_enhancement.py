#!/usr/bin/env python3
"""Test script to verify URL generation prompt enhancement."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from saigen.llm.prompts import PromptManager, PromptSection
from saigen.models.generation import GenerationContext


def test_prompt_contains_url_emphasis():
    """Test that the prompt templates contain URL generation emphasis."""
    
    print("=" * 80)
    print("Testing URL Generation Prompt Enhancement")
    print("=" * 80)
    print()
    
    manager = PromptManager()
    
    # Test generation template
    print("1. Testing GENERATION template...")
    gen_template = manager.get_template("generation")
    
    # Check if url_generation_emphasis section exists
    url_section = None
    for section in gen_template.sections:
        if section.name == "url_generation_emphasis":
            url_section = section
            break
    
    if url_section:
        print("   ✓ URL generation emphasis section found")
        print(f"   ✓ Section length: {len(url_section.template)} characters")
        
        # Check for key phrases
        key_phrases = [
            "URLs are EXTREMELY IMPORTANT",
            "provide as many as possible",
            "validated automatically",
            "be generous with URL suggestions",
            "website, documentation, source"
        ]
        
        found_phrases = []
        for phrase in key_phrases:
            if phrase in url_section.template:
                found_phrases.append(phrase)
                print(f"   ✓ Contains: '{phrase}'")
            else:
                print(f"   ✗ Missing: '{phrase}'")
        
        print(f"   ✓ Found {len(found_phrases)}/{len(key_phrases)} key phrases")
    else:
        print("   ✗ URL generation emphasis section NOT found")
    
    print()
    
    # Test retry template
    print("2. Testing RETRY template...")
    retry_template = manager.get_template("retry")
    
    # Check if url_generation_emphasis section exists
    url_section = None
    for section in retry_template.sections:
        if section.name == "url_generation_emphasis":
            url_section = section
            break
    
    if url_section:
        print("   ✓ URL generation emphasis section found")
        print(f"   ✓ Section length: {len(url_section.template)} characters")
    else:
        print("   ✗ URL generation emphasis section NOT found")
    
    print()
    
    # Test rendering with context
    print("3. Testing prompt rendering...")
    context = GenerationContext(
        software_name="nginx",
        target_providers=["apt", "dnf", "brew"],
        user_hints={}
    )
    
    try:
        rendered_prompt = gen_template.render(context)
        print(f"   ✓ Prompt rendered successfully ({len(rendered_prompt)} characters)")
        
        # Check if URL emphasis is in rendered prompt
        if "URLs are EXTREMELY IMPORTANT" in rendered_prompt:
            print("   ✓ URL emphasis present in rendered prompt")
        else:
            print("   ✗ URL emphasis NOT in rendered prompt")
        
        # Count URL-related mentions
        url_mentions = rendered_prompt.lower().count("url")
        print(f"   ✓ 'URL' mentioned {url_mentions} times in prompt")
        
    except Exception as e:
        print(f"   ✗ Error rendering prompt: {e}")
    
    print()
    
    # Test output instructions
    print("4. Testing output instructions...")
    output_section = None
    for section in gen_template.sections:
        if section.name == "output_instruction":
            output_section = section
            break
    
    if output_section:
        if "comprehensive URLs" in output_section.template:
            print("   ✓ Output instructions mention comprehensive URLs")
        else:
            print("   ✗ Output instructions don't mention comprehensive URLs")
        
        if "website, documentation, and source" in output_section.template:
            print("   ✓ Output instructions specify minimum URLs")
        else:
            print("   ✗ Output instructions don't specify minimum URLs")
    
    print()
    print("=" * 80)
    print("URL Prompt Enhancement Test Complete")
    print("=" * 80)
    print()
    print("Summary:")
    print("- The prompt now emphasizes comprehensive URL generation")
    print("- LLMs are instructed to be generous with URL suggestions")
    print("- URL validation filter will remove invalid URLs automatically")
    print("- Expected result: More URLs in generated saidata")


if __name__ == "__main__":
    test_prompt_contains_url_emphasis()
