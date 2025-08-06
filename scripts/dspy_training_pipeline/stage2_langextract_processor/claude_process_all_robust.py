#!/usr/bin/env python3
"""
Process all issues using Claude CLI with checkpoint saving
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
        except Exception as e:
            print(f"  Error parsing response: {e}")
    else:
        print(f"  Claude CLI error: {result.stderr}")
    
    return None


def load_checkpoint():
    """Load checkpoint to resume processing"""
    checkpoint_file = Path("../data/extracted/claude_intelligent/checkpoint.json")
    if checkpoint_file.exists():
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    return {'processed': [], 'last_index': -1}


def save_checkpoint(checkpoint):
    """Save checkpoint"""
    checkpoint_file = Path("../data/extracted/claude_intelligent/checkpoint.json")
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint, f)


def main():
    """Process all issues with Claude"""
    
    # Load enriched data
    input_file = Path("../data/enriched/enriched_flopy_issues_quality_20250804_231116_20250804_232240.json")
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    issues = data.get('enriched_issues', [])
    total_issues = len(issues)
    
    # Output directory
    output_dir = Path("../data/extracted/claude_intelligent")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load checkpoint
    checkpoint = load_checkpoint()
    start_index = checkpoint['last_index'] + 1
    
    print(f"Processing {total_issues} issues with Claude CLI...")
    if start_index > 0:
        print(f"Resuming from issue {start_index + 1}")
    
    start_time = time.time()
    
    # Process all issues
    for i in range(start_index, total_issues):
        issue = issues[i]
        issue_num = issue.get('issue_number')
        print(f"\n[{i+1}/{total_issues}] Processing issue #{issue_num}")
        
        extracted = extract_with_claude(issue)
        
        if extracted:
            result = {
                'issue_number': issue_num,
                'title': issue.get('title'),
                'modules': extracted.get('modules', []),
                'problem': extracted.get('problem', ''),
                'resolution': extracted.get('resolution', ''),
                'extraction_time': datetime.now().isoformat()
            }
            
            # Save individual result
            result_file = output_dir / f"issue_{issue_num:04d}_claude.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"  ✓ Found {len(result['modules'])} modules")
            for mod in result['modules']:
                print(f"    - {mod}")
            
            # Update checkpoint
            checkpoint['processed'].append(issue_num)
            checkpoint['last_index'] = i
            save_checkpoint(checkpoint)
        else:
            print(f"  ✗ Extraction failed")
        
        # Progress update every 10 issues
        if (i + 1) % 10 == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / (i + 1 - start_index)
            remaining = (total_issues - i - 1) * avg_time
            print(f"\n⏱️  Progress: {i+1}/{total_issues} ({(i+1)/total_issues*100:.1f}%)")
            print(f"   Average: {avg_time:.1f}s per issue")
            print(f"   Estimated remaining: {remaining/60:.1f} minutes")
        
        # Rate limiting - adjust as needed
        if i < total_issues - 1:
            time.sleep(1)  # 1 second between requests
    
    # Combine all results
    print("\n" + "="*60)
    print("Combining all results...")
    
    all_results = []
    for file in sorted(output_dir.glob("issue_*_claude.json")):
        with open(file, 'r') as f:
            all_results.append(json.load(f))
    
    # Calculate statistics
    total_modules = sum(len(r['modules']) for r in all_results)
    issues_with_modules = sum(1 for r in all_results if r['modules'])
    issues_with_resolution = sum(1 for r in all_results if r['resolution'])
    
    # Save combined results
    final_file = output_dir / f"all_issues_claude_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(final_file, 'w') as f:
        json.dump({
            'metadata': {
                'method': 'claude_cli_intelligent',
                'total_issues': len(all_results),
                'total_modules': total_modules,
                'issues_with_modules': issues_with_modules,
                'issues_with_resolution': issues_with_resolution,
                'average_modules_per_issue': round(total_modules / len(all_results), 2) if all_results else 0,
                'timestamp': datetime.now().isoformat()
            },
            'results': all_results
        }, f, indent=2)
    
    elapsed = time.time() - start_time
    print(f"\n✅ COMPLETE!")
    print(f"Processed {len(all_results)} issues in {elapsed/60:.1f} minutes")
    print(f"Total modules found: {total_modules}")
    print(f"Average modules per issue: {total_modules/len(all_results):.2f}")
    print(f"Results saved to: {final_file}")


if __name__ == "__main__":
    main()