#!/usr/bin/env python3
"""Comprehensive script to fix all test models."""

import os
import glob
import shutil

# Models already manually fixed
ALREADY_FIXED = [
    'test_shapefile_utils', 'test_lgr', 'test_swr_binaryread', 
    'test_str', 'test_modeltime', 'test_model_splitter',
    'test_cbc_full3D'  # Just fixed this one
]

def fix_workspace_directory(model_path):
    """Ensure model uses standard model_output directory."""
    with open(model_path, 'r') as f:
        content = f.read()
    
    modified = False
    
    # Common non-standard workspace patterns
    replacements = [
        ("ws = './cbc_full3d_example'", "ws = './model_output'"),
        ("ws = 'temp'", "ws = './model_output'"),
        ("ws = 'workspace'", "ws = './model_output'"),
        ("ws = './workspace'", "ws = './model_output'"),
        ("model_ws = 'temp'", "model_ws = './model_output'"),
        ("model_ws = 'workspace'", "model_ws = './model_output'"),
    ]
    
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            modified = True
    
    return content, modified

def add_exe_name(content, model_type='mf2005'):
    """Add executable path if missing."""
    modified = False
    
    if model_type == 'mf2005':
        # Check if Modflow() is created without exe_name
        if 'Modflow(' in content and 'exe_name=' not in content:
            # Add exe_name to Modflow constructor
            content = content.replace(
                'flopy.modflow.Modflow(',
                'flopy.modflow.Modflow(exe_name="/home/danilopezmella/flopy_expert/bin/mf2005", '
            )
            content = content.replace(
                'Modflow(',
                'Modflow(exe_name="/home/danilopezmella/flopy_expert/bin/mf2005", '
            )
            modified = True
    
    elif model_type == 'mf6':
        if 'MFSimulation(' in content and 'exe_name=' not in content:
            content = content.replace(
                'flopy.mf6.MFSimulation(',
                'flopy.mf6.MFSimulation(exe_name="/home/danilopezmella/flopy_expert/bin/mf6", '
            )
            content = content.replace(
                'MFSimulation(',
                'MFSimulation(exe_name="/home/danilopezmella/flopy_expert/bin/mf6", '
            )
            modified = True
    
    elif model_type == 'mfnwt':
        if 'ModflowNwt(' in content and 'exe_name=' not in content:
            content = content.replace(
                'flopy.modflow.ModflowNwt(',
                'flopy.modflow.ModflowNwt(exe_name="/home/danilopezmella/flopy_expert/bin/mfnwt", '
            )
            content = content.replace(
                'ModflowNwt(',
                'ModflowNwt(exe_name="/home/danilopezmella/flopy_expert/bin/mfnwt", '
            )
            modified = True
    
    return content, modified

def add_output_control(content):
    """Add output control if missing for heads."""
    modified = False
    
    # For MF6 models
    if 'ModflowGwfoc' in content:
        # Check if head_filerecord is missing
        if 'head_filerecord' not in content and 'budget_filerecord' in content:
            # Add head file recording
            content = content.replace(
                "budget_filerecord=",
                "head_filerecord=f'{name}.hds',\n    budget_filerecord="
            )
            # Update saverecord to include HEAD
            if "saverecord=[('BUDGET'" in content:
                content = content.replace(
                    "saverecord=[('BUDGET'",
                    "saverecord=[('HEAD', 'ALL'), ('BUDGET'"
                )
                modified = True
    
    # For MF2005 models
    elif 'ModflowOc' in content:
        # Check if save head is missing
        if 'save head' not in content.lower():
            # Update stress_period_data to include save head
            content = content.replace(
                "['save budget']",
                "['save head', 'save budget']"
            )
            content = content.replace(
                '["save budget"]',
                '["save head", "save budget"]'
            )
            modified = True
    
    return content, modified

def ensure_model_runs(content):
    """Ensure model actually runs (not just writes)."""
    modified = False
    
    # MF6 models
    if 'write_simulation()' in content and 'run_simulation()' not in content:
        # Add run_simulation after write_simulation
        content = content.replace(
            'sim.write_simulation()',
            'sim.write_simulation()\nsuccess, buff = sim.run_simulation(silent=True)\nif success:\n    print("✓ Model ran successfully")'
        )
        modified = True
    
    # MF2005 models
    elif '.write_input()' in content and '.run_model()' not in content:
        # Find model variable name
        import re
        match = re.search(r'(\w+)\.write_input\(\)', content)
        if match:
            var_name = match.group(1)
            content = content.replace(
                f'{var_name}.write_input()',
                f'{var_name}.write_input()\nsuccess, buff = {var_name}.run_model(silent=True)\nif success:\n    print("✓ Model ran successfully")'
            )
            modified = True
    
    return content, modified

def fix_model(model_path):
    """Fix a single model file."""
    model_name = model_path.split('/')[-3]
    
    if model_name in ALREADY_FIXED:
        return False, "Already fixed"
    
    try:
        with open(model_path, 'r') as f:
            content = f.read()
        
        original = content
        any_modified = False
        
        # Apply fixes
        content, mod1 = fix_workspace_directory(model_path)
        if mod1:
            any_modified = True
        
        # Detect model type
        if 'MFSimulation' in content or 'mf6' in content.lower():
            content, mod2 = add_exe_name(content, 'mf6')
        elif 'ModflowNwt' in content:
            content, mod2 = add_exe_name(content, 'mfnwt')
        else:
            content, mod2 = add_exe_name(content, 'mf2005')
        
        if mod2:
            any_modified = True
        
        content, mod3 = add_output_control(content)
        if mod3:
            any_modified = True
        
        content, mod4 = ensure_model_runs(content)
        if mod4:
            any_modified = True
        
        if any_modified:
            # Backup original
            backup_path = model_path + '.backup'
            if not os.path.exists(backup_path):
                shutil.copy(model_path, backup_path)
            
            # Write fixed version
            with open(model_path, 'w') as f:
                f.write(content)
            
            return True, "Fixed"
        
        return False, "No changes needed"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    models_dir = "/home/danilopezmella/flopy_expert/test_review/models"
    model_files = sorted(glob.glob(os.path.join(models_dir, "*/basic/model.py")))
    
    print(f"Checking {len(model_files)} models...\n")
    
    fixed = []
    errors = []
    skipped = []
    unchanged = []
    
    for model_file in model_files:
        model_name = model_file.split('/')[-3]
        success, message = fix_model(model_file)
        
        if message == "Already fixed":
            skipped.append(model_name)
            print(f"  Skipped {model_name} (already fixed)")
        elif success:
            fixed.append(model_name)
            print(f"✓ Fixed {model_name}")
        elif "Error" in message:
            errors.append((model_name, message))
            print(f"✗ Error in {model_name}: {message}")
        else:
            unchanged.append(model_name)
            print(f"  {model_name}: {message}")
    
    print("\n" + "="*60)
    print("Summary:")
    print(f"  Total models: {len(model_files)}")
    print(f"  Fixed: {len(fixed)}")
    print(f"  Skipped (already fixed): {len(skipped)}")
    print(f"  Unchanged: {len(unchanged)}")
    print(f"  Errors: {len(errors)}")
    
    if fixed:
        print(f"\nModels fixed ({len(fixed)}):")
        for name in fixed[:10]:  # Show first 10
            print(f"  - {name}")
        if len(fixed) > 10:
            print(f"  ... and {len(fixed)-10} more")
    
    if errors:
        print(f"\nErrors encountered ({len(errors)}):")
        for name, error in errors[:5]:
            print(f"  - {name}: {error}")

if __name__ == "__main__":
    main()