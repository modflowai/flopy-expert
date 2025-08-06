#!/usr/bin/env python3
"""
Process issues in batches to avoid timeouts
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import time
import argparse

# Load environment
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)

import langextract as lx
from langextract import data


def create_comprehensive_examples():
    """Create comprehensive extraction examples"""
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
        )
    ]


def prepare_issue_text(issue):
    """Prepare issue text for extraction"""
    parts = []
    orig = issue.get('original_issue', issue)
    
    parts.append(f"TITLE: {orig.get('title', '')}")
    parts.append(f"CREATED: {orig.get('created_at', '')[:10]}")
    parts.append(f"CLOSED: {orig.get('closed_at', '')[:10]}")
    parts.append(f"\nPROBLEM:")
    parts.append(orig.get('body', ''))
    
    comments = orig.get('comments', [])
    if comments:
        parts.append("\nRESOLUTION:")
        for comment in comments:
            author = comment.get('author', 'unknown')
            body = comment.get('body', '')
            created = comment.get('created_at', '')[:10]
            parts.append(f"{created} - {author}: {body}")
    
    return "\n".join(parts)


def extract_from_issue(issue_data, examples):
    """Extract from a single issue"""
    issue_number = issue_data.get('issue_number', 'unknown')
    text = prepare_issue_text(issue_data)
    
    prompt = """Extract structured information about this FloPy issue:
1. Problem details including error and module relationships
2. ALL modules used in the code example
3. Resolution details with timeline
NO DUPLICATES - extract each fact once."""
    
    try:
        result = lx.extract(
            text_or_documents=text,
            prompt_description=prompt,
            examples=examples,
            model_id="gemini-2.5-flash",
            api_key=os.getenv("GEMINI_API_KEY"),
            max_char_buffer=3000,
            temperature=0.3
        )
        
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
                'has_resolution': has_resolution
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
    parser = argparse.ArgumentParser(description='Process issues in batches')
    parser.add_argument('--batch', type=int, default=0, help='Batch number (0-based)')
    parser.add_argument('--size', type=int, default=10, help='Batch size')
    args = parser.parse_args()
    
    # Load enriched data
    input_file = Path("../data/enriched/enriched_flopy_issues_quality_20250804_231116_20250804_232240.json")
    
    print(f"Loading enriched issues from: {input_file}")
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    issues = data.get('enriched_issues', [])
    total_issues = len(issues)
    
    # Calculate batch boundaries
    start_idx = args.batch * args.size
    end_idx = min(start_idx + args.size, total_issues)
    
    if start_idx >= total_issues:
        print(f"Batch {args.batch} is out of range. Total issues: {total_issues}")
        return
    
    batch_issues = issues[start_idx:end_idx]
    print(f"\nProcessing batch {args.batch}: issues {start_idx+1}-{end_idx} of {total_issues}")
    
    # Create examples
    examples = create_comprehensive_examples()
    
    # Process batch
    results = []
    start_time = time.time()
    
    for i, issue in enumerate(batch_issues):
        issue_number = issue.get('issue_number', 'unknown')
        print(f"\nProcessing issue {start_idx+i+1}/{total_issues}: #{issue_number}")
        
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
        if i < len(batch_issues) - 1:
            time.sleep(1)
    
    # Save batch results
    output_dir = Path("../data/extracted/batches")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"batch_{args.batch:03d}_{timestamp}.json"
    
    processing_time = time.time() - start_time
    successful = [r for r in results if 'error' not in r]
    
    batch_data = {
        'metadata': {
            'batch_number': args.batch,
            'batch_size': args.size,
            'start_index': start_idx,
            'end_index': end_idx,
            'timestamp': timestamp,
            'processing_time_seconds': round(processing_time, 2),
            'successful': len(successful),
            'failed': len(results) - len(successful)
        },
        'results': results
    }
    
    with open(output_file, 'w') as f:
        json.dump(batch_data, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"BATCH {args.batch} COMPLETE!")
    print(f"{'='*60}")
    print(f"Results saved to: {output_file}")
    print(f"Processed: {len(results)} issues in {processing_time:.1f} seconds")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(results) - len(successful)}")


if __name__ == "__main__":
    main()