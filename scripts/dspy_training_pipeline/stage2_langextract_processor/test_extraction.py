#!/usr/bin/env python3
"""
Test LangExtract on a single issue to verify setup and extraction quality
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))

from extract_comprehensive import ComprehensiveIssueExtractor


def test_single_issue():
    """Test extraction on a single issue"""
    
    # Sample issue from our data (simplified)
    test_issue = {
        "number": 2497,
        "title": "bug: `Mf6Splitter` does not work when ATS is active",
        "body": """**Describe the bug**
Using `flopy.mf6.utils.Mf6Splitter` to split a model with method `split_model()` fails when ATS is active with following error:
`'ModflowUtlats' object has no attribute 'parent_package'`

**To reproduce**
```python
import flopy
sim = flopy.mf6.MFSimulation(sim_name=name, sim_ws=ws)
tdis = flopy.mf6.ModflowTdis(sim, ats_perioddata=[(0, 0.0, 1.0, 30.0, 2.0, 5.0)])
mfsplit = flopy.mf6.utils.Mf6Splitter(sim)
sim_parallel = mfsplit.split_model(split_array) # gives error with ATS
```

**Expected behavior**
The `Mf6Splitter` should work whether ATS is active or not.

**Desktop:**
 - OS: Windows 11
 - Flopy v3.9.2, MODFLOW v6.6.1
""",
        "labels": ["bug"],
        "state": "closed",
        "created_at": "2025-04-29T11:57:58+00:00",
        "closed_at": "2025-05-08T21:09:03+00:00",
        "comments": [
            {
                "author": "jlarsen-usgs",
                "body": "@cneyens I'll take a look at this today and try to provide a fix."
            },
            {
                "author": "jlarsen-usgs",
                "body": "@cneyens ATS support has been implemented in develop"
            },
            {
                "author": "cneyens",
                "body": "Thanks @jlarsen-usgs!"
            }
        ]
    }
    
    # Initialize extractor
    print("Initializing LangExtract...")
    try:
        extractor = ComprehensiveIssueExtractor()
        print("✓ Extractor initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return
    
    # Test extraction
    print(f"\nTesting extraction on issue #{test_issue['number']}: {test_issue['title']}")
    print("-" * 80)
    
    try:
        result = extractor.extract_comprehensive(test_issue)
        
        # Display results
        print("\n=== EXTRACTION RESULTS ===")
        
        # Problem extraction
        if 'problem' in result['extractions']:
            print("\nPROBLEM ANALYSIS:")
            problem = result['extractions']['problem']
            if 'extractions' in problem:
                for ext in problem['extractions']:
                    print(f"  Text: {ext.get('text', '')}")
                    attrs = ext.get('attributes', {})
                    for key, value in attrs.items():
                        print(f"    {key}: {value}")
        
        # Module extraction
        if 'module' in result['extractions']:
            print("\nMODULE REFERENCES:")
            modules = result['extractions']['module']
            if 'extractions' in modules:
                for ext in modules['extractions']:
                    print(f"  Found: {ext.get('text', '')}")
                    attrs = ext.get('attributes', {})
                    if 'module_name' in attrs:
                        print(f"    Module: {attrs['module_name']}")
                    if 'full_path' in attrs:
                        print(f"    Path: {attrs['full_path']}")
        
        # Code extraction
        if 'code' in result['extractions']:
            print("\nCODE SNIPPETS:")
            code = result['extractions']['code']
            if 'extractions' in code:
                for ext in code['extractions']:
                    attrs = ext.get('attributes', {})
                    snippet_type = attrs.get('snippet_type', 'unknown')
                    print(f"  {snippet_type.upper()}:")
                    print(f"    {ext.get('text', '')[:100]}...")
        
        # Resolution extraction
        if 'resolution' in result['extractions']:
            print("\nRESOLUTION:")
            resolution = result['extractions']['resolution']
            if 'extractions' in resolution:
                for ext in resolution['extractions']:
                    print(f"  {ext.get('text', '')}")
                    attrs = ext.get('attributes', {})
                    if 'resolution_type' in attrs:
                        print(f"    Type: {attrs['resolution_type']}")
        
        # Environment extraction
        if 'environment' in result['extractions']:
            print("\nENVIRONMENT:")
            env = result['extractions']['environment']
            if 'extractions' in env:
                for ext in env['extractions']:
                    attrs = ext.get('attributes', {})
                    for key, value in attrs.items():
                        print(f"  {key}: {value}")
        
        # Relationships
        if 'relationships' in result['extractions']:
            print("\nRELATIONSHIPS:")
            for rel in result['extractions']['relationships']:
                print(f"  {rel['source']} {rel['type']} {rel['target']}")
                print(f"    Evidence: {rel['evidence']}")
        
        # Save full result
        output_file = Path("test_extraction_result.json")
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n✓ Full result saved to: {output_file}")
        
    except Exception as e:
        print(f"\n✗ Extraction failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=== LangExtract Test Script ===")
    print("Testing comprehensive extraction on a sample FloPy issue\n")
    
    # Check API key
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not set in .env file")
        sys.exit(1)
    
    test_single_issue()