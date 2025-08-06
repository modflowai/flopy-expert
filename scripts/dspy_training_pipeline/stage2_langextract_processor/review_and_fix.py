#!/usr/bin/env python3
"""
Interactive review and fix tool for extraction results
"""

import json
from pathlib import Path
from typing import Dict, List, Any
import os


class ExtractionReviewer:
    def __init__(self):
        self.incremental_dir = Path("../data/extracted/incremental")
        self.reviewed_dir = Path("../data/extracted/reviewed")
        self.reviewed_dir.mkdir(parents=True, exist_ok=True)
        
        # Load all issues
        self.issues = {}
        for file in sorted(self.incremental_dir.glob("issue_*.json")):
            with open(file, 'r') as f:
                data = json.load(f)
                self.issues[data['issue_number']] = data
        
        # Track review progress
        self.progress_file = self.reviewed_dir / "progress.json"
        self.progress = self.load_progress()
    
    def load_progress(self):
        """Load review progress"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {'reviewed': [], 'current_index': 0}
    
    def save_progress(self):
        """Save review progress"""
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def get_next_issue(self):
        """Get next issue to review"""
        sorted_issues = sorted(self.issues.keys())
        for issue_num in sorted_issues:
            if issue_num not in self.progress['reviewed']:
                return issue_num
        return None
    
    def display_issue(self, issue_num: int):
        """Display issue for review"""
        data = self.issues[issue_num]
        
        print("\n" + "="*80)
        print(f"ISSUE #{issue_num}: {data.get('title', 'No title')}")
        print("="*80)
        
        extractions = data.get('extractions', {})
        
        # Display problems
        print("\n📋 PROBLEMS:")
        problems = extractions.get('problem', [])
        for i, prob in enumerate(problems):
            print(f"  {i+1}. {prob['text']}")
            attrs = prob.get('attributes', {})
            if attrs:
                for k, v in attrs.items():
                    if v and v != 'null':
                        print(f"     - {k}: {v}")
        
        # Display modules
        print("\n📦 MODULES:")
        modules = extractions.get('module', [])
        
        # Group by FloPy vs non-FloPy
        flopy_modules = []
        non_flopy_modules = []
        duplicates = set()
        seen = set()
        
        for mod in modules:
            text = mod['text']
            if text in seen:
                duplicates.add(text)
            seen.add(text)
            
            attrs = mod.get('attributes') or {}
            package = attrs.get('package', '')
            
            if text.startswith('flopy.') or 'flopy' in package:
                flopy_modules.append(mod)
            else:
                non_flopy_modules.append(mod)
        
        print("  FloPy modules:")
        for i, mod in enumerate(flopy_modules):
            attrs = mod.get('attributes') or {}
            dup_marker = " [DUP]" if mod['text'] in duplicates else ""
            print(f"    {i+1}. {mod['text']}{dup_marker}")
            if attrs:
                print(f"       package: {attrs.get('package', 'N/A')}, module: {attrs.get('module', 'N/A')}")
        
        if non_flopy_modules:
            print("\n  ⚠️  Non-FloPy modules (should probably be removed):")
            for mod in non_flopy_modules:
                print(f"    - {mod['text']}")
        
        # Display resolutions
        print("\n✅ RESOLUTIONS:")
        resolutions = extractions.get('resolution', [])
        for i, res in enumerate(resolutions):
            print(f"  {i+1}. {res['text']}")
            attrs = res.get('attributes', {})
            if attrs:
                for k, v in attrs.items():
                    if v and v != 'null':
                        print(f"     - {k}: {v}")
        
        # Show statistics
        print(f"\n📊 STATS:")
        print(f"  - Total extractions: {data.get('extraction_count', 0)}")
        print(f"  - FloPy modules: {len(flopy_modules)}")
        print(f"  - Non-FloPy modules: {len(non_flopy_modules)}")
        print(f"  - Duplicates: {len(duplicates)}")
        
        return data
    
    def analyze_issue_quality(self, issue_num: int):
        """Analyze quality issues"""
        data = self.issues[issue_num]
        extractions = data.get('extractions', {})
        
        issues = []
        
        # Check modules
        modules = extractions.get('module', [])
        seen = set()
        for mod in modules:
            text = mod['text']
            attrs = mod.get('attributes') or {}
            
            # Check duplicates
            if text in seen:
                issues.append(f"Duplicate module: {text}")
            seen.add(text)
            
            # Check non-FloPy
            if not text.startswith('flopy.') and 'flopy' not in str(attrs.get('package', '')):
                if text not in ['numpy', 'pandas', 'matplotlib']:  # Common dependencies
                    issues.append(f"Non-FloPy module: {text}")
            
            # Check malformed
            if attrs and (attrs.get('package') == 'null' or attrs.get('module') == 'null'):
                issues.append(f"Malformed attributes: {text}")
            
            # Check methods vs modules
            if '.' in text and text.count('.') > 2:
                if any(method_word in text.split('.')[-1] for method_word in 
                       ['to_', 'from_', 'get_', 'set_', 'load', 'write', 'read']):
                    issues.append(f"Method not module: {text}")
        
        # Check problems
        problems = extractions.get('problem', [])
        if not problems:
            issues.append("No problems extracted")
        
        # Check resolutions for bugs
        if 'bug' in data.get('title', '').lower():
            resolutions = extractions.get('resolution', [])
            if not resolutions:
                issues.append("Bug issue without resolution")
            else:
                # Check for weak resolutions
                for res in resolutions:
                    if any(weak in res['text'].lower() for weak in ['will look', 'will fix', 'will provide']):
                        issues.append(f"Weak resolution: {res['text']}")
        
        return issues
    
    def create_fixed_extraction(self, issue_num: int):
        """Create a manually fixed version"""
        data = self.issues[issue_num]
        
        # Start with original
        fixed = {
            'issue_number': issue_num,
            'title': data.get('title', ''),
            'original_extraction_count': data.get('extraction_count', 0),
            'status': 'reviewed',
            'extractions': {}
        }
        
        extractions = data.get('extractions', {})
        
        # Clean problems (usually good as-is)
        fixed['extractions']['problem'] = extractions.get('problem', [])
        
        # Clean modules
        modules = extractions.get('module', [])
        cleaned_modules = []
        seen = set()
        
        for mod in modules:
            text = mod['text']
            
            # Skip duplicates
            if text in seen:
                continue
            seen.add(text)
            
            # Skip non-FloPy modules (with some exceptions)
            if not text.startswith('flopy.'):
                attrs = mod.get('attributes') or {}
                if 'flopy' not in str(attrs.get('package', '')):
                    # Skip unless it's a key dependency
                    if text not in ['numpy', 'pandas', 'matplotlib', 'shapely', 'rasterio']:
                        continue
            
            # Fix attributes
            attrs = mod.get('attributes') or {}
            if attrs:
                # Clean null values
                if attrs.get('package') == 'null':
                    attrs['package'] = text.split('.')[0] if '.' in text else text
                if attrs.get('module') == 'null':
                    attrs['module'] = text.split('.')[-1] if '.' in text else text
            
            cleaned_modules.append({
                'text': text,
                'attributes': attrs
            })
        
        fixed['extractions']['module'] = cleaned_modules
        
        # Clean resolutions
        resolutions = extractions.get('resolution', [])
        cleaned_resolutions = []
        
        for res in resolutions:
            # Skip weak resolutions
            if any(weak in res['text'].lower() for weak in ['will look', 'will fix', 'will provide']):
                continue
            cleaned_resolutions.append(res)
        
        fixed['extractions']['resolution'] = cleaned_resolutions
        
        # Add quality metrics
        fixed['quality_metrics'] = {
            'modules_removed': len(modules) - len(cleaned_modules),
            'resolutions_removed': len(resolutions) - len(cleaned_resolutions),
            'has_problem': len(fixed['extractions']['problem']) > 0,
            'has_flopy_modules': len(cleaned_modules) > 0,
            'has_resolution': len(cleaned_resolutions) > 0
        }
        
        return fixed
    
    def review_all(self):
        """Review all issues and create cleaned dataset"""
        print(f"Starting review of {len(self.issues)} issues...")
        print(f"Already reviewed: {len(self.progress['reviewed'])}")
        
        stats = {
            'total': len(self.issues),
            'reviewed': 0,
            'modules_removed': 0,
            'issues_with_problems': []
        }
        
        for issue_num in sorted(self.issues.keys()):
            print(f"\n\n{'='*80}")
            print(f"Reviewing issue {issue_num} ({stats['reviewed']+1}/{stats['total']})")
            
            # Display issue
            self.display_issue(issue_num)
            
            # Analyze quality
            quality_issues = self.analyze_issue_quality(issue_num)
            if quality_issues:
                print("\n⚠️  QUALITY ISSUES:")
                for issue in quality_issues:
                    print(f"  - {issue}")
                stats['issues_with_problems'].append(issue_num)
            
            # Create fixed version
            fixed = self.create_fixed_extraction(issue_num)
            
            # Save fixed version
            output_file = self.reviewed_dir / f"issue_{issue_num:04d}_reviewed.json"
            with open(output_file, 'w') as f:
                json.dump(fixed, f, indent=2)
            
            # Update stats
            metrics = fixed['quality_metrics']
            stats['modules_removed'] += metrics['modules_removed']
            stats['reviewed'] += 1
            
            # Update progress
            self.progress['reviewed'].append(issue_num)
            self.save_progress()
            
            print(f"\n✅ Fixed version saved. Removed {metrics['modules_removed']} modules.")
        
        # Final summary
        print(f"\n\n{'='*80}")
        print("REVIEW COMPLETE!")
        print(f"{'='*80}")
        print(f"Total issues reviewed: {stats['reviewed']}")
        print(f"Total modules removed: {stats['modules_removed']}")
        print(f"Issues with quality problems: {len(stats['issues_with_problems'])}")
        
        # Combine all reviewed files
        self.create_final_dataset()
    
    def create_final_dataset(self):
        """Create final cleaned dataset"""
        all_reviewed = []
        
        for file in sorted(self.reviewed_dir.glob("issue_*_reviewed.json")):
            with open(file, 'r') as f:
                all_reviewed.append(json.load(f))
        
        # Calculate final statistics
        total_modules = sum(len(r['extractions'].get('module', [])) for r in all_reviewed)
        total_problems = sum(len(r['extractions'].get('problem', [])) for r in all_reviewed)
        total_resolutions = sum(len(r['extractions'].get('resolution', [])) for r in all_reviewed)
        
        final_dataset = {
            'metadata': {
                'total_issues': len(all_reviewed),
                'total_modules': total_modules,
                'total_problems': total_problems,
                'total_resolutions': total_resolutions,
                'average_modules_per_issue': round(total_modules / len(all_reviewed), 2),
                'extraction_method': 'langextract_reviewed'
            },
            'issues': all_reviewed
        }
        
        output_file = self.reviewed_dir / "flopy_issues_reviewed_final.json"
        with open(output_file, 'w') as f:
            json.dump(final_dataset, f, indent=2)
        
        print(f"\nFinal dataset saved to: {output_file}")
        print(f"  - Total issues: {len(all_reviewed)}")
        print(f"  - Total modules: {total_modules}")
        print(f"  - Average modules per issue: {total_modules / len(all_reviewed):.1f}")


if __name__ == "__main__":
    reviewer = ExtractionReviewer()
    reviewer.review_all()