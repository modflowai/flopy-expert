#!/usr/bin/env python3

"""
Multi-Node Well Version 2 (MNW2) Package Demonstration

This model demonstrates the MNW2 package with advanced features
including complex well configurations, skin effects, pump capacity
limits, and multi-layer screening.

Based on test_mnw.py from the FloPy autotest suite.
"""

import numpy as np
import flopy
from pathlib import Path
import json

def build_mnw2_model(workspace):
    """
    Build a MODFLOW model with MNW2 package.
    
    Demonstrates:
    - Multi-node wells spanning multiple layers
    - Well skin effects
    - Pump location specifications
    - Variable pumping rates by stress period
    """
    modelname = "mnw2_example"
    
    # Create MODFLOW model
    mf = flopy.modflow.Modflow(
        modelname=modelname,
        exe_name="mf2005",
        model_ws=str(workspace)
    )
    
    # Model dimensions
    nlay, nrow, ncol = 3, 10, 10
    nper = 3
    
    # Discretization package
    dis = flopy.modflow.ModflowDis(
        mf,
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        nper=nper,
        delr=100.0,
        delc=100.0,
        top=100.0,
        botm=[80.0, 50.0, 0.0],
        perlen=[1.0, 100.0, 100.0],
        nstp=[1, 10, 10],
        steady=[True, False, False]
    )
    
    # Basic package
    ibound = np.ones((nlay, nrow, ncol), dtype=int)
    strt = 95.0 * np.ones((nlay, nrow, ncol))
    bas = flopy.modflow.ModflowBas(mf, ibound=ibound, strt=strt)
    
    # Layer Property Flow package
    lpf = flopy.modflow.ModflowLpf(
        mf,
        hk=10.0,
        vka=1.0,
        sy=0.2,
        ss=1e-5,
        laytyp=1,  # Convertible layers
        ipakcb=53  # Save cell-by-cell flows
    )
    
    # Create MNW2 node data (well construction details)
    # Well 1: Spans layers 1-2, located at (3, 3)
    # Well 2: Spans all 3 layers, located at (7, 7)
    node_data = [
        # Well 1 nodes
        (0, 3, 3, 95.0, 85.0, "WELL1", "SKIN", -1, 0, 0, 0, 0.5, 1.0, 5.0, 90.0),
        (1, 3, 3, 85.0, 55.0, "WELL1", "SKIN", -1, 0, 0, 0, 0.5, 1.0, 5.0, 90.0),
        # Well 2 nodes
        (0, 7, 7, 95.0, 85.0, "WELL2", "SKIN", -1, 0, 0, 0, 0.5, 1.5, 3.0, 90.0),
        (1, 7, 7, 85.0, 55.0, "WELL2", "SKIN", -1, 0, 0, 0, 0.5, 1.5, 3.0, 90.0),
        (2, 7, 7, 55.0, 5.0, "WELL2", "SKIN", -1, 0, 0, 0, 0.5, 1.5, 3.0, 90.0),
    ]
    
    # Convert to structured array
    dtype = [
        ("k", int), ("i", int), ("j", int),
        ("ztop", float), ("zbotm", float),
        ("wellid", object), ("losstype", object),
        ("pumploc", int), ("qlimit", int), ("ppflag", int), ("pumpcap", int),
        ("rw", float), ("rskin", float), ("kskin", float), ("zpump", float)
    ]
    node_data = np.array(node_data, dtype=dtype).view(np.recarray)
    
    # Stress period data (pumping rates)
    stress_period_data = {
        0: [("WELL1", 0.0), ("WELL2", 0.0)],  # No pumping in steady state
        1: [("WELL1", -500.0), ("WELL2", -1000.0)],  # Pumping in period 1
        2: [("WELL1", -250.0), ("WELL2", -1500.0)],  # Different rates in period 2
    }
    
    # Convert stress period data to structured arrays
    spd_dtype = [("wellid", object), ("qdes", float)]
    for kper in stress_period_data:
        stress_period_data[kper] = np.array(
            stress_period_data[kper], dtype=spd_dtype
        ).view(np.recarray)
    
    # MNW2 package
    mnw2 = flopy.modflow.ModflowMnw2(
        mf,
        mnwmax=2,  # Maximum number of multi-node wells
        nodtot=5,  # Total number of nodes
        node_data=node_data,
        stress_period_data=stress_period_data,
        itmp=[2, 2, 2],  # Number of wells active each period
        ipakcb=53  # Save cell-by-cell flows
    )
    
    # Add constant head boundaries
    chd_data = []
    # Add CHD cells on left boundary (column 0)
    for k in range(nlay):
        for i in range(nrow):
            chd_data.append([k, i, 0, 95.0, 95.0])
    # Add CHD cells on right boundary (column ncol-1)
    for k in range(nlay):
        for i in range(nrow):
            chd_data.append([k, i, ncol-1, 90.0, 90.0])
    
    chd = flopy.modflow.ModflowChd(mf, stress_period_data=chd_data, ipakcb=53)
    
    # Output Control
    oc = flopy.modflow.ModflowOc(
        mf,
        stress_period_data={
            (0, 0): ['save head', 'save budget'],
            (1, 9): ['save head', 'save budget'],
            (2, 9): ['save head', 'save budget']
        },
        compact=True,
        extension=['oc', 'hds', 'cbc']
    )
    
    # PCG solver with relaxed convergence criteria
    pcg = flopy.modflow.ModflowPcg(
        mf, 
        hclose=1e-3,
        rclose=1e-3,
        mxiter=200,
        iter1=50
    )
    
    return mf

def demonstrate_mnw2_features():
    """
    Demonstrate MNW2 package features and capabilities.
    """
    print("\nMulti-Node Well Version 2 (MNW2) Features:")
    print("=" * 60)
    
    print("\nEnhanced Capabilities:")
    print("  • Advanced well loss equations")
    print("  • Pump capacity constraints")
    print("  • Partial penetration effects")
    print("  • Multiple pumping locations")
    print("  • Observation well capabilities")
    print("  • Improved numerical stability")
    
    print("\nWell Loss Types:")
    print("  • NONE - No well losses")
    print("  • THIEM - Thiem equation")
    print("  • SKIN - Skin effect losses")
    print("  • GENERAL - General well loss equation")
    print("  • SPECIFYCWC - User-specified well loss coefficient")
    
    print("\nTypical Applications:")
    print("  • Complex water supply systems")
    print("  • Advanced dewatering designs")
    print("  • Heat pump systems")
    print("  • Aquifer storage and recovery")

def run_model(workspace):
    """
    Run the MNW2 model and analyze results.
    """
    # Build model
    mf = build_mnw2_model(workspace)
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
    Main function to demonstrate MNW2 package.
    """
    print("=" * 60)
    print("Multi-Node Well Version 2 (MNW2) Demonstration")
    print("=" * 60)
    
    # Create workspace
    workspace = Path("mnw2_workspace")
    workspace.mkdir(exist_ok=True)
    
    # Demonstrate features
    demonstrate_mnw2_features()
    
    # Run model
    print("\nRunning MNW2 model...")
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