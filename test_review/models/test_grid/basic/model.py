#!/usr/bin/env python3
"""
Grid Demonstration - Structured and Vertex Grids
Shows different grid types and their properties in MODFLOW 6
"""

import numpy as np
import flopy
from pathlib import Path

# Phase 1: Create MODFLOW 6 model with structured grid
print("=== Phase 1: Structured Grid (DIS) ===")
sim_ws = Path("model_output")
sim_ws.mkdir(exist_ok=True)

# Create simulation
sim = flopy.mf6.MFSimulation(
    sim_name="grid_demo",
    sim_ws=str(sim_ws),
    exe_name="/home/danilopezmella/flopy_expert/bin/mf6"
)

# Time discretization
tdis = flopy.mf6.ModflowTdis(sim, nper=1, perioddata=[(1.0, 1, 1.0)])

# Solver
ims = flopy.mf6.ModflowIms(sim, complexity="simple")
sim.register_ims_package(ims, ["model"])

# Create groundwater flow model
gwf = flopy.mf6.ModflowGwf(sim, modelname="model", save_flows=True)

# Structured grid discretization
nlay, nrow, ncol = 2, 10, 10
delr = delc = 100.0
top = 10.0
botm = [5.0, 0.0]

dis = flopy.mf6.ModflowGwfdis(
    gwf,
    nlay=nlay,
    nrow=nrow, 
    ncol=ncol,
    delr=delr,
    delc=delc,
    top=top,
    botm=botm
)

# Phase 2: Flow properties
npf = flopy.mf6.ModflowGwfnpf(gwf, icelltype=0, k=10.0)

# Phase 3: Initial conditions
ic = flopy.mf6.ModflowGwfic(gwf, strt=10.0)

# Phase 4: Boundary conditions - simple CHD
chd_data = [
    [(0, 0, 0), 10.0],
    [(0, nrow-1, ncol-1), 5.0]
]
chd = flopy.mf6.ModflowGwfchd(gwf, stress_period_data=chd_data)

# Phase 5: Output control
oc = flopy.mf6.ModflowGwfoc(
    gwf,
    head_filerecord="model.hds",
    budget_filerecord="model.cbc",
    saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")]
)

# Display grid properties
print(f"\nStructured Grid Properties:")
print(f"  Layers: {nlay}")
print(f"  Rows: {nrow}")
print(f"  Columns: {ncol}")
print(f"  Total cells: {nlay * nrow * ncol}")
print(f"  Cell size: {delr} x {delc} m")

# Phase 6: Write and run
print("\n=== Phase 6: Running Model ===")
sim.write_simulation()
success, buff = sim.run_simulation(silent=True)

if success:
    print("✓ Model ran successfully!")
    
    # Phase 7: Post-processing
    print("\n=== Phase 7: Grid Analysis ===")
    
    # Get the modelgrid object
    modelgrid = gwf.modelgrid
    
    # Grid properties
    print(f"\nGrid type: {modelgrid.grid_type}")
    print(f"Grid shape: {modelgrid.shape}")
    print(f"Number of cells: {modelgrid.nnodes}")
    print(f"Cell centers shape: {modelgrid.xyzcellcenters[0].shape}")
    
    # Example cell centers (first 3 cells)
    print("\nExample cell centers (X, Y):")
    for i in range(min(3, ncol)):
        x = modelgrid.xyzcellcenters[0][0, i]
        y = modelgrid.xyzcellcenters[1][0, i]
        print(f"  Cell (0,{i}): ({x:.1f}, {y:.1f})")
    
    # Get heads
    head_file = gwf.output.head()
    head = head_file.get_data()
    
    print(f"\nHead array shape: {head.shape}")
    print(f"Head range: {head.min():.2f} to {head.max():.2f} m")
    
    # Example: Get extent for plotting
    extent = modelgrid.extent
    print(f"\nModel extent (xmin, xmax, ymin, ymax): {extent}")
    
else:
    print("✗ Model failed to run")

print("\n=== Grid Demo Complete ===")