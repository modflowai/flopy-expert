#!/usr/bin/env python3
"""
Standalone FloPy model demonstrating binary file operations
Extracted from: test_binaryfile.py

Demonstrates Phase 7: Post-processing with focus on binary file I/O
"""

import flopy
import numpy as np
from pathlib import Path
import sys
sys.path.append('/home/danilopezmella/flopy_expert/test_review')
from mf6_config import get_mf6_exe

def build_model(ws="./model_output", name="binary_demo"):
    """
    Build a simple MODFLOW 6 model to generate binary output files
    for demonstrating reading/writing operations.
    """
    
    # Ensure workspace exists
    Path(ws).mkdir(exist_ok=True)
    
    # ========================================
    # PHASE 1: DISCRETIZATION
    # ========================================
    print("Phase 1: Setting up discretization...")
    
    # Create simulation
    sim = flopy.mf6.MFSimulation(
        sim_name=name, 
        sim_ws=ws, 
        exe_name=get_mf6_exe()
    )
    
    # Time discretization - transient with multiple steps
    tdis = flopy.mf6.ModflowTdis(
        sim, 
        nper=2,
        perioddata=[
            (10.0, 5, 1.0),  # 10 days, 5 steps
            (10.0, 5, 1.0),  # 10 days, 5 steps
        ]
    )
    
    # ========================================
    # PHASE 5: SOLVER CONFIGURATION
    # ========================================
    print("Phase 5: Configuring solver...")
    
    ims = flopy.mf6.ModflowIms(
        sim,
        print_option="SUMMARY",
        complexity="SIMPLE"
    )
    
    # Create groundwater flow model
    gwf = flopy.mf6.ModflowGwf(sim, modelname=name, save_flows=True)
    
    # Structured discretization
    dis = flopy.mf6.ModflowGwfdis(
        gwf,
        nlay=2,
        nrow=10,
        ncol=10,
        delr=100.0,
        delc=100.0,
        top=0.0,
        botm=[-10.0, -20.0]
    )
    
    # ========================================
    # PHASE 2: PROPERTIES
    # ========================================
    print("Phase 2: Setting hydraulic properties...")
    
    npf = flopy.mf6.ModflowGwfnpf(
        gwf,
        save_specific_discharge=True,
        icelltype=1,  # Convertible
        k=[10.0, 5.0]  # Different K for each layer
    )
    
    # Storage for transient simulation
    sto = flopy.mf6.ModflowGwfsto(
        gwf,
        steady_state=False,
        transient=True,
        ss=1e-5,
        sy=0.1
    )
    
    # ========================================
    # PHASE 3: INITIAL CONDITIONS
    # ========================================
    print("Phase 3: Setting initial conditions...")
    
    ic = flopy.mf6.ModflowGwfic(gwf, strt=0.0)
    
    # ========================================
    # PHASE 4: BOUNDARY CONDITIONS
    # ========================================
    print("Phase 4: Setting boundary conditions...")
    
    # Constant head boundaries
    chd = flopy.mf6.ModflowGwfchd(
        gwf,
        stress_period_data=[
            [(0, 0, 0), 10.0],   # High head
            [(1, 9, 9), -5.0],   # Low head
        ]
    )
    
    # Recharge
    rch = flopy.mf6.ModflowGwfrcha(
        gwf,
        recharge=0.001  # 1 mm/day
    )
    
    # ========================================
    # OUTPUT CONTROL
    # ========================================
    print("Setting up output control...")
    
    oc = flopy.mf6.ModflowGwfoc(
        gwf,
        budget_filerecord=f"{name}.cbb",
        head_filerecord=f"{name}.hds",
        saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")]
    )
    
    return sim, gwf

