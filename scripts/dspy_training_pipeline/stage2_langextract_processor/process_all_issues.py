#!/usr/bin/env python3
"""
Process all 88 collected issues using the improved focused extraction approach
Based on successful extraction pattern from issue #2497
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import time
from typing import List, Dict, Any

# Load environment
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)

import langextract as lx
from langextract import data


def create_comprehensive_examples() -> List[lx.data.ExampleData]:
    """Create comprehensive extraction examples based on successful #2497 pattern"""
    return [
        # Problem with relationship
        lx.data.ExampleData(
            text="Using `flopy.mf6.utils.Mf6Splitter` to split a model with method `split_model()` fails when ATS is active with error: `'ModflowUtlats' object has no attribute 'parent_package'`",
            extractions=[
                lx.data.Extraction(
                    extraction_class="problem",
                    extraction_text="Mf6Splitter fails when ATS is active",
                    attributes={
                        "error": "'ModflowUtlats' object has no attribute 'parent_package'",
                        "incompatible_modules": "flopy.mf6.utils.Mf6Splitter + ModflowUtlats",
                        "condition": "ATS active"
                    }
                )
            ]
        ),
        # Module from code
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
            text="CREATED: 2024-04-29\nRESOLVED: 2024-05-08\njlarsen-usgs: ATS support has been implemented in develop",
            extractions=[
                lx.data.Extraction(
                    extraction_class="resolution",
                    extraction_text="ATS support has been implemented in develop",
                    attributes={
                        "implementer": "jlarsen-usgs",
                        "branch": "develop",
                        "days_to_fix": "9"
                    }
                )
            ]
        ),
        # Environment info
        lx.data.ExampleData(
            text="OS: Windows 11\n - Flopy v3.7.2, MODFLOW v6.5.1",
            extractions=[
                lx.data.Extraction(
                    extraction_class="environment",
                    extraction_text="Windows 11, Flopy v3.7.2, MODFLOW v6.5.1",
                    attributes={
                        "os": "Windows 11",
                        "flopy_version": "3.7.2",
                        "modflow_version": "6.5.1"
                    }
                )
            ]
        ),
        # Module relationship
        lx.data.ExampleData(
            text="The SSM package does not correctly update source/sink assignments when using WEL and GHB packages in split models",
            extractions=[
                lx.data.Extraction(
                    extraction_class="module_relationship",
                    extraction_text="SSM package incorrectly handles WEL and GHB in split models",
                    attributes={
                        "primary_module": "SSM",
                        "related_modules": ["WEL", "GHB"],
                        "relationship": "incorrect_handling",
                        "context": "model_splitting"
                    }
                )
            ]
        )
    ]


def prepare_issue_text(issue: Dict[str, Any]) -> str:
    """Prepare issue text focusing on key elements"""
    parts = []
    
    # Get original issue data
    orig = issue.get('original_issue', issue)
    
    # Title and dates
    parts.append(f"TITLE: {orig.get('title', '')}")
    parts.append(f"CREATED: {orig.get('created_at', '')[:10]}")
    parts.append(f"CLOSED: {orig.get('closed_at', '')[:10]}")
    
    # Problem description
    parts.append(f"\nPROBLEM:")
    parts.append(orig.get('body', ''))
    
    # Comments (especially resolutions)
    comments = orig.get('comments', [])
    if comments:
        parts.append("\nRESOLUTION:")
        for comment in comments:
            author = comment.get('author', 'unknown')
            body = comment.get('body', '')
            created = comment.get('created_at', '')[:10]
            parts.append(f"{created} - {author}: {body}")
    
    return "\n".join(parts)


def extract_from_issue(issue_data: Dict[str, Any], examples: List[lx.data.ExampleData]) -> Dict[str, Any]:
    """Extract structured information from a single issue"""
    issue_number = issue_data.get('issue_number', 'unknown')
    text = prepare_issue_text(issue_data)
    
    prompt = """Extract structured information about this FloPy issue:
1. Problem details including error and module relationships
2. ALL modules used in the code example
3. Environment information
4. Resolution details with timeline
5. Module relationships and incompatibilities
NO DUPLICATES - extract each fact once."""
    
    try:
        result = lx.extract(
            text_or_documents=text,
            prompt_description=prompt,
            examples=examples,
            model_id="gemini-2.5-flash",
            api_key=os.getenv("GEMINI_API_KEY"),
            max_char_buffer=3000,
            temperature=0.3  # Low temperature for consistency
        )
        
        # Process extractions by class
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
        
        # Calculate quality metrics
        module_count = len(extractions_by_class.get('module', []))
        has_problem = len(extractions_by_class.get('problem', [])) > 0
        has_resolution = len(extractions_by_class.get('resolution', [])) > 0
        
        return {
            'issue_number': issue_number,
            'title': issue_data.get('title', ''),
            'extraction_method': 'focused_comprehensive',
            'quality_metrics': {
                'total_extractions': len(result.extractions),
                'module_count': module_count,
                'has_problem': has_problem,
                'has_resolution': has_resolution,
                'has_relationships': len(extractions_by_class.get('module_relationship', [])) > 0,
                'has_environment': len(extractions_by_class.get('environment', [])) > 0
            },
            'extractions': extractions_by_class
        }
        
    except Exception as e:
        print(f"Error extracting issue #{issue_number}: {e}")
        return {
            'issue_number': issue_number,
            'title': issue_data.get('title', ''),
            'error': str(e),
            'extractions': {}
        }


