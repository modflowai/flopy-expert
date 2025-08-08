#!/usr/bin/env python3
"""
Standalone FloPy model demonstrating binary grid file operations
Extracted from: test_binarygrid_util.py

Demonstrates Phase 1: Discretization with focus on binary grid files
"""

import flopy
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import sys
sys.path.append('/home/danilopezmella/flopy_expert/test_review')
from mf6_config import get_mf6_exe

def create_structured_model(ws="./model_output/structured", name="grid_dis_demo"):
    """
    Create a model with structured grid and demonstrate .grb file operations
    """
    
    Path(ws).mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*60)
    print("STRUCTURED GRID (DIS) DEMONSTRATION")
    print("="*60)
    
    # ========================================
    # PHASE 1: DISCRETIZATION
    # ========================================
    print("\nPhase 1: Creating structured discretization...")
    
    # Create simulation
    sim = flopy.mf6.MFSimulation(
        sim_name=name,
        sim_ws=ws,
        exe_name=get_mf6_exe()
    )
    
    # Time discretization
    tdis = flopy.mf6.ModflowTdis(sim, nper=1, perioddata=[(1.0, 1, 1.0)])
    
    # Solver
    ims = flopy.mf6.ModflowIms(sim, print_option="SUMMARY")
    
    # Create groundwater flow model
    gwf = flopy.mf6.ModflowGwf(sim, modelname=name, save_flows=True)
    
    # Structured discretization with varying layer thickness
    dis = flopy.mf6.ModflowGwfdis(
        gwf,
        nlay=3,
        nrow=20,
        ncol=25,
        delr=100.0,  # 100m cells
        delc=100.0,
        top=50.0,
        botm=[20.0, 0.0, -30.0],
        idomain=1  # All cells active
    )
    
    # Simple flow packages for completeness
    npf = flopy.mf6.ModflowGwfnpf(gwf, save_specific_discharge=True, icelltype=0, k=10.0)
    ic = flopy.mf6.ModflowGwfic(gwf, strt=30.0)
    
    # Boundary conditions
    chd = flopy.mf6.ModflowGwfchd(
        gwf,
        stress_period_data=[
            [(0, 0, 0), 35.0],
            [(2, 19, 24), 25.0]
        ]
    )
    
    # Output control
    oc = flopy.mf6.ModflowGwfoc(
        gwf,
        head_filerecord=f"{name}.hds",
        budget_filerecord=f"{name}.cbb",
        saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")]
    )
    
    return sim, gwf

def create_vertex_model(ws="./model_output/vertex", name="grid_disv_demo"):
    """
    Create a model with vertex grid and demonstrate .grb file operations
    """
    
    Path(ws).mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*60)
    print("VERTEX GRID (DISV) DEMONSTRATION")
    print("="*60)
    
    # ========================================
    # PHASE 1: DISCRETIZATION
    # ========================================
    print("\nPhase 1: Creating vertex discretization...")
    
    # Create simulation  
    sim = flopy.mf6.MFSimulation(
        sim_name=name,
        sim_ws=ws,
        exe_name=get_mf6_exe()
    )
    
    # Time discretization
    tdis = flopy.mf6.ModflowTdis(sim, nper=1, perioddata=[(1.0, 1, 1.0)])
    
    # Solver
    ims = flopy.mf6.ModflowIms(sim, print_option="SUMMARY")
    
    # Create groundwater flow model
    gwf = flopy.mf6.ModflowGwf(sim, modelname=name, save_flows=True)
    
    # Create a simple rectangular vertex grid manually
    # 5x5 grid for simplicity
    nrow, ncol = 5, 5
    delr, delc = 100.0, 100.0
    ncpl = nrow * ncol  # cells per layer
    nvert = (nrow + 1) * (ncol + 1)  # vertices
    
    # Create vertices (need vertex id, x, y)
    vertices = []
    iv = 0
    for i in range(nrow + 1):
        for j in range(ncol + 1):
            x = j * delr
            y = (nrow - i) * delc
            vertices.append([iv, x, y])
            iv += 1
    
    # Create cell2d (cell definitions)
    cell2d = []
    for i in range(nrow):
        for j in range(ncol):
            icell = i * ncol + j
            # Vertices for this cell (counterclockwise)
            iv1 = i * (ncol + 1) + j
            iv2 = iv1 + 1
            iv3 = (i + 1) * (ncol + 1) + j + 1
            iv4 = iv3 - 1
            xc = (j + 0.5) * delr
            yc = (nrow - i - 0.5) * delc
            cell2d.append([icell, xc, yc, 4, iv1, iv2, iv3, iv4])
    
    # Vertex discretization
    disv = flopy.mf6.ModflowGwfdisv(
        gwf,
        nlay=2,
        ncpl=ncpl,
        nvert=nvert,
        top=10.0,
        botm=[-10.0, -30.0],
        vertices=vertices,
        cell2d=cell2d
    )
    
    # Simple flow packages
    npf = flopy.mf6.ModflowGwfnpf(gwf, save_specific_discharge=True, icelltype=0, k=5.0)
    ic = flopy.mf6.ModflowGwfic(gwf, strt=5.0)
    
    # Boundary conditions (for DISV, use layer and cell index)
    chd = flopy.mf6.ModflowGwfchd(
        gwf,
        stress_period_data=[
            [(0, 0), 8.0],      # Layer 0, cell 0
            [(1, ncpl-1), 2.0]  # Layer 1, last cell
        ]
    )
    
    # Output control
    oc = flopy.mf6.ModflowGwfoc(
        gwf,
        head_filerecord=f"{name}.hds",
        budget_filerecord=f"{name}.cbb",
        saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")]
    )
    
    return sim, gwf

