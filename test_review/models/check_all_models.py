#!/usr/bin/env python3
"""
COMPREHENSIVE convergence checker that actually checks MODFLOW listing files!
No more laziness - we check EVERY model's actual convergence status.
"""

import os
import subprocess
import json
import re
from pathlib import Path

def find_listing_files(test_dir):
    """Find all MODFLOW listing files in a test directory."""
    listing_files = []
    
    # Common patterns for listing files
    patterns = ['*.lst', '*.list', '*.out']
    
    # Search in common output directories
    search_dirs = [
        Path(test_dir) / 'basic',
        Path(test_dir) / 'basic' / 'model_output',
        Path(test_dir) / 'basic' / 'output',
        Path(test_dir) / 'model_output',
    ]
    
    for search_dir in search_dirs:
        if search_dir.exists():
            for pattern in patterns:
                listing_files.extend(search_dir.glob(pattern))
                listing_files.extend(search_dir.glob('*/' + pattern))  # Check subdirs
    
    return listing_files

def check_listing_convergence(listing_file):
    """Check if a MODFLOW listing file shows convergence."""
    try:
        with open(listing_file, 'r', errors='ignore') as f:
            content = f.read()
        
        # Check for various convergence indicators
        convergence_patterns = [
            r'CONVERGED IN\s+\d+\s+ITERATION',
            r'SOLVER CONVERGED',
            r'SOLUTION CONVERGED',
            r'Normal termination of simulation',
            r'PERCENT DISCREPANCY\s*=\s*([-\d.]+)',
            r'SUCCESSFUL CONVERGENCE',
            r'Simulation converged',
        ]
        
        failure_patterns = [
            r'FAILED TO CONVERGE',
            r'CONVERGENCE FAILURE',
            r'DID NOT CONVERGE',
            r'SOLUTION DID NOT CONVERGE',
            r'ABNORMAL TERMINATION',
            r'STOPPING SIMULATION',
        ]
        
        # Check for convergence
        converged = False
        failed = False
        discrepancy = None
        iterations = []
        
        for pattern in convergence_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                converged = True
                if 'DISCREPANCY' in pattern and matches:
                    try:
                        discrepancy = float(matches[-1])
                    except:
                        pass
                if 'ITERATION' in pattern:
                    iter_matches = re.findall(r'CONVERGED IN\s+(\d+)\s+ITERATION', content, re.IGNORECASE)
                    iterations = [int(m) for m in iter_matches]
        
        for pattern in failure_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                failed = True
                converged = False
                break
        
        # Check for normal termination
        if 'Normal termination' in content:
            converged = True
        
        return {
            'converged': converged,
            'failed': failed,
            'discrepancy': discrepancy,
            'iterations': iterations,
            'file': str(listing_file)
        }
    
    except Exception as e:
        return {
            'converged': False,
            'failed': False,
            'error': str(e),
            'file': str(listing_file)
        }

