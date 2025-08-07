"""
Local Grid Refinement (LGR) Demonstration

This script demonstrates FloPy's Local Grid Refinement utilities for creating
nested grids within MODFLOW models. Key concepts demonstrated:
- Parent-child grid relationships
- Grid refinement for detailed local analysis  
- LGR utility functions for grid manipulation
- Coordinate transformations between grid levels
- Nested model setup principles

LGR is used for:
- Focusing computational resources on areas of interest
- Maintaining detail while managing computational cost
- Simulating complex local processes (wells, contaminant plumes)
- Bridging scales from regional to local modeling
"""

import numpy as np
import flopy
from flopy.utils import lgrutil

def run_model():
    """
    Create and demonstrate Local Grid Refinement concepts.
    Shows parent grid setup, child grid creation, and LGR utilities.
    """
    
    print("=== Local Grid Refinement (LGR) Demonstration ===\n")
    
    # Create model workspace
    model_ws = "model_output"
    
    # 1. Parent Grid Setup
    print("1. Setting Up Parent Grid")
    print("-" * 40)
    
    # Parent grid dimensions
    parent_nlay, parent_nrow, parent_ncol = 1, 20, 30
    parent_delr = parent_delc = 500.0  # 500m cells
    parent_top = 100.0
    parent_botm = [0.0]
    
    # Parent grid extent
    Lx = parent_ncol * parent_delr  # 15 km
    Ly = parent_nrow * parent_delc  # 10 km
    
    print(f"  Parent grid: {parent_nlay}×{parent_nrow}×{parent_ncol}")
    print(f"  Cell size: {parent_delr}m × {parent_delc}m")
    print(f"  Total extent: {Lx/1000:.1f}km × {Ly/1000:.1f}km")
    
    # Create parent MODFLOW model
    parent_mf = flopy.modflow.Modflow(
        modelname="parent_grid",
        model_ws=model_ws,
        exe_name="mf2005" if False else None  # Skip execution for demo
    )
    
    # Parent discretization
    parent_dis = flopy.modflow.ModflowDis(
        parent_mf,
        nlay=parent_nlay,
        nrow=parent_nrow,
        ncol=parent_ncol,
        delr=parent_delr,
        delc=parent_delc,
        top=parent_top,
        botm=parent_botm,
        nper=1,
        perlen=[365],
        nstp=[1],
        steady=[True]
    )
    
    # Parent basic package
    parent_ibound = np.ones((parent_nlay, parent_nrow, parent_ncol), dtype=int)
    parent_strt = np.ones((parent_nlay, parent_nrow, parent_ncol)) * 90.0
    
    parent_bas = flopy.modflow.ModflowBas(
        parent_mf,
        ibound=parent_ibound,
        strt=parent_strt
    )
    
    # Parent hydraulic properties
    parent_hk = 10.0 * np.ones((parent_nlay, parent_nrow, parent_ncol))
    
    parent_lpf = flopy.modflow.ModflowLpf(
        parent_mf,
        hk=parent_hk,
        vka=1.0
    )
    
    # 2. Child Grid Definition
    print(f"\n2. Defining Child Grid Refinement Area")
    print("-" * 40)
    
    # Define area of interest for refinement (central area with well)
    # Child grid will be 5x finer resolution in area around a pumping well
    
    # Child grid location in parent grid coordinates
    child_ncpp = 5  # Child cells per parent cell (5x refinement)
    
    # Define parent cells to refine (rows 8-12, columns 12-18)
    parent_row_start, parent_row_end = 8, 13  # 5 parent rows  
    parent_col_start, parent_col_end = 12, 19  # 7 parent columns
    
    child_nrow = (parent_row_end - parent_row_start) * child_ncpp  # 25 rows
    child_ncol = (parent_col_end - parent_col_start) * child_ncpp  # 35 columns
    
    child_delr = parent_delr / child_ncpp  # 100m cells
    child_delc = parent_delc / child_ncpp  # 100m cells
    
    print(f"  Refinement area: parent rows {parent_row_start}-{parent_row_end-1}, cols {parent_col_start}-{parent_col_end-1}")
    print(f"  Refinement ratio: {child_ncpp}:1 (child:parent)")
    print(f"  Child grid: {parent_nlay}×{child_nrow}×{child_ncol}")
    print(f"  Child cell size: {child_delr}m × {child_delc}m")
    
    # 3. LGR Utility Demonstrations
    print(f"\n3. LGR Utility Functions")
    print("-" * 40)
    
    # Calculate child grid origin in real-world coordinates
    # Assuming parent grid origin at (0, 0)
    child_xul = parent_col_start * parent_delr
    child_yul = Ly - (parent_row_start * parent_delc)  # Upper left y-coordinate
    
    print(f"  Child grid origin: ({child_xul}, {child_yul})")
    
    # Demonstrate coordinate transformations
    # Example: Convert parent cell (10, 15) to child grid coordinates
    parent_test_row, parent_test_col = 10, 15
    
    if (parent_row_start <= parent_test_row < parent_row_end and 
        parent_col_start <= parent_test_col < parent_col_end):
        
        # This parent cell is within the child grid
        child_row_start = (parent_test_row - parent_row_start) * child_ncpp
        child_col_start = (parent_test_col - parent_col_start) * child_ncpp
        child_row_end = child_row_start + child_ncpp
        child_col_end = child_col_start + child_ncpp
        
        print(f"  Parent cell ({parent_test_row}, {parent_test_col}) maps to child cells:")
        print(f"    Rows {child_row_start}-{child_row_end-1}, Cols {child_col_start}-{child_col_end-1}")
    
    # 4. Create Child Model
    print(f"\n4. Creating Child Grid Model")
    print("-" * 40)
    
    child_mf = flopy.modflow.Modflow(
        modelname="child_grid",
        model_ws=model_ws
    )
    
    # Child discretization  
    child_dis = flopy.modflow.ModflowDis(
        child_mf,
        nlay=parent_nlay,
        nrow=child_nrow,
        ncol=child_ncol,
        delr=child_delr,
        delc=child_delc,
        top=parent_top,
        botm=parent_botm,
        nper=1,
        perlen=[365], 
        nstp=[1],
        steady=[True]
    )
    
    # Child boundary conditions - link to parent
    child_ibound = np.ones((parent_nlay, child_nrow, child_ncol), dtype=int)
    
    # Set boundary cells that interface with parent
    # In real LGR, these would be linked through special boundary conditions
    child_ibound[:, 0, :] = -1   # Specified head on top edge
    child_ibound[:, -1, :] = -1  # Specified head on bottom edge  
    child_ibound[:, :, 0] = -1   # Specified head on left edge
    child_ibound[:, :, -1] = -1  # Specified head on right edge
    
    # Interior cells are active
    child_strt = np.ones((parent_nlay, child_nrow, child_ncol)) * 85.0
    
    # Set boundary head values (would come from parent model)
    child_strt[:, 0, :] = 88.0   # Top boundary
    child_strt[:, -1, :] = 82.0  # Bottom boundary
    child_strt[:, :, 0] = 90.0   # Left boundary  
    child_strt[:, :, -1] = 80.0  # Right boundary
    
    child_bas = flopy.modflow.ModflowBas(
        child_mf,
        ibound=child_ibound,
        strt=child_strt
    )
    
    # Child hydraulic properties (more detailed)
    child_hk = np.ones((parent_nlay, child_nrow, child_ncol)) * 8.0
    
    # Add some heterogeneity that couldn't be resolved in parent grid
    center_row = child_nrow // 2
    center_col = child_ncol // 2
    
    # High-K channel feature
    child_hk[:, center_row-2:center_row+3, :] = 25.0
    
    # Low-K clay lens
    child_hk[:, center_row-8:center_row-5, center_col-5:center_col+5] = 1.0
    
    child_lpf = flopy.modflow.ModflowLpf(
        child_mf,
        hk=child_hk,
        vka=0.8
    )
    
    # Add high-capacity production well in center of child grid
    wel_data = [[0, center_row, center_col, -2000.0]]  # 2000 m3/d pumping
    
    child_wel = flopy.modflow.ModflowWel(
        child_mf,
        stress_period_data={0: wel_data}
    )
    
    print(f"  Child model created with detailed features:")
    print(f"    - High-K channel through center")  
    print(f"    - Low-K clay lens for heterogeneity")
    print(f"    - Production well at ({center_row}, {center_col}) pumping 2000 m³/d")
    
    # 5. Grid Relationship Analysis
    print(f"\n5. Parent-Child Grid Relationships")
    print("-" * 40)
    
    # Calculate resolution improvement
    parent_area = parent_delr * parent_delc  # m²
    child_area = child_delr * child_delc    # m²
    resolution_ratio = parent_area / child_area
    
    total_parent_cells = parent_nrow * parent_ncol
    refined_parent_cells = (parent_row_end - parent_row_start) * (parent_col_end - parent_col_start)
    child_cells = child_nrow * child_ncol
    
    print(f"  Resolution improvement: {resolution_ratio:.0f}x finer")
    print(f"  Parent grid total cells: {total_parent_cells}")
    print(f"  Parent cells being refined: {refined_parent_cells}")
    print(f"  Child grid cells: {child_cells}")
    print(f"  Net cell increase: {child_cells - refined_parent_cells}")
    
    # 6. Write Models
    print(f"\n6. Writing Model Files")
    print("-" * 40)
    
    print("  Writing parent model...")
    parent_mf.write_input()
    
    print("  Writing child model...")
    child_mf.write_input()
    
    print("  ✓ Both models written successfully")
    
    # 7. LGR Applications and Benefits
    print(f"\n7. LGR Applications Demonstrated")
    print("-" * 40)
    
    print("  Local Grid Refinement benefits:")
    print("    • Focus computation on areas of interest")
    print("    • Resolve small-scale features (clay lenses, channels)")
    print("    • Accurate well drawdown simulation")
    print("    • Maintain regional context with local detail")
    print("    • Computational efficiency vs. uniform fine grid")
    
    print(f"\n  Typical LGR applications:")
    print(f"    • Wellfield optimization and drawdown analysis")
    print(f"    • Contaminant plume transport modeling") 
    print(f"    • Surface water-groundwater interaction")
    print(f"    • Urban groundwater systems")
    print(f"    • Mining dewatering studies")
    
    print(f"\n✓ Local Grid Refinement Demonstration Completed!")
    print(f"  - Created parent grid (20×30, 500m cells)")
    print(f"  - Defined child refinement area (25×35, 100m cells)")
    print(f"  - Demonstrated coordinate transformations")
    print(f"  - Implemented detailed local features")
    print(f"  - Showed practical LGR applications")
    
    return parent_mf, child_mf

if __name__ == "__main__":
    parent_model, child_model = run_model()