#!/usr/bin/env python3
"""
Use Claude CLI to extract structured information from issue #2150
"""

import json
import subprocess
import os
from pathlib import Path


def extract_with_claude_cli(issue_data):
    """Use Claude CLI to extract structured information"""
    
    # Prepare the issue context
    issue_num = issue_data['issue_number']
    title = issue_data['title']
    body = issue_data['original_issue']['body'][:2000]  # Limit body size
    comments = issue_data['original_issue'].get('comments', [])
    
    # Build the prompt
    prompt = f"""Analyze this FloPy GitHub issue and extract ONLY FloPy modules that have bugs.

ISSUE #{issue_num}: {title}

BODY: {body}

COMMENTS: {'; '.join([f"{c['author']}: {c['body'][:200]}" for c in comments[:2]])}

Extract:
1. FloPy modules/functions with bugs (full path like flopy.utils.cvfd_utils.shapefile_to_xcyc)
2. The specific problem
3. Any resolution

Output JSON only:
{{"flopy_modules": ["full.path.here"], "problem": "description", "resolution": "if any"}}"""
    
    # Run Claude CLI (it will use the environment's ANTHROPIC_API_KEY)
    result = subprocess.run(
        ['claude', '-p', prompt, '--output-format', 'json'],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        print(f"Error: {result.stderr}")
        return None


def main():
    """Process issue #2150 with Claude CLI"""
    
    # Load issue data
    with open('issue_2150.json', 'r') as f:
        issue_data = json.load(f)
    
    print(f"Processing issue #{issue_data['issue_number']}: {issue_data['title']}")
    print("Using Claude CLI for extraction...")
    
    result = extract_with_claude_cli(issue_data)
    
    if result and 'result' in result:
        print("\nClaude's extraction:")
        print(result['result'])
        
        # Try to parse the JSON from the result
        try:
            # Extract JSON from the result text
            result_text = result['result']
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_text = result_text[start:end]
                extracted = json.loads(json_text)
                
                print("\nExtracted data:")
                print(f"FloPy modules: {extracted.get('flopy_modules', [])}")
                print(f"Problem: {extracted.get('problem', 'N/A')}")
                print(f"Resolution: {extracted.get('resolution', 'N/A')}")
                
                # Save
                with open('issue_2150_claude_cli_extracted.json', 'w') as f:
                    json.dump(extracted, f, indent=2)
                
                # Compare with LangExtract result
                print("\n" + "="*60)
                print("COMPARISON WITH LANGEXTRACT:")
                
                # Load LangExtract result
                langextract_file = Path("../data/extracted/incremental/issue_2150.json")
                if langextract_file.exists():
                    with open(langextract_file, 'r') as f:
                        langextract_data = json.load(f)
                    
                    lang_modules = [m['text'] for m in langextract_data['extractions'].get('module', [])]
                    print(f"\nLangExtract found {len(lang_modules)} modules:")
                    for mod in lang_modules[:5]:
                        print(f"  - {mod}")
                    print("  ... (and more)")
                    
                    print(f"\nClaude CLI found {len(extracted.get('flopy_modules', []))} modules:")
                    for mod in extracted.get('flopy_modules', []):
                        print(f"  - {mod}")
                
        except Exception as e:
            print(f"Error parsing JSON: {e}")


if __name__ == "__main__":
    main()