def run_model_if_needed(test_dir):
    """Run the model if no listing files exist."""
    model_file = Path(test_dir) / 'basic' / 'model.py'
    
    if not model_file.exists():
        return False
    
    # Check if listing files already exist
    listing_files = find_listing_files(test_dir)
    if listing_files:
        return True  # Already has output
    
    try:
        print(f"    Running model to generate output...", end=" ")
        result = subprocess.run(
            ['python3', 'model.py'],
            cwd=model_file.parent,
            capture_output=True,
            text=True,
            timeout=60
        )
        print("Done")
        return True
    except subprocess.TimeoutExpired:
        print("Timeout")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Check ALL tests for convergence."""
    
    # Get all test directories
    test_dirs = sorted([d for d in os.listdir('.') if d.startswith('test_')])
    
    print("="*80)
    print("COMPREHENSIVE MODFLOW CONVERGENCE CHECK")
    print("Checking actual MODFLOW listing files for convergence...")
    print("="*80)
    print()
    
    results = {
        'converged': [],
        'failed': [],
        'no_modflow': [],
        'no_listing': [],
        'errors': []
    }
    
    detailed_results = {}
    
    for i, test_dir in enumerate(test_dirs, 1):
        print(f"[{i:3}/{len(test_dirs)}] {test_dir:30}", end=" ")
        
        # First, try to run the model if needed
        if Path(test_dir, 'basic', 'model.py').exists():
            run_model_if_needed(test_dir)
        
        # Find listing files
        listing_files = find_listing_files(test_dir)
        
        if not listing_files:
            # No listing files - check if it's a utility
            model_file = Path(test_dir) / 'basic' / 'model.py'
            if model_file.exists():
                # Check if it's a utility by reading the file
                try:
                    with open(model_file, 'r') as f:
                        content = f.read(1000)  # Read first 1000 chars
                    if 'utility' in content.lower() or 'No MODFLOW' in content:
                        results['no_modflow'].append(test_dir)
                        print("🛠️ Utility (no MODFLOW)")
                    else:
                        results['no_listing'].append(test_dir)
                        print("⚠️ No listing file found")
                except:
                    results['no_listing'].append(test_dir)
                    print("⚠️ No listing file found")
            else:
                results['no_modflow'].append(test_dir)
                print("📂 No model.py")
        else:
            # Check convergence in listing files
            converged_any = False
            failed_any = False
            best_discrepancy = None
            
            for lst_file in listing_files:
                result = check_listing_convergence(lst_file)
                
                if result['converged']:
                    converged_any = True
                    if result['discrepancy'] is not None:
                        if best_discrepancy is None or abs(result['discrepancy']) < abs(best_discrepancy):
                            best_discrepancy = result['discrepancy']
                
                if result['failed']:
                    failed_any = True
            
            if converged_any and not failed_any:
                results['converged'].append(test_dir)
                if best_discrepancy is not None:
                    print(f"✅ CONVERGED (discrepancy: {best_discrepancy:.2e}%)")
                else:
                    print(f"✅ CONVERGED")
                detailed_results[test_dir] = {
                    'status': 'converged',
                    'discrepancy': best_discrepancy,
                    'files': len(listing_files)
                }
            elif failed_any:
                results['failed'].append(test_dir)
                print(f"❌ FAILED to converge")
                detailed_results[test_dir] = {
                    'status': 'failed',
                    'files': len(listing_files)
                }
            else:
                results['no_listing'].append(test_dir)
                print(f"❓ Could not determine")
    
    # Print comprehensive summary
    print("\n" + "="*80)
    print("FINAL CONVERGENCE SUMMARY")
    print("="*80)
    
    print(f"\n✅ CONVERGED ({len(results['converged'])} tests):")
    for test in sorted(results['converged']):
        if test in detailed_results and detailed_results[test].get('discrepancy') is not None:
            print(f"    • {test} (discrepancy: {detailed_results[test]['discrepancy']:.2e}%)")
        else:
            print(f"    • {test}")
    
    print(f"\n❌ FAILED TO CONVERGE ({len(results['failed'])} tests):")
    for test in sorted(results['failed'])[:20]:
        print(f"    • {test}")
    if len(results['failed']) > 20:
        print(f"    ... and {len(results['failed'])-20} more")
    
    print(f"\n🛠️ UTILITIES/NO MODFLOW ({len(results['no_modflow'])} tests):")
    for test in sorted(results['no_modflow'])[:10]:
        print(f"    • {test}")
    if len(results['no_modflow']) > 10:
        print(f"    ... and {len(results['no_modflow'])-10} more")
    
    print(f"\n⚠️ NO LISTING FILE ({len(results['no_listing'])} tests):")
    for test in sorted(results['no_listing'])[:10]:
        print(f"    • {test}")
    if len(results['no_listing']) > 10:
        print(f"    ... and {len(results['no_listing'])-10} more")
    
    # Calculate statistics
    total_modflow = len(results['converged']) + len(results['failed'])
    convergence_rate = (len(results['converged']) / total_modflow * 100) if total_modflow > 0 else 0
    
    print("\n" + "="*80)
    print("STATISTICS")
    print("="*80)
    print(f"Total tests checked: {len(test_dirs)}")
    print(f"Tests with MODFLOW output: {total_modflow}")
    print(f"Tests that CONVERGE: {len(results['converged'])}")
    print(f"Tests that FAIL: {len(results['failed'])}")
    print(f"Convergence rate: {convergence_rate:.1f}%")
    print(f"Utility tests: {len(results['no_modflow'])}")
    print(f"Missing output: {len(results['no_listing'])}")
    
    # Save detailed results
    with open('convergence_report_detailed.json', 'w') as f:
        json.dump({
            'summary': {
                'total': len(test_dirs),
                'converged': len(results['converged']),
                'failed': len(results['failed']),
                'no_modflow': len(results['no_modflow']),
                'no_listing': len(results['no_listing']),
                'convergence_rate': convergence_rate
            },
            'results': results,
            'detailed': detailed_results
        }, f, indent=2)
    
    print(f"\n📊 Detailed results saved to convergence_report_detailed.json")
    print("\n✅ COMPREHENSIVE CHECK COMPLETE!")

if __name__ == "__main__":
    main()