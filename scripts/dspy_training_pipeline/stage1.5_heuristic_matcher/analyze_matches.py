#!/usr/bin/env python3
"""
Analyze the quality and distribution of module matches
"""

import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List


def analyze_enriched_file(file_path: Path) -> Dict:
    """Analyze an enriched JSON file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    issues = data['enriched_issues']
    stats = data['metadata']['statistics']
    
    # Detailed analysis
    analysis = {
        'file': file_path.name,
        'basic_stats': stats,
        'confidence_distribution': Counter(),
        'match_type_distribution': Counter(),
        'package_distribution': Counter(),
        'model_family_distribution': Counter(),
        'issues_by_match_count': defaultdict(int),
        'sample_matches': []
    }
    
    # Analyze each issue
    for issue in issues:
        match_count = issue['match_count']
        analysis['issues_by_match_count'][match_count] += 1
        
        for match in issue['matched_modules']:
            analysis['confidence_distribution'][match['confidence']] += 1
            analysis['match_type_distribution'][match['match_type']] += 1
            analysis['package_distribution'][match['package_code']] += 1
            analysis['model_family_distribution'][match['model_family']] += 1
    
    # Get sample matches for each type
    samples_by_type = defaultdict(list)
    for issue in issues[:20]:  # First 20 issues
        for match in issue['matched_modules']:
            key = f"{match['match_type']}_{match['confidence']}"
            if len(samples_by_type[key]) < 2:
                samples_by_type[key].append({
                    'issue': issue['issue_number'],
                    'title': issue['title'][:60] + '...',
                    'match': match
                })
    
    analysis['sample_matches'] = dict(samples_by_type)
    
    return analysis


def print_analysis(analysis: Dict):
    """Print analysis results"""
    print(f"\n{'='*60}")
    print(f"ANALYSIS: {analysis['file']}")
    print(f"{'='*60}")
    
    # Basic stats
    stats = analysis['basic_stats']
    print(f"\nBasic Statistics:")
    print(f"  Total issues: {stats['total_issues']}")
    print(f"  Issues with matches: {stats['issues_with_matches']} ({stats['issues_with_matches']/stats['total_issues']*100:.1f}%)")
    print(f"  Total matches: {stats['total_matches']}")
    print(f"  Average matches per issue: {stats['avg_matches_per_issue']:.1f}")
    
    # Confidence distribution
    print(f"\nConfidence Distribution:")
    for conf, count in analysis['confidence_distribution'].most_common():
        print(f"  {conf}: {count}")
    
    # Match type distribution
    print(f"\nMatch Type Distribution:")
    for match_type, count in analysis['match_type_distribution'].most_common():
        print(f"  {match_type}: {count}")
    
    # Top packages
    print(f"\nTop 15 Matched Packages:")
    for pkg, count in analysis['package_distribution'].most_common(15):
        print(f"  {pkg}: {count}")
    
    # Model family distribution
    print(f"\nModel Family Distribution:")
    for family, count in analysis['model_family_distribution'].most_common():
        print(f"  {family}: {count}")
    
    # Issues by match count
    print(f"\nIssues by Match Count:")
    for count in sorted(analysis['issues_by_match_count'].keys()):
        num_issues = analysis['issues_by_match_count'][count]
        print(f"  {count} matches: {num_issues} issues")
    
    # Sample matches
    print(f"\nSample Matches by Type:")
    for key, samples in analysis['sample_matches'].items():
        match_type, confidence = key.rsplit('_', 1)
        print(f"\n  {match_type} ({confidence} confidence):")
        for sample in samples:
            match = sample['match']
            print(f"    Issue #{sample['issue']}: {sample['title']}")
            print(f"      → {match['class_name']} ({match['package_code']})")
            print(f"      Context: '{match['match_context']}'")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Analyze enriched module matches")
    parser.add_argument("--input", required=True, help="Enriched JSON file pattern")
    
    args = parser.parse_args()
    
    # Find input files
    input_pattern = Path(args.input)
    input_files = list(input_pattern.parent.glob(input_pattern.name))
    
    if not input_files:
        print(f"No files found matching pattern: {args.input}")
        return
    
    for input_file in input_files:
        analysis = analyze_enriched_file(input_file)
        print_analysis(analysis)


if __name__ == "__main__":
    main()