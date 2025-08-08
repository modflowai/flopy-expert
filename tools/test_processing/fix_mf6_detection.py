#!/usr/bin/env python3
"""Fix MF6 convergence detection."""

import os
import glob
import re

def check_mf6_convergence(list_file):
    """Check if MF6 model converged successfully."""
    try:
        with open(list_file, 'r') as f:
            content = f.read()
        
        # Check for MF6 completion indicators
        has_end_timestep = 'end timestep' in content
        has_time_summary = 'TIME SUMMARY AT END OF TIME STEP' in content
        has_failed = 'FAILED' in content.upper() or 'ERROR' in content.upper()
        
        # MF6 models are considered converged if they complete without failures
        if has_end_timestep and has_time_summary and not has_failed:
            return True, 0.0  # MF6 doesn't report discrepancy like classic MODFLOW
        
        return False, None
        
    except Exception as e:
        return False, None

def check_classic_convergence(list_file):
    """Check classic MODFLOW convergence."""
    try:
        with open(list_file, 'r') as f:
            content = f.read()
        
        # Look for percent discrepancy
        matches = re.findall(r'PERCENT DISCREPANCY\s*=\s*([-\d.]+)', content)
        if matches:
            last_discrepancy = float(matches[-1])
            if abs(last_discrepancy) < 1.0:
                return True, last_discrepancy
            else:
                return False, last_discrepancy
        
        return False, None
        
    except Exception:
        return False, None

# Check the problematic models
models_to_check = ['test_export', 'test_particledata']

for model_name in models_to_check:
    model_dir = f"/home/danilopezmella/flopy_expert/test_review/models/{model_name}/basic/model_output"
    
    if os.path.exists(model_dir):
        # Find listing files
        list_files = glob.glob(os.path.join(model_dir, "*.list")) + \
                     glob.glob(os.path.join(model_dir, "*.lst"))
        
        if list_files:
            list_file = list_files[0]
            print(f"\nChecking {model_name}:")
            print(f"  Listing file: {os.path.basename(list_file)}")
            
            # Try MF6 detection first
            mf6_converged, mf6_disc = check_mf6_convergence(list_file)
            if mf6_converged:
                print(f"  ✓ MF6 model converged successfully")
                continue
            
            # Try classic MODFLOW detection
            classic_converged, classic_disc = check_classic_convergence(list_file)
            if classic_converged:
                print(f"  ✓ Classic MODFLOW converged: {classic_disc}%")
            else:
                print(f"  ✗ Model did not converge properly")
                # Show end of file for diagnosis
                with open(list_file, 'r') as f:
                    lines = f.readlines()
                print(f"  Last 5 lines:")
                for line in lines[-5:]:
                    print(f"    {line.strip()}")
        else:
            print(f"\n{model_name}: No listing files found")
    else:
        print(f"\n{model_name}: No output directory found")