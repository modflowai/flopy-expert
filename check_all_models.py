#!/usr/bin/env python3
"""Check all models for convergence and runtime issues."""

import os
import subprocess
from pathlib import Path
import json

def check_model(model_dir):
    """Check a model by running it and checking output."""
    model_py = model_dir / "model.py"
    
    if not model_py.exists():
        return "no_model", "No model.py found"
    
    try:
        # Run the model
        result = subprocess.run(
            ["python3", "model.py"],
            cwd=str(model_dir),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Check for output files - multiple possible patterns
        output_dir = model_dir / "model_output"
        list_files = []
        
        if output_dir.exists():
            # Check for various listing file patterns
            patterns = ["*.list", "*.lst"]
            for pattern in patterns:
                list_files.extend(output_dir.glob(pattern))
        
        # Also check in model dir itself
        list_files.extend(model_dir.glob("*.list"))
        list_files.extend(model_dir.glob("*.lst"))
        
        # Check in all subdirectories (for models that create their own output dirs)
        for subdir in model_dir.iterdir():
            if subdir.is_dir() and subdir.name not in ['__pycache__', '.ipynb_checkpoints']:
                list_files.extend(subdir.glob("*.list"))
                list_files.extend(subdir.glob("*.lst"))
        
        # Check convergence from listing files
        converged = False
        max_discrepancy = None
        
        for list_file in list_files:
            try:
                with open(list_file, 'r') as f:
                    content = f.read()
                    
                    # Check for convergence indicators
                    if "PERCENT DISCREPANCY" in content:
                        # Extract max discrepancy
                        for line in content.split('\n'):
                            if "PERCENT DISCREPANCY" in line:
                                parts = line.split()
                                for i, part in enumerate(parts):
                                    if "DISCREPANCY" in part and i+2 < len(parts):
                                        try:
                                            disc = abs(float(parts[i+2]))
                                            if max_discrepancy is None or disc > max_discrepancy:
                                                max_discrepancy = disc
                                        except:
                                            pass
                        
                        if max_discrepancy is not None and max_discrepancy < 1.0:
                            converged = True
                    
                    # Also check for normal termination
                    if "Normal termination" in content:
                        converged = True
                    
                    # Check for MODFLOW 6 style
                    if "Simulation completed" in content:
                        converged = True
                        
            except Exception as e:
                pass
        
        if converged:
            if max_discrepancy is not None:
                return "converged", f"Max discrepancy: {max_discrepancy:.6f}%"
            else:
                return "converged", "Model converged"
        elif list_files:
            return "not_converged", f"Did not converge (found {len(list_files)} list files)"
        else:
            # Check if model created any output
            if output_dir.exists() and any(output_dir.iterdir()):
                return "ran", "Model ran but no listing file found"
            else:
                return "error", "No output generated"
                
    except subprocess.TimeoutExpired:
        return "timeout", "Timeout (>30s)"
    except Exception as e:
        return "error", f"Error: {str(e)}"

def main():
    base_dir = Path("test_review/models")
    
    results = {
        "converged": [],
        "not_converged": [],
        "ran": [],
        "error": [],
        "timeout": [],
        "no_model": []
    }
    
    # Get all test directories
    test_dirs = sorted([d for d in base_dir.glob("test_*/basic") if d.is_dir()])
    
    print(f"\nChecking {len(test_dirs)} models...")
    print("=" * 70)
    
    for i, test_dir in enumerate(test_dirs, 1):
        test_name = test_dir.parent.name
        print(f"\n[{i}/{len(test_dirs)}] Checking {test_name}...")
        
        status, message = check_model(test_dir)
        
        result_entry = {"name": test_name, "path": str(test_dir), "message": message}
        results[status].append(result_entry)
        
        symbol = {
            "converged": "✓",
            "not_converged": "✗", 
            "ran": "○",
            "error": "✗",
            "timeout": "⏱",
            "no_model": "?"
        }.get(status, "?")
        
        print(f"  {symbol} {message}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY:")
    print(f"  ✓ Converged: {len(results['converged'])}")
    print(f"  ✗ Not Converged: {len(results['not_converged'])}")
    print(f"  ○ Ran (unclear): {len(results['ran'])}")
    print(f"  ✗ Errors: {len(results['error'])}")
    print(f"  ⏱ Timeouts: {len(results['timeout'])}")
    print(f"  ? No model: {len(results['no_model'])}")
    print(f"  Total: {len(test_dirs)}")
    
    # List converged models
    if results['converged']:
        print("\n" + "=" * 70)
        print("CONVERGED MODELS:")
        for model in sorted(results['converged'], key=lambda x: x['name']):
            print(f"  ✓ {model['name']}: {model['message']}")
    
    # List models needing fixes
    if results['not_converged'] or results['error']:
        print("\n" + "=" * 70)
        print("MODELS NEEDING FIXES:")
        
        if results['not_converged']:
            print("\nNot Converging:")
            for model in results['not_converged'][:10]:
                print(f"  - {model['name']}: {model['message']}")
        
        if results['error']:
            print("\nErrors:")
            for model in results['error'][:10]:
                print(f"  - {model['name']}: {model['message']}")
    
    # Save detailed report
    with open("convergence_report_detailed.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed report saved to convergence_report_detailed.json")
    
    return results

if __name__ == "__main__":
    results = main()