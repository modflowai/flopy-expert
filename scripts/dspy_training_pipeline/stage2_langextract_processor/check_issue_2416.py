#!/usr/bin/env python3
"""Check issue 2416"""

import json
from pathlib import Path

# Load enriched data
input_file = Path("../data/enriched/enriched_flopy_issues_quality_20250804_231116_20250804_232240.json")

with open(input_file, 'r') as f:
    data = json.load(f)

# Find issue 2416
for issue in data['enriched_issues']:
    if issue['issue_number'] == 2416:
        print(f"Issue #{issue['issue_number']}: {issue['title']}")
        print(f"\nBody:\n{issue['original_issue']['body']}")
        print(f"\nComments:")
        for comment in issue['original_issue'].get('comments', [])[:3]:
            print(f"\n{comment['author']}:")
            print(comment['body'][:300])
        break