#!/usr/bin/env python3

"""
MODFLOW DIS Package and Spatial Reference Demonstration

This model demonstrates the MODFLOW DIS (Discretization) package capabilities:
- Spatial discretization with rotation and coordinate reference systems
- Grid coordinate transformations
- ModelGrid functionality with real-world coordinates
- Spatial reference system integration (CRS/EPSG codes)

Based on test_modflowdis.py from the FloPy autotest suite.
"""

import numpy as np
import flopy
from pathlib import Path
import matplotlib.pyplot as plt
import os
import sys

# Add the config directory to the path
config_dir = Path(__file__).parent.parent.parent.parent / "config"
sys.path.append(str(config_dir))

try:
    from mf2005_config import mf2005_exe_path
except ImportError:
    # Use the actual mf2005 executable path
    mf2005_exe_path = "/home/danilopezmella/flopy_expert/bin/mf2005"
    if not Path(mf2005_exe_path).exists():
        mf2005_exe_path = "mf2005"
        print(f"Warning: Using default mf2005 executable name.")

def create_dis_model_with_spatial_ref():
    """Create MODFLOW model with DIS package demonstrating spatial reference capabilities."""
    
    print("Creating MODFLOW DIS spatial reference demonstration...")
    
    # Model workspace
    workspace = Path("dis_spatial_ref")
    workspace.mkdir(exist_ok=True)
    
    # Grid parameters (similar to test case)
    delr = 640  # Column spacing in meters
    delc = 640  # Row spacing in meters  
    nrow = int(np.ceil(59040.0 / delc))  # ~92 rows
    ncol = int(np.ceil(33128.0 / delr))  # ~52 columns
    nlay = 3
    
    print(f"Grid dimensions: {nlay} layers, {nrow} rows, {ncol} columns")
    print(f"Cell size: {delr}m x {delc}m")
    
    # Real-world coordinates (example from Montana State Plane)
    xul = 2746975.089  # X coordinate of upper-left corner
    yul = 1171446.45   # Y coordinate of upper-left corner  
    rotation = -39     # Grid rotation in degrees
    
    # Create MODFLOW model
    mf = flopy.modflow.Modflow(
        modelname="dis_demo",
        model_ws=str(workspace),
        exe_name=mf2005_exe_path
    )
    
    # Layer elevations
    top = 100.0
    botm = [80.0, 60.0, 40.0]
    
    # Create DIS package with spatial reference
    dis = flopy.modflow.ModflowDis(
        mf,
        nlay=nlay,
        nrow=nrow, 
        ncol=ncol,
        delr=delr,
        delc=delc,
        top=top,
        botm=botm,
        lenuni=1,  # Length units: feet
        itmuni=1,  # Time units: seconds
        rotation=rotation,
        xul=xul,
        yul=yul,
        crs="epsg:2243"  # Montana State Plane West (EPSG:2243)
    )
    
    print(f"Spatial reference: EPSG:2243 (Montana State Plane West)")
    print(f"Upper-left corner: ({xul}, {yul})")
    print(f"Grid rotation: {rotation}°")
    
    # Add essential packages to make it runnable
    bas = flopy.modflow.ModflowBas(mf)
    lpf = flopy.modflow.ModflowLpf(mf, hk=10.0, vka=10.0)
    
    # Add constant head boundaries on edges
    chd_spd = []
    for i in range(nrow):
        chd_spd.append([0, i, 0, 95.0, 95.0])  # Left edge
        chd_spd.append([0, i, ncol-1, 85.0, 85.0])  # Right edge
    chd = flopy.modflow.ModflowChd(mf, stress_period_data=chd_spd)
    
    # Output control to save heads and budget
    spd = {(0, 0): ['save head', 'save budget']}
    oc = flopy.modflow.ModflowOc(mf, stress_period_data=spd)
    
    # Solver
    pcg = flopy.modflow.ModflowPcg(mf)
    
    return mf, workspace

