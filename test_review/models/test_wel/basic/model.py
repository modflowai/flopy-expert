"""
WEL - Well Package Advanced Demonstration

This script demonstrates the WEL (Well) package with advanced features.
Key concepts demonstrated:
- Standard well package configuration
- Auxiliary variables for well attributes
- Binary vs ASCII output formats
- Multi-layer well systems
- Time-varying pumping rates
- Well efficiency and skin effects (conceptual)
- get_empty() method for structured data entry

The WEL package is used for:
- Groundwater extraction and injection
- Water supply well fields
- Dewatering systems
- Remediation pump-and-treat
- Artificial recharge wells
- Monitoring well networks
- Agricultural irrigation wells
"""

import numpy as np
import os
import flopy

def run_model():
    """
    Create demonstration model with advanced WEL package features.
    Shows auxiliary variables, binary output, and structured data entry.
    """
    
    print("=== WEL Package Advanced Demonstration ===\n")
    
    # Create model workspace
    model_ws = "./model_output"
    
    # 1. WEL Package Overview
    print("1. WEL Package Overview")
    print("-" * 40)
    
    print("  WEL package capabilities:")
    print("    • Point source/sink for groundwater")
    print("    • Positive rates for injection")
    print("    • Negative rates for extraction")
    print("    • Auxiliary variables for attributes")
    print("    • Binary output option for large datasets")
    print("    • Time-varying pumping schedules")
    
    # 2. Create Base Model
    print(f"\n2. Creating Base MODFLOW Model")
    print("-" * 40)
    
    # Model dimensions
    model_name = "wel_demo"
    nlay, nrow, ncol = 3, 10, 10
    delr = delc = 100.0  # 100m cells
    top = 50.0
    botm = [30.0, 10.0, -10.0]
    
    # Create model
    mf = flopy.modflow.Modflow(
        modelname=model_name,
        exe_name="/home/danilopezmella/flopy_expert/bin/mf2005",
        model_ws=model_ws
    )
    
    print(f"  Model grid: {nlay}×{nrow}×{ncol} cells")
    print(f"  Cell size: {delr:.0f}m × {delc:.0f}m")
    print(f"  Domain: {ncol*delr/1000:.1f}km × {nrow*delc/1000:.1f}km")
    print(f"  Layers: 3 (shallow, middle, deep)")
    
    # 3. Discretization
    print(f"\n3. Model Discretization")
    print("-" * 40)
    
    # Time discretization
    nper = 3
    perlen = [365.0, 365.0, 365.0]  # Three 1-year periods
    nstp = [10, 10, 10]
    steady = [True, False, False]
    
    dis = flopy.modflow.ModflowDis(
        mf,
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        delr=delr,
        delc=delc,
        top=top,
        botm=botm,
        nper=nper,
        perlen=perlen,
        nstp=nstp,
        steady=steady
    )
    
    print(f"  Stress periods: {nper}")
    print(f"    Period 1: Steady-state baseline")
    print(f"    Period 2: Transient year 1")
    print(f"    Period 3: Transient year 2")
    
    # 4. Basic Package
    print(f"\n4. Basic Package Configuration")
    print("-" * 40)
    
    # Active cells
    ibound = np.ones((nlay, nrow, ncol), dtype=int)
    # Set constant head boundaries on edges
    ibound[:, 0, :] = -1   # North boundary
    ibound[:, -1, :] = -1  # South boundary
    ibound[:, :, 0] = -1   # West boundary
    ibound[:, :, -1] = -1  # East boundary
    
    # Initial heads
    strt = np.ones((nlay, nrow, ncol)) * 45.0
    
    bas = flopy.modflow.ModflowBas(mf, ibound=ibound, strt=strt)
    
    print(f"  Active cells: {np.sum(ibound > 0)}")
    print(f"  Constant head boundaries: {np.sum(ibound < 0)}")
    print(f"  Initial head: 45.0m uniform")
    
    # 5. Layer Property Flow
    print(f"\n5. Aquifer Properties")
    print("-" * 40)
    
    hk = [50.0, 10.0, 5.0]  # Decreasing K with depth
    vka = [10.0, 1.0, 0.5]  # Vertical K
    sy = 0.15  # Specific yield
    ss = 1e-5  # Specific storage
    
    lpf = flopy.modflow.ModflowLpf(
        mf,
        hk=hk,
        vka=vka,
        sy=sy,
        ss=ss,
        laytyp=[1, 0, 0],  # Top unconfined, others confined
        ipakcb=102  # Unit number for cell-by-cell budget
    )
    
    print(f"  Layer 1: Unconfined, K = {hk[0]:.1f} m/d")
    print(f"  Layer 2: Confined, K = {hk[1]:.1f} m/d")
    print(f"  Layer 3: Confined, K = {hk[2]:.1f} m/d")
    
    # 6. Well Package with Auxiliary Variables
    print(f"\n6. Well Package Configuration")
    print("-" * 40)
    
    # Define auxiliary variable names
    aux_names = ["well_id", "efficiency", "depth_m", "owner_code"]
    
    print(f"  Auxiliary variables:")
    for i, name in enumerate(aux_names, 1):
        print(f"    {i}. {name}")
    
    # 7. Creating Well Data with get_empty()
    print(f"\n7. Structured Well Data Creation")
    print("-" * 40)
    
    # Period 1: Initial wells
    ncells_p1 = 5  # 5 wells in period 1
    wel_p1 = flopy.modflow.ModflowWel.get_empty(
        ncells=ncells_p1,
        aux_names=aux_names
    )
    
    print(f"  Period 1: {ncells_p1} wells")
    print(f"  Data structure fields: {wel_p1.dtype.names}")
    
    # Municipal supply well
    wel_p1["k"][0] = 0  # Layer 1
    wel_p1["i"][0] = 5  # Row 6
    wel_p1["j"][0] = 5  # Column 6
    wel_p1["flux"][0] = -1500.0  # m³/day extraction
    wel_p1["well_id"][0] = 101
    wel_p1["efficiency"][0] = 0.85
    wel_p1["depth_m"][0] = 25.0
    wel_p1["owner_code"][0] = 1  # Municipal
    
    # Agricultural well 1
    wel_p1["k"][1] = 1  # Layer 2
    wel_p1["i"][1] = 3
    wel_p1["j"][1] = 3
    wel_p1["flux"][1] = -800.0
    wel_p1["well_id"][1] = 201
    wel_p1["efficiency"][1] = 0.75
    wel_p1["depth_m"][1] = 35.0
    wel_p1["owner_code"][1] = 2  # Agricultural
    
    # Agricultural well 2
    wel_p1["k"][2] = 1  # Layer 2
    wel_p1["i"][2] = 7
    wel_p1["j"][2] = 7
    wel_p1["flux"][2] = -600.0
    wel_p1["well_id"][2] = 202
    wel_p1["efficiency"][2] = 0.70
    wel_p1["depth_m"][2] = 38.0
    wel_p1["owner_code"][2] = 2  # Agricultural
    
    # Industrial well
    wel_p1["k"][3] = 2  # Layer 3 (deep)
    wel_p1["i"][3] = 4
    wel_p1["j"][3] = 7
    wel_p1["flux"][3] = -2000.0
    wel_p1["well_id"][3] = 301
    wel_p1["efficiency"][3] = 0.90
    wel_p1["depth_m"][3] = 55.0
    wel_p1["owner_code"][3] = 3  # Industrial
    
    # Injection well (ASR)
    wel_p1["k"][4] = 1  # Layer 2
    wel_p1["i"][4] = 6
    wel_p1["j"][4] = 3
    wel_p1["flux"][4] = 500.0  # Injection (positive)
    wel_p1["well_id"][4] = 401
    wel_p1["efficiency"][4] = 0.95
    wel_p1["depth_m"][4] = 30.0
    wel_p1["owner_code"][4] = 4  # ASR system
    
    # 8. Time-Varying Well Data
    print(f"\n8. Time-Varying Pumping Rates")
    print("-" * 40)
    
    # Period 2: Summer pumping increase
    ncells_p2 = 6  # Add one more well
    wel_p2 = flopy.modflow.ModflowWel.get_empty(
        ncells=ncells_p2,
        aux_names=aux_names
    )
    
    # Copy and modify existing wells
    for i in range(5):
        for field in wel_p1.dtype.names:
            wel_p2[field][i] = wel_p1[field][i]
    
    # Increase agricultural pumping by 50% (summer irrigation)
    wel_p2["flux"][1] *= 1.5  # -800 → -1200
    wel_p2["flux"][2] *= 1.5  # -600 → -900
    
    # Add new temporary well
    wel_p2["k"][5] = 0
    wel_p2["i"][5] = 8
    wel_p2["j"][5] = 4
    wel_p2["flux"][5] = -400.0
    wel_p2["well_id"][5] = 501
    wel_p2["efficiency"][5] = 0.60
    wel_p2["depth_m"][5] = 20.0
    wel_p2["owner_code"][5] = 5  # Temporary
    
    print(f"  Period 2: {ncells_p2} wells (summer increase)")
    print(f"    Agricultural pumping increased 50%")
    print(f"    Added temporary well #501")
    
    # Period 3: Winter reduction
    ncells_p3 = 4  # Reduce to 4 wells
    wel_p3 = flopy.modflow.ModflowWel.get_empty(
        ncells=ncells_p3,
        aux_names=aux_names
    )
    
    # Keep only essential wells
    indices_to_keep = [0, 1, 3, 4]  # Municipal, Ag1, Industrial, ASR
    for new_idx, old_idx in enumerate(indices_to_keep):
        for field in wel_p1.dtype.names:
            wel_p3[field][new_idx] = wel_p1[field][old_idx]
    
    # Reduce agricultural pumping
    wel_p3["flux"][1] *= 0.5  # Winter reduction
    
    print(f"  Period 3: {ncells_p3} wells (winter reduction)")
    print(f"    Removed temporary and Ag well #2")
    print(f"    Reduced agricultural pumping 50%")
    
    # Compile stress period data
    stress_period_data = {
        0: wel_p1,
        1: wel_p2,
        2: wel_p3
    }
    
    # 9. Create Well Package
    print(f"\n9. Well Package Creation")
    print("-" * 40)
    
    wel = flopy.modflow.ModflowWel(
        mf,
        stress_period_data=stress_period_data,
        dtype=wel_p1.dtype,  # Use the structured dtype
        binary=False,  # ASCII output for readability
        ipakcb=102  # Save cell-by-cell flows
    )
    
    print(f"  Well package created with auxiliary variables")
    print(f"  Output format: ASCII")
    print(f"  Cell-by-cell flows: Unit 102")
    
    # 10. Well Summary Statistics
    print(f"\n10. Well Summary Statistics")
    print("-" * 40)
    
    for per in range(nper):
        wel_data = stress_period_data[per]
        total_extraction = np.sum(wel_data["flux"][wel_data["flux"] < 0])
        total_injection = np.sum(wel_data["flux"][wel_data["flux"] > 0])
        
        print(f"\n  Period {per + 1}:")
        print(f"    Active wells: {len(wel_data)}")
        print(f"    Total extraction: {abs(total_extraction):,.0f} m³/day")
        print(f"    Total injection: {total_injection:,.0f} m³/day")
        print(f"    Net extraction: {abs(total_extraction + total_injection):,.0f} m³/day")
    
    # 11. Well Categories Analysis
    print(f"\n11. Well Categories Analysis")
    print("-" * 40)
    
    categories = {
        1: "Municipal",
        2: "Agricultural",
        3: "Industrial",
        4: "ASR System",
        5: "Temporary"
    }
    
    print("\n  Well distribution by category:")
    for code, name in categories.items():
        count_p1 = np.sum(wel_p1["owner_code"] == code) if code <= 4 else 0
        if count_p1 > 0:
            total_rate = np.sum(wel_p1["flux"][wel_p1["owner_code"] == code])
            print(f"    {name}: {count_p1} well(s), {abs(total_rate):,.0f} m³/day")
    
    # 12. Output Control
    print(f"\n12. Output Control")
    print("-" * 40)
    
    oc = flopy.modflow.ModflowOc(
        mf,
        stress_period_data={(0, 0): ['save head', 'save budget'],
                           (1, 9): ['save head', 'save budget'],
                           (2, 9): ['save head', 'save budget']},
        compact=True
    )
    
    print(f"  Save heads: End of each stress period")
    print(f"  Save budget: End of each stress period")
    print(f"  Cell-by-cell flows: When requested")
    
    # 13. Solver
    print(f"\n13. Solver Configuration")
    print("-" * 40)
    
    pcg = flopy.modflow.ModflowPcg(
        mf,
        mxiter=100,
        iter1=50,
        hclose=1e-4,
        rclose=1e-3
    )
    
    print(f"  Solver: PCG")
    print(f"  Max iterations: 100")
    print(f"  Convergence criteria: 1e-4 m, 1e-3 m³/d")
    
    # 14. Run Model
    print(f"\n14. Model Execution")
    print("-" * 40)
    
    try:
        print(f"  Writing model input files...")
        mf.write_input()
        
        print(f"  Running MODFLOW simulation...")
        success, buff = mf.run_model(silent=True)
        
        if success:
            print(f"  ✓ Model run completed successfully")
        else:
            print(f"  ⚠ Model run failed")
            if buff:
                print(f"    Last error: {buff[-1] if buff else 'Unknown error'}")
        
        # Check files created
        if os.path.exists(model_ws):
            files = os.listdir(model_ws)
            output_files = [f for f in files if f.endswith(('.hds', '.cbc', '.lst', '.list'))]
            
            print(f"\n  Total files: {len(files)}")
            if output_files:
                print(f"  Output files: {len(output_files)}")
                print(f"    • Head file (.hds): {'✓' if any('.hds' in f for f in output_files) else '✗'}")
                print(f"    • Budget file (.cbc): {'✓' if any('.cbc' in f for f in output_files) else '✗'}")
                print(f"    • Listing file (.lst/.list): {'✓' if any(('.lst' in f or '.list' in f) for f in output_files) else '✗'}")
            else:
                print(f"  ⚠ No output files found")
            
            for f in sorted(files)[:10]:
                print(f"    - {f}")
            if len(files) > 10:
                print(f"    ... and {len(files)-10} more")
                
    except Exception as e:
        print(f"  ⚠ Model writing info: {str(e)}")
    
    # 15. Professional Applications
    print(f"\n15. Professional Applications")
    print("-" * 40)
    
    applications = [
        ("Municipal water supply", "Public drinking water systems"),
        ("Agricultural irrigation", "Crop water management"),
        ("Industrial processes", "Manufacturing and cooling"),
        ("Dewatering operations", "Construction and mining"),
        ("Remediation systems", "Pump-and-treat cleanup"),
        ("ASR systems", "Aquifer storage and recovery"),
        ("Geothermal extraction", "Heat pump systems"),
        ("Mine water management", "Dewatering and control")
    ]
    
    print("  Professional applications:")
    for application, description in applications:
        print(f"    • {application}: {description}")
    
    # 16. Well Design Considerations
    print(f"\n16. Well Design Considerations")
    print("-" * 40)
    
    print("  Design factors:")
    print("    • Screen length and placement")
    print("    • Well efficiency and development")
    print("    • Pump capacity and depth")
    print("    • Interference with other wells")
    print("    • Water quality zones")
    print("    • Regulatory constraints")
    print("    • Maintenance requirements")
    print("    • Energy efficiency")
    
    # 17. Binary Output Benefits
    print(f"\n17. Binary vs ASCII Output")
    print("-" * 40)
    
    print("  Binary output advantages:")
    print("    • Smaller file sizes")
    print("    • Faster I/O operations")
    print("    • Precision preservation")
    print("    • Efficient for large datasets")
    
    print("\n  ASCII output advantages:")
    print("    • Human readable")
    print("    • Platform independent")
    print("    • Easy debugging")
    print("    • Simple post-processing")
    
    print(f"\n✓ WEL Package Advanced Demonstration Completed!")
    print(f"  - Created multi-layer well system")
    print(f"  - Configured auxiliary variables")
    print(f"  - Demonstrated get_empty() method")
    print(f"  - Showed time-varying pumping")
    print(f"  - Analyzed well categories")
    print(f"  - Explained professional applications")
    
    return mf

if __name__ == "__main__":
    model = run_model()