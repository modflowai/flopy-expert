#!/usr/bin/env python3
"""
Process issues incrementally, saving after each one
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
        # Resolution
        lx.data.ExampleData(
            text="jlarsen-usgs: ATS support has been implemented in develop",
            extractions=[
                lx.data.Extraction(
                    extraction_class="resolution",
                    extraction_text="ATS support has been implemented in develop",
                    attributes={
                        "implementer": "jlarsen-usgs",
                        "branch": "develop"
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
    parts.append(f"PROBLEM: {orig.get('body', '')[:2000]}")  # Limit body size
    
    # Add first few comments
    comments = orig.get('comments', [])[:3]  # Limit to first 3 comments
    if comments:
        parts.append("\nCOMMENTS:")
        for comment in comments:
            author = comment.get('author', 'unknown')
            body = comment.get('body', '')[:500]  # Limit comment size
            parts.append(f"{author}: {body}")
    
    return "\n".join(parts)


def extract_from_issue(issue_data, examples):
    """Extract from a single issue"""
    issue_number = issue_data.get('issue_number', 'unknown')
    text = prepare_issue_text(issue_data)
    
    prompt = """Extract: 1) Problem with error, 2) ALL modules mentioned, 3) Resolution if any. NO DUPLICATES."""
    
    try:
        result = lx.extract(
            text_or_documents=text,
            prompt_description=prompt,
            examples=examples,
            model_id="gemini-2.5-flash",
            api_key=os.getenv("GEMINI_API_KEY"),
            max_char_buffer=2000,  # Reduced buffer
            temperature=0.3
        )
        
        extractions_by_class = {}
        for ext in result.extractions:
            cls = ext.extraction_class
            if cls not in extractions_by_class:
                extractions_by_class[cls] = []
            
            extraction_data = {
                'text': ext.extraction_text[:200],  # Limit text size
                'attributes': ext.attributes
            }
            extractions_by_class[cls].append(extraction_data)
        
        return {
            'issue_number': issue_number,
            'title': issue_data.get('title', '')[:100],
            'extractions': extractions_by_class,
            'extraction_count': len(result.extractions),
            'status': 'success'
        }
        
    except Exception as e:
        return {
            'issue_number': issue_number,
            'title': issue_data.get('title', '')[:100],
            'error': str(e)[:200],
            'status': 'failed'
        }


def load_checkpoint():
    """Load checkpoint to resume processing"""
    checkpoint_file = Path("../data/extracted/checkpoint.json")
    if checkpoint_file.exists():
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    return {'processed_issues': [], 'last_index': -1}


def save_checkpoint(checkpoint):
    """Save checkpoint"""
    checkpoint_file = Path("../data/extracted/checkpoint.json")
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint, f)


def save_result(result, output_dir):
    """Save individual result"""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"issue_{result['issue_number']:04d}.json"
    with open(output_dir / filename, 'w') as f:
        json.dump(result, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description='Process issues incrementally')
    parser.add_argument('--limit', type=int, default=5, help='Number of issues to process')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    args = parser.parse_args()
    
    # Load enriched data
    input_file = Path("../data/enriched/enriched_flopy_issues_quality_20250804_231116_20250804_232240.json")
    
    print(f"Loading enriched issues from: {input_file}")
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    issues = data.get('enriched_issues', [])
    total_issues = len(issues)
    print(f"Found {total_issues} enriched issues")
    
    # Load checkpoint if resuming
    checkpoint = load_checkpoint() if args.resume else {'processed_issues': [], 'last_index': -1}
    start_index = checkpoint['last_index'] + 1
    
    if start_index >= total_issues:
        print("All issues already processed!")
        return
    
    # Create examples
    examples = create_comprehensive_examples()
    
    # Output directory
    output_dir = Path("../data/extracted/incremental")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process issues
    processed_count = 0
    start_time = time.time()
    
    for i in range(start_index, min(start_index + args.limit, total_issues)):
        issue = issues[i]
        issue_number = issue.get('issue_number', 'unknown')
        
        print(f"\nProcessing issue {i+1}/{total_issues}: #{issue_number}")
        
        result = extract_from_issue(issue, examples)
        
        # Save result immediately
        save_result(result, output_dir)
        
        # Update checkpoint
        checkpoint['processed_issues'].append(issue_number)
        checkpoint['last_index'] = i
        save_checkpoint(checkpoint)
        
        # Print summary
        if result['status'] == 'success':
            print(f"  ✓ Extracted: {result['extraction_count']} items")
            extractions = result.get('extractions', {})
            print(f"    - Modules: {len(extractions.get('module', []))}")
            print(f"    - Problems: {len(extractions.get('problem', []))}")
            print(f"    - Resolutions: {len(extractions.get('resolution', []))}")
        else:
            print(f"  ✗ Error: {result.get('error', 'Unknown error')}")
        
        processed_count += 1
        
        # Rate limiting
        if i < start_index + args.limit - 1:
            print("  Waiting 2 seconds...")
            time.sleep(2)
    
    # Summary
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"INCREMENTAL PROCESSING COMPLETE!")
    print(f"{'='*60}")
    print(f"Processed: {processed_count} issues in {elapsed:.1f} seconds")
    print(f"Average: {elapsed/processed_count:.1f} seconds per issue")
    print(f"Results saved to: {output_dir}")
    print(f"Total processed so far: {len(checkpoint['processed_issues'])}/{total_issues}")
    
    if len(checkpoint['processed_issues']) < total_issues:
        remaining = total_issues - len(checkpoint['processed_issues'])
        print(f"\nTo continue processing the remaining {remaining} issues, run:")
        print(f"  python3 process_incremental.py --resume --limit {remaining}")


if __name__ == "__main__":
    main()