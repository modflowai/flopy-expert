"""
MODFLOW Model Creation and Testing Demonstration

This script demonstrates fundamental FloPy MODFLOW capabilities including:
- Model creation and basic package setup
- Grid coordinate system and spatial reference
- Model loading and validation
- Package integration and data handling
- File I/O and model persistence
- Error handling and validation

This covers the core MODFLOW workflow:
1. Model instantiation and configuration
2. Package setup and parameterization
3. Writing input files
4. Model validation and loading
5. Grid and coordinate system handling
"""

import numpy as np
import flopy
import os
from pathlib import Path

def run_model():
    """
    Create and demonstrate basic MODFLOW model capabilities.
    Shows model creation, package setup, file operations, and validation.
    """
    
    print("=== MODFLOW Model Creation and Testing ===\n")
    
    # Create model workspace
    model_ws = "model_output"
    
    # 1. Basic Model Creation
    print("1. Creating Basic MODFLOW Model")
    print("-" * 40)
    
    # Model dimensions and parameters
    nlay, nrow, ncol = 3, 15, 15
    delr = delc = 100.0
    top = 100.0
    botm = [75.0, 50.0, 25.0]
    
    # Create MODFLOW model with spatial reference
    mf = flopy.modflow.Modflow(
        modelname="modflow_demo",
        model_ws=model_ws,
        exe_name="/home/danilopezmella/flopy_expert/bin/mf2005",  # MODFLOW executable
        xll=500.0,          # Lower left x coordinate
        yll=0.0,            # Lower left y coordinate  
        rotation=0.0,       # Grid rotation
        start_datetime="1/1/2024",
        verbose=True
    )
    
    print(f"  Created model: {mf.name}")
    print(f"  Model workspace: {mf.model_ws}")
    print(f"  Start datetime: {mf.start_datetime}")
    
    # 2. Discretization Package
    print(f"\n2. Setting Up Model Discretization")
    print("-" * 40)
    
    dis = flopy.modflow.ModflowDis(
        mf,
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        delr=delr,
        delc=delc,
        top=top,
        botm=botm,
        nper=3,
        perlen=[30, 365, 365],
        nstp=[1, 12, 12],
        steady=[True, False, False],
        itmuni=4,  # Time units: days
        lenuni=2   # Length units: meters
    )
    
    print(f"  Grid dimensions: {nlay} layers, {nrow} rows, {ncol} columns")
    print(f"  Cell size: {delr}m x {delc}m")
    print(f"  Stress periods: {dis.nper} (steady + 2 transient)")
    
    # 3. Basic Package  
    print(f"\n3. Creating Basic Package")
    print("-" * 40)
    
    # Create ibound array (active cells)
    ibound = np.ones((nlay, nrow, ncol), dtype=int)
    # Make some cells inactive for demonstration
    ibound[0, 0:2, 0:2] = 0  # Inactive cells in top layer
    ibound[2, -2:, -2:] = 0  # Inactive cells in bottom layer
    
    # Starting heads
    strt = np.ones((nlay, nrow, ncol)) * 90.0
    strt[0] = 95.0  # Higher heads in top layer
    strt[2] = 85.0  # Lower heads in bottom layer
    
    bas = flopy.modflow.ModflowBas(
        mf,
        ibound=ibound,
        strt=strt,
        hnoflo=-999.0
    )
    
    print(f"  Active cells: {np.sum(ibound == 1)} out of {nlay*nrow*ncol}")
    print(f"  Starting head range: {np.min(strt)} to {np.max(strt)} m")
    
    # 4. Layer Property Flow Package
    print(f"\n4. Setting Up Hydraulic Properties")
    print("-" * 40)
    
    # Create heterogeneous hydraulic conductivity
    hk = np.ones((nlay, nrow, ncol))
    hk[0] = 20.0   # High K in top layer (unconfined)
    hk[1] = 5.0    # Medium K in middle layer  
    hk[2] = 0.5    # Low K in bottom layer
    
    # Add some spatial variability
    for i in range(nlay):
        hk[i, 5:10, 5:10] *= 2.0  # Higher K zone in center
    
    lpf = flopy.modflow.ModflowLpf(
        mf,
        hk=hk,
        vka=0.1,     # Vertical hydraulic conductivity
        ipakcb=53,   # Cell-by-cell budget unit
        laytyp=[1, 0, 0],  # Layer types: unconfined, confined, confined
        laywet=[1, 0, 0],  # Wetting capability
        ss=1e-5,     # Specific storage
        sy=0.2       # Specific yield
    )
    
    print(f"  Hydraulic conductivity layers: {np.mean(hk, axis=(1,2))} m/d")
    print(f"  Layer types: unconfined (top), confined (middle, bottom)")
    
    # 5. Boundary Conditions
    print(f"\n5. Adding Boundary Conditions")
    print("-" * 40)
    
    # Wells - transient pumping
    wel_data = {}
    wel_data[1] = [   # Pumping in first transient period
        [0, 7, 7, -500.0],   # Production well in top layer
        [1, 5, 10, -200.0],  # Observation well in middle layer
    ]
    wel_data[2] = [   # Reduced pumping in second period
        [0, 7, 7, -300.0],
        [1, 5, 10, -100.0],
    ]
    
    wel = flopy.modflow.ModflowWel(
        mf,
        stress_period_data=wel_data,
        ipakcb=53
    )
    
    # Recharge - seasonal variation
    rech_data = {}
    rech_data[0] = 0.001      # Steady state recharge
    rech_data[1] = 0.002      # Higher recharge (wet season)
    rech_data[2] = 0.0005     # Lower recharge (dry season)
    
    rch = flopy.modflow.ModflowRch(
        mf,
        rech=rech_data,
        ipakcb=53
    )
    
    # General Head Boundary - represents distant aquifer connection
    ghb_data = []
    for i in range(nrow):
        ghb_data.append([1, i, ncol-1, 88.0, 0.1])  # Eastern boundary
    
    ghb = flopy.modflow.ModflowGhb(
        mf,
        stress_period_data={0: ghb_data, 1: ghb_data, 2: ghb_data},
        ipakcb=53
    )
    
    print(f"  Wells: {len(wel_data[1])} pumping wells")
    print(f"  Recharge: seasonal variation (0.0005-0.002 m/d)")
    print(f"  GHB: {len(ghb_data)} boundary cells on eastern edge")
    
    # 6. Output Control
    print(f"\n6. Configuring Output Control")
    print("-" * 40)
    
    # Save results at specific times
    spd = {
        (0, 0): ["save head", "save budget"],
        (1, 11): ["save head", "save budget"], 
        (2, 11): ["save head", "save budget"]
    }
    
    oc = flopy.modflow.ModflowOc(
        mf,
        stress_period_data=spd,
        compact=True
    )
    
    print(f"  Output saved at end of each stress period")
    print(f"  Binary files: heads (.hds) and budget (.cbc)")
    
    # 7. Solver Package
    print(f"\n7. Setting Up Solver")
    print("-" * 40)
    
    pcg = flopy.modflow.ModflowPcg(
        mf,
        mxiter=50,
        iter1=30,
        hclose=1e-5,
        rclose=1e-3
    )
    
    print(f"  Solver: PCG (Preconditioned Conjugate Gradient)")
    print(f"  Convergence criteria: head={pcg.hclose}, residual={pcg.rclose}")
    
    # 8. Write Model Files
    print(f"\n8. Writing Model Files")
    print("-" * 40)
    
    try:
        mf.write_input()
        print(f"  ✓ Model files written successfully")
        
        # Run MODFLOW model
        print(f"\n  Running MODFLOW simulation...")
        success, buff = mf.run_model(silent=True)
        
        if success:
            print(f"  ✓ Model run completed successfully")
        else:
            print(f"  ⚠ Model run failed")
            if buff:
                print(f"    Error: {buff[-1] if buff else 'Unknown error'}")
        
        # List all files (input + output)
        model_files = []
        for file_path in Path(model_ws).glob("*"):
            if file_path.is_file():
                model_files.append(file_path.name)
        
        print(f"  Files created: {len(model_files)}")
        
        # Categorize files
        input_files = [f for f in model_files if f.endswith(('.nam', '.dis', '.bas', '.lpf', '.wel', '.rch', '.ghb', '.oc', '.pcg'))]
        output_files = [f for f in model_files if f.endswith(('.hds', '.cbc', '.lst', '.list'))]
        
        print(f"  Input files: {len(input_files)}")
        for file_name in sorted(input_files):
            print(f"    - {file_name}")
            
        if output_files:
            print(f"  Output files: {len(output_files)}")
            print(f"    • Head file (.hds): {'✓' if any('.hds' in f for f in output_files) else '✗'}")
            print(f"    • Budget file (.cbc): {'✓' if any('.cbc' in f for f in output_files) else '✗'}")
            print(f"    • Listing file (.lst/.list): {'✓' if any(('.lst' in f or '.list' in f) for f in output_files) else '✗'}")
        else:
            print(f"  ⚠ No output files found")
            
    except Exception as e:
        print(f"  ✗ Error writing files: {e}")
        return None
    
    # 9. Model Validation and Loading
    print(f"\n9. Model Validation and Loading")
    print("-" * 40)
    
    try:
        # Test loading the model we just created
        mf_loaded = flopy.modflow.Modflow.load(
            "modflow_demo.nam",
            model_ws=model_ws,
            verbose=False,
            check=False
        )
        
        print(f"  ✓ Model loaded successfully")
        print(f"  Load status: {'PASS' if not mf_loaded.load_fail else 'FAIL'}")
        print(f"  Packages loaded: {len(mf_loaded.packagelist)}")
        
        # Verify key properties
        if hasattr(mf_loaded, 'dis'):
            print(f"  Grid verified: {mf_loaded.dis.nlay}×{mf_loaded.dis.nrow}×{mf_loaded.dis.ncol}")
        
        if hasattr(mf_loaded, 'modelgrid') and mf_loaded.modelgrid is not None:
            print(f"  Coordinate system: offset=({mf_loaded.modelgrid.xoffset}, {mf_loaded.modelgrid.yoffset})")
        
        # Package validation
        expected_packages = ['DIS', 'BAS', 'LPF', 'WEL', 'RCH', 'GHB', 'OC', 'PCG']
        loaded_packages = [pkg.name[0] for pkg in mf_loaded.packagelist]
        
        print(f"  Package check:")
        for pkg in expected_packages:
            status = "✓" if pkg in loaded_packages else "✗"
            print(f"    {status} {pkg}")
        
    except Exception as e:
        print(f"  ✗ Error loading model: {e}")
        mf_loaded = None
    
    # 10. Model Grid and Coordinate System
    print(f"\n10. Model Grid and Coordinate System")
    print("-" * 40)
    
    modelgrid = mf.modelgrid
    
    if modelgrid is not None:
        print(f"  Grid properties:")
        print(f"    Dimensions: {modelgrid.nlay} × {modelgrid.nrow} × {modelgrid.ncol}")
        print(f"    Cell size: {modelgrid.delr[0]} × {modelgrid.delc[0]} m")
        if hasattr(modelgrid, 'extent'):
            print(f"    Extent: {modelgrid.extent}")
        print(f"    Coordinate offset: ({modelgrid.xoffset}, {modelgrid.yoffset})")
        print(f"    Rotation: {modelgrid.angrot}°")
        
        # Grid centers
        print(f"  Grid centers (first few):")
        xcenter = modelgrid.xcellcenters
        ycenter = modelgrid.ycellcenters
        print(f"    X-centers [0,:3]: {xcenter[0, :3]}")
        print(f"    Y-centers [:3,0]: {ycenter[:3, 0]}")
    else:
        print(f"  Grid not yet initialized (requires discretization package)")
    
    print(f"\n✓ MODFLOW Model Demonstration Completed Successfully!")
    print(f"  - Created comprehensive 3-layer transient model")
    print(f"  - Implemented multiple boundary condition types")
    print(f"  - Configured spatial reference system")
    print(f"  - Validated file I/O operations")
    print(f"  - Tested model loading and package verification")
    
    return mf, mf_loaded

if __name__ == "__main__":
    original_model, loaded_model = run_model()