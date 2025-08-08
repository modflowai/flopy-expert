#!/usr/bin/env python3
"""Fix next batch of models that are missing output files."""

import os
import subprocess

# Models that need fixing (from check_all_models output)
models_to_check = [
    'test_dis_cases',
    'test_example_notebooks', 
    'test_flopy_module',
    'test_formattedfile',
    'test_gage',
    'test_geospatial_util',
    'test_get_modflow',
    'test_grid_cases',
    'test_gridgen',
    'test_gridintersect'
]

def check_model(model_name):
    """Check if model creates actual MODFLOW model or is utility-only."""
    model_path = f"/home/danilopezmella/flopy_expert/test_review/models/{model_name}/basic/model.py"
    
    if not os.path.exists(model_path):
        return "missing", "File not found"
    
    with open(model_path, 'r') as f:
        content = f.read()
    
    # Check if it creates a MODFLOW model
    has_modflow = 'Modflow(' in content or 'MFModel(' in content or 'MFSimulation(' in content
    has_exe = 'exe_name=' in content
    has_run = 'run_model()' in content or 'run_simulation()' in content
    
    if not has_modflow:
        return "utility", "No MODFLOW model created (utility/demo only)"
    
    if 'exe_name=None' in content:
        return "fix_exe", "Has exe_name=None"
    
    if not has_exe:
        return "no_exe", "Missing exe_name parameter"
    
    if not has_run:
        return "no_run", "Missing run_model() call"
    
    # Test if it runs
    try:
        result = subprocess.run(
            ['python3', model_path],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=f"/home/danilopezmella/flopy_expert/test_review/models/{model_name}/basic"
        )
        if result.returncode == 0:
            # Check for output files
            model_ws = f"/home/danilopezmella/flopy_expert/test_review/models/{model_name}/basic/model_output"
            if os.path.exists(model_ws):
                files = os.listdir(model_ws)
                has_hds = any('.hds' in f for f in files)
                has_list = any('.list' in f or '.lst' in f for f in files)
                if has_hds and has_list:
                    return "working", "Model runs and produces output"
                elif has_list:
                    return "no_hds", "Model runs but no .hds file"
                else:
                    return "no_output", "Model runs but no output files"
            else:
                return "no_ws", "No model_output directory"
        else:
            return "error", f"Error: {result.stderr[:100]}"
    except subprocess.TimeoutExpired:
        return "timeout", "Model takes too long to run"
    except Exception as e:
        return "exception", str(e)[:100]

print("Checking models to determine which need fixing...")
print("=" * 80)

for model in models_to_check:
    status, message = check_model(model)
    
    if status == "utility":
        print(f"✓ {model}: {message} (OK - no fix needed)")
    elif status == "working":
        print(f"✓ {model}: {message}")
    elif status in ["fix_exe", "no_run", "no_hds"]:
        print(f"⚠ {model}: {message} (NEEDS FIX)")
    else:
        print(f"✗ {model}: {message}")

print("=" * 80)