#!/usr/bin/env python3
"""
Test script to verify prompt improvements for saidata generation.
This script checks that the prompt template includes the correct structure.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from saigen.llm.prompts import SAIDATA_GENERATION_TEMPLATE

def test_prompt_structure():
    """Test that the prompt template has the correct structure."""
    
    print("Testing SAIDATA_GENERATION_TEMPLATE structure...")
    print(f"Template name: {SAIDATA_GENERATION_TEMPLATE.name}")
    print(f"Number of sections: {len(SAIDATA_GENERATION_TEMPLATE.sections)}")
    print()
    
    # Check for required sections
    section_names = [s.name for s in SAIDATA_GENERATION_TEMPLATE.sections]
    print("Sections found:")
    for name in section_names:
        print(f"  - {name}")
    print()
    
    # Find and check the schema_requirements section
    schema_section = None
    for section in SAIDATA_GENERATION_TEMPLATE.sections:
        if section.name == "schema_requirements":
            schema_section = section
            break
    
    if not schema_section:
        print("❌ ERROR: schema_requirements section not found!")
        return False
    
    print("Checking schema_requirements section content...")
    
    # Check for key phrases that should be in the updated prompt
    required_phrases = [
        "Top-Level Resource Sections",
        "IMPORTANT - almost always needed",
        "Optional Installation Method Sections",
        "only include with valid, verified data",
        "Provider and Compatibility Sections"
    ]
    
    missing_phrases = []
    for phrase in required_phrases:
        if phrase not in schema_section.template:
            missing_phrases.append(phrase)
    
    if missing_phrases:
        print("❌ ERROR: Missing required phrases in schema_requirements:")
        for phrase in missing_phrases:
            print(f"  - {phrase}")
        return False
    else:
        print("✅ All required phrases found in schema_requirements")
    
    # Check the example structure section
    if "**EXAMPLE 0.3 STRUCTURE:**" in schema_section.template:
        print("✅ Example structure section found")
        
        # Check for top-level sections in example
        example_sections = ["packages:", "services:", "files:", "directories:", "commands:", "ports:"]
        missing_sections = []
        for section in example_sections:
            if section not in schema_section.template:
                missing_sections.append(section)
        
        if missing_sections:
            print("❌ ERROR: Missing sections in example:")
            for section in missing_sections:
                print(f"  - {section}")
            return False
        else:
            print("✅ All top-level sections present in example")
    else:
        print("❌ ERROR: Example structure section not found")
        return False
    
    # Check output instructions
    output_section = None
    for section in SAIDATA_GENERATION_TEMPLATE.sections:
        if section.name == "output_instruction":
            output_section = section
            break
    
    if output_section:
        if "ALWAYS include top-level sections" in output_section.template:
            print("✅ Output instructions emphasize top-level sections")
        else:
            print("⚠️  WARNING: Output instructions don't emphasize top-level sections")
    
    print()
    print("=" * 60)
    print("✅ Prompt structure test PASSED!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_prompt_structure()
    sys.exit(0 if success else 1)
