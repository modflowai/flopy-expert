#!/usr/bin/env python3
"""
Manual review tool - review one issue at a time interactively
"""

import json
from pathlib import Path
from typing import Dict, List, Any
import sys


def load_issue(issue_num: int) -> Dict:
    """Load a single issue"""
    file_path = Path(f"../data/extracted/incremental/issue_{issue_num:04d}.json")
    if file_path.exists():
        with open(file_path, 'r') as f:
            return json.load(f)
    return None


def analyze_modules(modules: List[Dict]) -> Dict:
    """Analyze module quality"""
    analysis = {
        'total': len(modules),
        'flopy': [],
        'non_flopy': [],
        'duplicates': [],
        'malformed': []
    }
    
    seen = set()
    for mod in modules:
        text = mod['text']
        attrs = mod.get('attributes') or {}
        
        # Check duplicates
        if text in seen:
            analysis['duplicates'].append(text)
        seen.add(text)
        
        # Categorize
        package = attrs.get('package', '')
        if text.startswith('flopy.') or 'flopy' in package:
            analysis['flopy'].append(mod)
        else:
            analysis['non_flopy'].append(mod)
        
        # Check malformed
        if attrs and (attrs.get('package') == 'null' or attrs.get('module') == 'null'):
            analysis['malformed'].append(text)
    
    return analysis


def clean_modules(modules: List[Dict]) -> List[Dict]:
    """Clean and deduplicate modules"""
    cleaned = []
    seen = set()
    
    # Define acceptable non-FloPy packages
    acceptable_external = {'numpy', 'pandas', 'matplotlib', 'shapely', 'rasterio', 'xarray'}
    
    for mod in modules:
        text = mod['text']
        
        # Skip duplicates
        if text in seen:
            continue
        seen.add(text)
        
        # Skip non-FloPy modules (unless acceptable)
        attrs = mod.get('attributes') or {}
        package = attrs.get('package', '')
        
        if not text.startswith('flopy.') and 'flopy' not in package:
            # Check if it's an acceptable external package
            base_package = text.split('.')[0] if '.' in text else text
            if base_package.lower() not in acceptable_external:
                continue
        
        # Fix null attributes
        if attrs:
            if attrs.get('package') == 'null':
                if '.' in text:
                    attrs['package'] = '.'.join(text.split('.')[:-1])
                else:
                    attrs['package'] = text
            
            if attrs.get('module') == 'null':
                if '.' in text:
                    attrs['module'] = text.split('.')[-1]
                else:
                    attrs['module'] = text
        
        cleaned.append({
            'text': text,
            'attributes': attrs
        })
    
    return cleaned


def review_issue(issue_num: int):
    """Review a single issue"""
    data = load_issue(issue_num)
    if not data:
        print(f"Issue {issue_num} not found")
        return None
    
    print(f"\n{'='*80}")
    print(f"ISSUE #{issue_num}: {data.get('title', 'No title')[:70]}")
    print(f"{'='*80}")
    
    extractions = data.get('extractions', {})
    
    # Problems
    problems = extractions.get('problem', [])
    print(f"\n📋 PROBLEMS ({len(problems)}):")
    for i, prob in enumerate(problems):
        print(f"  {i+1}. {prob['text'][:100]}")
    
    # Modules
    modules = extractions.get('module', [])
    analysis = analyze_modules(modules)
    
    print(f"\n📦 MODULES ({analysis['total']} total):")
    print(f"  - FloPy: {len(analysis['flopy'])}")
    print(f"  - Non-FloPy: {len(analysis['non_flopy'])}")
    print(f"  - Duplicates: {len(analysis['duplicates'])}")
    print(f"  - Malformed: {len(analysis['malformed'])}")
    
    # Show problematic modules
    if analysis['non_flopy']:
        print(f"\n  ⚠️  Non-FloPy modules:")
        for mod in analysis['non_flopy'][:5]:
            print(f"    - {mod['text']}")
    
    if analysis['duplicates']:
        print(f"\n  ⚠️  Duplicates: {analysis['duplicates'][:3]}")
    
    # Resolutions
    resolutions = extractions.get('resolution', [])
    print(f"\n✅ RESOLUTIONS ({len(resolutions)}):")
    for i, res in enumerate(resolutions[:3]):
        print(f"  {i+1}. {res['text'][:100]}")
    
    # Clean automatically
    cleaned_modules = clean_modules(modules)
    modules_removed = len(modules) - len(cleaned_modules)
    
    print(f"\n🔧 AUTO-CLEAN RESULT:")
    print(f"  - Original modules: {len(modules)}")
    print(f"  - Cleaned modules: {len(cleaned_modules)}")
    print(f"  - Removed: {modules_removed}")
    
    # Create cleaned version
    cleaned_data = {
        'issue_number': issue_num,
        'title': data.get('title', ''),
        'status': 'reviewed',
        'extractions': {
            'problem': problems,
            'module': cleaned_modules,
            'resolution': [r for r in resolutions if 'will look' not in r['text'].lower() 
                          and 'will fix' not in r['text'].lower()]
        },
        'quality_metrics': {
            'modules_removed': modules_removed,
            'original_count': data.get('extraction_count', 0),
            'cleaned_count': len(problems) + len(cleaned_modules) + len(resolutions)
        }
    }
    
    return cleaned_data


def save_reviewed(issue_num: int, cleaned_data: Dict):
    """Save reviewed issue"""
    output_dir = Path("../data/extracted/reviewed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"issue_{issue_num:04d}_reviewed.json"
    with open(output_file, 'w') as f:
        json.dump(cleaned_data, f, indent=2)
    
    print(f"✅ Saved to: {output_file}")


def main():
    """Main review loop"""
    if len(sys.argv) > 1:
        # Review specific issue
        issue_num = int(sys.argv[1])
        cleaned = review_issue(issue_num)
        if cleaned:
            save_reviewed(issue_num, cleaned)
    else:
        # Review all issues
        print("Reviewing all 88 issues...")
        
        stats = {
            'reviewed': 0,
            'modules_removed': 0,
            'problematic': []
        }
        
        # Get all issue numbers
        incremental_dir = Path("../data/extracted/incremental")
        issue_files = sorted(incremental_dir.glob("issue_*.json"))
        
        for file in issue_files:
            issue_num = int(file.stem.split('_')[1])
            
            cleaned = review_issue(issue_num)
            if cleaned:
                save_reviewed(issue_num, cleaned)
                
                metrics = cleaned['quality_metrics']
                stats['reviewed'] += 1
                stats['modules_removed'] += metrics['modules_removed']
                
                if metrics['modules_removed'] > 5:
                    stats['problematic'].append(issue_num)
        
        print(f"\n{'='*80}")
        print("REVIEW COMPLETE!")
        print(f"{'='*80}")
        print(f"Issues reviewed: {stats['reviewed']}")
        print(f"Total modules removed: {stats['modules_removed']}")
        print(f"Highly problematic issues (>5 modules removed): {stats['problematic']}")


if __name__ == "__main__":
    main()