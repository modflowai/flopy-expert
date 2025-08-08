#!/usr/bin/env python3
"""Quick check of all models to see which ones run"""
import os
import subprocess
import json
from pathlib import Path

def check_model(model_dir):
    """Check if a model runs and produces output"""
    model_py = model_dir / "model.py"
    if not model_py.exists():
        return None
    
    # Run the model
    result = subprocess.run(
        ["python3", str(model_py)],
        cwd=str(model_dir),
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Check for output files
    output_files = []
    for ext in ['.hds', '.cbc', '.lst', '.dat', '.out']:
        output_files.extend(list(model_dir.rglob(f'*{ext}')))
    
    return {
        'runs': result.returncode == 0,
        'has_output': len(output_files) > 0,
        'error': result.stderr[:200] if result.stderr else None
    }

def main():
    models_dir = Path("/home/danilopezmella/flopy_expert/test_review/models")
    results = {}
    
    # Get all model directories
    model_dirs = sorted([d for d in models_dir.iterdir() if d.is_dir()])
    
    print(f"Checking {len(model_dirs)} models...")
    
    for model_dir in model_dirs:
        # Find all basic subdirectories
        basic_dirs = list(model_dir.glob("*/model.py"))
        for model_py in basic_dirs:
            subdir = model_py.parent
            model_name = f"{model_dir.name}/{subdir.name}"
            print(f"Checking {model_name}...", end=" ")
            
            try:
                result = check_model(subdir)
                if result:
                    results[model_name] = result
                    status = "✓" if result['runs'] else "✗"
                    output = "📁" if result['has_output'] else "❌"
                    print(f"{status} {output}")
                else:
                    print("SKIP")
            except Exception as e:
                print(f"ERROR: {e}")
                results[model_name] = {'runs': False, 'has_output': False, 'error': str(e)}
    
    # Summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    
    working = sum(1 for r in results.values() if r['runs'])
    with_output = sum(1 for r in results.values() if r['has_output'])
    total = len(results)
    
    print(f"Total models: {total}")
    print(f"Running successfully: {working} ({working*100/total:.1f}%)")
    print(f"Producing output: {with_output} ({with_output*100/total:.1f}%)")
    
    print("\nFailed models:")
    for name, result in results.items():
        if not result['runs']:
            print(f"  - {name}")
    
    print("\nModels without output:")
    for name, result in results.items():
        if result['runs'] and not result['has_output']:
            print(f"  - {name}")

if __name__ == "__main__":
    main()