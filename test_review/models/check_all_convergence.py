#!/usr/bin/env python3
"""
Check convergence status of ALL FloPy test models.
This script runs each model and reports actual convergence status.
"""

import os
import subprocess
import json
from pathlib import Path

def check_model_convergence(test_dir):
    """Check if a model converges by running it."""
    model_file = Path(test_dir) / "basic" / "model.py"
    
    if not model_file.exists():
        return "NO_MODEL"
    
    try:
        # Run the model with timeout
        result = subprocess.run(
            ["python3", str(model_file)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=model_file.parent
        )
        
        output = result.stdout + result.stderr
        
        # Check for various convergence indicators
        if "CONVERGED" in output or "converged" in output:
            if "SUCCESSFULLY CONVERGED" in output or "successfully converged" in output:
                return "CONVERGED"
            elif "MODEL CONVERGED" in output:
                return "CONVERGED"
            elif "FAILED" in output or "failed" in output:
                return "FAILED"
            else:
                # Check if it says converged without failed
                if "FAILED" not in output.upper():
                    return "CONVERGED"
                else:
                    return "FAILED"
        
        # Check for MODFLOW execution
        if "MODFLOW" in output or "mf2005" in output or "mfnwt" in output or "mf6" in output:
            return "RUNS_MODFLOW"
        
        # Check if it's a utility
        if "utility" in output.lower() or "demonstration" in output.lower():
            if "MODFLOW" not in output:
                return "UTILITY"
        
        return "UNKNOWN"
        
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {str(e)}"

def main():
    """Check all test models."""
    
    # Get all test directories
    test_dirs = sorted([d for d in os.listdir(".") if d.startswith("test_")])
    
    print(f"Checking {len(test_dirs)} test models for convergence...\n")
    print("="*60)
    
    results = {
        "CONVERGED": [],
        "FAILED": [],
        "RUNS_MODFLOW": [],
        "UTILITY": [],
        "NO_MODEL": [],
        "TIMEOUT": [],
        "ERROR": [],
        "UNKNOWN": []
    }
    
    # Check each test
    for i, test_dir in enumerate(test_dirs, 1):
        print(f"[{i:3}/{len(test_dirs)}] Checking {test_dir}...", end=" ")
        
        status = check_model_convergence(test_dir)
        
        # Categorize result
        if status == "CONVERGED":
            results["CONVERGED"].append(test_dir)
            print("✅ CONVERGED!")
        elif status == "FAILED":
            results["FAILED"].append(test_dir)
            print("❌ FAILED")
        elif status == "RUNS_MODFLOW":
            results["RUNS_MODFLOW"].append(test_dir)
            print("🔄 Runs MODFLOW (no convergence check)")
        elif status == "UTILITY":
            results["UTILITY"].append(test_dir)
            print("🛠️ Utility (no MODFLOW)")
        elif status == "NO_MODEL":
            results["NO_MODEL"].append(test_dir)
            print("⚠️ No model.py found")
        elif status == "TIMEOUT":
            results["TIMEOUT"].append(test_dir)
            print("⏱️ Timeout")
        elif status.startswith("ERROR"):
            results["ERROR"].append(test_dir)
            print(f"❗ {status}")
        else:
            results["UNKNOWN"].append(test_dir)
            print("❓ Unknown")
    
    # Print summary
    print("\n" + "="*60)
    print("CONVERGENCE CHECK SUMMARY")
    print("="*60)
    
    print(f"\n✅ CONVERGED ({len(results['CONVERGED'])} tests):")
    for test in sorted(results["CONVERGED"]):
        print(f"    • {test}")
    
    print(f"\n❌ FAILED TO CONVERGE ({len(results['FAILED'])} tests):")
    for test in sorted(results["FAILED"])[:10]:
        print(f"    • {test}")
    if len(results["FAILED"]) > 10:
        print(f"    ... and {len(results['FAILED'])-10} more")
    
    print(f"\n🔄 RUNS MODFLOW (no convergence check) ({len(results['RUNS_MODFLOW'])} tests):")
    for test in sorted(results["RUNS_MODFLOW"])[:10]:
        print(f"    • {test}")
    if len(results["RUNS_MODFLOW"]) > 10:
        print(f"    ... and {len(results['RUNS_MODFLOW'])-10} more")
    
    print(f"\n🛠️ UTILITIES (no MODFLOW) ({len(results['UTILITY'])} tests):")
    for test in sorted(results["UTILITY"]):
        print(f"    • {test}")
    
    # Save results
    with open("convergence_check_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Final statistics
    total_modflow = len(results["CONVERGED"]) + len(results["FAILED"]) + len(results["RUNS_MODFLOW"])
    convergence_rate = len(results["CONVERGED"]) / total_modflow * 100 if total_modflow > 0 else 0
    
    print(f"\n" + "="*60)
    print("FINAL STATISTICS")
    print("="*60)
    print(f"Total tests checked: {len(test_dirs)}")
    print(f"Tests that run MODFLOW: {total_modflow}")
    print(f"Tests that CONVERGE: {len(results['CONVERGED'])}")
    print(f"Convergence rate: {convergence_rate:.1f}%")
    print(f"Utility tests: {len(results['UTILITY'])}")
    
    print(f"\n✅ Results saved to convergence_check_results.json")

if __name__ == "__main__":
    main()