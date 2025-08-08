"""
MODPATH-6 Particle Tracking Demonstration

This script demonstrates MODPATH-6 particle tracking capabilities and simulation setup.
Key concepts demonstrated:
- MODPATH-6 simulation file creation and configuration
- Modpath6Sim and StartingLocationsFile classes
- Forward and backward particle tracking setup
- Endpoint and pathline tracking modes
- Package-specific particle release (RCH, MNW2, WEL)
- Destination data extraction and analysis

MODPATH-6 is used for:
- Advanced particle tracking in MODFLOW models
- Capture zone delineation and wellhead protection
- Contaminant transport pathway analysis
- Time-of-travel and age dating studies
- Source water assessment and protection
- Remediation system design and evaluation
"""

import numpy as np
import os
import flopy
from flopy.modflow import Modflow, ModflowDis, ModflowBas, ModflowLpf, ModflowRch, ModflowWel, ModflowOc, ModflowPcg, ModflowMnw2
from flopy.modpath import Modpath6, Modpath6Bas
from flopy.modpath.mp6sim import Modpath6Sim, StartingLocationsFile

def run_model():
    """
    Create demonstration MODFLOW/MODPATH-6 model with advanced particle tracking.
    Shows simulation setup, starting locations, and tracking configuration.
    """
    
    print("=== MODPATH-6 Particle Tracking Demonstration ===\n")
    
    # Create model workspace
    model_ws = "./model_output"
    
    # 1. MODPATH-6 Overview
    print("1. MODPATH-6 Overview")
    print("-" * 40)
    
    print("  MODPATH-6 capabilities:")
    print("    • Advanced particle tracking algorithms")
    print("    • Forward and backward tracking modes")
    print("    • Endpoint, pathline, and timeseries output")
    print("    • Package-specific particle release")
    print("    • Multi-well systems (MNW2) support")
    print("    • Improved performance and accuracy")
    
    # 2. Create Base MODFLOW Model
    print(f"\n2. Creating Base MODFLOW Model")
    print("-" * 40)
    
    # Model dimensions
    model_name = "mp6_demo"
    nlay, nrow, ncol = 5, 21, 21
    delr = np.ones(ncol) * 500.0  # 500m cells
    delc = np.ones(nrow) * 500.0  # 500m cells
    top = 100.0
    botm = [80.0, 60.0, 40.0, 20.0, 0.0]
    
    # Create model
    mf = Modflow(model_name, model_ws=model_ws, exe_name="/home/danilopezmella/flopy_expert/bin/mf2005")
    
    # Discretization
    dis = ModflowDis(
        mf,
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        delr=delr,
        delc=delc,
        top=top,
        botm=botm,
        nper=3,
        perlen=[365, 365, 365],
        nstp=[1, 1, 1],
        steady=[True, False, False]
    )
    
    print(f"  Model grid: {nlay}×{nrow}×{ncol} cells")
    print(f"  Cell size: {delr[0]:.0f}m × {delc[0]:.0f}m")
    print(f"  Domain: {ncol*delr[0]/1000:.1f}km × {nrow*delc[0]/1000:.1f}km")
    print(f"  Multi-layer system: {nlay} layers, 20m each")
    
    # 3. Model Setup for Particle Tracking
    print(f"\n3. Setting Up Model for Particle Tracking")
    print("-" * 40)
    
    # Basic package
    ibound = np.ones((nlay, nrow, ncol), dtype=int)
    # Set inactive areas
    ibound[:, 0, :] = 0      # North boundary
    ibound[:, -1, :] = 0     # South boundary
    ibound[:, :, 0] = 0      # West boundary  
    ibound[:, :, -1] = 0     # East boundary
    
    # Initial heads
    strt = np.ones((nlay, nrow, ncol)) * 90.0
    # Create head gradient
    for j in range(ncol):
        strt[:, :, j] -= (j * 10.0 / ncol)
    
    bas = ModflowBas(mf, ibound=ibound, strt=strt)
    
    # Layer properties
    laytyp = [1, 0, 0, 0, 0]  # Layer 1 convertible, others confined
    hk = [50.0, 0.01, 25.0, 0.01, 100.0]  # Alternating aquifer/aquitard
    vka = [10.0, 0.001, 5.0, 0.001, 20.0]  # Vertical K
    
    lpf = ModflowLpf(
        mf,
        laytyp=laytyp,
        hk=hk,
        vka=vka,
        sy=0.2,
        ss=1e-5,
        hdry=-999.0
    )
    
    print(f"  Layer properties:")
    for i in range(nlay):
        layer_type = "Unconfined" if laytyp[i] == 1 else "Confined"
        layer_desc = "Aquifer" if hk[i] > 1.0 else "Aquitard"
        print(f"    Layer {i+1}: {layer_type} {layer_desc}, K = {hk[i]:.2f} m/d")
    
    # 4. Stress Packages for Particle Sources
    print(f"\n4. Configuring Stress Packages")
    print("-" * 40)
    
    # Recharge (particle source)
    rch_rate = 0.001  # m/d
    rch = ModflowRch(mf, rech=rch_rate)
    print(f"  Recharge: {rch_rate:.3f} m/d uniform rate")
    
    # Standard pumping well - reduced for convergence
    wel_data = {
        0: [[3, 12, 12, -40000.0]]  # Layer 4, center location, reduced from -150000
    }
    wel = ModflowWel(mf, stress_period_data=wel_data)
    print(f"  Standard well: {abs(wel_data[0][0][3]):,.0f} m³/d at layer {wel_data[0][0][0]+1}")
    
    # 5. MNW2 Multi-Node Well Setup
    print(f"\n5. Multi-Node Well (MNW2) Configuration")
    print("-" * 40)
    
    # MNW2 node data - well penetrating multiple layers
    node_data = np.array(
        [
            (2, 12, 12, "well1", "skin", -1, 0, 0, 0, 1.0, 2.0, 5.0, 62.0),
            (3, 12, 12, "well1", "skin", -1, 0, 0, 0, 0.5, 2.0, 5.0, 42.0),
            (4, 12, 12, "well1", "skin", -1, 0, 0, 0, 0.5, 2.0, 5.0, 22.0),
        ],
        dtype=[
            ("k", int),
            ("i", int),
            ("j", int),
            ("wellid", object),
            ("losstype", object),
            ("pumploc", int),
            ("qlimit", int),
            ("ppflag", int),
            ("pumpcap", int),
            ("rw", float),      # Well radius
            ("rskin", float),   # Skin radius
            ("kskin", float),   # Skin K
            ("zpump", float),   # Pump elevation
        ],
    ).view(np.recarray)
    
    # MNW2 stress period data - reduced pumping for convergence
    mnw2_spd = {
        0: np.array(
            [(0, "well1", -5000.0)],  # Reduced from -200000 to -5000 m³/d
            dtype=[("per", int), ("wellid", object), ("qdes", float)],
        )
    }
    
    mnw2 = ModflowMnw2(
        model=mf,
        mnwmax=1,
        node_data=node_data,
        stress_period_data=mnw2_spd,
        itmp=[1, -1, -1],  # Reuse for periods 2 and 3
    )
    
    print(f"  MNW2 well 'well1':")
    print(f"    Screens: Layers 3-5 (depths 40-80m)")
    print(f"    Total pumping: {abs(mnw2_spd[0][0][2]):,.0f} m³/d")
    print(f"    Well radius: {node_data[0]['rw']:.1f}m")
    print(f"    Skin effects included")
    
    # 6. Output Control
    print(f"\n6. Configuring Output Control")
    print("-" * 40)
    
    oc = ModflowOc(
        mf,
        stress_period_data={(0,0): ['save head', 'save budget']},
        compact=True
    )
    
    # Solver
    pcg = ModflowPcg(mf, mxiter=100, hclose=1e-4, rclose=1e-3)
    
    print(f"  Output: Heads and budgets saved")
    print(f"  Solver: PCG with standard convergence")
    
    # 7. MODPATH-6 Setup
    print(f"\n7. MODPATH-6 Configuration")
    print("-" * 40)
    
    # Create MODPATH-6 instance
    mp = Modpath6(
        modelname=f"{model_name}_mp6",
        exe_name="/home/danilopezmella/flopy_expert/bin/mfnwt",
        modflowmodel=mf,
        model_ws=model_ws,
        dis_file=f"{model_name}.dis",
        head_file=f"{model_name}.hds",
        budget_file=f"{model_name}.cbc",
    )
    
    # MODPATH-6 basic package
    mpb = Modpath6Bas(
        mp,
        hdry=lpf.hdry,
        laytyp=lpf.laytyp,
        ibound=1,  # All cells active for tracking
        prsity=0.3  # Porosity
    )
    
    print(f"  MODPATH-6 model created: {mp.name}")
    print(f"  Porosity: 0.3 uniform")
    print(f"  Dry cell value: {lpf.hdry}")
    
    # 8. Simulation Types and Tracking Modes
    print(f"\n8. Simulation Types and Tracking Modes")
    print("-" * 40)
    
    print("  Tracking directions:")
    print("    • Forward: From recharge/sources to discharge")
    print("    • Backward: From wells/sinks to sources")
    
    print("\n  Simulation types:")
    print("    • Endpoint: Final particle locations only")
    print("    • Pathline: Complete particle trajectories")
    print("    • Timeseries: Particle locations at specified times")
    
    # 9. Create Simulations for Different Packages
    print(f"\n9. Creating Package-Specific Simulations")
    print("-" * 40)
    
    # Forward tracking from recharge
    sim_rch = mp.create_mpsim(
        trackdir="forward",
        simtype="pathline",
        packages="RCH"
    )
    print(f"  ✓ Forward pathline tracking from RCH package")
    
    # Backward tracking from standard well
    sim_wel = mp.create_mpsim(
        trackdir="backward",
        simtype="endpoint",
        packages="WEL"
    )
    print(f"  ✓ Backward endpoint tracking from WEL package")
    
    # Backward tracking from MNW2
    sim_mnw2 = mp.create_mpsim(
        trackdir="backward",
        simtype="pathline",
        packages="MNW2"
    )
    print(f"  ✓ Backward pathline tracking from MNW2 package")
    
    # 10. Starting Locations File
    print(f"\n10. Starting Locations File Configuration")
    print("-" * 40)
    
    # Create custom starting locations
    stl = StartingLocationsFile(model=mp)
    
    # Get empty starting locations data structure
    npt = 10  # Number of particles
    stldata = StartingLocationsFile.get_empty_starting_locations_data(npt=npt)
    
    # Configure particle locations
    for i in range(npt):
        stldata[i]["label"] = f"p{i+1}"
        stldata[i]["k0"] = 0  # Layer 1
        stldata[i]["i0"] = 5 + i  # Rows 5-14
        stldata[i]["j0"] = 10  # Column 10
        stldata[i]["xloc0"] = 0.5  # Cell center
        stldata[i]["yloc0"] = 0.5  # Cell center
        stldata[i]["zloc0"] = 0.5  # Layer center
        # Group is set separately, not in the data structure
    
    stl.data = stldata
    
    print(f"  Starting locations file:")
    print(f"    Particles: {npt} custom locations")
    print(f"    Release area: Layer 1, rows 6-15, column 11")
    print(f"    Labels: p1 through p{npt}")
    
    # 11. Simulation File Structure
    print(f"\n11. MODPATH-6 File Structure")
    print("-" * 40)
    
    print("  Input files:")
    print("    • .mpsim: Simulation control file")
    print("    • .mpbas: Basic data file")
    print("    • .mplst: List output file")
    print("    • .loc: Starting locations file")
    
    print("\n  Output files:")
    print("    • .mpend: Endpoint file")
    print("    • .mppth: Pathline file")
    print("    • .timeseries: Time series file")
    
    # 12. Model Completion
    print(f"\n12. Completing Model Setup")
    print("-" * 40)
    
    # Write model files
    try:
        mf.write_input()
        mp.write_input()
        print("  ✓ MODFLOW files written successfully")
        print("  ✓ MODPATH-6 files written successfully")
        
        # Run MODFLOW model first
        success, buff = mf.run_model(silent=True)
        if success:
            print("  ✓ MODFLOW model ran successfully")
        else:
            print("  ⚠ MODFLOW model failed to run")
        
        # List generated files
        if os.path.exists(model_ws):
            files = os.listdir(model_ws)
            modflow_files = [f for f in files if f.startswith(model_name) and not f.startswith(f"{model_name}_mp6")]
            mp6_files = [f for f in files if f.startswith(f"{model_name}_mp6")]
            
            print(f"\n  MODFLOW files ({len(modflow_files)}):")
            for f in sorted(modflow_files)[:5]:
                print(f"    - {f}")
            if len(modflow_files) > 5:
                print(f"    ... and {len(modflow_files)-5} more")
                
            print(f"\n  MODPATH-6 files ({len(mp6_files)}):")
            for f in sorted(mp6_files)[:5]:
                print(f"    - {f}")
            if len(mp6_files) > 5:
                print(f"    ... and {len(mp6_files)-5} more")
                
    except Exception as e:
        print(f"  ⚠ Model writing info: {str(e)}")
    
    # 13. Professional Applications
    print(f"\n13. Professional Applications")
    print("-" * 40)
    
    applications = [
        ("Wellhead protection", "Zone delineation and time-of-travel"),
        ("Contaminant forensics", "Source identification and pathway analysis"),
        ("Remediation design", "Capture zone optimization"),
        ("Water quality assessment", "Source water contribution analysis"),
        ("Environmental compliance", "Regulatory zone definition"),
        ("Climate impact studies", "Flow system response analysis"),
        ("Aquifer vulnerability", "Recharge area protection"),
        ("Water resource planning", "Sustainable yield evaluation")
    ]
    
    print("  Professional applications:")
    for application, description in applications:
        print(f"    • {application}: {description}")
    
    # 14. MODPATH-6 vs Other Versions
    print(f"\n14. MODPATH Version Comparison")
    print("-" * 40)
    
    version_features = [
        ("MODPATH-5", "Basic tracking", "Standard algorithms"),
        ("MODPATH-6", "Enhanced features", "MNW2 support, improved accuracy"),
        ("MODPATH-7", "Latest version", "MODFLOW 6 compatibility")
    ]
    
    print("  Version features:")
    for version, category, features in version_features:
        print(f"    • {version} - {category}: {features}")
    
    print(f"\n✓ MODPATH-6 Particle Tracking Demonstration Completed!")
    print(f"  - Explained MODPATH-6 capabilities and setup")
    print(f"  - Demonstrated simulation types and tracking modes")
    print(f"  - Showed package-specific particle release")
    print(f"  - Configured MNW2 multi-node wells")
    print(f"  - Created starting locations file")
    print(f"  - Provided professional applications")
    
    return mf, mp

if __name__ == "__main__":
    model, mp6 = run_model()