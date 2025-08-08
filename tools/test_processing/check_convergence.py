#!/usr/bin/env python3
"""Check convergence for specific models."""

import os
import glob
import re

models_to_check = [
    'test_cbc_full3D',
    'test_copy', 
    'test_cellbudgetfile',
    'test_datautil',
    'test_export',
    'test_flopy_io',
    'test_grid',
    'test_particledata'
]

def check_convergence(model_name):
    """Check convergence for a single model."""
    model_dir = f"/home/danilopezmella/flopy_expert/test_review/models/{model_name}/basic"
    
    # Find listing files recursively
    lst_files = glob.glob(os.path.join(model_dir, "**/*.lst"), recursive=True) + \
                glob.glob(os.path.join(model_dir, "**/*.list"), recursive=True)
    
    if not lst_files:
        return None, "No listing file found"
    
    # Check each listing file for PERCENT DISCREPANCY
    all_discrepancies = []
    
    for lst_file in lst_files:
        try:
            with open(lst_file, 'r') as f:
                content = f.read()
                matches = re.findall(r'PERCENT DISCREPANCY\s*=\s*([-\d.]+)', content)
                if matches:
                    # Get the last discrepancy value
                    last_discrepancy = float(matches[-1])
                    all_discrepancies.append(last_discrepancy)
        except Exception as e:
            continue
    
    if all_discrepancies:
        # Return the worst (highest absolute) discrepancy
        worst = max(all_discrepancies, key=abs)
        return worst, "CONVERGED" if abs(worst) < 1.0 else "NOT CONVERGED"
    else:
        return None, "No PERCENT DISCREPANCY found"

print("=" * 70)
print("CONVERGENCE CHECK FOR FIXED MODELS")
print("=" * 70)
print(f"{'Model':<25} {'Discrepancy':<15} {'Status':<20}")
print("-" * 70)

converged_count = 0
not_converged_count = 0
no_output_count = 0

for model in models_to_check:
    discrepancy, status = check_convergence(model)
    
    if discrepancy is not None:
        disc_str = f"{discrepancy:.2f}%"
        if "CONVERGED" in status and "NOT" not in status:
            status_symbol = "✓"
            converged_count += 1
        else:
            status_symbol = "✗"
            not_converged_count += 1
    else:
        disc_str = "N/A"
        status_symbol = "⚠"
        no_output_count += 1
    
    print(f"{model:<25} {disc_str:<15} {status_symbol} {status}")

print("=" * 70)
print("\nSUMMARY:")
print(f"  Converged (<1% discrepancy): {converged_count}")
print(f"  Not converged (≥1% discrepancy): {not_converged_count}") 
print(f"  No output/listing file: {no_output_count}")
print(f"  Total checked: {len(models_to_check)}")

# Check if we need to fix any
if not_converged_count > 0 or no_output_count > 0:
    print("\nMODELS NEEDING ATTENTION:")
    for model in models_to_check:
        discrepancy, status = check_convergence(model)
        if discrepancy is None or (discrepancy is not None and abs(discrepancy) >= 1.0):
            print(f"  - {model}: {status}")