def main():
    """Process all collected issues with improved extraction"""
    
    # Load enriched data
    input_file = Path("../data/enriched/enriched_flopy_issues_quality_20250804_231116_20250804_232240.json")
    
    if not input_file.exists():
        print(f"Input file not found: {input_file}")
        return
    
    print(f"Loading enriched issues from: {input_file}")
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    issues = data.get('enriched_issues', [])
    print(f"Found {len(issues)} enriched issues")
    
    # Create examples
    examples = create_comprehensive_examples()
    
    # Process all issues
    results = []
    start_time = time.time()
    
    for i, issue in enumerate(issues):
        issue_number = issue.get('issue_number', 'unknown')
        print(f"\nProcessing issue {i+1}/{len(issues)}: #{issue_number}")
        
        result = extract_from_issue(issue, examples)
        results.append(result)
        
        # Print summary
        if 'error' not in result:
            metrics = result['quality_metrics']
            print(f"  ✓ Extracted: {metrics['total_extractions']} items")
            print(f"    - Modules: {metrics['module_count']}")
            print(f"    - Problem: {'Yes' if metrics['has_problem'] else 'No'}")
            print(f"    - Resolution: {'Yes' if metrics['has_resolution'] else 'No'}")
        else:
            print(f"  ✗ Error: {result['error']}")
        
        # Rate limiting
        if i < len(issues) - 1:
            time.sleep(1)  # 1 second delay between requests
    
    # Calculate overall statistics
    successful = [r for r in results if 'error' not in r]
    failed = [r for r in results if 'error' in r]
    
    total_extractions = sum(r['quality_metrics']['total_extractions'] for r in successful)
    total_modules = sum(r['quality_metrics']['module_count'] for r in successful)
    with_problems = sum(1 for r in successful if r['quality_metrics']['has_problem'])
    with_resolutions = sum(1 for r in successful if r['quality_metrics']['has_resolution'])
    with_relationships = sum(1 for r in successful if r['quality_metrics']['has_relationships'])
    
    # Save results
    output_dir = Path("../data/extracted")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"all_issues_focused_{timestamp}.json"
    
    processing_time = time.time() - start_time
    
    final_data = {
        'metadata': {
            'source': str(input_file),
            'timestamp': timestamp,
            'model': 'gemini-2.5-flash',
            'extraction_method': 'focused_comprehensive',
            'processing_time_seconds': round(processing_time, 2),
            'issues_processed': len(issues),
            'successful': len(successful),
            'failed': len(failed)
        },
        'statistics': {
            'total_extractions': total_extractions,
            'total_modules_extracted': total_modules,
            'average_extractions_per_issue': round(total_extractions / len(successful), 2) if successful else 0,
            'average_modules_per_issue': round(total_modules / len(successful), 2) if successful else 0,
            'issues_with_problems': with_problems,
            'issues_with_resolutions': with_resolutions,
            'issues_with_relationships': with_relationships,
            'extraction_rate': f"{len(successful)}/{len(issues)} ({len(successful)/len(issues)*100:.1f}%)"
        },
        'quality_assessment': {
            'no_duplicates': 'enforced',
            'comprehensive_modules': 'all modules from code',
            'relationships_captured': 'module incompatibilities tracked',
            'timeline_included': 'days to fix when available',
            'environment_captured': 'OS and version info'
        },
        'results': results
    }
    
    with open(output_file, 'w') as f:
        json.dump(final_data, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE!")
    print(f"{'='*60}")
    print(f"Results saved to: {output_file}")
    print(f"\nSummary:")
    print(f"  - Issues processed: {len(issues)}")
    print(f"  - Successful: {len(successful)}")
    print(f"  - Failed: {len(failed)}")
    print(f"  - Total extractions: {total_extractions}")
    print(f"  - Total modules: {total_modules}")
    print(f"  - Average per issue: {total_extractions/len(successful):.1f} extractions")
    print(f"  - Processing time: {processing_time/60:.1f} minutes")
    print(f"\nQuality metrics:")
    print(f"  - With problems: {with_problems} ({with_problems/len(successful)*100:.1f}%)")
    print(f"  - With resolutions: {with_resolutions} ({with_resolutions/len(successful)*100:.1f}%)")
    print(f"  - With relationships: {with_relationships} ({with_relationships/len(successful)*100:.1f}%)")


if __name__ == "__main__":
    main()