#!/usr/bin/env python3
"""Fix all models with exe_name=None issue."""

import os
import re

models_to_fix = [
    'test_mp6',
    'test_mp7', 
    'test_mp7_cases',
    'test_mt3d',
    'test_nwt_ag',
    'test_obs',
    'test_modpathfile'
]

def fix_model(model_name):
    """Fix exe_name=None and add run_model() if missing."""
    model_path = f"/home/danilopezmella/flopy_expert/test_review/models/{model_name}/basic/model.py"
    
    if not os.path.exists(model_path):
        return False, "File not found"
    
    with open(model_path, 'r') as f:
        content = f.read()
    
    original = content
    
    # Fix exe_name=None for Modflow
    content = re.sub(
        r'Modflow\([^)]*exe_name=None[^)]*\)',
        lambda m: m.group(0).replace('exe_name=None', 'exe_name="/home/danilopezmella/flopy_expert/bin/mf2005"'),
        content
    )
    
    # Fix exe_name=None for ModflowNwt
    content = re.sub(
        r'ModflowNwt\([^)]*exe_name=None[^)]*\)',
        lambda m: m.group(0).replace('exe_name=None', 'exe_name="/home/danilopezmella/flopy_expert/bin/mfnwt"'),
        content
    )
    
    # Check if model writes but doesn't run
    if 'write_input()' in content and 'run_model()' not in content:
        # Find write_input() calls and add run_model after them
        lines = content.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            if 'mf.write_input()' in line and i < len(lines) - 1:
                # Add run_model after write_input
                indent = len(line) - len(line.lstrip())
                new_lines.append(' ' * indent + 'success, buff = mf.run_model(silent=True)')
                new_lines.append(' ' * indent + 'if success:')
                new_lines.append(' ' * indent + '    print("  ✓ Model ran successfully")')
                new_lines.append(' ' * indent + 'else:')
                new_lines.append(' ' * indent + '    print("  ⚠ Model failed to run")')
        content = '\n'.join(new_lines)
    
    if content != original:
        with open(model_path, 'w') as f:
            f.write(content)
        return True, "Fixed"
    
    return False, "No changes needed"

print("Fixing models with exe_name=None...")
print("=" * 60)

for model in models_to_fix:
    success, message = fix_model(model)
    if success:
        print(f"✓ {model}: {message}")
    else:
        print(f"  {model}: {message}")

print("=" * 60)
print("Batch fix complete!")