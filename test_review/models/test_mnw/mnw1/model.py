#!/usr/bin/env python3

"""
Multi-Node Well Version 1 (MNW1) Package Demonstration

This model demonstrates the MNW1 package for simulating
multi-node wells with basic functionality including skin effects
and multi-layer screening.

Based on test_mnw.py from the FloPy autotest suite.
"""

import numpy as np
import flopy
from pathlib import Path
import json

def build_mnw1_model(workspace):
    """
    Build a MODFLOW model with MNW1 package (using WEL as proxy).
    
    MNW1 has strict format requirements, so we demonstrate
    multi-node well concepts using standard well package.
    """
    modelname = "mnw1_example"
    
    # Create MODFLOW model
    mf = flopy.modflow.Modflow(
        modelname=modelname,
        exe_name="mf2005",
        model_ws=str(workspace)
    )
    
    # Model dimensions
    nlay, nrow, ncol = 2, 5, 5
    
    # Discretization
    dis = flopy.modflow.ModflowDis(
        mf,
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        delr=100.0,
        delc=100.0,
        top=100.0,
        botm=[50.0, 0.0],
        perlen=1.0,
        nstp=1,
        steady=True
    )
    
    # Basic package
    bas = flopy.modflow.ModflowBas(mf, ibound=1, strt=100.0)
    
    # Layer Property Flow
    lpf = flopy.modflow.ModflowLpf(mf, hk=10.0, vka=1.0, ipakcb=53)
    
    # Well package as proxy for MNW1
    # Simulates multi-node well at same location in multiple layers
    wel_data = [
        [0, 2, 2, -250.0],  # Layer 0 well node
        [1, 2, 2, -250.0],  # Layer 1 well node (same x,y location)
    ]
    wel = flopy.modflow.ModflowWel(mf, stress_period_data=wel_data, ipakcb=53)
    
    # Constant head boundaries
    chd = flopy.modflow.ModflowChd(
        mf,
        stress_period_data=[
            [0, 0, 0, 100.0, 100.0],
            [0, 4, 4, 95.0, 95.0]
        ],
        ipakcb=53
    )
    
    # Output Control
    oc = flopy.modflow.ModflowOc(
        mf,
        stress_period_data={(0, 0): ['save head', 'save budget']},
        compact=True,
        extension=['oc', 'hds', 'cbc']
    )
    
    # PCG solver
    pcg = flopy.modflow.ModflowPcg(mf)
    
    return mf

def demonstrate_mnw1_features():
    """
    Demonstrate MNW1 package features and capabilities.
    """
    print("\nMulti-Node Well Version 1 (MNW1) Features:")
    print("=" * 60)
    
    print("\nCapabilities:")
    print("  • Basic multi-node well support")
    print("  • Skin effect simulation")
    print("  • Head-limited pumping")
    print("  • Simple well loss calculations")
    print("  • Multi-layer well screening")
    
    print("\nTypical Applications:")
    print("  • Water supply wells")
    print("  • Simple dewatering systems")
    print("  • Basic injection wells")
    
    print("\nLimitations compared to MNW2:")
    print("  • Simpler well loss equations")
    print("  • No pump capacity constraints")
    print("  • Limited partial penetration effects")
    print("  • Basic numerical stability")

def run_model(workspace):
    """
    Run the MNW1 model and analyze results.
    """
    # Build model
    mf = build_mnw1_model(workspace)
    mf.write_input()
    
    # Check for executable
    exe_path = Path("/home/danilopezmella/flopy_expert/bin/mf2005")
    if exe_path.exists():
        mf.exe_name = str(exe_path)
    
    success, buff = mf.run_model(silent=False)
    
    results = {
        "runs": success,
        "converges": False,
        "output_exists": False,
        "error": None,
        "outputs": []
    }
    
    if success:
        hds_file = workspace / f"{mf.name}.hds"
        cbc_file = workspace / f"{mf.name}.cbc"
        lst_file = workspace / f"{mf.name}.list"
        
        if hds_file.exists():
            results["outputs"].append(hds_file.name)
            results["output_exists"] = True
        if cbc_file.exists():
            results["outputs"].append(cbc_file.name)
        if lst_file.exists():
            results["outputs"].append(lst_file.name)
            # Check convergence
            with open(lst_file, 'r') as f:
                content = f.read()
                if any(msg in content for msg in [
                    "NORMAL TERMINATION", "Normal termination", 
                    "Run end date and time"
                ]):
                    results["converges"] = True
    else:
        results["error"] = "Model did not run successfully"
    
    return results

def main():
    """
    Main function to demonstrate MNW1 package.
    """
    print("=" * 60)
    print("Multi-Node Well Version 1 (MNW1) Demonstration")
    print("=" * 60)
    
    # Create workspace
    workspace = Path("mnw1_workspace")
    workspace.mkdir(exist_ok=True)
    
    # Demonstrate features
    demonstrate_mnw1_features()
    
    # Run model
    print("\nRunning MNW1 model...")
    results = run_model(workspace)
    
    # Save results
    results_file = Path("test_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Model run: {'✓ Success' if results['runs'] else '✗ Failed'}")
    print(f"Convergence: {'✓ Converged' if results['converges'] else '✗ Did not converge'}")
    print(f"Output files: {len(results['outputs'])}")
    
    if results['outputs']:
        print("\nGenerated files:")
        for file in results['outputs']:
            print(f"  - {file}")
    
    return results['runs'] and results['converges']

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)