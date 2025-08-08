#!/usr/bin/env python3
"""
Test version that only builds the model without running MODFLOW
"""

import flopy
import numpy as np
from pathlib import Path

def build_model(ws="./model_output", name="reverse_demo_dis"):
    """
    Build a simple MODFLOW 6 model with structured grid for demonstrating 
    binary file reversal post-processing.
    """
    
    # Ensure workspace exists
    Path(ws).mkdir(exist_ok=True)
    
    print("Phase 1: Setting up discretization...")
    
    # Create simulation
    sim = flopy.mf6.MFSimulation(sim_name=name, sim_ws=ws, exe_name="mf6")
    
    # Time discretization - 3 stress periods with different configurations
    tdis = flopy.mf6.ModflowTdis(
        sim, 
        nper=3,
        perioddata=[
            (1.0, 2, 1.0),  # Period 1: 1 day, 2 steps (0.5 day each)
            (1.0, 1, 1.0),  # Period 2: 1 day, 1 step
            (1.0, 1, 1.0),  # Period 3: 1 day, 1 step
        ]
    )
    
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
    
    print("Phase 2: Setting hydraulic properties...")
    
    # Node Property Flow package
    npf = flopy.mf6.ModflowGwfnpf(
        gwf,
        save_specific_discharge=True,
        icelltype=0,  # Confined
        k=10.0        # Hydraulic conductivity
    )
    
    print("Phase 3: Setting initial conditions...")
    
    # Initial conditions - gradient from left to right
    ic = flopy.mf6.ModflowGwfic(gwf, strt=1.0)
    
    print("Phase 4: Setting boundary conditions...")
    
    # Constant head boundaries
    chd = flopy.mf6.ModflowGwfchd(
        gwf,
        stress_period_data=[
            [(0, 0, 0), 1.0],  # Upper-left corner
            [(0, 9, 9), 0.0],  # Lower-right corner
        ]
    )
    
    print("Setting up output control...")
    
    oc = flopy.mf6.ModflowGwfoc(
        gwf,
        budget_filerecord=f"{name}.bud",
        head_filerecord=f"{name}.hds",
        saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")]
    )
    
    return sim, gwf

def test_model():
    """Test model building without running MODFLOW"""
    
    print("="*60)
    print("MODFLOW 6 Model Building Test (DIS)")
    print("="*60 + "\n")
    
    # Build model
    sim, gwf = build_model()
    
    # Write files
    print("\nWriting simulation files...")
    sim.write_simulation()
    
    print("✓ Model built and written successfully!")
    print("\nFiles created in ./model_output/")
    
    # List created files
    ws = Path(sim.sim_path)
    files = list(ws.glob("*"))
    print(f"Created {len(files)} files:")
    for f in sorted(files)[:10]:
        print(f"  - {f.name}")
    
    return sim, gwf

if __name__ == "__main__":
    test_model()