#!/usr/bin/env python3
"""Check all test models for output files and convergence."""

import os
import glob

def check_model(model_dir):
    """Check a single model for output files and convergence."""
    model_name = os.path.basename(os.path.dirname(model_dir))
    output_dir = os.path.join(model_dir, "model_output")
    
    # Check for output files recursively (some models use subdirectories)
    hds_files = glob.glob(os.path.join(output_dir, "*.hds")) + \
                glob.glob(os.path.join(output_dir, "**/*.hds"), recursive=True)
    has_hds = bool(hds_files)
    
    cbc_files = glob.glob(os.path.join(output_dir, "*.cbc")) + \
                glob.glob(os.path.join(output_dir, "**/*.cbc"), recursive=True)
    has_cbc = bool(cbc_files)
    
    # Find listing file recursively
    list_files = (glob.glob(os.path.join(output_dir, "*.lst")) + 
                  glob.glob(os.path.join(output_dir, "*.list")) +
                  glob.glob(os.path.join(output_dir, "**/*.lst"), recursive=True) +
                  glob.glob(os.path.join(output_dir, "**/*.list"), recursive=True))
    
    has_listing = bool(list_files)
    converged = None
    discrepancy = None
    
    # Check convergence if listing file exists
    if list_files:
        list_file = list_files[0]
        try:
            with open(list_file, 'r') as f:
                content = f.read()
                # Look for PERCENT DISCREPANCY
                if "PERCENT DISCREPANCY" in content:
                    # Find all occurrences
                    import re
                    matches = re.findall(r'PERCENT DISCREPANCY\s*=\s*([-\d.]+)', content)
                    if matches:
                        # Get the last discrepancy value
                        discrepancy = float(matches[-1])
                        converged = abs(discrepancy) < 1.0  # Consider converged if < 1%
        except Exception as e:
            pass
    
    return {
        'name': model_name,
        'has_hds': has_hds,
        'has_cbc': has_cbc,
        'has_listing': has_listing,
        'converged': converged,
        'discrepancy': discrepancy
    }

def main():
    models_dir = "/home/danilopezmella/flopy_expert/test_review/models"
    
    # Find all basic model directories
    model_dirs = sorted(glob.glob(os.path.join(models_dir, "*/basic")))
    
    print(f"Checking {len(model_dirs)} test models...\n")
    
    results = []
    for model_dir in model_dirs:
        result = check_model(model_dir)
        results.append(result)
    
    # Summary statistics
    with_hds = sum(1 for r in results if r['has_hds'])
    with_listing = sum(1 for r in results if r['has_listing'])
    converged = sum(1 for r in results if r['converged'])
    
    # Print detailed results
    print("=" * 80)
    print(f"{'Model Name':<30} {'HDS':<5} {'LIST':<5} {'CONVERGED':<10} {'DISCREPANCY':<15}")
    print("-" * 80)
    
    for r in results:
        hds_mark = "✓" if r['has_hds'] else "✗"
        list_mark = "✓" if r['has_listing'] else "✗"
        conv_mark = "✓" if r['converged'] else ("✗" if r['converged'] is False else "?")
        disc_str = f"{r['discrepancy']:.2f}%" if r['discrepancy'] is not None else "N/A"
        
        print(f"{r['name']:<30} {hds_mark:<5} {list_mark:<5} {conv_mark:<10} {disc_str:<15}")
    
    print("=" * 80)
    print("\nSummary:")
    print(f"  Total models: {len(results)}")
    print(f"  With .hds files: {with_hds}/{len(results)}")
    print(f"  With listing files: {with_listing}/{len(results)}")
    print(f"  Converged (< 1% discrepancy): {converged}/{len(results)}")
    
    # List models that need fixing
    need_fixing = [r for r in results if not r['has_hds'] or not r['has_listing'] or not r['converged']]
    
    if need_fixing:
        print(f"\nModels needing attention ({len(need_fixing)} total):")
        for r in need_fixing:
            issues = []
            if not r['has_hds']:
                issues.append("missing .hds")
            if not r['has_listing']:
                issues.append("missing listing")
            if r['converged'] is False:
                issues.append(f"high discrepancy: {r['discrepancy']:.2f}%")
            elif r['converged'] is None and r['has_listing']:
                issues.append("convergence unknown")
            
            print(f"  - {r['name']}: {', '.join(issues)}")

if __name__ == "__main__":
    main()