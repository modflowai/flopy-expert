#!/usr/bin/env python3
"""Update progress status file with current state."""

import os
import json
import glob
import re
from datetime import datetime

def check_model(model_dir):
    """Check model for output files and convergence."""
    model_name = os.path.basename(model_dir)
    output_dir = os.path.join(model_dir, "basic", "model_output")
    
    # Initialize results
    has_hds = False
    has_listing = False
    converged = False
    discrepancy = None
    
    if os.path.exists(output_dir):
        # Check for .hds files recursively
        hds_files = glob.glob(os.path.join(output_dir, "*.hds")) + \
                    glob.glob(os.path.join(output_dir, "**/*.hds"), recursive=True)
        has_hds = len(hds_files) > 0
        
        # Check for listing files
        list_files = glob.glob(os.path.join(output_dir, "*.list")) + \
                     glob.glob(os.path.join(output_dir, "*.lst")) + \
                     glob.glob(os.path.join(output_dir, "**/*.list"), recursive=True) + \
                     glob.glob(os.path.join(output_dir, "**/*.lst"), recursive=True)
        has_listing = len(list_files) > 0
        
        # Check convergence
        if has_listing:
            for list_file in list_files:
                try:
                    with open(list_file, 'r') as f:
                        content = f.read()
                        # Look for percent discrepancy
                        matches = re.findall(r'PERCENT DISCREPANCY\s*=\s*([-\d.]+)', content)
                        if matches:
                            # Get the last (most recent) discrepancy
                            last_discrepancy = float(matches[-1])
                            if abs(last_discrepancy) < 1.0:
                                converged = True
                                discrepancy = last_discrepancy
                            else:
                                discrepancy = last_discrepancy
                except:
                    pass
    
    return {
        'name': model_name,
        'has_hds': has_hds,
        'has_listing': has_listing,
        'converged': converged,
        'discrepancy': discrepancy
    }

# Get all test models
test_dir = "/home/danilopezmella/flopy_expert/test_review/models"
model_dirs = sorted([os.path.join(test_dir, d) for d in os.listdir(test_dir) 
                     if os.path.isdir(os.path.join(test_dir, d))])

# Check all models
results = []
for model_dir in model_dirs:
    result = check_model(model_dir)
    results.append(result)

# Calculate statistics
total_models = len(results)
models_with_hds = sum(1 for r in results if r['has_hds'])
models_with_listing = sum(1 for r in results if r['has_listing'])
models_converged = sum(1 for r in results if r['converged'])
models_needing_fix = total_models - models_converged

# Separate converged models
converged_models = [r for r in results if r['converged']]
failed_models = [r for r in results if not r['converged']]

# Update progress status
progress_status = {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "summary": {
        "total_models": total_models,
        "models_with_hds": models_with_hds,
        "models_with_listing": models_with_listing,
        "models_converged": models_converged,
        "models_needing_fix": models_needing_fix
    },
    "converged_models": [
        {"name": m['name'], "discrepancy": m['discrepancy']} 
        for m in converged_models
    ],
    "models_with_issues": [
        {
            "name": m['name'],
            "has_hds": m['has_hds'],
            "has_listing": m['has_listing'],
            "issue": "missing output" if not m['has_listing'] else "convergence issue" if m['discrepancy'] else "unknown"
        }
        for m in failed_models
    ],
    "improvements_from_initial": {
        "hds_files_added": models_with_hds - 14,  # Initial was 14
        "listing_files_added": models_with_listing - 12,  # Initial was 12
        "convergence_fixed": models_converged - 11  # Initial was 11
    }
}

# Save to file
with open('/home/danilopezmella/flopy_expert/test_review/progress_status.json', 'w') as f:
    json.dump(progress_status, f, indent=2)

print(f"Progress Status Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
print(f"Total models: {total_models}")
print(f"Models with .hds files: {models_with_hds}/{total_models}")
print(f"Models with listing files: {models_with_listing}/{total_models}")
print(f"Models converged: {models_converged}/{total_models}")
print(f"Models needing fix: {models_needing_fix}")
print("=" * 60)
print(f"Improvements from initial state:")
print(f"  HDS files added: +{models_with_hds - 14}")
print(f"  Listing files added: +{models_with_listing - 12}")
print(f"  Convergence fixed: +{models_converged - 11}")
print("=" * 60)
print("Progress saved to test_review/progress_status.json")