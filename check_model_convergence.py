#!/usr/bin/env python3
"""Check convergence status of all test models."""

import os
import subprocess
import json
from pathlib import Path

def check_model_convergence(model_dir):
    """Check if a model converges by running it."""
    model_py = model_dir / "model.py"
    if not model_py.exists():
        return None, "No model.py found"
    
    try:
        # Run the model with timeout
        result = subprocess.run(
            ["python3", str(model_py)],
            cwd=str(model_dir),
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Check for convergence indicators
        output = result.stdout + result.stderr
        
        if "PERCENT DISCREPANCY" in output:
            # Extract convergence value
            for line in output.split('\n'):
                if "PERCENT DISCREPANCY" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if "PERCENT" in part and i+1 < len(parts):
                            try:
                                discrepancy = float(parts[i+1])
                                if discrepancy < 1.0:
                                    return True, f"Converged: {discrepancy:.6f}%"
                                else:
                                    return False, f"Not converged: {discrepancy:.6f}%"
                            except:
                                pass
        
        if "did not converge" in output.lower():
            return False, "Model did not converge"
        
        if "converge" in output.lower() and "success" in output.lower():
            return True, "Converged successfully"
        
        if result.returncode != 0:
            # Check for specific errors
            if "Traceback" in output:
                # Extract error type
                for line in output.split('\n'):
                    if "Error" in line and ":" in line:
                        return False, line.strip()
            return False, f"Exit code {result.returncode}"
        
        # If model ran but no clear convergence info
        if os.path.exists(model_dir / "model_output"):
            return None, "Model ran but convergence unclear"
        
        return False, "Unknown status"
        
    except subprocess.TimeoutExpired:
        return False, "Timeout (>10s)"
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    base_dir = Path("test_review/models")
    
    results = {
        "converged": [],
        "not_converged": [],
        "error": [],
        "unknown": []
    }
    
    # Get all test directories
    test_dirs = sorted([d for d in base_dir.glob("test_*/basic") if d.is_dir()])
    
    print(f"Checking {len(test_dirs)} models...")
    print("=" * 60)
    
    for test_dir in test_dirs:
        test_name = test_dir.parent.name
        status, message = check_model_convergence(test_dir)
        
        result_entry = {"name": test_name, "message": message}
        
        if status is True:
            results["converged"].append(result_entry)
            print(f"✓ {test_name}: {message}")
        elif status is False:
            if "Error" in message or "Traceback" in message:
                results["error"].append(result_entry)
                print(f"✗ {test_name}: {message}")
            else:
                results["not_converged"].append(result_entry)
                print(f"✗ {test_name}: {message}")
        else:
            results["unknown"].append(result_entry)
            print(f"? {test_name}: {message}")
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"  Converged: {len(results['converged'])}")
    print(f"  Not Converged: {len(results['not_converged'])}")
    print(f"  Errors: {len(results['error'])}")
    print(f"  Unknown: {len(results['unknown'])}")
    print(f"  Total: {len(test_dirs)}")
    
    print("\n" + "=" * 60)
    print("MODELS NEEDING FIXES:")
    
    if results["not_converged"]:
        print("\nNot Converging:")
        for model in results["not_converged"][:10]:  # Show first 10
            print(f"  - {model['name']}: {model['message']}")
    
    if results["error"]:
        print("\nErrors:")
        for model in results["error"][:10]:  # Show first 10
            print(f"  - {model['name']}: {model['message']}")
    
    # Save results
    with open("convergence_report.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull report saved to convergence_report.json")

if __name__ == "__main__":
    main()