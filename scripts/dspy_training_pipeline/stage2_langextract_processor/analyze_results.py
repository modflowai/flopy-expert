#!/usr/bin/env python3
"""
Critical analysis of LangExtract results
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
import statistics


def analyze_extraction_quality():
    """Perform critical analysis of extraction results"""
    
    incremental_dir = Path("../data/extracted/incremental")
    files = sorted(incremental_dir.glob("issue_*.json"))
    
    print(f"Found {len(files)} extracted issues\n")
    
    # Metrics collection
    all_results = []
    failed_issues = []
    extraction_counts = []
    module_counts = []
    problem_counts = []
    resolution_counts = []
    
    # Quality issues
    issues_without_problems = []
    issues_without_modules = []
    issues_without_resolutions = []
    duplicate_modules = []
    malformed_modules = []
    generic_resolutions = []
    
    # Module analysis
    all_modules = []
    module_packages = Counter()
    
    for file in files:
        with open(file, 'r') as f:
            data = json.load(f)
        
        all_results.append(data)
        issue_num = data['issue_number']
        
        if data['status'] == 'failed':
            failed_issues.append(issue_num)
            continue
        
        # Count extractions
        total_extractions = data.get('extraction_count', 0)
        extraction_counts.append(total_extractions)
        
        extractions = data.get('extractions', {})
        
        # Problems analysis
        problems = extractions.get('problem', [])
        problem_counts.append(len(problems))
        if len(problems) == 0:
            issues_without_problems.append(issue_num)
        
        # Modules analysis
        modules = extractions.get('module', [])
        module_counts.append(len(modules))
        if len(modules) == 0:
            issues_without_modules.append(issue_num)
        
        # Check for duplicates and malformed modules
        seen_modules = set()
        for mod in modules:
            mod_text = mod['text']
            if mod_text in seen_modules:
                duplicate_modules.append((issue_num, mod_text))
            seen_modules.add(mod_text)
            
            # Check module quality
            attrs = mod.get('attributes') or {}
            package = attrs.get('package', '')
            module_name = attrs.get('module', '')
            
            # Collect all modules
            all_modules.append(mod_text)
            if package and package != 'null':
                module_packages[package] += 1
            
            # Check for malformed modules
            if package == 'null' or module_name == 'null':
                malformed_modules.append((issue_num, mod_text))
            elif not mod_text.startswith('flopy.'):
                if '.' not in mod_text and mod_text != module_name:
                    malformed_modules.append((issue_num, mod_text))
        
        # Resolutions analysis
        resolutions = extractions.get('resolution', [])
        resolution_counts.append(len(resolutions))
        if len(resolutions) == 0 and 'bug' in data.get('title', '').lower():
            issues_without_resolutions.append(issue_num)
        
        # Check for generic resolutions
        for res in resolutions:
            res_text = res['text'].lower()
            if any(generic in res_text for generic in ['will look', 'will fix', 'will provide']):
                generic_resolutions.append((issue_num, res['text']))
    
    # Print critical analysis
    print("="*60)
    print("CRITICAL ANALYSIS OF LANGEXTRACT RESULTS")
    print("="*60)
    
    # Success rate
    success_rate = (len(files) - len(failed_issues)) / len(files) * 100
    print(f"\n1. SUCCESS RATE: {success_rate:.1f}%")
    if failed_issues:
        print(f"   ❌ Failed issues: {failed_issues}")
    
    # Extraction statistics
    print(f"\n2. EXTRACTION STATISTICS:")
    print(f"   - Average extractions per issue: {statistics.mean(extraction_counts):.1f}")
    print(f"   - Min/Max extractions: {min(extraction_counts)}/{max(extraction_counts)}")
    print(f"   - Standard deviation: {statistics.stdev(extraction_counts):.2f}")
    
    # Module quality
    print(f"\n3. MODULE EXTRACTION QUALITY:")
    print(f"   - Average modules per issue: {statistics.mean(module_counts):.1f}")
    print(f"   - Issues without modules: {len(issues_without_modules)} ({len(issues_without_modules)/len(files)*100:.1f}%)")
    if issues_without_modules[:5]:
        print(f"     Examples: {issues_without_modules[:5]}")
    print(f"   - Duplicate modules found: {len(duplicate_modules)}")
    if duplicate_modules[:3]:
        print(f"     Examples: {duplicate_modules[:3]}")
    print(f"   - Malformed modules: {len(malformed_modules)}")
    if malformed_modules[:5]:
        print(f"     Examples: {malformed_modules[:5]}")
    
    # Problem extraction
    print(f"\n4. PROBLEM EXTRACTION QUALITY:")
    print(f"   - Average problems per issue: {statistics.mean(problem_counts):.1f}")
    print(f"   - Issues without problems: {len(issues_without_problems)} ({len(issues_without_problems)/len(files)*100:.1f}%)")
    if issues_without_problems[:5]:
        print(f"     Examples: {issues_without_problems[:5]}")
    
    # Resolution quality
    print(f"\n5. RESOLUTION EXTRACTION QUALITY:")
    print(f"   - Average resolutions per issue: {statistics.mean(resolution_counts):.1f}")
    print(f"   - Bug issues without resolutions: {len(issues_without_resolutions)}")
    if issues_without_resolutions[:5]:
        print(f"     Examples: {issues_without_resolutions[:5]}")
    print(f"   - Generic/weak resolutions: {len(generic_resolutions)}")
    if generic_resolutions[:3]:
        print(f"     Examples: {generic_resolutions[:3]}")
    
    # Module distribution
    print(f"\n6. MODULE PACKAGE DISTRIBUTION:")
    for package, count in module_packages.most_common(10):
        print(f"   - {package}: {count}")
    
    # Specific quality issues
    print(f"\n7. SPECIFIC QUALITY ISSUES:")
    
    # Check for extraction imbalance
    high_extraction_issues = [(r['issue_number'], r['extraction_count']) 
                             for r in all_results 
                             if r.get('extraction_count', 0) > 15]
    if high_extraction_issues:
        print(f"   - Issues with excessive extractions (>15): {len(high_extraction_issues)}")
        print(f"     Examples: {high_extraction_issues[:3]}")
    
    # Check for incomplete extractions
    incomplete = []
    for r in all_results:
        if r['status'] == 'success':
            exts = r.get('extractions', {})
            if len(exts.get('problem', [])) == 0 or len(exts.get('module', [])) == 0:
                incomplete.append(r['issue_number'])
    
    print(f"   - Incomplete extractions (missing problem OR module): {len(incomplete)}")
    
    # Sample quality check
    print(f"\n8. SAMPLE QUALITY CHECK:")
    # Check a few specific issues
    sample_issues = [2497, 2558, 2477]
    for issue_num in sample_issues:
        file_path = incremental_dir / f"issue_{issue_num:04d}.json"
        if file_path.exists():
            with open(file_path, 'r') as f:
                data = json.load(f)
            exts = data.get('extractions', {})
            print(f"\n   Issue #{issue_num}:")
            print(f"   - Problems: {len(exts.get('problem', []))}")
            print(f"   - Modules: {len(exts.get('module', []))}")
            print(f"   - Resolutions: {len(exts.get('resolution', []))}")
            
            # Check specific quality
            mods = exts.get('module', [])
            if mods:
                malformed = [m['text'] for m in mods if 'null' in str(m.get('attributes', {}))]
                if malformed:
                    print(f"   - ⚠️  Malformed modules: {malformed}")
    
    print(f"\n9. OVERALL ASSESSMENT:")
    print(f"   ✅ Strengths:")
    print(f"      - High success rate ({success_rate:.1f}%)")
    print(f"      - Good module coverage (avg {statistics.mean(module_counts):.1f} per issue)")
    print(f"      - Consistent extraction across issues")
    
    print(f"\n   ❌ Weaknesses:")
    print(f"      - {len(malformed_modules)} malformed module extractions")
    print(f"      - {len(issues_without_problems)} issues missing problem descriptions")
    print(f"      - {len(generic_resolutions)} generic resolutions lacking detail")
    print(f"      - Some modules extracted as methods instead of classes")
    
    print(f"\n   ⚠️  Recommendations:")
    print(f"      1. Improve module name parsing (avoid 'null' values)")
    print(f"      2. Ensure all bug issues have problem extractions")
    print(f"      3. Extract more specific resolution details (PR numbers, commits)")
    print(f"      4. Better handling of method vs module distinction")
    
    return all_results


if __name__ == "__main__":
    results = analyze_extraction_quality()