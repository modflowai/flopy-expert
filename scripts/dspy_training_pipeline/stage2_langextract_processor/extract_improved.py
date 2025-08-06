#!/usr/bin/env python3
"""
Improved LangExtract processor focused on comprehensive extraction
Testing with issue #2497: Mf6Splitter + ATS incompatibility
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

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))

import langextract as lx
from langextract import data


def create_comprehensive_examples():
    """Create more comprehensive extraction examples"""
    return [
        # Complete problem extraction
        lx.data.ExampleData(
            text="""TITLE: bug: `Mf6Splitter` does not work when ATS is active
            
**Describe the bug**
Using `flopy.mf6.utils.Mf6Splitter` to split a model with method `split_model()` fails when ATS is active with following error:
`'ModflowUtlats' object has no attribute 'parent_package'`

**Desktop:**
 - OS: Windows 11
 - Flopy v3.9.2, MODFLOW v6.6.1""",
            extractions=[
                lx.data.Extraction(
                    extraction_class="problem",
                    extraction_text="Using `flopy.mf6.utils.Mf6Splitter` to split a model with method `split_model()` fails when ATS is active",
                    attributes={
                        "issue_type": "module_incompatibility",
                        "error_message": "'ModflowUtlats' object has no attribute 'parent_package'",
                        "error_type": "AttributeError",
                        "context": "parallel_model_splitting",
                        "condition": "when ATS is active"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="environment",
                    extraction_text="OS: Windows 11\n - Flopy v3.9.2, MODFLOW v6.6.1",
                    attributes={
                        "os": "Windows 11",
                        "flopy_version": "3.9.2",
                        "modflow_version": "6.6.1"
                    }
                )
            ]
        ),
        # Complete module extraction from code
        lx.data.ExampleData(
            text="""```python
import flopy
sim = flopy.mf6.MFSimulation(sim_name=name, sim_ws=ws)
tdis = flopy.mf6.ModflowTdis(sim, ats_perioddata=[(0, 0.0, 1.0, 30.0, 2.0, 5.0)])
ims = flopy.mf6.ModflowIms(sim)
gwf = flopy.mf6.ModflowGwf(sim, modelname=name)
mfsplit = flopy.mf6.utils.Mf6Splitter(sim)
sim_parallel = mfsplit.split_model(split_array)
```""",
            extractions=[
                lx.data.Extraction(
                    extraction_class="code_snippet",
                    extraction_text="sim = flopy.mf6.MFSimulation(sim_name=name, sim_ws=ws)\ntdis = flopy.mf6.ModflowTdis(sim, ats_perioddata=[(0, 0.0, 1.0, 30.0, 2.0, 5.0)])\nims = flopy.mf6.ModflowIms(sim)\ngwf = flopy.mf6.ModflowGwf(sim, modelname=name)\nmfsplit = flopy.mf6.utils.Mf6Splitter(sim)\nsim_parallel = mfsplit.split_model(split_array)",
                    attributes={
                        "code_type": "reproducer",
                        "demonstrates": "ATS configuration with model splitting"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="module_usage",
                    extraction_text="flopy.mf6.MFSimulation",
                    attributes={
                        "module": "MFSimulation",
                        "package": "flopy.mf6",
                        "role": "simulation_setup"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="module_usage",
                    extraction_text="flopy.mf6.ModflowTdis",
                    attributes={
                        "module": "ModflowTdis",
                        "package": "flopy.mf6",
                        "role": "time_discretization",
                        "critical_param": "ats_perioddata"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="module_usage",
                    extraction_text="flopy.mf6.utils.Mf6Splitter",
                    attributes={
                        "module": "Mf6Splitter",
                        "package": "flopy.mf6.utils",
                        "role": "model_parallelization",
                        "method_called": "split_model"
                    }
                )
            ]
        ),
        # Resolution and timeline extraction
        lx.data.ExampleData(
            text="""jlarsen-usgs: @cneyens I'll take a look at this today and try to provide a fix.
            
[8 days later]
jlarsen-usgs: @cneyens ATS support has been implemented in develop

