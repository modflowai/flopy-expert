#!/usr/bin/env python3
"""
Process all issues using Claude CLI for intelligent extraction
"""

import json
import subprocess
import time
from pathlib import Path
from datetime import datetime


def extract_with_claude(issue_data):
    """Use Claude CLI to intelligently extract information"""
    
    issue_num = issue_data['issue_number']
    title = issue_data['title']
    body = issue_data['original_issue']['body'][:1500]
    comments = issue_data['original_issue'].get('comments', [])
    
    # Build focused prompt
    prompt = f"""Analyze FloPy issue #{issue_num}: {title}

{body}

Comments: {'; '.join([f"{c['author']}: {c['body'][:150]}" for c in comments[:2]])}

Extract ONLY:
1. FloPy modules/functions with bugs (full path like flopy.utils.cvfd_utils.func_name)
2. The specific problem
3. Resolution if mentioned

Rules:
- Only include FloPy modules (start with flopy.)
- No external packages (numpy, geopandas, etc)
- No duplicates
- Be specific (function names, not just package names)

Output JSON: {{"modules": [], "problem": "", "resolution": ""}}"""
    
    result = subprocess.run(
        ['claude', '-p', prompt, '--output-format', 'json'],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        try:
            response = json.loads(result.stdout)
            result_text = response.get('result', '')
            
            # Extract JSON from response
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_text = result_text[start:end]
                return json.loads(json_text)
        except:
            pass
    
    return None


def main():
    """Process all issues with Claude"""
    
    # Load enriched data
    input_file = Path("../data/enriched/enriched_flopy_issues_quality_20250804_231116_20250804_232240.json")
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    issues = data.get('enriched_issues', [])
    print(f"Processing {len(issues)} issues with Claude CLI...")
    
    # Output directory
    output_dir = Path("../data/extracted/claude_intelligent")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    start_time = time.time()
    
    # Process first 10 as a test
    for i, issue in enumerate(issues[:10]):
        issue_num = issue.get('issue_number')
        print(f"\n[{i+1}/10] Processing issue #{issue_num}")
        
        extracted = extract_with_claude(issue)
        
        if extracted:
            result = {
                'issue_number': issue_num,
                'title': issue.get('title'),
                'modules': extracted.get('modules', []),
                'problem': extracted.get('problem', ''),
                'resolution': extracted.get('resolution', '')
            }
            results.append(result)
            
            print(f"  ✓ Found {len(result['modules'])} modules")
            for mod in result['modules']:
                print(f"    - {mod}")
        else:
            print(f"  ✗ Extraction failed")
        
        # Rate limiting
        if i < 9:
            time.sleep(2)
    
    # Save results
    output_file = output_dir / f"claude_intelligent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'metadata': {
                'method': 'claude_cli_intelligent',
                'issues_processed': len(results),
                'timestamp': datetime.now().isoformat()
            },
            'results': results
        }, f, indent=2)
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"Processed {len(results)} issues in {elapsed:.1f} seconds")
    print(f"Average: {elapsed/len(results):.1f} seconds per issue")
    print(f"Results saved to: {output_file}")


if __name__ == "__main__":
    main()