def demonstrate_grid_capabilities(mf):
    """Demonstrate ModelGrid coordinate transformation capabilities."""
    
    print("\nDemonstrating ModelGrid capabilities...")
    
    # Get the model grid
    mg = mf.modelgrid
    
    # Test coordinate transformations (from test case)
    delc = mf.dis.delc.array[0]
    nrow = mf.dis.nrow
    
    # Get coordinates at specific location
    x, y = mg.get_coords(0, delc * nrow)
    
    print(f"Grid properties:")
    print(f"  EPSG code: {mg.epsg}")
    print(f"  Rotation angle: {mg.angrot}°")
    print(f"  Grid origin: ({mg.xoffset}, {mg.yoffset})")
    print(f"  Grid extent: {mg.extent}")
    
    # Test coordinate at upper-left corner  
    xul_expected = 2746975.089
    yul_expected = 1171446.45
    print(f"Coordinate test:")
    print(f"  Expected upper-left: ({xul_expected}, {yul_expected})")
    print(f"  Calculated position: ({x:.3f}, {y:.3f})")
    print(f"  Match: {np.allclose([x, y], [xul_expected, yul_expected])}")
    
    # Get grid cell centers
    xcenters = mg.xcellcenters
    ycenters = mg.ycellcenters
    
    print(f"Cell centers:")
    print(f"  X range: {xcenters.min():.1f} to {xcenters.max():.1f}")
    print(f"  Y range: {ycenters.min():.1f} to {ycenters.max():.1f}")
    
    return True

def create_additional_dis_packages(workspace):
    """Create additional DIS package demonstrations."""
    
    print("\nCreating additional DIS package demonstrations...")
    
    # 1. Simple structured grid
    mf_simple = flopy.modflow.Modflow(
        modelname="dis_simple",
        model_ws=str(workspace),
        exe_name=mf2005_exe_path
    )
    
    dis_simple = flopy.modflow.ModflowDis(
        mf_simple,
        nlay=2,
        nrow=10,
        ncol=10,
        delr=100.0,
        delc=100.0,
        top=50.0,
        botm=[25.0, 0.0],
        lenuni=2  # Meters
    )
    
    # Add packages to make it runnable
    bas_simple = flopy.modflow.ModflowBas(mf_simple)
    lpf_simple = flopy.modflow.ModflowLpf(mf_simple, hk=5.0)
    chd_simple = flopy.modflow.ModflowChd(mf_simple, 
        stress_period_data=[[0, 0, 0, 50.0, 50.0], [0, 9, 9, 45.0, 45.0]])
    oc_simple = flopy.modflow.ModflowOc(mf_simple, 
        stress_period_data={(0, 0): ['save head', 'save budget']})
    pcg_simple = flopy.modflow.ModflowPcg(mf_simple)
    
    # 2. Variable spacing grid
    mf_variable = flopy.modflow.Modflow(
        modelname="dis_variable",
        model_ws=str(workspace),
        exe_name=mf2005_exe_path
    )
    
    # Create variable spacing - finer in center
    ncol = 21
    nrow = 11
    delr_array = np.ones(ncol) * 200.0
    delr_array[8:13] = 50.0  # Finer spacing in center columns
    
    delc_array = np.ones(nrow) * 200.0
    delc_array[4:7] = 50.0   # Finer spacing in center rows
    
    dis_variable = flopy.modflow.ModflowDis(
        mf_variable,
        nlay=1,
        nrow=nrow,
        ncol=ncol,
        delr=delr_array,
        delc=delc_array,
        top=30.0,
        botm=[0.0]
    )
    
    # Add packages to make it runnable
    bas_variable = flopy.modflow.ModflowBas(mf_variable)
    lpf_variable = flopy.modflow.ModflowLpf(mf_variable, hk=2.0)
    wel_variable = flopy.modflow.ModflowWel(mf_variable,
        stress_period_data=[[0, 5, 10, -100.0]])  # Pumping well in center
    oc_variable = flopy.modflow.ModflowOc(mf_variable,
        stress_period_data={(0, 0): ['save head', 'save budget']})
    pcg_variable = flopy.modflow.ModflowPcg(mf_variable)
    
    print(f"  Simple grid: 2 layers, 10x10 cells, uniform 100m spacing")
    print(f"  Variable grid: 1 layer, {nrow}x{ncol} cells, variable spacing")
    print(f"    Column widths: {delr_array.min()}-{delr_array.max()}m")
    print(f"    Row heights: {delc_array.min()}-{delc_array.max()}m")
    
    return [mf_simple, mf_variable]

