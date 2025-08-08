#!/usr/bin/env python3
"""
Vertex Grid (DISV) Model with Rotation and Origin Offset

This example demonstrates how to create an unstructured vertex discretization (DISV)
grid with custom origin coordinates and rotation angle in MODFLOW 6.
"""

import numpy as np
from pathlib import Path
from flopy.mf6 import MFSimulation, ModflowGwf, ModflowGwfdisv, ModflowIms
from flopy.mf6.modflow import ModflowGwfnpf, ModflowGwfic, ModflowGwfchd, ModflowGwfoc

def create_vertex_grid_model(workspace='.'):
    """Create a MODFLOW 6 model with vertex DISV grid"""
    
    # Phase 1: Create simulation and solver
    sim = MFSimulation(sim_name='disv_model', sim_ws=workspace, exe_name='/home/danilopezmella/flopy_expert/bin/mf6')
    
    # Create time discretization (required for simulation)
    from flopy.mf6 import ModflowTdis
    tdis_data = [(1.0, 1, 1.0)]  # One stress period, 1 day
    tdis = ModflowTdis(sim, nper=1, perioddata=tdis_data)
    
    # Create IMS solver
    ims = ModflowIms(sim, complexity='simple', outer_maximum=100, inner_maximum=100)
    sim.register_ims_package(ims, ['disv_model'])
    
    # Create groundwater flow model
    gwf = ModflowGwf(sim, modelname='disv_model', save_flows=True)
    
    # Phase 1: Create vertex grid geometry
    nrow, ncol = 21, 20
    delr, delc = 500.0, 500.0
    ncpl = nrow * ncol  # Number of cells per layer
    
    # Create vertex coordinates
    xv = np.linspace(0, delr * ncol, ncol + 1)
    yv = np.linspace(delc * nrow, 0, nrow + 1)
    xv, yv = np.meshgrid(xv, yv)
    xv = xv.ravel()
    yv = yv.ravel()
    
    # Function to get vertex list for a cell
    def get_vlist(i, j, nrow, ncol):
        v1 = i * (ncol + 1) + j
        v2 = v1 + 1
        v3 = v2 + ncol + 1
        v4 = v3 - 1
        return [v1, v2, v3, v4]
    
    # Create cell-to-vertex connectivity
    iverts = []
    for i in range(nrow):
        for j in range(ncol):
            iverts.append(get_vlist(i, j, nrow, ncol))
    
    nvert = xv.shape[0]  # Number of vertices
    verts = np.hstack((xv.reshape(nvert, 1), yv.reshape(nvert, 1)))
    
    # Calculate cell centers
    cellxy = np.empty((ncpl, 2))
    for icpl in range(ncpl):
        iv = iverts[icpl]
        cellxy[icpl, 0] = (xv[iv[0]] + xv[iv[1]]) / 2.0
        cellxy[icpl, 1] = (yv[iv[1]] + yv[iv[2]]) / 2.0
    
    # Create cell2d list: [icpl, xc, yc, nv, iv1, iv2, iv3, iv4]
    cell2d = [
        [icpl, cellxy[icpl, 0], cellxy[icpl, 1], 4] + iverts[icpl]
        for icpl in range(ncpl)
    ]
    
    # Create vertices list: [ivert, x, y]
    vertices = [[ivert, verts[ivert, 0], verts[ivert, 1]] for ivert in range(nvert)]
    
    # Grid transformation parameters
    xorigin = 3000
    yorigin = 1000
    angrot = 10
    
    # Create DISV package
    disv = ModflowGwfdisv(
        gwf,
        nlay=3,           # 3 layers
        ncpl=ncpl,        # Cells per layer
        top=400.0,        # Top elevation
        botm=[220.0, 200.0, 0.0],  # Bottom elevations for 3 layers
        nvert=nvert,      # Number of vertices
        vertices=vertices,
        cell2d=cell2d,
        xorigin=xorigin,  # X-coordinate origin offset
        yorigin=yorigin,  # Y-coordinate origin offset
        angrot=angrot,    # Grid rotation angle (degrees)
    )
    
    # Set coordinate info on modelgrid
    gwf.modelgrid.set_coord_info(xoff=xorigin, yoff=yorigin, angrot=angrot)
    
    # Phase 2: Flow properties (NPF)
    npf = ModflowGwfnpf(
        gwf,
        save_specific_discharge=True,
        icelltype=0,      # Confined
        k=10.0,           # Hydraulic conductivity
    )
    
    # Phase 3: Initial conditions
    ic = ModflowGwfic(gwf, strt=350.0)  # Initial head = 350 m
    
    # Phase 4: Boundary conditions (CHD on edges)
    # Create CHD on left and right boundaries
    chd_data = []
    for k in range(3):  # For each layer
        for i in range(nrow):  # For each row
            # Left boundary (first column cells)
            cell_id = i * ncol  # First cell in row
            chd_data.append([(k, cell_id), 350.0])
            # Right boundary (last column cells)
            cell_id = i * ncol + (ncol - 1)  # Last cell in row
            chd_data.append([(k, cell_id), 340.0])
    
    chd = ModflowGwfchd(gwf, stress_period_data=chd_data)
    
    # Phase 5: Output control
    oc = ModflowGwfoc(
        gwf,
        budget_filerecord='disv_model.cbc',
        head_filerecord='disv_model.hds',
        saverecord=[('HEAD', 'ALL'), ('BUDGET', 'ALL')]
    )
    
    return sim, gwf

if __name__ == '__main__':
    # Create workspace
    workspace = Path('disv_model')
    workspace.mkdir(exist_ok=True)
    
    # Build and run the model
    sim, gwf = create_vertex_grid_model(workspace)
    
    # Write and run
    sim.write_simulation()
    success, buff = sim.run_simulation()
    
    # Verify grid properties
    print(f"\nVertex Grid (DISV) Model:")
    print(f"Number of layers: {gwf.disv.nlay.get_data()}")
    print(f"Cells per layer: {gwf.disv.ncpl.get_data()}")
    print(f"Number of vertices: {gwf.disv.nvert.get_data()}")
    print(f"Grid origin: X={gwf.disv.xorigin.get_data()}, Y={gwf.disv.yorigin.get_data()}")
    print(f"Grid rotation: {gwf.disv.angrot.get_data()} degrees")
    
    if success:
        print("\nModel ran successfully!")
    else:
        print("\nModel failed to run")