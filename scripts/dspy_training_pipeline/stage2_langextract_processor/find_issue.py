#!/usr/bin/env python3
"""Find specific issue in enriched data"""

import json
from pathlib import Path

# Load enriched data
input_file = Path("../data/enriched/enriched_flopy_issues_quality_20250804_231116_20250804_232240.json")

with open(input_file, 'r') as f:
    data = json.load(f)

issues = data.get('enriched_issues', [])

# Find issue 2150
for issue in issues:
    if issue.get('issue_number') == 2150:
        print(f"Found issue #2150")
        print(f"Title: {issue.get('title')}")
        print(f"\nBody preview:")
        print(issue.get('original_issue', {}).get('body', '')[:500])
        
        # Save just this issue
        with open('issue_2150.json', 'w') as f:
            json.dump(issue, f, indent=2)
        print("\nSaved to issue_2150.json")
        break
else:
    print("Issue #2150 not found")