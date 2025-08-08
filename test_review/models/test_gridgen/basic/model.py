import os
import numpy as np
import flopy
import matplotlib.pyplot as plt
from pathlib import Path

# Working directory
ws = Path('unstructured_grid_model')
ws.mkdir(exist_ok=True)

# Phase 1: Create base structured grid and convert to unstructured concept
print('Phase 1: Setting up unstructured grid concept')
Lx = 100.0
Ly = 100.0
nlay = 2

# For unstructured grid, we define nodes directly
# This is a simplified example - normally gridgen would generate this

# Create MODFLOW 6 simulation
sim = flopy.mf6.MFSimulation(sim_name='unstructured_demo', sim_ws=str(ws), exe_name='/home/danilopezmella/flopy_expert/bin/mf6')
tdis = flopy.mf6.ModflowTdis(sim, time_units='DAYS', nper=1, perioddata=[(1.0, 1, 1.0)])
gwf = flopy.mf6.ModflowGwf(sim, modelname='model', save_flows=True)
ims = flopy.mf6.ModflowIms(sim, print_option='SUMMARY', complexity='SIMPLE')
sim.register_ims_package(ims, [gwf.name])

# Create simplified unstructured grid using DISU
# Define nodes in active domain with refinement
print('Defining unstructured grid nodes...')

# Create a simple unstructured grid
# Base grid 10x10, with refinement in center
nodes = []
node_id = 0

# Coarse grid cells (10m spacing)
for i in range(10):
    for j in range(10):
        x = j * 10.0 + 5.0
        y = i * 10.0 + 5.0
        
        # Skip cells in refinement zone (center)
        if 30 <= x <= 70 and 30 <= y <= 70:
            continue
            
        for k in range(nlay):
            nodes.append({
                'id': node_id,
                'x': x,
                'y': y,
                'layer': k,
                'top': 10.0 if k == 0 else -5.0,
                'bot': -5.0 if k == 0 else -10.0,
                'area': 100.0  # 10x10 cell
            })
            node_id += 1

# Refined cells in center (5m spacing)
for i in range(8):
    for j in range(8):
        x = 30.0 + j * 5.0 + 2.5
        y = 30.0 + i * 5.0 + 2.5
        
        for k in range(nlay):
            nodes.append({
                'id': node_id,
                'x': x,
                'y': y,
                'layer': k,
                'top': 10.0 if k == 0 else -5.0,
                'bot': -5.0 if k == 0 else -10.0,
                'area': 25.0  # 5x5 cell
            })
            node_id += 1

nnodes = len(nodes)
print(f'Created {nnodes} unstructured nodes')
print(f'  Coarse cells: {(100 - 16) * nlay}')
print(f'  Refined cells: {64 * nlay}')

# Create DISU package data
# For DISU, top is only for the top layer nodes
top = np.array([n['top'] for n in nodes])
bot = np.array([n['bot'] for n in nodes])
area = np.array([n['area'] for n in nodes])

# Simple connectivity (simplified - normally would be complex)
# This creates a basic connected grid
ja = []
iac = []
ihc = []  # Horizontal connection indicator
cl12 = []  # Connection lengths
hwva = []  # Horizontal width/vertical area
ivc = 0

for i, node in enumerate(nodes):
    connections = [i]  # Self connection
    connection_types = [0]  # Self connection is 0
    connection_lengths = [0.0]  # Self connection length is 0
    connection_areas = [node['area']]  # Self connection area
    
    # Find neighbors (simplified)
    for j, other in enumerate(nodes):
        if i != j:
            dx = abs(node['x'] - other['x'])
            dy = abs(node['y'] - other['y'])
            
            # Check for horizontal neighbors (same layer)
            if node['layer'] == other['layer']:
                # Adjacent if within threshold
                if (dx <= 10 and dy < 1.0) or (dy <= 10 and dx < 1.0):
                    connections.append(j)
                    connection_types.append(1)  # Horizontal connection
                    # Connection length (distance between cell centers / 2)
                    dist = np.sqrt(dx**2 + dy**2)
                    connection_lengths.append(dist / 2.0)
                    # Connection area (geometric mean of areas)
                    connection_areas.append(np.sqrt(node['area'] * other['area']))
            # Check for vertical neighbors (different layer, same x,y)
            elif abs(dx) < 1.0 and abs(dy) < 1.0:
                if abs(node['layer'] - other['layer']) == 1:
                    connections.append(j)
                    connection_types.append(0)  # Vertical connection
                    # Vertical connection length (half thickness)
                    connection_lengths.append(2.5)  # Half of 5m layer thickness
                    connection_areas.append(node['area'])  # Use cell area
    
    iac.append(len(connections))
    ja.extend(connections)
    ihc.extend(connection_types)
    cl12.extend(connection_lengths)
    hwva.extend(connection_areas)

iac = np.array(iac)
ja = np.array(ja)
ihc = np.array(ihc)
cl12 = np.array(cl12)
hwva = np.array(hwva)

