#!/usr/bin/env python3
"""
Create final cleaned dataset from reviewed issues
"""

import json
from pathlib import Path
from collections import Counter


def create_final_dataset():
    """Combine all reviewed issues into final dataset"""
    
    reviewed_dir = Path("../data/extracted/reviewed")
    reviewed_files = sorted(reviewed_dir.glob("issue_*_reviewed.json"))
    
    print(f"Found {len(reviewed_files)} reviewed issues")
    
    all_issues = []
    stats = {
        'total_modules': 0,
        'total_problems': 0,
        'total_resolutions': 0,
        'modules_by_package': Counter(),
        'issues_without_resolution': [],
        'issues_without_modules': []
    }
    
    for file in reviewed_files:
        with open(file, 'r') as f:
            data = json.load(f)
        
        all_issues.append(data)
        
        # Update statistics
        extractions = data.get('extractions', {})
        
        modules = extractions.get('module', [])
        problems = extractions.get('problem', [])
        resolutions = extractions.get('resolution', [])
        
        stats['total_modules'] += len(modules)
        stats['total_problems'] += len(problems)
        stats['total_resolutions'] += len(resolutions)
        
        # Count packages
        for mod in modules:
            text = mod['text']
            if text.startswith('flopy.'):
                package = '.'.join(text.split('.')[:2])  # e.g., "flopy.mf6"
                stats['modules_by_package'][package] += 1
        
        # Track issues without key data
        if len(resolutions) == 0 and 'bug' in data.get('title', '').lower():
            stats['issues_without_resolution'].append(data['issue_number'])
        
        if len(modules) == 0:
            stats['issues_without_modules'].append(data['issue_number'])
    
    # Create final dataset
    final_dataset = {
        'metadata': {
            'version': '1.0',
            'extraction_method': 'langextract_reviewed',
            'total_issues': len(all_issues),
            'total_extractions': stats['total_modules'] + stats['total_problems'] + stats['total_resolutions'],
            'quality': 'manually_reviewed'
        },
        'statistics': {
            'total_modules': stats['total_modules'],
            'total_problems': stats['total_problems'],
            'total_resolutions': stats['total_resolutions'],
            'average_modules_per_issue': round(stats['total_modules'] / len(all_issues), 2),
            'average_problems_per_issue': round(stats['total_problems'] / len(all_issues), 2),
            'average_resolutions_per_issue': round(stats['total_resolutions'] / len(all_issues), 2),
            'issues_without_resolution': len(stats['issues_without_resolution']),
            'issues_without_modules': len(stats['issues_without_modules'])
        },
        'module_distribution': dict(stats['modules_by_package'].most_common()),
        'data_quality': {
            'all_issues_reviewed': True,
            'duplicates_removed': True,
            'non_flopy_filtered': True,
            'malformed_fixed': True
        },
        'issues': all_issues
    }
    
    # Save final dataset
    output_file = Path("../data/extracted/flopy_issues_final_cleaned.json")
    with open(output_file, 'w') as f:
        json.dump(final_dataset, f, indent=2)
    
    print(f"\n{'='*60}")
    print("FINAL DATASET CREATED")
    print(f"{'='*60}")
    print(f"Saved to: {output_file}")
    print(f"\nSummary:")
    print(f"  - Total issues: {len(all_issues)}")
    print(f"  - Total modules: {stats['total_modules']}")
    print(f"  - Total problems: {stats['total_problems']}")
    print(f"  - Total resolutions: {stats['total_resolutions']}")
    print(f"\nAverages per issue:")
    print(f"  - Modules: {stats['total_modules'] / len(all_issues):.1f}")
    print(f"  - Problems: {stats['total_problems'] / len(all_issues):.1f}")
    print(f"  - Resolutions: {stats['total_resolutions'] / len(all_issues):.1f}")
    print(f"\nTop FloPy packages:")
    for package, count in stats['modules_by_package'].most_common(5):
        print(f"  - {package}: {count}")
    print(f"\nData quality:")
    print(f"  - Issues without resolutions: {len(stats['issues_without_resolution'])}")
    print(f"  - Issues without modules: {len(stats['issues_without_modules'])}")
    
    # Create a sample for Stage 3
    sample_issues = all_issues[:5]
    sample_file = Path("../data/extracted/sample_for_stage3.json")
    with open(sample_file, 'w') as f:
        json.dump({
            'description': 'Sample of 5 issues for Stage 3 DSPy development',
            'issues': sample_issues
        }, f, indent=2)
    
    print(f"\nAlso created sample file for Stage 3: {sample_file}")


if __name__ == "__main__":
    create_final_dataset()