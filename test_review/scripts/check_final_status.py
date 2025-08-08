#!/usr/bin/env python3
"""Check final status of all test models."""

import os
import glob
import re

def check_model_status(model_dir):
    '''Check model status.'''
    # Find output directory
    output_dir = None
    for subdir in ['basic', 'dis', 'disv']:
        test_dir = os.path.join(model_dir, subdir, 'model_output')
        if os.path.exists(test_dir):
            output_dir = test_dir
            break
    
    if not output_dir:
        return 'no_output_dir'
    
    # Check for files
    hds_files = glob.glob(os.path.join(output_dir, '*.hds'))
    list_files = glob.glob(os.path.join(output_dir, '*.list')) + glob.glob(os.path.join(output_dir, '*.lst'))
    
    if not hds_files and not list_files:
        return 'no_output_files'
    
    # Check convergence
    if list_files:
        try:
            with open(list_files[0], 'r') as f:
                content = f.read()
            
            # MF6 check
            if 'Normal termination' in content or 'end timestep' in content:
                return 'converged'
            
            # Classic check
            matches = re.findall(r'PERCENT DISCREPANCY\s*=\s*([-\d.]+)', content)
            if matches:
                last_disc = float(matches[-1])
                if abs(last_disc) < 1.0:
                    return 'converged'
                else:
                    return f'discrepancy_{last_disc:.2f}%'
        except:
            pass
    
    if hds_files:
        return 'has_hds_no_convergence_check'
    
    return 'unknown'

# Check all test models
models_dir = 'models'
all_models = sorted([d for d in os.listdir(models_dir) if d.startswith('test_')])

status_counts = {}
converged_models = []
problem_models = []

for model in all_models:
    model_path = os.path.join(models_dir, model)
    status = check_model_status(model_path)
    
    if status not in status_counts:
        status_counts[status] = []
    status_counts[status].append(model)
    
    if status == 'converged':
        converged_models.append(model)
    elif status not in ['no_output_dir', 'converged']:
        problem_models.append((model, status))

print('📊 Final Model Status Report:')
print(f'  Total models: {len(all_models)}')
print(f'  ✅ Converged: {len(converged_models)}')
print(f'  ❌ Issues: {len(problem_models)}')
print(f'  📁 No output (utilities): {len(status_counts.get("no_output_dir", []))}')

print('\n📈 Status breakdown:')
for status, models in sorted(status_counts.items()):
    if status != 'converged':
        print(f'  {status}: {len(models)} models')

if problem_models:
    print('\n⚠️ Models with issues:')
    for model, status in problem_models[:10]:
        print(f'  - {model}: {status}')
        
print('\n✅ Recently fixed models now converging:')
recently_fixed = ['test_export', 'test_particledata', 'test_gage', 'test_nwt_ag', 'test_cbc_full3D']
for model in recently_fixed:
    if model in converged_models:
        print(f'  - {model}')