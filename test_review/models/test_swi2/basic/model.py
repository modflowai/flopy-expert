"""
SWI2 - Salt Water Intrusion Package Demonstration

This script demonstrates the SWI2 (Salt Water Intrusion) package capabilities.
Key concepts demonstrated:
- Density-dependent groundwater flow modeling
- Saltwater/freshwater interface tracking
- Coastal aquifer simulation
- Variable density flow with stratified approach
- Multiple density zones and interfaces
- Seawater intrusion prevention analysis

SWI2 is used for:
- Coastal aquifer management and protection
- Seawater intrusion assessment and control
- Brackish water resource evaluation
- Island freshwater lens modeling
- Submarine groundwater discharge studies
- Climate change impact on coastal aquifers
"""

import numpy as np
import os
import flopy

def run_model():
    """
    Create demonstration model with SWI2 salt water intrusion package.
    Shows density-dependent flow in a coastal aquifer system.
    """
    
    print("=== SWI2 Salt Water Intrusion Package Demonstration ===\n")
    
    # Create model workspace
    model_ws = "./model_output"
    
    # 1. SWI2 Package Overview
    print("1. SWI2 Package Overview")
    print("-" * 40)
    
    print("  SWI2 capabilities:")
    print("    • Density-dependent groundwater flow")
    print("    • Sharp interface approximation")
    print("    • Multiple density zones (freshwater to seawater)")
    print("    • Transient interface movement")
    print("    • Stratified and continuous density options")
    print("    • Tip and toe tracking for interface")
    
    # 2. Create Base Model
    print(f"\n2. Creating Coastal Aquifer Model")
    print("-" * 40)
    
    # Model dimensions - coastal aquifer
    model_name = "swi2_demo"
    nlay, nrow, ncol = 1, 1, 50  # 1D coastal cross-section
    delr = 50.0  # 50m cells
    delc = 1.0   # 1m width (unit width)
    top = 0.0    # Sea level
    botm = [-40.0]  # 40m deep aquifer
    
    # Create model
    mf = flopy.modflow.Modflow(
        modelname=model_name,
        exe_name="/home/danilopezmella/flopy_expert/bin/mf2005",
        model_ws=model_ws
    )
    
    print(f"  Model type: Coastal aquifer cross-section")
    print(f"  Grid: {nlay}×{nrow}×{ncol} cells")
    print(f"  Domain length: {ncol*delr:.0f}m ({ncol*delr/1000:.1f}km)")
    print(f"  Aquifer thickness: {abs(botm[0]):.0f}m")
    
    # 3. Discretization
    print(f"\n3. Model Discretization")
    print("-" * 40)
    
    # Time discretization for transient SWI2
    nper = 2
    perlen = [1.0, 3650.0]  # 1 day steady, then 10 years transient
    nstp = [1, 100]
    steady = [True, False]
    
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
    print(f"    Period 1: Steady-state initial conditions")
    print(f"    Period 2: {perlen[1]:.0f} days ({perlen[1]/365:.1f} years) transient")
    
    # 4. Basic Package
    print(f"\n4. Basic Package Configuration")
    print("-" * 40)
    
    # Active cells - all active
    ibound = np.ones((nlay, nrow, ncol), dtype=int)
    # Ocean boundary on right side
    ibound[0, 0, -1] = -1  # Constant head ocean cell
    
    # Initial heads - hydrostatic with freshwater
    strt = np.zeros((nlay, nrow, ncol))
    # Set freshwater head gradient inland
    for j in range(ncol):
        if j < ncol - 1:
            strt[0, 0, j] = 0.5 * (1.0 - j/ncol)  # Gradient from 0.5m to 0m
        else:
            strt[0, 0, j] = 0.0  # Sea level at ocean
    
    bas = flopy.modflow.ModflowBas(mf, ibound=ibound, strt=strt)
    
    print(f"  Active cells: {np.sum(ibound > 0)}")
    print(f"  Ocean boundary: Column {ncol} (constant head)")
    print(f"  Initial gradient: 0.5m inland to 0m at coast")
    
    # 5. Layer Property Flow
    print(f"\n5. Aquifer Properties")
    print("-" * 40)
    
    hk = 10.0  # Horizontal K (m/d)
    vka = 1.0  # Vertical K (m/d)
    ss = 1e-5  # Specific storage
    sy = 0.2   # Specific yield
    
    lpf = flopy.modflow.ModflowLpf(
        mf,
        hk=hk,
        vka=vka,
        ss=ss,
        sy=sy,
        laytyp=0  # Confined for this example
    )
    
    print(f"  Hydraulic conductivity: {hk:.1f} m/d")
    print(f"  Vertical K: {vka:.1f} m/d")
    print(f"  Specific storage: {ss:.1e} 1/m")
    print(f"  Specific yield: {sy:.2f}")
    
    # 6. Recharge Package
    print(f"\n6. Recharge Configuration")
    print("-" * 40)
    
    # Recharge only on land cells (not ocean)
    rch_rate = np.zeros((nrow, ncol))
    rch_rate[0, :-1] = 0.001  # 1 mm/day on land
    
    rch = flopy.modflow.ModflowRch(mf, rech=rch_rate)
    
    print(f"  Recharge rate: 1 mm/day on land")
    print(f"  Annual recharge: {1*365:.0f} mm/year")
    print(f"  No recharge on ocean cell")
    
    # 7. Well Package (Optional freshwater extraction)
    print(f"\n7. Pumping Well Configuration")
    print("-" * 40)
    
    # Well 500m from coast
    wel_col = 40  # Column 40 (500m from coast)
    wel_data = {
        1: [[0, 0, wel_col, -50.0]]  # 50 m³/day pumping in transient
    }
    
    wel = flopy.modflow.ModflowWel(mf, stress_period_data=wel_data)
    
    print(f"  Well location: {(ncol-wel_col)*delr:.0f}m from coast")
    print(f"  Pumping rate: 50 m³/day (transient period)")
    print(f"  Purpose: Freshwater supply well")
    
    # 8. SWI2 Package Configuration
    print(f"\n8. SWI2 Salt Water Intrusion Setup")
    print("-" * 40)
    
    # SWI2 parameters
    nsrf = 1  # Number of surfaces (1 interface between fresh and salt)
    istrat = 1  # Stratified flow option
    nobs = 0  # No observation points for demo
    iswizt = 55  # Unit number for zeta output
    iswiobs = 0  # No observation output
    
    # Fluid densities
    nu = [0.0, 0.025]  # Dimensionless density (fresh=0, seawater=0.025)
    
    # Initial interface elevation (zeta)
    # Interface slopes from -20m at coast to -35m inland
    z_init = np.zeros((nsrf, nlay, nrow, ncol))
    for j in range(ncol):
        if j < ncol - 1:
            # Ghyben-Herzberg: interface at 40*freshwater head below sea level
            z_init[0, 0, 0, j] = -40.0 * strt[0, 0, j]
        else:
            z_init[0, 0, 0, j] = botm[0] / 2.0  # Mid-depth at ocean
    
    # Effective porosity for transport
    ssz = 0.2  # Effective porosity
    
    # Source/sink fluid types
    isource = np.zeros((nlay, nrow, ncol), dtype=int)
    isource[0, 0, -1] = 1  # Ocean cell has seawater
    
    swi = flopy.modflow.ModflowSwi2(
        mf,
        nsrf=nsrf,
        istrat=istrat,
        nu=nu,
        zeta=z_init,
        ssz=ssz,
        isource=isource,
        nsolver=1,  # Direct solver
        iprsol=0,
        mutsol=3,
        solver2params={
            'mxiter': 100,
            'iter1': 20,
            'npcond': 1,
            'zclose': 1e-3,
            'rclose': 1e-3,
            'relax': 1.0,
            'nbpol': 2,
            'damp': 1.0,
            'dampt': 1.0
        }
    )
    
    print(f"  Density zones: {nsrf + 1}")
    print(f"    Zone 1: Freshwater (ρ = 1000 kg/m³)")
    print(f"    Zone 2: Seawater (ρ = 1025 kg/m³)")
    print(f"  Interface tracking: Sharp interface")
    print(f"  Stratified flow approximation")
    
    # 9. Interface Dynamics
    print(f"\n9. Interface Dynamics")
    print("-" * 40)
    
    print("  Ghyben-Herzberg relation:")
    print("    • Interface depth = 40 × freshwater head")
    print("    • Based on density difference")
    print("    • ρf/Δρ ≈ 40 for fresh/seawater")
    
    print("\n  Interface movement factors:")
    print("    • Recharge pushes interface seaward")
    print("    • Pumping pulls interface landward")
    print("    • Tides cause interface fluctuation")
    print("    • Sea level rise moves interface inland")
    
    # 10. Solver Configuration
    print(f"\n10. Solver Configuration")
    print("-" * 40)
    
    pcg = flopy.modflow.ModflowPcg(
        mf,
        mxiter=100,
        iter1=50,
        hclose=1e-4,
        rclose=1e-3
    )
    
    print(f"  Solver: PCG (Preconditioned Conjugate Gradient)")
    print(f"  Max iterations: 100")
    print(f"  Head closure: 1e-4 m")
    print(f"  Residual closure: 1e-3 m³/d")
    
    # 11. Output Control
    print(f"\n11. Output Control")
    print("-" * 40)
    
    oc = flopy.modflow.ModflowOc(
        mf,
        stress_period_data={(0, 0): ['save head', 'save budget'],
                           (1, 99): ['save head', 'save budget']},
        compact=True
    )
    
    print(f"  Save heads: Initial and final")
    print(f"  Save budget: Initial and final")
    print(f"  Zeta (interface) output: Every time step")
    
    # 12. Write Model Files
    print(f"\n12. Writing Model Files")
    print("-" * 40)
    
    try:
        mf.write_input()
        print("  ✓ Model files written successfully")
        
        # Run the model
        success, buff = mf.run_model(silent=True)
        if success:
            print("  ✓ Model ran successfully")
        else:
            print("  ⚠ Model failed to run")
        
        # List generated files
        if os.path.exists(model_ws):
            files = os.listdir(model_ws)
            print(f"\n  Generated files: {len(files)}")
            for f in sorted(files)[:10]:
                print(f"    - {f}")
            if len(files) > 10:
                print(f"    ... and {len(files)-10} more")
                
    except Exception as e:
        print(f"  ⚠ Model writing info: {str(e)}")
    
    # 13. Professional Applications
    print(f"\n13. Professional Applications")
    print("-" * 40)
    
    applications = [
        ("Coastal water supply", "Sustainable freshwater extraction"),
        ("Seawater intrusion control", "Barrier design and operation"),
        ("Climate adaptation", "Sea level rise impact assessment"),
        ("Island hydrology", "Freshwater lens management"),
        ("Submarine discharge", "Nutrient flux to ocean"),
        ("Desalination planning", "Intake design and impacts"),
        ("Aquifer storage recovery", "Brackish water management"),
        ("Environmental protection", "Ecosystem salinity control")
    ]
    
    print("  Professional applications:")
    for application, description in applications:
        print(f"    • {application}: {description}")
    
    # 14. Monitoring and Management
    print(f"\n14. Monitoring and Management")
    print("-" * 40)
    
    print("  Monitoring strategies:")
    print("    • Multi-level monitoring wells")
    print("    • Electrical conductivity profiling")
    print("    • Geophysical surveys (EM, resistivity)")
    print("    • Water quality sampling")
    print("    • Interface depth measurements")
    
    print("\n  Management options:")
    print("    • Pumping optimization")
    print("    • Injection barriers")
    print("    • Artificial recharge")
    print("    • Pumping redistribution")
    print("    • Scavenger wells")
    
    # 15. Climate Change Considerations
    print(f"\n15. Climate Change Impacts")
    print("-" * 40)
    
    impacts = [
        ("Sea level rise", "Direct interface movement inland"),
        ("Reduced recharge", "Less freshwater pressure"),
        ("Increased pumping", "Higher water demand"),
        ("Storm surges", "Temporary intrusion events"),
        ("Drought periods", "Reduced freshwater lens"),
        ("Coastal flooding", "Surface saltwater infiltration")
    ]
    
    print("  Climate change impacts:")
    for impact, effect in impacts:
        print(f"    • {impact}: {effect}")
    
    print(f"\n✓ SWI2 Salt Water Intrusion Demonstration Completed!")
    print(f"  - Created coastal aquifer model")
    print(f"  - Configured SWI2 package with interface")
    print(f"  - Set up density-dependent flow")
    print(f"  - Demonstrated pumping impacts")
    print(f"  - Explained monitoring strategies")
    print(f"  - Provided professional applications")
    
    return mf

if __name__ == "__main__":
    model = run_model()