# Create angle arrays for specific discharge calculation
angldegx = np.zeros(len(ja))  # Angle of x-axis for each connection
angldegx[ihc == 1] = 0.0  # Horizontal connections aligned with x-axis

# Create DISU package
disu = flopy.mf6.ModflowGwfdisu(
    gwf,
    nodes=nnodes,
    iac=iac,
    ja=ja,
    ihc=ihc,
    cl12=cl12,
    hwva=hwva,
    angldegx=angldegx,
    top=top,
    bot=bot,
    area=area,
    length_units='METERS'
)

# Phase 2: Properties
print('\nPhase 2: Setting hydraulic properties')
npf = flopy.mf6.ModflowGwfnpf(
    gwf,
    save_specific_discharge=False,  # Disabled for unstructured grid
    icelltype=1,
    k=10.0
)

# Phase 3: Initial conditions
print('\nPhase 3: Setting initial conditions')
ic = flopy.mf6.ModflowGwfic(gwf, strt=5.0)

# Phase 4: Boundary conditions
print('\nPhase 4: Adding boundary conditions')
# Add constant heads at corners
stress_period_data = [
    [0, 10.0],  # First node
    [nnodes-1, 5.0]  # Last node
]
chd = flopy.mf6.ModflowGwfchd(gwf, stress_period_data=stress_period_data)

# Phase 5: Output control
print('\nPhase 5: Setting output control')
oc = flopy.mf6.ModflowGwfoc(
    gwf,
    head_filerecord=f'{gwf.name}.hds',
    budget_filerecord=f'{gwf.name}.cbc',
    saverecord=[('HEAD', 'ALL'), ('BUDGET', 'ALL')]
)

# Write and run simulation
print('\nWriting simulation files...')
sim.write_simulation()

print('\nRunning simulation...')
success, buff = sim.run_simulation()

if success:
    print('\nSimulation completed successfully!')
    
    # Phase 7: Post-processing
    print('\nPhase 7: Post-processing')
    
    # Load heads
    head_file = gwf.output.head()
    heads = head_file.get_data()
    
    # Create visualization of unstructured grid
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # Plot node locations and refinement
    layer0_nodes = [n for n in nodes if n['layer'] == 0]
    x_coords = [n['x'] for n in layer0_nodes]
    y_coords = [n['y'] for n in layer0_nodes]
    areas = [n['area'] for n in layer0_nodes]
    
    # Color by area (shows refinement)
    sc = axes[0].scatter(x_coords, y_coords, c=areas, s=50, cmap='coolwarm', edgecolors='black', linewidth=0.5)
    axes[0].set_title('Unstructured Grid with Refinement')
    axes[0].set_xlabel('X (m)')
    axes[0].set_ylabel('Y (m)')
    axes[0].set_xlim(0, Lx)
    axes[0].set_ylim(0, Ly)
    axes[0].grid(True, alpha=0.3)
    plt.colorbar(sc, ax=axes[0], label='Cell Area (m²)')
    
    # Add refinement zone outline
    from matplotlib.patches import Rectangle
    rect = Rectangle((30, 30), 40, 40, fill=False, edgecolor='red', linewidth=2, linestyle='--')
    axes[0].add_patch(rect)
    axes[0].text(50, 72, 'Refinement Zone', ha='center', color='red', fontweight='bold')
    
    # Plot heads for layer 0
    # For unstructured grid, heads array is 1D per stress period
    # Get all heads and take only the layer 0 nodes (first nnodes//nlay nodes)
    if heads.shape[1] == nnodes:
        # All nodes in one array
        layer0_heads = heads[0, :len(layer0_nodes)]
    else:
        # Handle case where heads might be reshaped differently
        layer0_heads = heads.flatten()[:len(layer0_nodes)]
    
    sc2 = axes[1].scatter(x_coords, y_coords, c=layer0_heads, s=50, cmap='viridis', edgecolors='black', linewidth=0.5)
    axes[1].set_title('Hydraulic Head Distribution (Layer 1)')
    axes[1].set_xlabel('X (m)')
    axes[1].set_ylabel('Y (m)')
    axes[1].set_xlim(0, Lx)
    axes[1].set_ylim(0, Ly)
    axes[1].grid(True, alpha=0.3)
    plt.colorbar(sc2, ax=axes[1], label='Head (m)')
    
    plt.tight_layout()
    plt.savefig(ws / 'results.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    # Summary statistics
    print(f'\nUnstructured grid statistics:')
    print(f'  Total nodes: {nnodes}')
    print(f'  Nodes per layer: {nnodes // nlay}')
    print(f'  Coarse cell area: 100 m²')
    print(f'  Refined cell area: 25 m²')
    print(f'  Refinement ratio: 4:1')
    print(f'\nHead statistics:')
    print(f'  Minimum head: {heads.min():.2f} m')
    print(f'  Maximum head: {heads.max():.2f} m')
    print(f'  Mean head: {heads.mean():.2f} m')
else:
    print('\nSimulation failed!')
    print('Error messages:')
    for line in buff:
        print(line)