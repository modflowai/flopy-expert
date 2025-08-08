import numpy as np
from flopy.utils.gridutil import get_lni

# Demonstrate get_lni utility function
print('Layer-Node Index (LNI) Utility Demonstration')
print('=' * 50)

# Example 1: Single layer model
print('\nExample 1: Single Layer Model')
ncpl = 10  # 10 cells per layer
nodes = [0, 5, 9]  # First, middle, and last cells
lni = get_lni(ncpl, nodes)
print(f'  Cells per layer: {ncpl}')
print(f'  Node numbers: {nodes}')
print(f'  Layer-Node indices:')
for node, (layer, idx) in zip(nodes, lni):
    print(f'    Node {node} -> Layer {layer}, Index {idx}')

# Example 2: Multi-layer model with list ncpl
print('\nExample 2: Two Layer Model (equal cells per layer)')
ncpl = [10, 10]  # 10 cells in each layer
nodes = [0, 9, 10, 15, 19]  # Various nodes
lni = get_lni(ncpl, nodes)
print(f'  Cells per layer: {ncpl}')
print(f'  Node numbers: {nodes}')
print(f'  Layer-Node indices:')
for node, (layer, idx) in zip(nodes, lni):
    print(f'    Node {node} -> Layer {layer}, Index {idx}')

# Example 3: Variable cells per layer
print('\nExample 3: Two Layer Model (variable cells per layer)')
ncpl = [10, 20]  # 10 cells in layer 1, 20 in layer 2
nodes = [5, 9, 10, 25, 29]  # Various nodes
lni = get_lni(ncpl, nodes)
print(f'  Cells per layer: {ncpl}')
print(f'  Node numbers: {nodes}')
print(f'  Layer-Node indices:')
for node, (layer, idx) in zip(nodes, lni):
    print(f'    Node {node} -> Layer {layer}, Index {idx}')

# Example 4: Practical use case - finding neighbors
print('\nExample 4: Finding Cell Neighbors')
ncpl = [15, 15, 15]  # 3 layers, 15 cells each
node = 20  # Cell in layer 2

# Find layer and index
lni = get_lni(ncpl, [node])
layer, idx = lni[0]
print(f'  Node {node} is in Layer {layer}, Cell index {idx}')

# Calculate potential neighbors
neighbors = []
# Same layer neighbors
if idx > 0:
    neighbors.append(node - 1)  # Previous cell
if idx < ncpl[layer] - 1:
    neighbors.append(node + 1)  # Next cell
# Vertical neighbors
if layer > 0:
    neighbors.append(node - ncpl[layer-1])  # Cell above
if layer < len(ncpl) - 1:
    neighbors.append(node + ncpl[layer])  # Cell below

print(f'  Potential neighbor nodes: {neighbors}')
neighbor_lni = get_lni(ncpl, neighbors)
print(f'  Neighbor layer-indices:')
for n, (l, i) in zip(neighbors, neighbor_lni):
    print(f'    Node {n} -> Layer {l}, Index {i}')

# Example 5: Automatic layer inference
print('\nExample 5: Automatic Layer Inference')
ncpl = 5  # When int, infers layers from node numbers
nodes = [4, 9, 14, 19]  # Nodes spanning multiple layers
lni = get_lni(ncpl, nodes)
print(f'  Cells per layer: {ncpl} (integer - will infer layers)')
print(f'  Node numbers: {nodes}')
print(f'  Layer-Node indices (inferred):')
for node, (layer, idx) in zip(nodes, lni):
    print(f'    Node {node} -> Layer {layer}, Index {idx}')

print('\n' + '=' * 50)
print('LNI utility demonstration complete!')

# Phase 7: Create and run a MODFLOW model that uses gridutil
print('\nPhase 7: Creating MODFLOW model using gridutil functions')
import flopy
import os

ws = './model_output'
os.makedirs(ws, exist_ok=True)

# Create MODFLOW 6 simulation
sim = flopy.mf6.MFSimulation(sim_name='gridutil_demo', sim_ws=ws, exe_name='/home/danilopezmella/flopy_expert/bin/mf6')
tdis = flopy.mf6.ModflowTdis(sim, nper=1, perioddata=[(10.0, 10, 1.0)])
gwf = flopy.mf6.ModflowGwf(sim, modelname='model', save_flows=True)
ims = flopy.mf6.ModflowIms(sim, complexity='SIMPLE')
sim.register_ims_package(ims, [gwf.name])

# Discretization - 3 layer model
nlay, nrow, ncol = 3, 10, 10
dis = flopy.mf6.ModflowGwfdis(gwf, nlay=nlay, nrow=nrow, ncol=ncol,
                               delr=10.0, delc=10.0, top=30.0,
                               botm=[20.0, 10.0, 0.0])

# Flow properties
npf = flopy.mf6.ModflowGwfnpf(gwf, icelltype=1, k=[10.0, 5.0, 1.0])

# Initial conditions
ic = flopy.mf6.ModflowGwfic(gwf, strt=25.0)

# Use gridutil to set boundary conditions based on layer-node indices
print('Using gridutil to set layer-specific boundaries...')
ncpl_model = nrow * ncol  # cells per layer

# Add CHD boundaries in specific layers using gridutil
chd_cells = []
# Top layer corners
corner_nodes_layer0 = [0, ncol-1, ncpl_model-ncol, ncpl_model-1]
for node in corner_nodes_layer0:
    lni = get_lni(ncpl_model, [node])
    layer, idx = lni[0]
    row = idx // ncol
    col = idx % ncol
    chd_cells.append([(layer, row, col), 30.0])
    print(f'  Added CHD at Layer {layer}, Row {row}, Col {col} (Node {node})')

# Bottom layer center
center_node_layer2 = 2 * ncpl_model + (nrow//2) * ncol + ncol//2
lni = get_lni([ncpl_model]*nlay, [center_node_layer2])
layer, idx = lni[0]
row = idx // ncol
col = idx % ncol
chd_cells.append([(layer, row, col), 20.0])
print(f'  Added CHD at Layer {layer}, Row {row}, Col {col} (Node {center_node_layer2})')

chd = flopy.mf6.ModflowGwfchd(gwf, stress_period_data=chd_cells)

# Add wells using gridutil for middle layer
wel_cells = []
middle_layer_start = ncpl_model  # Start of layer 1
well_nodes = [middle_layer_start + 25, middle_layer_start + 75]  # Two wells
for node in well_nodes:
    lni = get_lni([ncpl_model]*nlay, [node])
    layer, idx = lni[0]
    row = idx // ncol
    col = idx % ncol
    wel_cells.append([(layer, row, col), -50.0])
    print(f'  Added Well at Layer {layer}, Row {row}, Col {col} (Node {node})')

wel = flopy.mf6.ModflowGwfwel(gwf, stress_period_data=wel_cells)

# Output control
oc = flopy.mf6.ModflowGwfoc(gwf, head_filerecord='model.hds',
                            saverecord=[('HEAD', 'ALL')])

# Write and run
print('\nWriting and running model...')
sim.write_simulation()
success, buff = sim.run_simulation(silent=True)

if success:
    print('✓ Model ran successfully!')
    head = gwf.output.head().get_data()
    print(f'\nHead statistics by layer:')
    for layer in range(nlay):
        layer_head = head[layer, :, :]
        print(f'  Layer {layer}: min={layer_head.min():.2f}, max={layer_head.max():.2f}, mean={layer_head.mean():.2f}')
    print('\nGridutil functions successfully used for boundary condition setup!')
else:
    print('Model failed to run')

print('\n=== Complete: Gridutil Demo with Working Model ===')