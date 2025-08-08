"""
IMPORTANT NOTE: This is a grid visualization demonstration only.
This script demonstrates VertexGrid creation and visualization capabilities.
It does NOT run a MODFLOW model and therefore does NOT produce output files (.hds, .cbc, etc.).
This is intentional - the purpose is to show grid construction and properties.
"""
import numpy as np
from flopy.discretization import VertexGrid
import matplotlib.pyplot as plt

# Phase 1: Discretization - Create vertex grid
nlay = 3  # Number of layers
ncpl = 5  # Number of cells per layer

# Define vertices (node points)
vertices = [
    [0, 0.0, 3.0],
    [1, 1.0, 3.0],
    [2, 2.0, 3.0],
    [3, 0.0, 2.0],
    [4, 1.0, 2.0],
    [5, 2.0, 2.0],
    [6, 0.0, 1.0],
    [7, 1.0, 1.0],
    [8, 2.0, 1.0],
    [9, 0.0, 0.0],
    [10, 1.0, 0.0],
]

# Define cells using vertices (cell_id, xcenter, ycenter, nvert, vert1, vert2, ...)
cell2d = [
    [0, 0.5, 2.5, 4, 0, 1, 4, 3],   # Cell 0: quadrilateral
    [1, 1.5, 2.5, 4, 1, 2, 5, 4],   # Cell 1: quadrilateral
    [2, 0.5, 1.5, 4, 3, 4, 7, 6],   # Cell 2: quadrilateral
    [3, 1.5, 1.5, 4, 4, 5, 8, 7],   # Cell 3: quadrilateral
    [4, 0.5, 0.5, 4, 6, 7, 10, 9],  # Cell 4: quadrilateral
]

# Define active domain
idomain = np.ones((nlay, ncpl), dtype=int)

# Define top and bottom elevations
top = np.ones(ncpl, dtype=float) * 10.0
botm = np.zeros((nlay, ncpl), dtype=float)
botm[0, :] = 5.0   # Layer 1 bottom
botm[1, :] = 0.0   # Layer 2 bottom
botm[2, :] = -5.0  # Layer 3 bottom

# Create the vertex grid
grid = VertexGrid(
    nlay=nlay,
    ncpl=ncpl,
    vertices=vertices,
    cell2d=cell2d,
    top=top,
    botm=botm,
    idomain=idomain,
)

# Phase 7: Post-processing - Display grid properties
print(f"Vertex grid dimensions: {grid.nlay} layers, {grid.ncpl} cells per layer")
print(f"Total cells: {grid.nnodes}")
print(f"Number of vertices: {len(vertices)}")
print(f"Grid extent: {grid.extent}")

# Display cell information
print("\nCell information:")
for i, cell in enumerate(cell2d):
    cell_id = cell[0]
    xcenter = cell[1]
    ycenter = cell[2]
    nvert = cell[3]
    print(f"Cell {cell_id}: center=({xcenter}, {ycenter}), vertices={nvert}")

# Visualize the grid
fig, ax = plt.subplots(figsize=(8, 6))
grid.plot(ax=ax)
ax.set_title('Vertex Grid (DISV)')
ax.set_xlabel('X coordinate')
ax.set_ylabel('Y coordinate')
ax.set_aspect('equal')

# Add cell numbers
for i in range(ncpl):
    x, y = grid.xcellcenters[i], grid.ycellcenters[i]
    ax.text(x, y, str(i), ha='center', va='center')

plt.show()

# Access grid properties
print("\nCell areas:")
for i in range(ncpl):
    print(f"Cell {i}: {grid.get_cell_vertices(i)}")

print("\nGrid demonstration complete!")
print("\nNOTE: This was a grid visualization demo only.")
print("No MODFLOW model was run, so no output files (.hds, .cbc) were created.")
print("This is intentional - the purpose was to demonstrate VertexGrid construction.")