def write_and_test_models(models, workspace):
    """Write model files and test DIS package."""
    
    print("\nWriting and testing models...")
    
    results = {
        "models_created": len(models),
        "files_written": [],
        "grid_tests_passed": 0,
        "total_tests": 0,
        "models_run": 0
    }
    
    for mf in models:
        try:
            # Write model files
            mf.write_input()
            print(f"  ✓ Model '{mf.name}' files written")
            
            # Try to run the model
            try:
                success, buff = mf.run_model(silent=True)
                if success:
                    results["models_run"] += 1
                    print(f"  ✓ Model '{mf.name}' ran successfully")
                    
                    # Check for output files
                    hds_file = Path(workspace) / f"{mf.name}.hds"
                    cbc_file = Path(workspace) / f"{mf.name}.cbc"
                    if hds_file.exists():
                        results["files_written"].append(hds_file.name)
                    if cbc_file.exists():
                        results["files_written"].append(cbc_file.name)
            except Exception as e:
                print(f"  ! Model '{mf.name}' could not run: {e}")
            
            # Check DIS file was created
            dis_file = Path(workspace) / f"{mf.name}.dis"
            if dis_file.exists():
                results["files_written"].append(dis_file.name)
                
            # Test grid properties
            results["total_tests"] += 1
            mg = mf.modelgrid
            
            # Basic grid tests
            if hasattr(mg, 'nrow') and hasattr(mg, 'ncol') and hasattr(mg, 'nlay'):
                if mg.nrow > 0 and mg.ncol > 0 and mg.nlay > 0:
                    results["grid_tests_passed"] += 1
                    print(f"  ✓ Grid dimensions valid: {mg.nlay}x{mg.nrow}x{mg.ncol}")
                    
        except Exception as e:
            print(f"  ✗ Error with model '{mf.name}': {e}")
    
    return results

def create_grid_visualization(mf, workspace):
    """Create visualization of the model grid."""
    
    try:
        import matplotlib.pyplot as plt
        
        print("\nCreating grid visualization...")
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Plot 1: Grid cells
        mg = mf.modelgrid
        mg.plot(ax=ax1)
        ax1.set_title(f"Model Grid - {mf.name}")
        ax1.set_xlabel("X Coordinate")
        ax1.set_ylabel("Y Coordinate")
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Cross section showing layers
        if hasattr(mf.dis, 'top') and hasattr(mf.dis, 'botm'):
            top = mf.dis.top.array
            botm = mf.dis.botm.array
            
            # Create a cross-section through middle row
            mid_row = mf.dis.nrow // 2
            x = np.arange(mf.dis.ncol) * mf.dis.delr.array[0]
            
            # Plot layer boundaries
            if np.isscalar(top):
                top_profile = np.ones(mf.dis.ncol) * top
            else:
                top_profile = top[mid_row, :] if top.ndim == 2 else np.ones(mf.dis.ncol) * top
                
            ax2.plot(x, top_profile, 'b-', linewidth=2, label='Top')
            
            for i, bot in enumerate(botm):
                if np.isscalar(bot):
                    bot_profile = np.ones(mf.dis.ncol) * bot
                else:
                    bot_profile = bot[mid_row, :] if bot.ndim == 2 else np.ones(mf.dis.ncol) * bot
                ax2.plot(x, bot_profile, 'r-', linewidth=1, label=f'Layer {i+1} bottom')
            
            ax2.set_title("Cross-Section (Middle Row)")
            ax2.set_xlabel("Distance (m)")
            ax2.set_ylabel("Elevation (m)")
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        plot_file = workspace / f"{mf.name}_grid.png"
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  ✓ Grid visualization saved: {plot_file.name}")
        return plot_file.name
        
    except ImportError:
        print("  ! matplotlib not available, skipping visualization")
        return None
    except Exception as e:
        print(f"  ✗ Error creating visualization: {e}")
        return None

def main():
    """Main function to demonstrate MODFLOW DIS package functionality."""
    
    print("=" * 60)
    print("MODFLOW DIS Package and Spatial Reference Demonstration") 
    print("=" * 60)
    
    try:
        # Create main model with spatial reference
        mf_main, workspace = create_dis_model_with_spatial_ref()
        
        # Demonstrate grid capabilities
        grid_success = demonstrate_grid_capabilities(mf_main)
        
        # Create additional DIS examples
        additional_models = create_additional_dis_packages(workspace)
        all_models = [mf_main] + additional_models
        
        # Write and test all models
        results = write_and_test_models(all_models, workspace)
        
        # Create visualization
        plot_file = create_grid_visualization(mf_main, workspace)
        if plot_file:
            results["files_written"].append(plot_file)
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Models created: {results['models_created']}")
        print(f"Models run successfully: {results['models_run']}/{results['models_created']}")
        print(f"Grid tests passed: {results['grid_tests_passed']}/{results['total_tests']}")
        print(f"Files generated: {len(results['files_written'])}")
        
        if results["files_written"]:
            print("Output files:")
            for file in sorted(results["files_written"]):
                print(f"  - {file}")
        
        success = (results['grid_tests_passed'] == results['total_tests'] and 
                  results['models_created'] > 0)
        
        return success
        
    except Exception as e:
        print(f"✗ Error in main execution: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)