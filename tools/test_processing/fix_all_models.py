#!/usr/bin/env python3
"""Fix all test models to ensure they run MODFLOW and produce output files."""

import os
import glob
import re

def fix_model(model_path):
    """Fix a single model file to ensure it runs MODFLOW."""
    
    with open(model_path, 'r') as f:
        content = f.read()
    
    modified = False
    original_content = content
    
    # Fix 1: Ensure exe_name is set for Modflow objects
    # Pattern: Modflow(...) without exe_name or with exe_name=None
    patterns = [
        (r'(flopy\.modflow\.Modflow\([^)]*?)(\))', 
         r'\1, exe_name="/home/danilopezmella/flopy_expert/bin/mf2005"\2'),
        (r'(Modflow\([^)]*?)(\))',
         r'\1, exe_name="/home/danilopezmella/flopy_expert/bin/mf2005"\2'),
    ]
    
    for pattern, replacement in patterns:
        # Check if exe_name is already there and not None
        if 'exe_name=' not in content or 'exe_name=None' in content:
            # Make sure we don't add exe_name twice
            if 'exe_name="/home/danilopezmella/flopy_expert/bin' not in content:
                content = re.sub(pattern, replacement, content, count=1)
                if content != original_content:
                    modified = True
    
    # Fix 2: Ensure MFSimulation has exe_name for MF6
    if 'MFSimulation' in content:
        if 'exe_name=' not in content or 'exe_name=None' in content:
            patterns_mf6 = [
                (r'(flopy\.mf6\.MFSimulation\([^)]*?)(\))',
                 r'\1, exe_name="/home/danilopezmella/flopy_expert/bin/mf6"\2'),
                (r'(MFSimulation\([^)]*?)(\))',
                 r'\1, exe_name="/home/danilopezmella/flopy_expert/bin/mf6"\2'),
            ]
            for pattern, replacement in patterns_mf6:
                if 'exe_name="/home/danilopezmella/flopy_expert/bin' not in content:
                    content = re.sub(pattern, replacement, content, count=1)
                    if content != original_content:
                        modified = True
    
    # Fix 3: Ensure ModflowNwt has exe_name
    if 'ModflowNwt' in content:
        if 'exe_name=' not in content or 'exe_name=None' in content:
            patterns_nwt = [
                (r'(flopy\.modflow\.ModflowNwt\([^)]*?)(\))',
                 r'\1, exe_name="/home/danilopezmella/flopy_expert/bin/mfnwt"\2'),
                (r'(ModflowNwt\([^)]*?)(\))',
                 r'\1, exe_name="/home/danilopezmella/flopy_expert/bin/mfnwt"\2'),
            ]
            for pattern, replacement in patterns_nwt:
                if 'exe_name="/home/danilopezmella/flopy_expert/bin' not in content:
                    content = re.sub(pattern, replacement, content, count=1)
                    if content != original_content:
                        modified = True
    
    # Fix 4: Ensure models are actually run
    # Look for write_input() without run_model()
    if 'write_input()' in content and 'run_model()' not in content and 'run_simulation()' not in content:
        # Add run_model() after write_input()
        content = re.sub(
            r'(\s+)(\w+)\.write_input\(\)',
            r'\1\2.write_input()\n\1success, buff = \2.run_model(silent=True)\n\1if success:\n\1    print("✓ Model ran successfully")\n\1else:\n\1    print("⚠ Model failed to run")',
            content
        )
        modified = True
    
    # Fix 5: Add essential packages if missing
    if 'ModflowPcg' not in content and 'ModflowGmg' not in content and 'ModflowSms' not in content and 'ModflowIms' not in content:
        # Model likely missing solver
        # Find where to add solver (after LPF/UPW/NPF package)
        if 'ModflowLpf' in content or 'ModflowUpw' in content:
            # Add PCG solver after LPF/UPW
            content = re.sub(
                r'(ModflowLpf\([^)]*\))',
                r'\1\n    \n    # Add PCG solver for convergence\n    pcg = flopy.modflow.ModflowPcg(mf, mxiter=100, hclose=1e-4, rclose=1e-3)',
                content
            )
            modified = True
    
    # Fix 6: Add OC package if missing
    if 'ModflowOc' not in content and 'Modflow(' in content:
        # Add OC package before write_input
        if 'write_input()' in content:
            content = re.sub(
                r'(\s+)(\w+)\.write_input\(\)',
                r'\1# Add output control\n\1oc = flopy.modflow.ModflowOc(\2, stress_period_data={(0,0): ["save head", "save budget"]})\n\1\n\1\2.write_input()',
                content
            )
            modified = True
    
    if modified:
        with open(model_path, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    models_dir = "/home/danilopezmella/flopy_expert/test_review/models"
    
    # Find all model.py files
    model_files = glob.glob(os.path.join(models_dir, "*/basic/model.py"))
    
    print(f"Found {len(model_files)} model files to check\n")
    
    fixed = []
    for model_file in sorted(model_files):
        model_name = model_file.split('/')[-3]  # Get test name
        
        # Skip models we've already fixed
        if model_name in ['test_shapefile_utils', 'test_lgr', 'test_swr_binaryread', 
                          'test_str', 'test_modeltime', 'test_model_splitter']:
            print(f"Skipping {model_name} (already fixed)")
            continue
        
        if fix_model(model_file):
            fixed.append(model_name)
            print(f"✓ Fixed {model_name}")
        else:
            print(f"  No changes needed for {model_name}")
    
    print(f"\nSummary:")
    print(f"  Fixed {len(fixed)} models")
    if fixed:
        print(f"  Models fixed: {', '.join(fixed)}")

if __name__ == "__main__":
    main()