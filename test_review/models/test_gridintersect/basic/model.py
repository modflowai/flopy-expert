import numpy as np
import flopy.discretization as fgrid
from flopy.utils.gridintersect import GridIntersect

# Phase 1: Create vertex grid (triangular mesh) discretization
print('Phase 1: Creating triangular vertex grid')

# Define triangular mesh manually (8 triangular cells)
cell2d = [
    [0, 16.666666666666668, 13.333333333333334, 3, 4, 2, 7],
    [1, 3.3333333333333335, 6.666666666666667, 3, 4, 0, 5],
    [2, 6.666666666666667, 16.666666666666668, 3, 1, 8, 4],
    [3, 3.3333333333333335, 13.333333333333334, 3, 5, 1, 4],
    [4, 6.666666666666667, 3.3333333333333335, 3, 6, 0, 4],
    [5, 13.333333333333334, 3.3333333333333335, 3, 4, 3, 6],
    [6, 16.666666666666668, 6.666666666666667, 3, 7, 3, 4],
    [7, 13.333333333333334, 16.666666666666668, 3, 8, 2, 4]
]

vertices = [
    [0, 0.0, 0.0],
    [1, 0.0, 20.0],
    [2, 20.0, 20.0],
    [3, 20.0, 0.0],
    [4, 10.0, 10.0],
    [5, 0.0, 10.0],
    [6, 10.0, 0.0],
    [7, 20.0, 10.0],
    [8, 10.0, 20.0]
]

# Create vertex grid
tgr = fgrid.VertexGrid(
    vertices,
    cell2d,
    botm=np.atleast_2d(np.zeros(len(cell2d))),
    top=np.ones(len(cell2d))
)

# Create grid intersect object
ix = GridIntersect(tgr, method='vertex')

# Test point intersection
print('\nTesting point intersection:')
point = (10, 10)  # Center point
result = ix.intersect(point, shapetype='point')
if result:
    print(f'Point {point} intersects cell: {result.cellids[0]}')

# Test line intersection
print('\nTesting line intersection:')
line = [(0, 0), (20, 20)]  # Diagonal line
result = ix.intersect(line, shapetype='linestring')
if result is not None and len(result) > 0:
    print(f'Line intersects {len(result.cellids)} cells')
    print(f'Cell IDs: {result.cellids}')
    print(f'Intersection lengths: {result.lengths}')

# Test polygon intersection
print('\nTesting polygon intersection:')
from shapely.geometry import Polygon
polygon = Polygon([(5, 5), (15, 5), (15, 15), (5, 15), (5, 5)])  # Central square
result = ix.intersect(polygon)
if result is not None and len(result) > 0:
    print(f'Polygon intersects {len(result.cellids)} cells')
    print(f'Cell IDs: {result.cellids}')
    print(f'Intersection areas: {result.areas}')

# Test multi-polygon intersection
print('\nTesting multi-polygon intersection:')
from shapely.geometry import MultiPolygon
multipolygon = MultiPolygon([
    Polygon([(1, 1), (4, 1), (4, 4), (1, 4), (1, 1)]),
    Polygon([(16, 16), (19, 16), (19, 19), (16, 19), (16, 16)])
])
result = ix.intersect(multipolygon)
if result is not None and len(result) > 0:
    print(f'Multi-polygon intersects {len(result.cellids)} cells')
    print(f'Cell IDs: {result.cellids}')

# Verify grid properties
print('\nGrid properties:')
print(f'Number of cells: {tgr.ncpl}')
print(f'Number of vertices: {len(vertices)}')
print(f'Grid extent: x=[{tgr.extent[0]}, {tgr.extent[1]}], y=[{tgr.extent[2]}, {tgr.extent[3]}]')

print('\n=== Grid Intersection Geometry Tests Complete ===')

# Phase 8: Create and run an actual MODFLOW model using grid intersection
print('\nPhase 8: Creating MODFLOW model with intersection-based boundaries')
import flopy

# Create a simple structured model for demonstration
ws = './model_output'
import os
os.makedirs(ws, exist_ok=True)

# Create MODFLOW 6 simulation
sim = flopy.mf6.MFSimulation(sim_name='grid_intersect_demo', sim_ws=ws, exe_name='/home/danilopezmella/flopy_expert/bin/mf6')
tdis = flopy.mf6.ModflowTdis(sim, nper=1, perioddata=[(1.0, 1, 1.0)])
gwf = flopy.mf6.ModflowGwf(sim, modelname='model', save_flows=True)
ims = flopy.mf6.ModflowIms(sim, complexity='SIMPLE')
sim.register_ims_package(ims, [gwf.name])

# Discretization - simple structured grid
nlay, nrow, ncol = 1, 20, 20
dis = flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=nrow, ncol=ncol, 
                               delr=1.0, delc=1.0, top=1.0, botm=0.0)

# Flow properties
npf = flopy.mf6.ModflowGwfnpf(gwf, icelltype=0, k=10.0)

# Initial conditions
ic = flopy.mf6.ModflowGwfic(gwf, strt=0.5)

# Use grid intersection to set boundary conditions along a line
print('Using grid intersection to set CHD boundary along line...')
# Create grid intersect for structured grid
sgr = gwf.modelgrid
ix_struct = GridIntersect(sgr, method='structured')

# Define a diagonal line across the model
from shapely.geometry import LineString
line = LineString([(5, 5), (15, 15)])

# Find cells intersected by the line
result = ix_struct.intersect(line)
chd_cells = []
if result is not None and len(result) > 0:
    for idx, cellid in enumerate(result['cellids']):
        # For structured grid, cellid is (row, col)
        if isinstance(cellid, tuple):
            row, col = cellid
        else:
            row, col = cellid, 0
        # Add CHD boundary with head = 1.0
        chd_cells.append([(0, row, col), 1.0])
    print(f'Added {len(chd_cells)} CHD cells along diagonal line')

if chd_cells:
    chd = flopy.mf6.ModflowGwfchd(gwf, stress_period_data=chd_cells)

# Add a well at polygon intersection
print('Using grid intersection to add well in polygon area...')
polygon_result = ix_struct.intersect(polygon)
wel_cells = []
if polygon_result is not None and len(polygon_result) > 0:
    # Add well in center of polygon area
    center_cell = polygon_result['cellids'][len(polygon_result)//2]
    if isinstance(center_cell, tuple):
        row, col = center_cell
    else:
        row, col = center_cell, 0
    wel_cells = [[(0, row, col), -10.0]]
    print(f'Added well at cell ({row}, {col})')
    wel = flopy.mf6.ModflowGwfwel(gwf, stress_period_data=wel_cells)

# Output control
oc = flopy.mf6.ModflowGwfoc(gwf, head_filerecord='model.hds', 
                            saverecord=[('HEAD', 'ALL')])

# Write and run
print('\nWriting and running MODFLOW model...')
sim.write_simulation()
success, buff = sim.run_simulation(silent=True)

if success:
    print('✓ Model ran successfully!')
    head = gwf.output.head().get_data()
    print(f'Head statistics: min={head.min():.2f}, max={head.max():.2f}, mean={head.mean():.2f}')
    print('\nGrid intersection successfully used to set boundary conditions!')
else:
    print('Model failed to run')

print('\n=== Complete: Grid Intersection Demo with Working Model ===')