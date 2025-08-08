#\!/usr/bin/env python3
"""Batch fix script to add model execution to all non-running models."""

import os
import glob
import re

def check_model_needs_fix(model_dir):
    """Check if model needs fixing."""
    output_dir = os.path.join(model_dir, 'basic', 'model_output')
    if not os.path.exists(output_dir):
        # Try other subdirs
        for subdir in os.listdir(model_dir):
            output_dir = os.path.join(model_dir, subdir, 'model_output')
            if os.path.exists(output_dir):
                break
    
    # Check for output files
    if os.path.exists(output_dir):
        hds_files = glob.glob(os.path.join(output_dir, '*.hds'))
        if hds_files:
            return False  # Has output, doesn't need fix
    
    return True  # Needs fix

def fix_mf6_model(filepath):
    """Add simulation execution to MF6 models."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if already has run_simulation
    if 'run_simulation' in content:
        return False
    
    # Check if it's MF6 (has sim variable)
    if 'MFSimulation' not in content:
        return False
    
    # Find where to add execution
    lines = content.split('\n')
    new_lines = []
    added = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        # Look for OC package or end of model setup
        if not added and ('ModflowGwfoc' in line or 'output control' in line.lower()):
            # Look ahead for a good place to add
            for j in range(i+1, min(i+10, len(lines))):
                if lines[j].strip() == '' or lines[j].startswith('print'):
                    # Add execution here
                    new_lines.append('')
                    new_lines.append('# Write and run simulation')
                    new_lines.append('print("Writing and running model...")')
                    new_lines.append('sim.write_simulation()')
                    new_lines.append('success, buff = sim.run_simulation(silent=True)')
                    new_lines.append('if success:')
                    new_lines.append('    print("  ✓ Model ran successfully")')
                    new_lines.append('else:')
                    new_lines.append('    print("  ⚠ Model run failed")')
                    new_lines.append('')
                    added = True
                    break
    
    if added:
        with open(filepath, 'w') as f:
            f.write('\n'.join(new_lines))
        return True
    
    return False

def fix_classic_model(filepath):
    """Add model execution to classic MODFLOW models."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if already has run_model
    if 'run_model' in content:
        return False
    
    # Check if it's classic MODFLOW
    if 'Modflow(' not in content:
        return False
    
    # Find write_input and add run_model after
    lines = content.split('\n')
    new_lines = []
    added = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        if not added and 'write_input()' in line:
            indent = len(line) - len(line.lstrip())
            new_lines.append('')
            new_lines.append(' ' * indent + '# Run the model')
            new_lines.append(' ' * indent + 'print("Running MODFLOW...")')
            new_lines.append(' ' * indent + 'success, buff = mf.run_model(silent=True)')
            new_lines.append(' ' * indent + 'if success:')
            new_lines.append(' ' * (indent + 4) + 'print("  ✓ Model ran successfully")')
            new_lines.append(' ' * indent + 'else:')
            new_lines.append(' ' * (indent + 4) + 'print("  ⚠ Model run failed")')
            added = True
    
    if added:
        with open(filepath, 'w') as f:
            f.write('\n'.join(new_lines))
        return True
    
    return False

# Main execution
models_dir = 'models'
all_models = sorted([d for d in os.listdir(models_dir) if os.path.isdir(os.path.join(models_dir, d))])

fixed_mf6 = []
fixed_classic = []
already_ok = []
needs_manual = []

for model in all_models:
    model_path = os.path.join(models_dir, model)
    
    if not check_model_needs_fix(model_path):
        already_ok.append(model)
        continue
    
    # Find model.py
    model_py = None
    for subdir in os.listdir(model_path):
        subpath = os.path.join(model_path, subdir)
        if os.path.isdir(subpath):
            candidate = os.path.join(subpath, 'model.py')
            if os.path.exists(candidate):
                model_py = candidate
                break
    
    if not model_py:
        needs_manual.append(model + ' (no model.py)')
        continue
    
    # Try to fix
    if fix_mf6_model(model_py):
        fixed_mf6.append(model)
    elif fix_classic_model(model_py):
        fixed_classic.append(model)
    else:
        needs_manual.append(model)

print(f'✅ Fixed {len(fixed_mf6)} MF6 models:')
for m in fixed_mf6[:5]:
    print(f'  - {m}')
if len(fixed_mf6) > 5:
    print(f'  ... and {len(fixed_mf6)-5} more')

print(f'\n✅ Fixed {len(fixed_classic)} classic MODFLOW models:')
for m in fixed_classic[:5]:
    print(f'  - {m}')
if len(fixed_classic) > 5:
    print(f'  ... and {len(fixed_classic)-5} more')

print(f'\n✓ Already OK: {len(already_ok)} models')

if needs_manual:
    print(f'\n⚠ Need manual fixing: {len(needs_manual)} models')
    for m in needs_manual[:10]:
        print(f'  - {m}')
