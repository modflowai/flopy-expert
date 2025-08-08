#!/usr/bin/env python3
"""
Standalone FloPy model demonstrating binary file reversal with structured grid (DIS)
Extracted from: test_binaryfile_reverse.py

Demonstrates all 7 conceptual phases with focus on Post-processing (Phase 7)
"""

import flopy
import numpy as np
from pathlib import Path
import sys
sys.path.append('/home/danilopezmella/flopy_expert/test_review')
from mf6_config import get_mf6_exe

def build_model(ws="./model_output", name="reverse_demo_dis"):
    """
    Build a simple MODFLOW 6 model with structured grid for demonstrating 
    binary file reversal post-processing.
    """
    
    # Ensure workspace exists
    Path(ws).mkdir(exist_ok=True)
    
    # ========================================
    # PHASE 1: DISCRETIZATION
    # ========================================
    print("Phase 1: Setting up discretization...")
    
    # Create simulation with shared MODFLOW 6 executable
    sim = flopy.mf6.MFSimulation(sim_name=name, sim_ws=ws, exe_name=get_mf6_exe())
    
    # Time discretization - 3 stress periods with different configurations
    # This creates asymmetric time steps to demonstrate reversal handling
    tdis = flopy.mf6.ModflowTdis(
        sim, 
        nper=3,
        perioddata=[
            (1.0, 2, 1.0),  # Period 1: 1 day, 2 steps (0.5 day each)
            (1.0, 1, 1.0),  # Period 2: 1 day, 1 step
            (1.0, 1, 1.0),  # Period 3: 1 day, 1 step
        ]
    )
    
    # ========================================
    # PHASE 5: SOLVER CONFIGURATION
    # ========================================
    print("Phase 5: Configuring solver...")
    
    # Iterative Model Solver
    ims = flopy.mf6.ModflowIms(
        sim,
        print_option="SUMMARY",
        complexity="SIMPLE"
    )
    
    # Create groundwater flow model
    gwf = flopy.mf6.ModflowGwf(sim, modelname=name, save_flows=True)
    
    # Structured discretization (DIS)
    dis = flopy.mf6.ModflowGwfdis(
        gwf,
        nlay=2,      # 2 layers
        nrow=10,     # 10 rows
        ncol=10,     # 10 columns
        delr=10.0,   # Cell width
        delc=10.0,   # Cell height
        top=0.0,     # Top elevation
        botm=[-1.0, -2.0]  # Bottom of each layer
    )
    
    # ========================================
    # PHASE 2: PROPERTIES
    # ========================================
    print("Phase 2: Setting hydraulic properties...")
    
    # Node Property Flow package
    npf = flopy.mf6.ModflowGwfnpf(
        gwf,
        save_specific_discharge=True,
        icelltype=0,  # Confined
        k=10.0        # Hydraulic conductivity
    )
    
    # ========================================
    # PHASE 3: INITIAL CONDITIONS
    # ========================================
    print("Phase 3: Setting initial conditions...")
    
    # Initial conditions - gradient from left to right
    ic = flopy.mf6.ModflowGwfic(gwf, strt=1.0)
    
    # ========================================
    # PHASE 4: BOUNDARY CONDITIONS
    # ========================================
    print("Phase 4: Setting boundary conditions...")
    
    # Constant head boundaries
    chd = flopy.mf6.ModflowGwfchd(
        gwf,
        stress_period_data=[
            [(0, 0, 0), 1.0],  # Upper-left corner
            [(0, 9, 9), 0.0],  # Lower-right corner
        ]
    )
    
    # ========================================
    # OUTPUT CONTROL
    # ========================================
    print("Setting up output control...")
    
    oc = flopy.mf6.ModflowGwfoc(
        gwf,
        budget_filerecord=f"{name}.bud",
        head_filerecord=f"{name}.hds",
        saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")]
    )
    
    return sim, gwf

def demonstrate_reversal(sim, gwf):
    """
    PHASE 7: POST-PROCESSING
    Demonstrate binary file reversal functionality
    """
    print("\n" + "="*50)
    print("Phase 7: Post-processing - Binary File Reversal")
    print("="*50)
    
    from flopy.utils import HeadFile, CellBudgetFile
    
    # Get output file paths
    ws = Path(sim.sim_path)
    head_file_path = ws / gwf.oc.head_filerecord.get_data()[0][0]
    budget_file_path = ws / gwf.oc.budget_filerecord.get_data()[0][0]
    
    # Load original files
    print("\n1. Loading original binary files...")
    hf = HeadFile(head_file_path)
    bf = CellBudgetFile(budget_file_path)
    
    # Get original data
    orig_times = hf.get_times()
    orig_kstpkper = hf.get_kstpkper()
    print(f"   Original times: {orig_times}")
    print(f"   Original (kstp, kper): {orig_kstpkper}")
    
    # Reverse head file
    print("\n2. Reversing head file...")
    rev_head_path = ws / f"{head_file_path.stem}_reversed.hds"
    hf.reverse(filename=rev_head_path)
    
    # Load reversed file
    hf_rev = HeadFile(rev_head_path)
    rev_times = hf_rev.get_times()
    rev_kstpkper = hf_rev.get_kstpkper()
    print(f"   Reversed times: {rev_times}")
    print(f"   Reversed (kstp, kper): {rev_kstpkper}")
    
    # Reverse budget file
    print("\n3. Reversing budget file...")
    rev_budget_path = ws / f"{budget_file_path.stem}_reversed.cbb"
    bf.reverse(rev_budget_path)
    print(f"   Budget file reversed (values negated)")
    
    # Verify reversal
    print("\n4. Verifying reversal...")
    orig_heads = hf.get_alldata()
    rev_heads = hf_rev.get_alldata()
    
    for i, t in enumerate(orig_times):
        # Check head reversal
        if np.allclose(orig_heads[i], rev_heads[-(i+1)]):
            print(f"   Time {t:.1f}: Head values match ✓")
    
    print("\n" + "="*50)
    print("Binary file reversal demonstration complete!")
    print("Files created:")
    print(f"  - Original: {head_file_path.name}, {budget_file_path.name}")
    print(f"  - Reversed: {rev_head_path.name}, {rev_budget_path.name}")
    print("="*50)

def run_model():
    """Run the model and demonstrate binary file reversal"""
    
    print("="*60)
    print("MODFLOW 6 Binary File Reversal Demonstration (DIS)")
    print("="*60 + "\n")
    
    # Build model
    sim, gwf = build_model()
    
    # Write and run
    print("\nWriting and running simulation...")
    sim.write_simulation()
    success, buff = sim.run_simulation()
    
    if not success:
        print("ERROR: Model failed to converge!")
        return None
    
    print("✓ Model ran successfully!")
    
    # Get final heads
    head = gwf.output.head().get_data()
    print(f"\nFinal head range: {head.min():.3f} to {head.max():.3f} m")
    
    # Demonstrate reversal
    demonstrate_reversal(sim, gwf)
    
    return sim, gwf

if __name__ == "__main__":
    run_model()