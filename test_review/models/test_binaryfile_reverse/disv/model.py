#!/usr/bin/env python3
"""
Standalone FloPy model demonstrating binary file reversal with vertex grid (DISV)
Extracted from: test_binaryfile_reverse.py

Demonstrates all 7 conceptual phases with focus on Post-processing (Phase 7)
"""

import flopy
import numpy as np
from pathlib import Path
from flopy.utils.gridutil import get_disv_kwargs

def build_model(ws="./model_output", name="rev_disv"):
    """
    Build a simple MODFLOW 6 model with vertex grid for demonstrating 
    binary file reversal post-processing.
    """
    
    # Ensure workspace exists
    Path(ws).mkdir(exist_ok=True)
    
    # ========================================
    # PHASE 1: DISCRETIZATION
    # ========================================
    print("Phase 1: Setting up discretization...")
    
    # Create simulation
    sim = flopy.mf6.MFSimulation(sim_name=name, sim_ws=ws, exe_name="/home/danilopezmella/flopy_expert/bin/mf6")
    
    # Time discretization - symmetric for simplicity
    tdis = flopy.mf6.ModflowTdis(
        sim, 
        nper=3,
        perioddata=[
            (1.0, 1, 1.0),  # Period 1: 1 day
            (1.0, 1, 1.0),  # Period 2: 1 day
            (1.0, 1, 1.0),  # Period 3: 1 day
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
    
    # Vertex discretization (DISV)
    # Using helper function to create vertex grid
    nlay = 2
    nrow = 10
    ncol = 10
    delr = 1.0
    delc = 1.0
    top = 25.0
    botm = [20.0, 15.0]
    
    # get_disv_kwargs requires tp and botm parameters
    disv_kwargs = get_disv_kwargs(
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        delr=delr,
        delc=delc,
        tp=top,  # top parameter
        botm=botm  # bottom elevations
    )
    
    dis = flopy.mf6.ModflowGwfdisv(gwf, **disv_kwargs)
    
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
    
    # Initial conditions
    ic = flopy.mf6.ModflowGwfic(gwf, strt=1.0)
    
    # ========================================
    # PHASE 4: BOUNDARY CONDITIONS
    # ========================================
    print("Phase 4: Setting boundary conditions...")
    
    # Constant head boundaries
    # Note: For DISV, we use cell IDs instead of (layer, row, col)
    chd = flopy.mf6.ModflowGwfchd(
        gwf,
        stress_period_data=[
            [(0, 0), 1.0],   # First cell, layer 0
            [(0, 99), 0.0],  # Last cell, layer 0
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
    
    # Load and reverse files
    print("\n1. Processing head file...")
    hf = HeadFile(head_file_path)
    orig_times = hf.get_times()
    print(f"   Original times: {orig_times}")
    
    # Reverse
    rev_head_path = ws / f"{head_file_path.stem}_reversed.hds"
    hf.reverse(filename=rev_head_path)
    hf_rev = HeadFile(rev_head_path)
    rev_times = hf_rev.get_times()
    print(f"   Reversed times: {rev_times}")
    
    print("\n2. Processing budget file...")
    bf = CellBudgetFile(budget_file_path)
    rev_budget_path = ws / f"{budget_file_path.stem}_reversed.cbb"
    bf.reverse(rev_budget_path)
    print(f"   Budget reversed (with value negation)")
    
    print("\n" + "="*50)
    print("DISV model with binary reversal complete!")
    print("="*50)

def run_model():
    """Run the model and demonstrate binary file reversal"""
    
    print("="*60)
    print("MODFLOW 6 Binary File Reversal Demonstration (DISV)")
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
    
    # Demonstrate reversal
    demonstrate_reversal(sim, gwf)
    
    return sim, gwf

if __name__ == "__main__":
    run_model()