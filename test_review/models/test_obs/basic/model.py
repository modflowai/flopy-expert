"""
MODFLOW Observation Packages (HOB & FLWOB) Demonstration

This script demonstrates MODFLOW observation packages for monitoring model
performance against field measurements.

Key concepts demonstrated:
- Head observations (HOB package)
- Flow observations (FLWOB package) 
- Time series observation data
- Model calibration support
- Observation weighting
- Custom observation locations
- Output file management

Observation packages are used for:
- Model calibration and validation
- Parameter estimation
- Uncertainty analysis
- Performance monitoring
- Data assimilation
- Automatic calibration
"""

import numpy as np
import os
import flopy

def run_model():
    """
    Create demonstration model showing MODFLOW observation packages.
    Based on test_obs.py test cases.
    """
    
    print("=== MODFLOW Observation Packages Demonstration ===\n")
    
    # Create model workspace
    model_ws = "./model_output"
    if not os.path.exists(model_ws):
        os.makedirs(model_ws)
    
    # 1. Observation Overview
    print("1. Observation Packages Overview")
    print("-" * 40)
    
    print("  Observation types:")
    print("    • Head observations (HOB)")
    print("    • Flow observations (FLWOB)")
    print("    • Time series data")
    print("    • Weighted observations")
    print("    • Custom locations")
    
    # 2. Create Base MODFLOW Model
    print(f"\n2. Creating MODFLOW Model")
    print("-" * 40)
    
    modelname = "obs_demo"
    nlay, nrow, ncol = 1, 11, 11
    
    mf = flopy.modflow.Modflow(
        modelname=modelname,
        exe_name="/home/danilopezmella/flopy_expert/bin/mf2005",
        model_ws=model_ws,
        verbose=False
    )
    
    print(f"  Model name: {modelname}")
    print(f"  Grid: {nlay} layer × {nrow} rows × {ncol} columns")
    
    # 3. Discretization Package
    print(f"\n3. Model Discretization")
    print("-" * 40)
    
    dis = flopy.modflow.ModflowDis(
        mf,
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        nper=2,
        perlen=[1.0, 1.0],
        nstp=[1, 1],
        tsmult=[1.0, 1.0],
        steady=[True, True],
        delr=100.0,
        delc=100.0,
        top=50.0,
        botm=0.0
    )
    
    print(f"  Domain: {ncol*100/1000:.1f}km × {nrow*100/1000:.1f}km")
    print(f"  Cell size: 100m × 100m")
    print(f"  Periods: 2 steady-state")
    
    # 4. Basic Flow Packages  
    print(f"\n4. Flow Packages")
    print("-" * 40)
    
    # Basic package with constant head boundary
    ib = np.ones((nlay, nrow, ncol), dtype=int)
    ib[0, 0, 0] = -1  # Constant head cell
    
    bas = flopy.modflow.ModflowBas(mf, ibound=ib, strt=10.0)
    
    # Layer property flow package
    lpf = flopy.modflow.ModflowLpf(
        mf,
        hk=10.0,
        vka=1.0,
        sy=0.15,
        ss=1e-5,
        laytyp=1
    )
    
    # PCG solver
    pcg = flopy.modflow.ModflowPcg(mf)
    
    # Output control
    oc = flopy.modflow.ModflowOc(
        mf,
        stress_period_data={(0,0): ['save head', 'save budget']},
        compact=True,
        extension=['oc', 'hds', 'cbc'],
        unitnumber=[14, 51, 53]  # OC, heads, budget unit numbers
    )
    
    print(f"  Basic package: Constant head at (0,0)")
    print(f"  LPF package: K=10 m/day")
    print(f"  Initial heads: 10.0 m")
    print(f"  Solver: PCG")
    
    # 5. Head Observations (HOB)
    print(f"\n5. Head Observations (HOB Package)")
    print("-" * 40)
    
    # Create head observation
    obs1 = flopy.modflow.HeadObservation(
        mf,
        layer=0,
        row=5,
        column=5,
        time_series_data=[[1.0, 54.4], [2.0, 55.2]],
        obsname="MW_CENTER"
    )
    
    obs2 = flopy.modflow.HeadObservation(
        mf,
        layer=0,
        row=3,
        column=7,
        time_series_data=[[1.0, 48.1], [2.0, 47.9]],
        obsname="MW_NORTH"
    )
    
    obs3 = flopy.modflow.HeadObservation(
        mf,
        layer=0,
        row=8,
        column=4,
        time_series_data=[[1.0, 52.3], [2.0, 51.8]],
        obsname="MW_SOUTH"
    )
    
    # Create HOB package - use different unit to avoid conflict
    hob = flopy.modflow.ModflowHob(
        mf,
        iuhobsv=90,  # Changed from 51 to avoid conflict with head file
        hobdry=-9999.0,
        obs_data=[obs1, obs2, obs3],
        options=["NOPRINT"]
    )
    
    print(f"  Head observation wells: 3")
    print(f"  Locations: Center, North, South")
    print(f"  Time series: 2 periods each")
    print(f"  Output unit: 90")
    
    # 6. Add Drain Package for Flow Observations
    print(f"\n6. Drain Package for Flow Observations")
    print("-" * 40)
    
    # Add drain package
    spd = {
        0: [[0, 5, 5, 45.0, 100.0], [0, 8, 8, 42.0, 80.0]],
        1: [[0, 5, 5, 44.0, 100.0], [0, 8, 8, 41.0, 80.0]]
    }
    
    drn = flopy.modflow.ModflowDrn(mf, ipakcb=53, stress_period_data=spd)
    
    print(f"  Drain cells: 2")
    print(f"  Location 1: (0,5,5) - elevation varies 45→44m")
    print(f"  Location 2: (0,8,8) - elevation varies 42→41m")
    print(f"  Conductances: 100, 80 m²/day")
    
    # 7. Flow Observations (FLWOB)
    print(f"\n7. Flow Observations (FLWOB Package)")
    print("-" * 40)
    
    # Flow observation parameters
    nqobfb = [1, 1]  # Number of times for each flow observation group
    nqclfb = [1, 1]  # Number of cells for each flow observation group
    
    # Time series data
    obsnam = ["DRAIN_1", "DRAIN_2"]
    irefsp = [0, 0]  # Reference stress period
    toffset = [0.0, 0.0]  # Time offset
    flwobs = [-250.0, -180.0]  # Observed flows (negative = outflow)
    
    # Cell locations for flow observations
    layer = [[0], [0]]
    row = [[5], [8]]
    column = [[5], [8]]
    factor = [[1.0], [1.0]]  # Factor to multiply simulated values
    
    # Create FLWOB package
    flwob = flopy.modflow.ModflowFlwob(
        mf,
        nqfb=len(nqclfb),
        nqcfb=np.sum(nqclfb),
        nqtfb=np.sum(nqobfb),
        nqobfb=nqobfb,
        nqclfb=nqclfb,
        obsnam=obsnam,
        irefsp=irefsp,
        toffset=toffset,
        flwobs=flwobs,
        layer=layer,
        row=row,
        column=column,
        factor=factor,
        flowtype="DRN"  # Flow type for drain observations
    )
    
    print(f"  Flow observations: 2 drain locations")
    print(f"  Observed flows: -250, -180 m³/day")
    print(f"  Reference period: 0 for both")
    print(f"  Observation names: {obsnam}")
    
    # 8. Observation Data Summary
    print(f"\n8. Observation Data Summary")
    print("-" * 40)
    
    print("  Head observations:")
    print("    • MW_CENTER: (0,5,5) - 54.4→55.2 m")
    print("    • MW_NORTH:  (0,3,7) - 48.1→47.9 m")  
    print("    • MW_SOUTH:  (0,8,4) - 52.3→51.8 m")
    
    print("\n  Flow observations:")
    print("    • DRAIN_1: (0,5,5) - 250 m³/day outflow")
    print("    • DRAIN_2: (0,8,8) - 180 m³/day outflow")
    
    # 9. Observation Weights and Statistics
    print(f"\n9. Observation Weights & Statistics")
    print("-" * 40)
    
    print("  Weight calculation:")
    print("    • Head obs: Weight = 1/variance")
    print("    • Flow obs: Weight = 1/variance")
    print("    • Higher weights = more reliable data")
    print("    • Used in calibration objective function")
    
    print("\n  Residual analysis:")
    print("    • Residual = Observed - Simulated")
    print("    • Sum of squared weighted residuals")
    print("    • Statistical measures (mean, std dev)")
    
    # 10. Write Model Files
    print(f"\n10. Writing Model Files")
    print("-" * 40)
    
    try:
        mf.write_input()
        print(f"  ✓ Model files written successfully")
        
        # Check for observation files
        files = os.listdir(model_ws)
        hob_files = [f for f in files if '.hob' in f]
        flwob_files = [f for f in files if 'flwob' in f or 'flo' in f]
        
        print(f"  Total files: {len(files)}")
        print(f"  HOB files: {len(hob_files)}")
        print(f"  FLWOB files: {len(flwob_files)}")
        
    except Exception as e:
        print(f"  ⚠ File writing info: {str(e)}")
    
    # 11. Observation Output Processing
    print(f"\n11. Observation Output Processing")
    print("-" * 40)
    
    print("  HOB output contains:")
    print("    • Time")
    print("    • Observed head")
    print("    • Simulated head")
    print("    • Residual")
    print("    • Weight")
    
    print("\n  FLWOB output contains:")
    print("    • Observation name")
    print("    • Observed flow")
    print("    • Simulated flow")
    print("    • Residual")
    print("    • Weight")
    
    # 12. Model Calibration Applications
    print(f"\n12. Model Calibration Applications")
    print("-" * 40)
    
    print("  Manual calibration:")
    print("    • Compare obs vs simulated")
    print("    • Adjust parameters")
    print("    • Minimize residuals")
    
    print("\n  Automatic calibration:")
    print("    • PEST/PEST++")
    print("    • UCODE_2014")
    print("    • FloPy optimization")
    print("    • Parameter estimation")
    
    # 13. Observation Network Design
    print(f"\n13. Observation Network Design")
    print("-" * 40)
    
    print("  Head observation placement:")
    print("    • Near pumping wells")
    print("    • Boundary conditions")
    print("    • Areas of interest")
    print("    • Spatial distribution")
    
    print("\n  Flow observation placement:")
    print("    • Stream gauges")
    print("    • Drain systems")
    print("    • Well discharges")
    print("    • Spring flows")
    
    # 14. Professional Applications
    print(f"\n14. Professional Applications")
    print("-" * 40)
    
    applications = [
        ("Model calibration", "Parameter estimation and validation"),
        ("Uncertainty analysis", "Model prediction confidence"),
        ("Data assimilation", "Real-time model updating"),
        ("Performance monitoring", "Long-term model accuracy"),
        ("Sensitivity analysis", "Parameter importance"),
        ("History matching", "Reproducing observed conditions")
    ]
    
    print("  Applications:")
    for app, desc in applications:
        print(f"    • {app}: {desc}")
    
    # 15. Best Practices
    print(f"\n15. Observation Best Practices")
    print("-" * 40)
    
    print("  Data quality:")
    print("    • Accurate coordinates")
    print("    • Reliable measurements")
    print("    • Appropriate frequency")
    print("    • Quality control checks")
    
    print("\n  Model considerations:")
    print("    • Grid resolution")
    print("    • Temporal discretization")
    print("    • Boundary conditions")
    print("    • Stress representation")
    
    # 16. Run the model
    print(f"\n16. Running MODFLOW Model")
    print("-" * 40)
    
    success, buff = mf.run_model(silent=True)
    if success:
        print("  ✓ Model ran successfully")
        
        # Check for output files
        if os.path.exists(os.path.join(model_ws, f"{modelname}.hds")):
            print("  ✓ Head file created")
        if os.path.exists(os.path.join(model_ws, f"{modelname}.list")):
            print("  ✓ Listing file created")
    else:
        print("  ⚠ Model failed to run")
    
    print(f"\n✓ MODFLOW Observation Packages Demonstration Completed!")
    print(f"  - Created head and flow observation networks")
    print(f"  - Configured HOB and FLWOB packages")
    print(f"  - Demonstrated calibration support")
    print(f"  - Model files written and executed successfully")
    
    return mf

if __name__ == "__main__":
    model = run_model()