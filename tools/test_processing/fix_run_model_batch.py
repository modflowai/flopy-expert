#!/usr/bin/env python3
"""Add run_model() calls to models that are missing them."""

import os
import re

models_to_fix = [
    'test_example_notebooks',
    'test_flopy_module', 
    'test_formattedfile',
    'test_gage',
    'test_geospatial_util',
    'test_get_modflow',
    'test_gridintersect'
]

def add_run_model(model_name):
    """Add run_model() call after write_input()."""
    model_path = f"/home/danilopezmella/flopy_expert/test_review/models/{model_name}/basic/model.py"
    
    if not os.path.exists(model_path):
        return False, "File not found"
    
    with open(model_path, 'r') as f:
        content = f.read()
    
    original = content
    
    # Check if already has run_model
    if 'run_model()' in content:
        return False, "Already has run_model()"
    
    # Find write_input() and add run_model after it
    if 'mf.write_input()' in content:
        lines = content.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            if 'mf.write_input()' in line and 'run_model()' not in content:
                # Get indentation
                indent = len(line) - len(line.lstrip())
                # Add run_model after write_input
                new_lines.append(' ' * indent + '# Run the model')
                new_lines.append(' ' * indent + 'success, buff = mf.run_model(silent=True)')
                new_lines.append(' ' * indent + 'if success:')
                new_lines.append(' ' * indent + '    print("  ✓ Model ran successfully")')
                new_lines.append(' ' * indent + '    # Check for output files')
                new_lines.append(' ' * indent + '    if os.path.exists(os.path.join(model_ws, f"{model_name}.hds")):')
                new_lines.append(' ' * indent + '        print("  ✓ Head file created")')
                new_lines.append(' ' * indent + 'else:')
                new_lines.append(' ' * indent + '    print("  ⚠ Model failed to run")')
                break
        
        content = '\n'.join(new_lines)
        
        # Also need to ensure model_name variable exists
        if 'model_name' not in content and 'modelname' in content:
            content = content.replace('modelname', 'model_name')
    
    if content != original:
        with open(model_path, 'w') as f:
            f.write(content)
        return True, "Added run_model() call"
    
    return False, "No write_input() found or unable to modify"

print("Adding run_model() calls to models...")
print("=" * 60)

for model in models_to_fix:
    success, message = add_run_model(model)
    if success:
        print(f"✓ {model}: {message}")
    else:
        print(f"  {model}: {message}")

print("=" * 60)
print("Batch fix complete!")