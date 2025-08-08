#!/usr/bin/env python3
"""
Demonstrate get_modflow utility and run a simple model
Shows how to use existing executables and create a working model
"""
import os
import sys
from pathlib import Path
from platform import system
import flopy
import numpy as np

def demo_get_modflow():
    """Example demonstrating MODFLOW executable management and usage."""
    
    # Phase 7: Post-processing and Utilities
    print("=== MODFLOW Executable Management Demo ===")
    print(f"Platform: {system()}")
    print(f"Python version: {sys.version}")
    print(f"FloPy version: {flopy.__version__}")
    
    # Show existing executables
    bindir = Path("/home/danilopezmella/flopy_expert/bin")
    print(f"\nExisting MODFLOW executables in {bindir}:")
    
    executables = {
        'mf6': 'MODFLOW 6',
        'mf2005': 'MODFLOW-2005', 
        'mfnwt': 'MODFLOW-NWT',
        'mfusg': 'MODFLOW-USG',
        'mt3dms': 'MT3DMS',
        'mt3dusgs': 'MT3D-USGS',
        'gridgen': 'Gridgen',
        'triangle': 'Triangle mesh generator',
        'zonbud3': 'Zone budget utility'
    }
    
    available = []
    for exe, desc in executables.items():
        exe_path = bindir / exe
        if exe_path.exists():
            available.append(exe)
            print(f"  ✓ {exe:12} - {desc}")
    
    print(f"\nFound {len(available)} executables")
    
    # Demonstrate using MODFLOW 6
    print("\n=== Creating and Running a Simple MODFLOW 6 Model ===")
    
    # Create workspace
    ws = Path("./mf6_example")
    ws.mkdir(exist_ok=True)
    
    # Phase 1: Create simulation
    print("\nPhase 1: Creating simulation...")
    sim = flopy.mf6.MFSimulation(
        sim_name='demo',
        sim_ws=str(ws),
        exe_name=str(bindir / 'mf6')
    )
    
    # Time discretization
    tdis = flopy.mf6.ModflowTdis(sim, nper=1, perioddata=[(1.0, 1, 1.0)])
    
    # Solver
    ims = flopy.mf6.ModflowIms(sim, complexity='simple')
    sim.register_ims_package(ims, ['model'])
    
    # Phase 2: Create groundwater flow model
    print("Phase 2: Creating groundwater flow model...")
    gwf = flopy.mf6.ModflowGwf(sim, modelname='model', save_flows=True)
    
    # Phase 3: Discretization
    print("Phase 3: Setting up discretization...")
    dis = flopy.mf6.ModflowGwfdis(
        gwf,
        nlay=1,
        nrow=10,
        ncol=10,
        delr=100.0,
        delc=100.0,
        top=10.0,
        botm=0.0
    )
    
    # Phase 4: Flow properties
    print("Phase 4: Setting flow properties...")
    npf = flopy.mf6.ModflowGwfnpf(gwf, icelltype=0, k=10.0)
    
    # Phase 5: Initial conditions
    print("Phase 5: Setting initial conditions...")
    ic = flopy.mf6.ModflowGwfic(gwf, strt=10.0)
    
    # Phase 6: Boundary conditions
    print("Phase 6: Adding boundary conditions...")
    # Add constant head boundaries
    chd_data = [
        [(0, 0, 0), 10.0],
        [(0, 9, 9), 5.0]
    ]
    chd = flopy.mf6.ModflowGwfchd(gwf, stress_period_data=chd_data)
    
    # Add a pumping well
    wel_data = [[(0, 5, 5), -100.0]]
    wel = flopy.mf6.ModflowGwfwel(gwf, stress_period_data=wel_data)
    
    # Output control
    oc = flopy.mf6.ModflowGwfoc(
        gwf,
        head_filerecord='model.hds',
        budget_filerecord='model.cbc',
        saverecord=[('HEAD', 'ALL'), ('BUDGET', 'ALL')]
    )
    
    # Write and run
    print("\nWriting model files...")
    sim.write_simulation()
    
    print("Running model...")
    success, buff = sim.run_simulation(silent=True)
    
    if success:
        print("✓ Model ran successfully!")
        
        # Phase 7: Post-processing
        print("\nPhase 7: Post-processing results...")
        head = gwf.output.head().get_data()
        budget = gwf.output.budget()
        
        print(f"  Head array shape: {head.shape}")
        print(f"  Min head: {head.min():.2f} m")
        print(f"  Max head: {head.max():.2f} m")
        print(f"  Mean head: {head.mean():.2f} m")
        
        # Get budget terms
        budget_records = budget.get_unique_record_names()
        print(f"\n  Available budget terms: {len(budget_records)}")
        for rec in budget_records[:3]:  # Show first 3
            print(f"    - {rec}")
    else:
        print("✗ Model failed to run")
    
    # Demonstrate MODFLOW-2005
    print("\n=== Creating a Simple MODFLOW-2005 Model ===")
    
    ws2005 = Path("./mf2005_example")
    ws2005.mkdir(exist_ok=True)
    
    # Create MODFLOW-2005 model
    mf = flopy.modflow.Modflow(
        modelname='demo2005',
        model_ws=str(ws2005),
        exe_name=str(bindir / 'mf2005')
    )
    
    # Discretization
    dis = flopy.modflow.ModflowDis(
        mf,
        nlay=1,
        nrow=10,
        ncol=10,
        delr=100.0,
        delc=100.0,
        top=10.0,
        botm=0.0
    )
    
    # Basic package
    bas = flopy.modflow.ModflowBas(mf, ibound=1, strt=10.0)
    
    # LPF package
    lpf = flopy.modflow.ModflowLpf(mf, hk=10.0)
    
    # Well package
    wel = flopy.modflow.ModflowWel(mf, stress_period_data={0: [[0, 5, 5, -100.0]]})
    
    # CHD package
    chd = flopy.modflow.ModflowChd(
        mf,
        stress_period_data={0: [[0, 0, 0, 10.0, 10.0], [0, 9, 9, 5.0, 5.0]]}
    )
    
    # PCG solver
    pcg = flopy.modflow.ModflowPcg(mf)
    
    # Output control
    oc = flopy.modflow.ModflowOc(mf)
    
    # Write and run
    print("Writing MODFLOW-2005 files...")
    mf.write_input()
    # Run the model
    success, buff = mf.run_model(silent=True)
    if success:
        print("  ✓ Model ran successfully")
        # Check for output files
        if os.path.exists(os.path.join(model_ws, f"{model_name}.hds")):
            print("  ✓ Head file created")
    else:
        print("  ⚠ Model failed to run")