#!/usr/bin/env python3
"""
Simple LangExtract processor using the correct API
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


def create_examples():
    """Create extraction examples"""
    return [
        # Problem extraction example
        lx.data.ExampleData(
            text="Mf6Splitter does not work when ATS is active with error 'ModflowUtlats' object has no attribute 'parent_package'",
            extractions=[
                lx.data.Extraction(
                    extraction_class="problem",
                    extraction_text="Mf6Splitter does not work when ATS is active",
                    attributes={
                        "error_message": "'ModflowUtlats' object has no attribute 'parent_package'",
                        "error_type": "AttributeError",
                        "problem_category": "compatibility"
                    }
                )
            ]
        ),
        # Module extraction example
        lx.data.ExampleData(
            text="Using flopy.mf6.utils.Mf6Splitter to split a model with method split_model() fails",
            extractions=[
                lx.data.Extraction(
                    extraction_class="module",
                    extraction_text="flopy.mf6.utils.Mf6Splitter",
                    attributes={
                        "module_name": "Mf6Splitter",
                        "package": "flopy.mf6.utils",
                        "method": "split_model"
                    }
                )
            ]
        ),
        # Resolution example
        lx.data.ExampleData(
            text="ATS support has been implemented in develop",
            extractions=[
                lx.data.Extraction(
                    extraction_class="resolution",
                    extraction_text="ATS support has been implemented in develop",
                    attributes={
                        "resolution_type": "code_fix",
                        "target_branch": "develop",
                        "status": "completed"
                    }
                )
            ]
        )
    ]


def prepare_issue_text(issue):
    """Prepare issue text for extraction"""
    parts = []
    
    # Get original issue data
    orig = issue.get('original_issue', issue)
    
    # Title and body
    parts.append(f"TITLE: {orig.get('title', '')}")
    parts.append(f"BODY:\n{orig.get('body', '')}")
    
    # Comments
    comments = orig.get('comments', [])
    if comments:
        parts.append("\nCOMMENTS:")
        for comment in comments:
            author = comment.get('author', 'unknown')
            body = comment.get('body', '')
            parts.append(f"\n{author}: {body}")
    
    return "\n\n".join(parts)


def extract_from_issue(issue_data, examples):
    """Extract information from a single issue"""
    text = prepare_issue_text(issue_data)
    
    prompt = """Extract the following from this GitHub issue:
    1. Problems: Main issue description, error messages, symptoms
    2. Modules: FloPy modules and packages mentioned (with full paths)
    3. Resolutions: How the issue was fixed or resolved
    
    Use exact text from the issue. Include all relevant attributes."""
    
    try:
        result = lx.extract(
            text_or_documents=text,
            prompt_description=prompt,
            examples=examples,
            model_id="gemini-2.5-flash",
            api_key=os.getenv("GEMINI_API_KEY"),
            max_char_buffer=2000,
            temperature=0.5
        )
        return result
    except Exception as e:
        print(f"Error extracting: {e}")
        return None


def main():
    """Process enriched issues with LangExtract"""
    
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
    examples = create_examples()
    
    # Process first 5 issues as a test
    test_issues = issues[:5]
    results = []
    
    for i, issue in enumerate(test_issues):
        print(f"\nProcessing issue {i+1}/5: #{issue.get('issue_number', 'unknown')}")
        result = extract_from_issue(issue, examples)
        
        if result:
            # Convert to serializable format
            issue_result = {
                'issue_number': issue.get('issue_number'),
                'title': issue.get('title'),
                'extractions': []
            }
            
            # Get extractions
            if hasattr(result, 'extractions'):
                for ext in result.extractions:
                    issue_result['extractions'].append({
                        'class': ext.extraction_class,
                        'text': ext.extraction_text,
                        'attributes': ext.attributes
                    })
            
            results.append(issue_result)
            
            # Print summary
            print(f"  Found {len(issue_result['extractions'])} extractions")
            for ext in issue_result['extractions']:
                print(f"    - {ext['class']}: {ext['text'][:60]}...")
    
    # Save results
    output_dir = Path("../data/extracted")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"langextract_test_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump({
            'metadata': {
                'source': str(input_file),
                'timestamp': timestamp,
                'model': 'gemini-2.5-flash',
                'issues_processed': len(results)
            },
            'results': results
        }, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    
    # Print summary
    total_extractions = sum(len(r['extractions']) for r in results)
    print(f"\nSummary:")
    print(f"  Issues processed: {len(results)}")
    print(f"  Total extractions: {total_extractions}")
    print(f"  Average per issue: {total_extractions/len(results):.1f}")


if __name__ == "__main__":
    main()