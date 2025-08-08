#!/usr/bin/env python3
"""
Simple script to check which models actually converge.
"""

import os
import subprocess
import json

def check_convergence(test_dir):
    """Check if a test converges by running it."""
    model_path = os.path.join(test_dir, "basic", "model.py")
    
    if not os.path.exists(model_path):
        return None
    
    try:
        # Run the model
        result = subprocess.run(
            ["python3", "model.py"],
            cwd=os.path.join(test_dir, "basic"),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout.upper()
        
        # Check for convergence
        if "SUCCESSFULLY CONVERGED" in output or "MODEL CONVERGED" in output:
            return "CONVERGED"
        elif "CONVERGED" in output and "FAILED" not in output:
            return "CONVERGED"
        elif "MODFLOW" in output or "MF2005" in output:
            return "RUNS_MODFLOW"
        else:
            return "NO_MODFLOW"
            
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"

# Main execution
print("Checking model convergence...")
print("=" * 60)

tests_to_check = [
    "test_chd", "test_drn", "test_evt", "test_ghb", "test_lak",
    "test_rch", "test_riv", "test_subwt", "test_uzf", "test_sfr",
    "test_grid_cases", "test_gridgen", "test_wel", "test_mnw",
    "test_mf6", "test_modflow", "test_obs", "test_compare"
]

converged = []
runs_modflow = []
no_modflow = []
errors = []

for test in tests_to_check:
    if os.path.exists(test):
        print(f"Checking {test}...", end=" ")
        status = check_convergence(test)
        
        if status == "CONVERGED":
            converged.append(test)
            print("✅ CONVERGED!")
        elif status == "RUNS_MODFLOW":
            runs_modflow.append(test)
            print("🔄 Runs MODFLOW")
        elif status == "NO_MODFLOW":
            no_modflow.append(test)
            print("🛠️ No MODFLOW")
        elif status == "TIMEOUT":
            errors.append((test, "timeout"))
            print("⏱️ Timeout")
        elif status and status.startswith("ERROR"):
            errors.append((test, status))
            print(f"❌ {status}")
        else:
            print("⚠️ Not found")

# Summary
print("\n" + "=" * 60)
print("CONVERGENCE SUMMARY")
print("=" * 60)

print(f"\n✅ CONVERGED ({len(converged)} tests):")
for t in converged:
    print(f"  • {t}")

print(f"\n🔄 RUNS MODFLOW ({len(runs_modflow)} tests):")
for t in runs_modflow[:5]:
    print(f"  • {t}")
if len(runs_modflow) > 5:
    print(f"  ... and {len(runs_modflow)-5} more")

# Save results
results = {
    "converged": converged,
    "runs_modflow": runs_modflow,
    "no_modflow": no_modflow,
    "errors": errors
}

with open("convergence_report.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\n📊 Final Statistics:")
print(f"  • Tests that CONVERGE: {len(converged)}")
print(f"  • Tests that run MODFLOW: {len(runs_modflow)}")
print(f"  • Utility tests: {len(no_modflow)}")
print(f"  • Total checked: {len(tests_to_check)}")
print(f"\nResults saved to convergence_report.json")