#!/usr/bin/env python3
"""
Focused extraction for issue #2497 with key improvements
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)

import langextract as lx
from langextract import data


def extract_issue_2497_focused():
    """Extract focused data from issue #2497"""
    
    # Key improvements in examples
    examples = [
        # Problem with relationship
        lx.data.ExampleData(
            text="Using `flopy.mf6.utils.Mf6Splitter` to split a model with method `split_model()` fails when ATS is active with error: `'ModflowUtlats' object has no attribute 'parent_package'`",
            extractions=[
                lx.data.Extraction(
                    extraction_class="problem",
                    extraction_text="Mf6Splitter fails when ATS is active",
                    attributes={
                        "error": "'ModflowUtlats' object has no attribute 'parent_package'",
                        "incompatible_modules": "Mf6Splitter + ModflowUtlats",
                        "condition": "ATS active"
                    }
                )
            ]
        ),
        # All modules from code
        lx.data.ExampleData(
            text="tdis = flopy.mf6.ModflowTdis(sim, ats_perioddata=[(0, 0.0, 1.0, 30.0, 2.0, 5.0)])",
            extractions=[
                lx.data.Extraction(
                    extraction_class="module",
                    extraction_text="flopy.mf6.ModflowTdis",
                    attributes={
                        "package": "flopy.mf6",
                        "module": "ModflowTdis",
                        "key_param": "ats_perioddata"
                    }
                )
            ]
        ),
        # Resolution with timeline
        lx.data.ExampleData(
            text="CREATED: 2025-04-29\nRESOLVED: 2025-05-08\njlarsen-usgs: ATS support has been implemented in develop",
            extractions=[
                lx.data.Extraction(
                    extraction_class="resolution",
                    extraction_text="ATS support has been implemented in develop",
                    attributes={
                        "implementer": "jlarsen-usgs",
                        "branch": "develop",
                        "days_to_fix": 9
                    }
                )
            ]
        )
    ]
    
    # Simplified issue text focusing on key elements
    issue_text = """
TITLE: bug: `Mf6Splitter` does not work when ATS is active
CREATED: 2025-04-29
CLOSED: 2025-05-08

PROBLEM:
Using `flopy.mf6.utils.Mf6Splitter` to split a model with method `split_model()` fails when ATS is active with error:
`'ModflowUtlats' object has no attribute 'parent_package'`

CODE:
sim = flopy.mf6.MFSimulation(sim_name=name, sim_ws=ws)
tdis = flopy.mf6.ModflowTdis(sim, ats_perioddata=[(0, 0.0, 1.0, 30.0, 2.0, 5.0)])
ims = flopy.mf6.ModflowIms(sim)
gwf = flopy.mf6.ModflowGwf(sim, modelname=name)
mfsplit = flopy.mf6.utils.Mf6Splitter(sim)
sim_parallel = mfsplit.split_model(split_array)

ENVIRONMENT:
OS: Windows 11
Flopy v3.9.2, MODFLOW v6.6.1

RESOLUTION:
jlarsen-usgs: I'll take a look at this today
[9 days later]
jlarsen-usgs: ATS support has been implemented in develop
cneyens: Thanks!
"""
    
    prompt = """Extract structured information about this FloPy issue:
1. Problem details including error and module relationships
2. ALL modules used in the code example
3. Environment information
4. Resolution details with timeline
NO DUPLICATES - extract each fact once."""
    
    print("Extracting focused data from issue #2497...")
    
    try:
        result = lx.extract(
            text_or_documents=issue_text,
            prompt_description=prompt,
            examples=examples,
            model_id="gemini-2.5-flash",
            api_key=os.getenv("GEMINI_API_KEY"),
            max_char_buffer=2000,
            temperature=0.3
        )
        
        # Process and display results
        print(f"\nExtracted {len(result.extractions)} items:")
        
        extractions_by_class = {}
        for ext in result.extractions:
            cls = ext.extraction_class
            if cls not in extractions_by_class:
                extractions_by_class[cls] = []
            
            extraction_data = {
                'text': ext.extraction_text,
                'attributes': ext.attributes
            }
            extractions_by_class[cls].append(extraction_data)
            
            # Print summary
            print(f"\n[{cls.upper()}] {ext.extraction_text[:60]}...")
            for key, value in ext.attributes.items():
                print(f"  {key}: {value}")
        
        # Save results
        output_dir = Path("../data/extracted")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"issue_2497_focused_{timestamp}.json"
        
        result_data = {
            'issue_number': 2497,
            'extraction_method': 'focused_comprehensive',
            'improvements': [
                'No duplicates',
                'All modules extracted',
                'Module relationships captured',
                'Timeline included',
                'Environment captured'
            ],
            'extractions': extractions_by_class
        }
        
        with open(output_file, 'w') as f:
            json.dump(result_data, f, indent=2)
        
        print(f"\nSaved to: {output_file}")
        
        # Analysis
        print("\nAnalysis:")
        print(f"- Problem extractions: {len(extractions_by_class.get('problem', []))}")
        print(f"- Module extractions: {len(extractions_by_class.get('module', []))}")
        print(f"- Resolution extractions: {len(extractions_by_class.get('resolution', []))}")
        
        # Check if we got all expected modules
        expected_modules = ['MFSimulation', 'ModflowTdis', 'ModflowIms', 'ModflowGwf', 'Mf6Splitter']
        found_modules = []
        for ext in extractions_by_class.get('module', []):
            if 'module' in ext['attributes']:
                found_modules.append(ext['attributes']['module'])
        
        print(f"\nModule coverage: {len(found_modules)}/{len(expected_modules)}")
        print(f"Found: {', '.join(found_modules)}")
        missing = set(expected_modules) - set(found_modules)
        if missing:
            print(f"Missing: {', '.join(missing)}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    extract_issue_2497_focused()