import os
import numpy as np
import flopy
from flopy.mf6 import MFSimulation, ModflowGwf, ModflowGwfdisu, ModflowGwfic
from flopy.mf6 import ModflowGwfnpf, ModflowGwfchd, ModflowGwfoc, ModflowIms, ModflowTdis
from flopy.modflow import Modflow, ModflowDis
from flopy.utils.gridgen import Gridgen
from flopy.export import vtk

# Setup workspace
workspace = 'model_output'
if not os.path.exists(workspace):
    os.makedirs(workspace)

# Create base structured grid for gridgen
Lx = 1000.0
Ly = 1000.0
nlay = 2
nrow = 10
ncol = 10
delr = Lx / ncol
delc = Ly / nrow
top = 100.0
botm = [50.0, 0.0]

# Create temporary MODFLOW-2005 model for gridgen
ml = Modflow()
dis = ModflowDis(
    ml,
    nlay=nlay,
    nrow=nrow,
    ncol=ncol,
    delr=delr,
    delc=delc,
    top=top,
    botm=botm
)

# Use gridgen to create unstructured grid with refinement
g = Gridgen(ml.modelgrid, model_ws=workspace, exe_name='/home/danilopezmella/flopy_expert/bin/gridgen')

# Add refinement in center of model
xmin = 3 * delr
xmax = 7 * delr
ymin = 3 * delc
ymax = 7 * delc
rfpoly = [[[(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax), (xmin, ymin)]]]
g.add_refinement_features(rfpoly, 'polygon', 2, [0, 1])
g.build(verbose=False)

# Get DISU properties
gridprops = g.get_gridprops_disu6()

# Phase 1: Create MODFLOW 6 simulation
sim = MFSimulation(sim_name='unstructured_export', sim_ws=workspace, exe_name='/home/danilopezmella/flopy_expert/bin/mf6')
tdis = ModflowTdis(sim, time_units='DAYS', nper=1, perioddata=[(1.0, 1, 1.0)])
ims = ModflowIms(sim, print_option='SUMMARY')

# Create GWF model
gwf = ModflowGwf(sim, modelname='model', save_flows=True)

# DISU package
disu = ModflowGwfdisu(gwf, **gridprops)

# Phase 2: Flow properties
nnodes = gwf.modelgrid.nnodes
k = np.random.uniform(1.0, 20.0, nnodes)
npf = ModflowGwfnpf(gwf, k=k)

# Phase 3: Initial conditions
strt = np.full(nnodes, 95.0)
ic = ModflowGwfic(gwf, strt=strt)

# Phase 4: Boundary conditions
# Add CHD to edges
chd_cells = []
for node in range(nnodes):
    x, y = gwf.modelgrid.xcellcenters[node], gwf.modelgrid.ycellcenters[node]
    if x < 10 or x > Lx - 10:
        chd_cells.append([(0, node), 95.0 - (x / Lx) * 5.0])
    elif y < 10 or y > Ly - 10:
        chd_cells.append([(0, node), 95.0 - (y / Ly) * 5.0])

if chd_cells:
    chd = ModflowGwfchd(gwf, stress_period_data=chd_cells)

# Phase 5: Output control
oc = ModflowGwfoc(
    gwf,
    budget_filerecord='model.bud',
    head_filerecord='model.hds',
    saverecord=[('HEAD', 'ALL'), ('BUDGET', 'ALL')]
)

# Write and run simulation
sim.write_simulation()
print('Running simulation...')
success, buff = sim.run_simulation(silent=True)

# Phase 7: Export to various formats
print('\nExporting to VTK...')
vtk_path = os.path.join(workspace, 'unstructured.vtu')
vtkobj = vtk.Vtk(gwf, xml=True)
vtkobj.add_array(k, 'hydraulic_conductivity')
vtkobj.add_array(strt, 'starting_head')

# Add cell IDs for visualization
cell_ids = np.arange(nnodes)
vtkobj.add_array(cell_ids, 'cell_id')

vtkobj.write(vtk_path)
print(f'VTK file written to: {vtk_path}')

# Export grid to shapefile
print('\nExporting grid to shapefile...')
shp_path = os.path.join(workspace, 'unstructured_grid.shp')
gwf.modelgrid.write_shapefile(shp_path)
print(f'Shapefile written to: {shp_path}')

# Export model properties
print('\nModel grid summary:')
print(f'  Grid type: {gwf.modelgrid.grid_type}')
print(f'  Number of nodes: {gwf.modelgrid.nnodes}')
print(f'  Number of layers: {gwf.modelgrid.nlay}')
print(f'  Refined cells: {nnodes - nrow * ncol * nlay}')

print('\nExport complete!')

if __name__ == "__main__":
    # Run the model
    pass  # Model execution added