def demonstrate_grid_operations(sim, gwf, grid_type="structured"):
    """
    Demonstrate binary grid file operations
    """
    
    print(f"\n" + "="*60)
    print(f"BINARY GRID FILE OPERATIONS - {grid_type.upper()}")
    print("="*60)
    
    from flopy.mf6.utils import MfGrdFile
    
    ws = Path(sim.sim_path)
    
    # After running, read the binary grid file
    grb_file = ws / f"{gwf.name}.dis.grb" if grid_type == "structured" else ws / f"{gwf.name}.disv.grb"
    
    if grb_file.exists():
        print(f"\n1. Reading binary grid file: {grb_file.name}")
        
        # Read with MfGrdFile
        grb = MfGrdFile(grb_file, verbose=False)
        
        # Get grid properties
        print(f"   Nodes: {grb.nodes}")
        print(f"   Model grid type: {type(grb.modelgrid).__name__}")
        
        # Get connectivity arrays
        ia = grb.ia
        ja = grb.ja
        print(f"   IA array shape: {ia.shape}")
        print(f"   JA array shape: {ja.shape}")
        print(f"   Number of connections (nnz): {ia[-1]}")
        
        # Get modelgrid object
        mg = grb.modelgrid
        
        # Grid properties
        print(f"\n2. Grid properties:")
        print(f"   Grid extent: {mg.extent}")
        
        if hasattr(mg, 'ncpl'):
            print(f"   Cells per layer: {mg.ncpl}")
        
        if grid_type == "structured":
            print(f"   Rows: {mg.nrow}, Columns: {mg.ncol}, Layers: {mg.nlay}")
        else:
            print(f"   Number of vertices: {mg.nvert}")
            print(f"   Number of cells: {len(mg.iverts)}")
        
        # Plot the grid
        print(f"\n3. Plotting grid...")
        fig, ax = plt.subplots(figsize=(10, 8))
        mg.plot(ax=ax)
        ax.set_title(f"{grid_type.title()} Grid Visualization")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")
        plt.tight_layout()
        
        # Save plot
        plot_file = ws / f"{gwf.name}_grid.png"
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        print(f"   Grid plot saved to: {plot_file.name}")
        plt.close()
        
        # Get cell centers
        print(f"\n4. Cell center coordinates:")
        if grid_type == "structured":
            xc, yc = mg.xyzcellcenters[0], mg.xyzcellcenters[1]
            print(f"   X centers shape: {xc.shape}")
            print(f"   Y centers shape: {yc.shape}")
            print(f"   Center of cell (0,0): ({xc[0,0]:.1f}, {yc[0,0]:.1f})")
        else:
            cellxy = np.column_stack(mg.xyzcellcenters[:2])
            print(f"   Cell centers shape: {cellxy.shape}")
            print(f"   Center of cell 0: ({cellxy[0,0]:.1f}, {cellxy[0,1]:.1f})")
        
        # Vertices information
        if hasattr(mg, 'verts'):
            print(f"\n5. Vertices information:")
            verts = mg.verts
            print(f"   Total vertices: {len(verts)}")
            print(f"   First vertex: {verts[0]}")
            print(f"   Last vertex: {verts[-1]}")
    
    else:
        print(f"\nNote: Binary grid file will be created when model runs.")

def run_demonstrations():
    """Run all grid type demonstrations"""
    
    print("="*70)
    print("MODFLOW 6 BINARY GRID FILE DEMONSTRATIONS")
    print("="*70)
    
    # Structured grid demonstration
    print("\n" + "-"*70)
    print("PART 1: STRUCTURED GRID (DIS)")
    print("-"*70)
    
    sim_dis, gwf_dis = create_structured_model()
    print("\nWriting and running structured model...")
    sim_dis.write_simulation()
    success, _ = sim_dis.run_simulation()
    
    if success:
        print("✓ Structured model ran successfully!")
        demonstrate_grid_operations(sim_dis, gwf_dis, "structured")
    else:
        print("✗ Structured model failed to run")
    
    # Vertex grid demonstration
    print("\n" + "-"*70)
    print("PART 2: VERTEX GRID (DISV)")
    print("-"*70)
    
    sim_disv, gwf_disv = create_vertex_model()
    print("\nWriting and running vertex model...")
    sim_disv.write_simulation()
    success, _ = sim_disv.run_simulation()
    
    if success:
        print("✓ Vertex model ran successfully!")
        demonstrate_grid_operations(sim_disv, gwf_disv, "vertex")
    else:
        print("✗ Vertex model failed to run")
    
    print("\n" + "="*70)
    print("Binary grid file demonstrations complete!")
    print("Created models with DIS and DISV discretizations")
    print("Demonstrated reading .grb files and accessing grid properties")
    print("="*70)

if __name__ == "__main__":
    run_demonstrations()