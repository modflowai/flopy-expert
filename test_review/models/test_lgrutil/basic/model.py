"""
LGR Utilities with FloPy - Local Grid Refinement Tools

This example demonstrates FloPy's Local Grid Refinement (LGR) utilities for creating
refined grids within parent grids. The utilities help generate child grids with
higher resolution in areas of interest and manage the connections between parent
and child grids.

Key FloPy components demonstrated:
- flopy.utils.lgrutil.Lgr - Local Grid Refinement utility class
- flopy.utils.lgrutil.LgrToDisv - Convert LGR to DISV grid format
- Grid refinement calculations and parent-child relationships
- Exchange data generation for grid connections
- Variable cell spacing handling

The model demonstrates various LGR scenarios including uniform and variable
parent grid spacing, multiple layers, and conversion to DISV format for
unstructured grid modeling.
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from flopy.utils.lgrutil import Lgr, LgrToDisv

def demonstrate_lgr_basics():
    """Demonstrate basic LGR utility functionality"""
    
    print("="*50)
    print("LGR UTILITIES DEMONSTRATION")
    print("="*50)
    
    # Define parent grid parameters
    print("\n1. Setting up parent grid...")
    nlayp = 5    # Number of layers in parent
    nrowp = 5    # Number of rows in parent  
    ncolp = 5    # Number of columns in parent
    delrp = 100.0  # Uniform column width
    delcp = 100.0  # Uniform row width
    topp = 100.0   # Top elevation
    botmp = [-100, -200, -300, -400, -500]  # Bottom elevations by layer
    
    # Define parent idomain (0 where child grid will be placed)
    idomainp = np.ones((nlayp, nrowp, ncolp), dtype=int)
    idomainp[0:2, 1:4, 1:4] = 0  # Child area in layers 1-2, rows 2-4, cols 2-4
    
    # Child grid refinement parameters
    ncpp = 3    # Number of child cells per parent cell
    ncppl = [1, 1, 0, 0, 0]  # Number of child layers per parent layer
    
    print(f"  Parent grid: {nlayp} layers, {nrowp}×{ncolp} cells")
    print(f"  Cell size: {delrp}×{delcp}")
    print(f"  Child refinement: {ncpp}×{ncpp} cells per parent cell")
    print(f"  Active child layers: {sum(ncppl)}")
    
    # Create LGR object
    print("\n2. Creating LGR object...")
    lgr = Lgr(
        nlayp, nrowp, ncolp,
        delrp, delcp, topp, botmp, idomainp,
        ncpp=ncpp, ncppl=ncppl,
        xllp=100.0, yllp=100.0  # Lower-left coordinates
    )
    
    # Get child grid properties
    child_shape = lgr.get_shape()
    print(f"  Child grid shape: {child_shape}")
    
    delr_child, delc_child = lgr.get_delr_delc()
    print(f"  Child cell size: {delr_child[0]:.2f}×{delc_child[0]:.2f}")
    
    # Get child idomain
    idomain_child = lgr.get_idomain()
    print(f"  Child active cells: {np.sum(idomain_child)}")
    
    # Get child top/bottom elevations
    top_child, botm_child = lgr.get_top_botm()
    print(f"  Child top shape: {top_child.shape}")
    print(f"  Child bottom shape: {botm_child.shape}")
    
    return lgr

def demonstrate_variable_spacing():
    """Demonstrate LGR with variable parent grid spacing"""
    
    print("\n" + "="*50)
    print("VARIABLE SPACING DEMONSTRATION")
    print("="*50)
    
    # Define parent grid with variable spacing
    print("\n3. Setting up variable spacing parent grid...")
    nlayp = 1
    nrowp = 5
    ncolp = 5
    
    # Variable cell dimensions
    delrp = 100.0 * np.array([1.0, 0.75, 0.5, 0.75, 1.0], dtype=float)
    delcp = 100.0 * np.array([1.0, 0.75, 0.5, 0.75, 1.0], dtype=float)
    
    topp = 100.0 * np.ones((nrowp, ncolp), dtype=float)
    botmp = np.empty((nlayp, nrowp, ncolp), dtype=float)
    botmp[0] = -100.0
    
    # Define child area
    idomainp = np.ones((nlayp, nrowp, ncolp), dtype=int)
    idomainp[:, 1:4, 1:4] = 0  # Child area in center
    
    ncpp = 3
    ncppl = [1]
    
    print(f"  Variable delr: {delrp}")
    print(f"  Variable delc: {delcp}")
    
    # Create LGR with variable spacing
    lgr_var = Lgr(
        nlayp, nrowp, ncolp,
        delrp, delcp, topp, botmp, idomainp,
        ncpp=ncpp, ncppl=ncppl,
        xllp=0.0, yllp=0.0
    )
    
    # Check child cell dimensions
    print(f"  Child delr: {lgr_var.delr}")
    print(f"  Child delc: {lgr_var.delc}")
    
    # Verify calculations
    expected_delr = [25.0, 25.0, 25.0, 50.0/3, 50.0/3, 50.0/3, 25.0, 25.0, 25.0]
    print(f"  Expected delr: {expected_delr}")
    print(f"  Match expected: {np.allclose(lgr_var.delr, expected_delr)}")
    
    return lgr_var

def demonstrate_disv_conversion():
    """Demonstrate conversion of LGR to DISV format"""
    
    print("\n" + "="*50)
    print("DISV CONVERSION DEMONSTRATION") 
    print("="*50)
    
    # Create a simple 3D LGR grid
    print("\n4. Setting up 3D LGR for DISV conversion...")
    nlayp = 3
    nrowp = 3  
    ncolp = 3
    
    delrp = 100.0 * np.ones(ncolp)
    delcp = 100.0 * np.ones(nrowp)
    topp = 10.0 * np.ones((nrowp, ncolp), dtype=float)
    botmp = np.empty((nlayp, nrowp, ncolp), dtype=float)
    for k in range(nlayp):
        botmp[k] = -(k + 1) * 10.0
        
    # Child area in center cell
    idomainp = np.ones((nlayp, nrowp, ncolp), dtype=int)
    idomainp[:, nrowp//2, ncolp//2] = 0  # Center cell
    
    ncpp = 3
    ncppl = nlayp * [1]
    
    # Create LGR
    lgr_3d = Lgr(
        nlayp, nrowp, ncolp,
        delrp, delcp, topp, botmp, idomainp,
        ncpp=ncpp, ncppl=ncppl,
        xllp=0.0, yllp=0.0
    )
    
    print(f"  3D LGR shape: {lgr_3d.get_shape()}")
    
    # Convert to DISV grid properties
    print("\n5. Converting to DISV format...")
    gridprops = lgr_3d.to_disv_gridprops()
    
    print(f"  DISV ncpl (cells per layer): {gridprops['ncpl']}")
    print(f"  DISV nvert (vertices): {gridprops['nvert']}")
    print(f"  DISV nlay (layers): {gridprops['nlay']}")
    print(f"  Top shape: {gridprops['top'].shape}")
    print(f"  Bottom shape: {gridprops['botm'].shape}")
    
    # Create LgrToDisv object for detailed analysis
    print("\n6. Analyzing LgrToDisv conversion details...")
    lgr_to_disv = LgrToDisv(lgr_3d)
    
    # Show some vertex connections
    print(f"  Sample vertex connections:")
    for i in [1, 3, 4, 6]:
        if i < len(lgr_to_disv.iverts):
            print(f"    Cell {i}: vertices {lgr_to_disv.iverts[i]}")
    
    return lgr_3d, gridprops

def demonstrate_exchange_data():
    """Demonstrate exchange data generation for parent-child connections"""
    
    print("\n" + "="*50)
    print("EXCHANGE DATA DEMONSTRATION")
    print("="*50)
    
    # Use the basic LGR from first example
    lgr = demonstrate_lgr_basics()
    
    print("\n7. Generating exchange data...")
    exchange_data = lgr.get_exchange_data(angldegx=True, cdist=True)
    
    print(f"  Total exchange connections: {len(exchange_data)}")
    print(f"  First connection: {exchange_data[0]}")
    print(f"  Last connection: {exchange_data[-1]}")
    
    # Analyze connection types
    horizontal_conns = sum(1 for conn in exchange_data if conn[2] in [1, 2])
    vertical_conns = sum(1 for conn in exchange_data if conn[2] == 0)
    
    print(f"  Horizontal connections: {horizontal_conns}")
    print(f"  Vertical connections: {vertical_conns}")
    
    # Show parent connections for specific child cells
    print(f"\n8. Parent connections for specific child cells:")
    parent_conns_000 = lgr.get_parent_connections(0, 0, 0)
    print(f"  Child (0,0,0): {parent_conns_000}")
    
    if lgr.get_shape()[0] > 1 and lgr.get_shape()[1] > 8 and lgr.get_shape()[2] > 8:
        parent_conns_188 = lgr.get_parent_connections(1, 8, 8) 
        print(f"  Child (1,8,8): {parent_conns_188}")
    
    return exchange_data

def create_visualization():
    """Create simple visualizations of the grid refinement"""
    
    print("\n" + "="*50)
    print("CREATING VISUALIZATIONS")
    print("="*50)
    
    try:
        # Create output directory
        output_dir = "lgr_output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Create a figure showing parent and child grids
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Parent grid
        nrowp, ncolp = 5, 5
        delrp, delcp = 100.0, 100.0
        
        # Plot parent grid
        for i in range(nrowp + 1):
            ax1.axhline(i * delcp, color='black', linewidth=1)
        for j in range(ncolp + 1):
            ax1.axvline(j * delrp, color='black', linewidth=1)
            
        # Highlight child area
        child_rows = [1, 2, 3, 4]
        child_cols = [1, 2, 3, 4]
        for i in child_rows:
            for j in child_cols:
                rect = plt.Rectangle((j * delrp, i * delcp), delrp, delcp, 
                                   facecolor='lightblue', alpha=0.7)
                ax1.add_patch(rect)
                
        ax1.set_xlim(0, ncolp * delrp)
        ax1.set_ylim(0, nrowp * delcp)
        ax1.set_aspect('equal')
        ax1.set_title('Parent Grid (5×5)\nChild area in blue')
        ax1.set_xlabel('X coordinate')
        ax1.set_ylabel('Y coordinate')
        
        # Child grid (refined area only)
        ncpp = 3
        child_delr = delrp / ncpp
        child_delc = delcp / ncpp
        child_extent = 3 * delrp  # 3 parent cells
        nchild = child_extent / child_delr
        
        # Plot child grid
        for i in range(int(nchild) + 1):
            ax2.axhline(i * child_delc, color='red', linewidth=1)
        for j in range(int(nchild) + 1):
            ax2.axvline(j * child_delr, color='red', linewidth=1)
            
        ax2.set_xlim(0, child_extent)
        ax2.set_ylim(0, child_extent)
        ax2.set_aspect('equal')
        ax2.set_title('Child Grid (9×9)\n3×3 refinement')
        ax2.set_xlabel('X coordinate')
        ax2.set_ylabel('Y coordinate')
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'lgr_grids.png'), dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  Grid visualization saved to: {os.path.join(output_dir, 'lgr_grids.png')}")
        
    except Exception as e:
        print(f"  Note: Could not create visualization: {e}")

def run_model():
    """Run the LGR utilities demonstration"""
    
    print("Starting LGR utilities demonstration...")
    
    try:
        # Demonstrate basic LGR functionality
        lgr1 = demonstrate_lgr_basics()
        
        # Demonstrate variable spacing
        lgr2 = demonstrate_variable_spacing()
        
        # Demonstrate DISV conversion
        lgr3, gridprops = demonstrate_disv_conversion()
        
        # Demonstrate exchange data
        exchange_data = demonstrate_exchange_data()
        
        # Create visualizations
        create_visualization()
        
        print("\n" + "="*50)
        print("LGR UTILITIES DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("="*50)
        
        print(f"\nSummary of demonstrations:")
        print(f"  1. Basic LGR: {lgr1.get_shape()} child shape")
        print(f"  2. Variable spacing: {len(lgr2.delr)} child cells")  
        print(f"  3. DISV conversion: {gridprops['ncpl']} cells per layer")
        print(f"  4. Exchange data: {len(exchange_data)} connections")
        print(f"  5. Visualizations: Created grid comparison plots")
        
        print(f"\nKey insights:")
        print(f"  - LGR utilities handle complex grid refinement calculations")
        print(f"  - Variable parent spacing is properly handled in child grids")
        print(f"  - DISV conversion enables unstructured grid modeling")
        print(f"  - Exchange data manages parent-child grid connections")
        print(f"  - No MODFLOW execution required - pure utility functions")
        
        return True
        
    except Exception as e:
        print(f"\n{'='*50}")
        print("LGR UTILITIES DEMONSTRATION FAILED")
        print("="*50)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    run_model()