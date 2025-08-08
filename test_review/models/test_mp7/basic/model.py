"""
MODPATH-7 Particle Tracking with MODFLOW 6 Demonstration

This script demonstrates MODPATH-7 particle tracking with MODFLOW 6 integration.
Key concepts demonstrated:
- MODPATH-7 setup with MODFLOW 6 models
- Advanced particle data types (CellDataType, FaceDataType, NodeParticleData, LRCParticleData)
- Particle groups and templates (ParticleGroup, ParticleGroupLRCTemplate, ParticleGroupNodeTemplate)
- Forward and backward tracking with structured grids
- Particle release strategies and placement options
- Modern particle tracking workflows with MF6

MODPATH-7 with MODFLOW 6 is used for:
- Next-generation particle tracking analysis
- Unstructured grid support (DISV, DISU)
- Advanced discretization compatibility
- Improved algorithms and performance
- Complex geological system modeling
- Regional-scale flow system analysis
"""

import numpy as np
import os
from flopy.mf6 import (
    MFSimulation,
    ModflowGwf,
    ModflowGwfdis,
    ModflowGwfic,
    ModflowGwfnpf,
    ModflowGwfoc,
    ModflowGwfrcha,
    ModflowGwfriv,
    ModflowGwfwel,
    ModflowIms,
    ModflowTdis,
)
from flopy.modpath import (
    CellDataType,
    FaceDataType,
    LRCParticleData,
    Modpath7,
    Modpath7Bas,
    Modpath7Sim,
    NodeParticleData,
    ParticleData,
    ParticleGroup,
    ParticleGroupLRCTemplate,
    ParticleGroupNodeTemplate,
)

def run_model():
    """
    Create demonstration MODFLOW 6/MODPATH-7 model with advanced particle tracking.
    Shows modern particle tracking with various data types and release strategies.
    """
    
    print("=== MODPATH-7 with MODFLOW 6 Demonstration ===\n")
    
    # Create model workspace
    model_ws = "./model_output"
    
    # 1. MODPATH-7 Overview
    print("1. MODPATH-7 Overview")
    print("-" * 40)
    
    print("  MODPATH-7 capabilities:")
    print("    • MODFLOW 6 native integration")
    print("    • Structured and unstructured grid support")
    print("    • Advanced particle data types")
    print("    • Improved tracking algorithms")
    print("    • Particle groups and templates")
    print("    • Enhanced performance and accuracy")
    
    # 2. Create MODFLOW 6 Model
    print(f"\n2. Creating MODFLOW 6 Model")
    print("-" * 40)
    
    # Model dimensions (example 1b from test)
    model_name = "mp7_mf6_demo"
    nper, nstp, perlen, tsmult = 1, 1, 1.0, 1.0
    nlay, nrow, ncol = 3, 21, 20
    delr = delc = 500.0  # 500 ft cells
    top = 400.0
    botm = [220.0, 200.0, 0.0]
    
    # Create simulation
    sim = MFSimulation(
        sim_name=model_name,
        exe_name=None,  # No execution for demo
        version="mf6",
        sim_ws=model_ws,
    )
    
    # Temporal discretization
    tdis = ModflowTdis(
        sim,
        pname="tdis",
        time_units="DAYS",
        nper=nper,
        perioddata=[(perlen, nstp, tsmult)]
    )
    
    # Create groundwater flow model
    gwf = ModflowGwf(
        sim,
        modelname=model_name,
        model_nam_file=f"{model_name}.nam",
        save_flows=True,
    )
    
    print(f"  Model grid: {nlay}×{nrow}×{ncol} cells")
    print(f"  Cell size: {delr:.0f}ft × {delc:.0f}ft")
    print(f"  Domain: {ncol*delr/5280:.1f}mi × {nrow*delc/5280:.1f}mi")
    print(f"  Layers: 3 with varying thickness")
    
    # 3. Discretization and Properties
    print(f"\n3. Model Discretization and Properties")
    print("-" * 40)
    
    # Discretization
    dis = ModflowGwfdis(
        gwf,
        pname="dis",
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        length_units="FEET",
        delr=delr,
        delc=delc,
        top=top,
        botm=botm,
    )
    
    # Initial conditions
    ic = ModflowGwfic(gwf, pname="ic", strt=top)
    
    # Node property flow
    laytyp = [1, 0, 0]  # Convertible, confined, confined
    kh = [50.0, 0.01, 200.0]  # Horizontal K
    kv = [10.0, 0.01, 20.0]   # Vertical K
    
    npf = ModflowGwfnpf(
        gwf,
        pname="npf",
        icelltype=laytyp,
        k=kh,
        k33=kv,
    )
    
    print(f"  Layer types and properties:")
    for i in range(nlay):
        ltype = "Convertible" if laytyp[i] == 1 else "Confined"
        print(f"    Layer {i+1}: {ltype}, Kh={kh[i]:.2f}, Kv={kv[i]:.2f} ft/d")
    
    # 4. Boundary Conditions
    print(f"\n4. Boundary Conditions for Tracking")
    print("-" * 40)
    
    # Recharge
    rch_rate = 0.005  # ft/d
    ModflowGwfrcha(gwf, recharge=rch_rate)
    print(f"  Recharge: {rch_rate:.3f} ft/d uniform")
    
    # Well
    wel_loc = (2, 10, 9)  # Layer 3, row 11, col 10
    wel_q = -150000.0  # ft³/d
    wel_data = [(wel_loc, wel_q)]
    ModflowGwfwel(gwf, maxbound=1, stress_period_data={0: wel_data})
    print(f"  Well: {wel_q:,.0f} ft³/d at layer {wel_loc[0]+1}")
    
    # River
    riv_h, riv_c, riv_z = 320.0, 1.0e5, 317.0
    riv_data = []
    for i in range(nrow):
        riv_data.append([(0, i, ncol-1), riv_h, riv_c, riv_z])
    ModflowGwfriv(gwf, stress_period_data={0: riv_data})
    print(f"  River: {len(riv_data)} cells on east boundary")
    
    # 5. Solver and Output Control

