#!/usr/bin/env python3
"""Quick validation of all models"""
import subprocess
import json
from pathlib import Path

models_dir = Path("models")
working = []
failing = []

for model_dir in sorted(models_dir.glob("*/basic")):
    model_file = model_dir / "model.py"
    if model_file.exists():
        test_name = model_dir.parent.name
        print(f"Testing {test_name}...", end=" ")
        
        result = subprocess.run(
            ["python3", "model.py"],
            cwd=model_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Check for actual convergence/success in output
            output = result.stdout.lower()
            if "model ran successfully" in output or "converged" in output or "complete" in output:
                print("✓ WORKING")
                working.append(test_name)
            else:
                print("✗ No convergence detected")
                failing.append(test_name)
        else:
            print(f"✗ FAILED")
            failing.append(test_name)

print(f"\n{'='*60}")
print(f"SUMMARY: {len(working)}/{len(working)+len(failing)} models working ({len(working)*100/(len(working)+len(failing)):.1f}%)")
print(f"\nWorking models ({len(working)}):")
for m in working:
    print(f"  ✓ {m}")
print(f"\nFailing models ({len(failing)}):")  
for m in failing:
    print(f"  ✗ {m}")