def demonstrate_binary_operations(sim, gwf):
    """
    PHASE 7: POST-PROCESSING
    Demonstrate various binary file operations
    """
    print("\n" + "="*60)
    print("Phase 7: Post-processing - Binary File Operations")
    print("="*60)
    
    from flopy.utils import HeadFile, CellBudgetFile, BinaryHeader, Util2d
    from flopy.utils.binaryfile import get_headfile_precision
    
    ws = Path(sim.sim_path)
    
    # ========================================
    # 1. READ BINARY OUTPUT FILES
    # ========================================
    print("\n1. Reading binary output files...")
    
    # Head file
    head_file = ws / f"{gwf.name}.hds"
    hf = HeadFile(head_file)
    
    # Get times and stress periods
    times = hf.get_times()
    kstpkper = hf.get_kstpkper()
    print(f"   Times: {times[:5]}... (showing first 5)")
    print(f"   (kstp, kper): {kstpkper[:3]}... (showing first 3)")
    
    # Get head data different ways
    head_by_time = hf.get_data(totim=times[0])
    head_by_kstpkper = hf.get_data(kstpkper=kstpkper[0])
    head_by_idx = hf.get_data(idx=0)
    
    print(f"   Head shape: {head_by_time.shape}")
    print(f"   Head range: {head_by_time.min():.2f} to {head_by_time.max():.2f}")
    
    # Budget file
    budget_file = ws / f"{gwf.name}.cbb"
    bf = CellBudgetFile(budget_file)
    
    print(f"\n   Budget records: {bf.get_unique_record_names()}")
    
    # ========================================
    # 2. EXTRACT TIME SERIES
    # ========================================
    print("\n2. Extracting time series data...")
    
    # Time series for specific cell
    ts = hf.get_ts((0, 5, 5))  # Layer 0, row 5, col 5
    print(f"   Time series shape: {ts.shape}")
    print(f"   Cell (0,5,5) head evolution:")
    for i in range(min(3, len(ts))):
        print(f"     Time {ts[i,0]:.1f}: {ts[i,1]:.3f} m")
    
    # ========================================
    # 3. DETECT PRECISION
    # ========================================
    print("\n3. Detecting file precision...")
    
    precision = get_headfile_precision(head_file)
    print(f"   Head file precision: {precision}")
    
    # ========================================
    # 4. WRITE CUSTOM BINARY FILE
    # ========================================
    print("\n4. Writing custom binary files...")
    
    # Write double precision file
    custom_data = np.random.randn(10, 10) * 5.0  # Random heads
    
    # Create header for double precision
    header_double = BinaryHeader.create(
        bintype="HEAD",
        precision="double",
        text="HEAD",
        nrow=10,
        ncol=10,
        ilay=1,
        pertim=1.0,
        totim=1.0,
        kstp=1,
        kper=1,
    )
    
    double_file = ws / "custom_double.hds"
    Util2d.write_bin(
        custom_data.shape, 
        double_file, 
        custom_data.astype(np.float64),
        header_data=header_double
    )
    print(f"   Written double precision file: {double_file.name}")
    
    # Create header for single precision
    header_single = BinaryHeader.create(
        bintype="HEAD",
        precision="single",
        text="HEAD",
        nrow=10,
        ncol=10,
        ilay=1,
        pertim=1.0,
        totim=1.0,
        kstp=1,
        kper=1,
    )
    
    single_file = ws / "custom_single.hds"
    Util2d.write_bin(
        custom_data.shape,
        single_file,
        custom_data.astype(np.float32),
        header_data=header_single
    )
    print(f"   Written single precision file: {single_file.name}")
    
    # ========================================
    # 5. VERIFY CUSTOM FILES
    # ========================================
    print("\n5. Verifying custom binary files...")
    
    # Read back and verify
    hf_double = HeadFile(double_file, precision="double")
    hf_single = HeadFile(single_file, precision="single")
    
    data_double = hf_double.get_data()
    data_single = hf_single.get_data()
    
    print(f"   Double precision data range: {data_double.min():.6f} to {data_double.max():.6f}")
    print(f"   Single precision data range: {data_single.min():.6f} to {data_single.max():.6f}")
    print(f"   Precision difference max: {np.abs(data_double - data_single).max():.9f}")
    
    # ========================================
    # 6. USE CONTEXT MANAGERS
    # ========================================
    print("\n6. Demonstrating context manager usage...")
    
    with HeadFile(head_file) as hf_context:
        data = hf_context.get_data(idx=0)
        print(f"   Read data with context manager: shape {data.shape}")
        print(f"   File automatically closed after context")
    
    # Verify file is closed
    try:
        hf_context.get_data()
    except ValueError as e:
        print(f"   Confirmed: {e}")
    
    print("\n" + "="*60)
    print("Binary file operations demonstration complete!")
    print("="*60)

def run_model():
    """Run the model and demonstrate binary file operations"""
    
    print("="*70)
    print("MODFLOW 6 Binary File Operations Demonstration")
    print("="*70 + "\n")
    
    # Build model
    sim, gwf = build_model()
    
    # Write and run
    print("\nWriting and running simulation...")
    sim.write_simulation()
    success, buff = sim.run_simulation()
    
    if not success:
        print("ERROR: Model failed to converge!")
        return None
    
    print("✓ Model ran successfully!\n")
    
    # Demonstrate binary operations
    demonstrate_binary_operations(sim, gwf)
    
    return sim, gwf

if __name__ == "__main__":
    run_model()