# Write and run simulation
print("Writing and running model...")
sim.write_simulation()
success, buff = sim.run_simulation(silent=True)
if success:
    print("  ✓ Model ran successfully")
else:
    print("  ⚠ Model run failed")

    print(f"\n5. Solver and Output Control")
    print("-" * 40)
    
    # IMS solver
    ims = ModflowIms(sim, pname="ims", complexity="SIMPLE")
    
    # Output control
    headfile = f"{model_name}.hds"
    budgetfile = f"{model_name}.cbb"
    oc = ModflowGwfoc(
        gwf,
        pname="oc",
        saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")],
        head_filerecord=[headfile],
        budget_filerecord=[budgetfile],
    )
    
    print(f"  Solver: IMS with SIMPLE complexity")
    print(f"  Output: Heads and budgets saved")
    
    # 6. MODPATH-7 Setup
    print(f"\n6. MODPATH-7 Configuration")
    print("-" * 40)
    
    # Create MODPATH-7
    mp = Modpath7(
        modelname=f"{model_name}_mp7",
        flowmodel=gwf,
        exe_name=None,  # No execution for demo
        model_ws=model_ws,
        headfilename=headfile,
        budgetfilename=budgetfile,
    )
    
    # MODPATH-7 basic data
    mpbas = Modpath7Bas(
        mp,
        porosity=0.3,
        defaultiface={"RECHARGE": 6, "ET": 6}  # Top face for recharge/ET
    )
    
    print(f"  MODPATH-7 model: {mp.name}")
    print(f"  Porosity: 0.3 uniform")
    print(f"  Default iface: Top (6) for recharge")
    
    # 7. Particle Data Types
    print(f"\n7. Particle Data Types")
    print("-" * 40)
    
    print("  Cell-based particles (CellDataType):")
    print("    • Particles distributed within cells")
    print("    • Subdivisions in local coordinates")
    print("    • Used for volumetric releases")
    
    print("\n  Face-based particles (FaceDataType):")
    print("    • Particles on cell faces")
    print("    • Used for flux-weighted releases")
    print("    • Common for boundary conditions")
    
    print("\n  Node particles (NodeParticleData):")
    print("    • Particles at specific nodes")
    print("    • Unstructured grid compatible")
    print("    • Direct node specification")
    
    print("\n  LRC particles (LRCParticleData):")
    print("    • Layer-Row-Column specification")
    print("    • Structured grid specific")
    print("    • Traditional MODPATH format")
    
    # 8. Create Particle Groups
    print(f"\n8. Creating Particle Groups")
    print("-" * 40)
    
    # Well capture zone analysis (backward tracking)
    print("  Well capture zone particles:")
    # Use NodeParticleData for MODPATH-7 with MF6
    # Create particles around the well location
    well_nodes = []
    for di in [-1, 0, 1]:
        for dj in [-1, 0, 1]:
            # Calculate node number for MF6 (0-based)
            node = wel_loc[0] * nrow * ncol + (wel_loc[1] + di) * ncol + (wel_loc[2] + dj)
            if 0 <= wel_loc[1] + di < nrow and 0 <= wel_loc[2] + dj < ncol:
                well_nodes.append(node)
    
    well_particles = ParticleGroupNodeTemplate(
        particlegroupname="WELL",
        releasedata=0.0,  # Release at start
        particledata=NodeParticleData(
            subdivisiondata=[CellDataType()],  # Default 3x3x3 subdivisions
            nodes=well_nodes
        )
    )
    print(f"    Location: Around well at Layer {wel_loc[0]+1}, Row {wel_loc[1]+1}, Col {wel_loc[2]+1}")
    print(f"    Pattern: 9 cells with 27 particles each")
    print(f"    Total particles: {len(well_nodes) * 27}")
    
    # Recharge area analysis (forward tracking)
    print("\n  Recharge area particles:")
    # Create particles in recharge area
    recharge_nodes = []
    for i in range(5, 16):  # Rows 6-16 (0-based: 5-15)
        for j in range(5, 16):  # Cols 6-16 (0-based: 5-15)
            # Layer 0 (top layer), calculate node number
            node = 0 * nrow * ncol + i * ncol + j
            recharge_nodes.append(node)
    
    recharge_particles = ParticleGroupNodeTemplate(
        particlegroupname="RECHARGE",
        releasedata=0.0,
        particledata=NodeParticleData(
            subdivisiondata=[CellDataType(
                columncelldivisions=1,
                rowcelldivisions=1,
                layercelldivisions=1
            )],
            nodes=recharge_nodes
        )
    )
    print(f"    Area: Layer 1, Rows 6-16, Cols 6-16")
    print(f"    Pattern: 1 particle per cell center")
    print(f"    Total particles: {len(recharge_nodes)}")
    
    # 9. Simulation Configuration
    print(f"\n9. MODPATH-7 Simulation Configuration")
    print("-" * 40)
    
    # Backward tracking from well
    mpsim_backward = Modpath7Sim(
        mp,
        simulationtype="combined",
        trackingdirection="backward",
        weaksinkoption="pass_through",
        weaksourceoption="pass_through",
        budgetoutputoption="summary",
        budgetcellnumbers=[wel_loc[2] + wel_loc[1]*ncol + wel_loc[0]*ncol*nrow],
        particlegroups=[well_particles],
    )
    
    print("  Backward tracking simulation:")
    print("    • Type: Combined (pathline + endpoint)")
    print("    • Direction: Backward from well")
    print("    • Weak sinks/sources: Pass through")
    print("    • Budget cell: Well location")
    
    # Forward tracking from recharge
    mpsim_forward = Modpath7Sim(
        mp,
        simulationtype="pathline",
        trackingdirection="forward",
        weaksinkoption="stop_at",
        weaksourceoption="pass_through",
        budgetoutputoption="summary",
        particlegroups=[recharge_particles],
    )
    
    print("\n  Forward tracking simulation:")
    print("    • Type: Pathline")
    print("    • Direction: Forward from recharge")
    print("    • Weak sinks: Stop at")
    print("    • Track to discharge locations")
    
    # 10. Advanced Features
    print(f"\n10. Advanced MODPATH-7 Features")
    print("-" * 40)
    
    print("  Zone budget support:")
    print("    • Define zones for mass balance")
    print("    • Track flow between zones")
    print("    • Particle-based water budgets")
    
    print("\n  Stochastic modeling:")
    print("    • Monte Carlo particle tracking")
    print("    • Uncertainty analysis")
    print("    • Probabilistic capture zones")
    
    print("\n  Time series output:")
    print("    • Particle locations vs time")
    print("    • Concentration breakthrough")
    print("    • Travel time distributions")
    
    # 11. MF6 Integration Benefits
    print(f"\n11. MODFLOW 6 Integration Benefits")
    print("-" * 40)
    
    benefits = [
        ("Native support", "Direct MF6 model compatibility"),
        ("Unstructured grids", "DISV and DISU discretization"),
        ("Advanced packages", "MAW, SFR, LAK, UZF support"),
        ("XT3D", "Full tensor conductivity"),
        ("Newton-Raphson", "Advanced solver options"),
        ("Multi-model", "LGR and model coupling"),
        ("Time series", "Dynamic boundary conditions"),
        ("Observations", "Integrated monitoring")
    ]
    
    print("  Integration benefits:")
    for feature, description in benefits:
        print(f"    • {feature}: {description}")
    
    # 12. Write Model Files
    print(f"\n12. Writing Model Files")
    print("-" * 40)
    
    try:
        # Write MODFLOW 6
        sim.write_simulation()
        print("  ✓ MODFLOW 6 simulation written")
        
        # Write MODPATH-7
        mp.write_input()
        print("  ✓ MODPATH-7 files written")
        
        # List files
        if os.path.exists(model_ws):
            files = os.listdir(model_ws)
            mf6_files = [f for f in files if not f.endswith(('.mpnam', '.mpbas', '.mpsim'))]
            mp7_files = [f for f in files if f.endswith(('.mpnam', '.mpbas', '.mpsim'))]
            
            print(f"\n  MODFLOW 6 files: {len(mf6_files)}")
            print(f"  MODPATH-7 files: {len(mp7_files)}")
            
    except Exception as e:
        print(f"  ⚠ File writing info: {str(e)}")
    
    # 13. Professional Applications
    print(f"\n13. Professional Applications")
    print("-" * 40)
    
    applications = [
        ("Regional flow systems", "Large-scale groundwater flow analysis"),
        ("Contaminant transport", "Plume migration and fate"),
        ("Water resource management", "Sustainable yield evaluation"),
        ("Environmental remediation", "Capture zone optimization"),
        ("Climate change impacts", "Flow system response"),
        ("Transboundary aquifers", "Cross-border flow assessment"),
        ("Coastal aquifers", "Saltwater intrusion analysis"),
        ("Mine dewatering", "Drawdown and recovery prediction")
    ]
    
    print("  Professional applications:")
    for application, description in applications:
        print(f"    • {application}: {description}")
    
    # 14. Version Evolution
    print(f"\n14. MODPATH Version Evolution")
    print("-" * 40)
    
    versions = [
        ("MODPATH-3", "1994", "Original version for MODFLOW-88/96"),
        ("MODPATH-4", "2000", "MODFLOW-2000 compatibility"),
        ("MODPATH-5", "2003", "MODFLOW-2005 support"),
        ("MODPATH-6", "2012", "Improved algorithms, MNW2"),
        ("MODPATH-7", "2016", "MODFLOW 6 integration, unstructured grids")
    ]
    
    print("  Version history:")
    for version, year, features in versions:
        print(f"    • {version} ({year}): {features}")
    
    print(f"\n✓ MODPATH-7 with MODFLOW 6 Demonstration Completed!")
    print(f"  - Created MODFLOW 6 groundwater flow model")
    print(f"  - Configured MODPATH-7 particle tracking")
    print(f"  - Demonstrated particle data types and groups")
    print(f"  - Showed forward and backward tracking setups")
    print(f"  - Explained MF6 integration benefits")
    print(f"  - Provided professional applications")
    
    return sim, mp

if __name__ == "__main__":
    simulation, modpath = run_model()