cneyens: Thanks @jlarsen-usgs!""",
            extractions=[
                lx.data.Extraction(
                    extraction_class="developer_response",
                    extraction_text="@cneyens I'll take a look at this today and try to provide a fix",
                    attributes={
                        "developer": "jlarsen-usgs",
                        "commitment": "will_fix",
                        "timeline": "same_day"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="resolution",
                    extraction_text="ATS support has been implemented in develop",
                    attributes={
                        "resolution_type": "feature_implementation",
                        "what_fixed": "ATS support in Mf6Splitter",
                        "target_branch": "develop",
                        "implementer": "jlarsen-usgs",
                        "days_to_fix": 8
                    }
                ),
                lx.data.Extraction(
                    extraction_class="user_confirmation",
                    extraction_text="Thanks @jlarsen-usgs!",
                    attributes={
                        "user": "cneyens",
                        "confirms_fix": True
                    }
                )
            ]
        ),
        # Module relationships
        lx.data.ExampleData(
            text="Mf6Splitter does not work when ATS is active. The error 'ModflowUtlats' object has no attribute 'parent_package' suggests that Mf6Splitter needs special handling for ATS objects.",
            extractions=[
                lx.data.Extraction(
                    extraction_class="module_relationship",
                    extraction_text="Mf6Splitter does not work when ATS is active",
                    attributes={
                        "module_1": "Mf6Splitter",
                        "module_2": "ModflowUtlats",
                        "relationship": "incompatible",
                        "condition": "when ATS is active",
                        "reason": "missing parent_package attribute handling"
                    }
                )
            ]
        )
    ]


def extract_issue_2497_comprehensive():
    """Extract comprehensive data from issue #2497"""
    
    # Full issue #2497 data
    issue_2497 = {
        "number": 2497,
        "title": "bug: `Mf6Splitter` does not work when ATS is active",
        "created_at": "2025-04-29T11:57:58+00:00",
        "closed_at": "2025-05-08T21:09:03+00:00",
        "body": """**Describe the bug**
Using `flopy.mf6.utils.Mf6Splitter` to split a model with method `split_model()` or `split_multi_model()` fails when ATS is active with following error:
`'ModflowUtlats' object has no attribute 'parent_package'`

I can get the parallel simulation with ATS to run when preparing the input files by hand.

**To reproduce**
<details open>
  <summary>Reprex</summary>
  
  ```py
import flopy
import os

ws = './mymodel'
name = 'mymodel'
mf6_extended = 'mf6'

sim = flopy.mf6.MFSimulation(sim_name=name, sim_ws=ws, exe_name=mf6_extended)
tdis = flopy.mf6.ModflowTdis(sim, 
                             perioddata=[(365.0, 20, 1.2)],
                             ats_perioddata=[(0, 0.0, 1.0, 30.0, 2.0, 5.0)], # ATS input data, omit this line to run without ATS
                             )
ims = flopy.mf6.ModflowIms(sim)
gwf = flopy.mf6.ModflowGwf(sim, modelname=name)
dis = flopy.mf6.ModflowGwfdis(gwf, nrow=10, ncol=10)
ic = flopy.mf6.ModflowGwfic(gwf)
npf = flopy.mf6.ModflowGwfnpf(gwf, k=10.)
sto = flopy.mf6.ModflowGwfsto(gwf, transient={0: True}, iconvert=1)
wel = flopy.mf6.ModflowGwfwel(gwf, stress_period_data=[[(0, 5, 5), -1.]])
chd = flopy.mf6.ModflowGwfchd(gwf, stress_period_data=[[(0, 0, 0), 1.],
                                                       [(0, 9, 9), 0.]])
budget_file = name + '.bud'
head_file = name + '.hds'
oc = flopy.mf6.ModflowGwfoc(gwf,
                            budget_filerecord=budget_file,
                            head_filerecord=head_file,
                            saverecord=[('HEAD', 'ALL'), ('BUDGET', 'ALL')],
                            printrecord=[('BUDGET', 'ALL')])

# run in sequential mode
sim.write_simulation(silent=True)
succes, pbuff = sim.run_simulation(silent=True)
assert succes, pbuff

# parallel set-up
ncores = 2
simdir = os.path.join(sim.sim_path, 'parallel')
mfsplit = flopy.mf6.utils.Mf6Splitter(sim)
split_array = mfsplit.optimize_splitting_mask(ncores)
sim_parallel = mfsplit.split_model(split_array) # gives error with ATS
sim_parallel.set_sim_path(simdir)

# write sim and run in parallel
sim_parallel.write_simulation(silent=True)
succes, pbuff = sim_parallel.run_simulation(silent=False, processors=ncores)
assert succes, pbuff

  ```
</details>

**Expected behavior**
The `Mf6Splitter` should work whether ATS is active or not.

**Desktop (please complete the following information):**
 - OS: Windows 11
 - Flopy v3.9.2, MODFLOW v6.6.1
""",
        "comments": [
            {
                "author": "jlarsen-usgs",
                "created_at": "2025-04-29T16:25:53Z",
                "body": "@cneyens \n\nI'll take a look at this today and try to provide a fix."
            },
            {
                "author": "jlarsen-usgs",
                "created_at": "2025-05-08T21:10:35Z",
                "body": "@cneyens \n\nATS support has been implemented in develop"
            },
            {
                "author": "cneyens",
                "created_at": "2025-05-09T09:01:44Z",
                "body": "> @cneyens \n> \n> ATS support has been implemented in develop\n\nThanks @jlarsen-usgs! "
            }
        ]
    }
    
    # Prepare complete text
    parts = []
    parts.append(f"TITLE: {issue_2497['title']}")
    parts.append(f"CREATED: {issue_2497['created_at']}")
    parts.append(f"CLOSED: {issue_2497['closed_at']}")
    parts.append(f"\nBODY:\n{issue_2497['body']}")
    parts.append("\nCOMMENTS:")
    for comment in issue_2497['comments']:
        parts.append(f"\n{comment['created_at']} - {comment['author']}:\n{comment['body']}")
    
    full_text = "\n".join(parts)
    
    # Create comprehensive prompt
    prompt = """Extract ALL information from this GitHub issue with NO DUPLICATES:

1. Problems: Extract the main problem ONCE with all details (error messages, types, conditions)
2. Environment: Extract OS, FloPy version, MODFLOW version
3. Code snippets: Extract the complete reproducer code
4. Module usage: Extract ALL modules used in code (not just the problematic one)
5. Module relationships: Identify incompatibilities and dependencies
6. Developer responses: Who responded, what they committed to
7. Resolution: What was fixed, where, when, by whom
8. User confirmation: Did the user confirm the fix worked?
9. Timeline: How long from report to fix?

IMPORTANT: 
- Extract each unique piece of information ONLY ONCE
- Include ALL modules from code examples, not just the main one
- Capture the relationship between modules (e.g., what doesn't work together)
- Include timeline information (days between comments)"""
    
    # Create examples
    examples = create_comprehensive_examples()
    
    # Run extraction
    print("Extracting comprehensive data from issue #2497...")
    try:
        result = lx.extract(
            text_or_documents=full_text,
            prompt_description=prompt,
            examples=examples,
            model_id="gemini-2.5-flash",
            api_key=os.getenv("GEMINI_API_KEY"),
            max_char_buffer=4000,  # Larger buffer for complete issue
            temperature=0.3  # Lower temperature for consistency
        )
        
        # Process results
        extractions_by_class = {}
        for ext in result.extractions:
            cls = ext.extraction_class
            if cls not in extractions_by_class:
                extractions_by_class[cls] = []
            extractions_by_class[cls].append({
                'text': ext.extraction_text,
                'attributes': ext.attributes
            })
        
        # Save results
        output_dir = Path("../data/extracted")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"issue_2497_comprehensive_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                'issue_number': 2497,
                'title': issue_2497['title'],
                'extraction_summary': {
                    'total_extractions': len(result.extractions),
                    'classes_found': list(extractions_by_class.keys()),
                    'deduplication': 'enforced'
                },
                'extractions': extractions_by_class
            }, f, indent=2)
        
        print(f"\nExtraction complete! Saved to: {output_file}")
        
        # Print summary
        print("\nExtraction Summary:")
        for cls, items in extractions_by_class.items():
            print(f"\n{cls.upper()} ({len(items)} items):")
            for item in items:
                text_preview = item['text'][:80] + "..." if len(item['text']) > 80 else item['text']
                print(f"  - {text_preview}")
                if cls in ['problem', 'module_relationship', 'resolution']:
                    for key, value in item['attributes'].items():
                        print(f"    {key}: {value}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    extract_issue_2497_comprehensive()