"""
MODFLOW Output Control (OC) Package Demonstration

This script demonstrates the OC (Output Control) package in MODFLOW, which controls 
when and how model results are saved and printed. Key concepts demonstrated:
- OC package setup for controlling output timing and format
- Head file output control and print options
- Budget file output and cell-by-cell flow saves
- Stress period and time step output specification
- Print format options and output unit management

The OC package is essential for:
- Managing simulation output files and formats
- Controlling when heads and budgets are saved
- Specifying output frequency and timing
- Managing disk space and file sizes
- Post-processing and analysis preparation
"""

import numpy as np
import os
import flopy
from flopy.modflow import Modflow, ModflowDis, ModflowBas, ModflowLpf, ModflowOc, ModflowPcg, ModflowWel

def run_model():
    """
    Create demonstration MODFLOW model with comprehensive OC package setup.
    Shows various output control options and timing specifications.
    """
    
    print("=== MODFLOW Output Control (OC) Package Demonstration ===\n")
    
    # Create model workspace
    model_ws = "./model_output"
    
    # 1. OC Package Overview
    print("1. OC Package Overview")
    print("-" * 40)
    
    print("  MODFLOW OC package capabilities:")
    print("    • Control when head files are saved")
    print("    • Manage budget and cell-by-cell flow output")
    print("    • Specify print options and formatting")
    print("    • Control output frequency and timing")
    print("    • Manage output units and file assignments")
    print("    • Configure drawdown and head difference output")
    
    # 2. Create Base MODFLOW Model
    print(f"\n2. Creating Base MODFLOW Model")
    print("-" * 40)
    
    # Model dimensions
    model_name = "oc_demo"
    nlay, nrow, ncol = 2, 15, 20
    delr = np.ones(ncol) * 100.0  # 100m cells
    delc = np.ones(nrow) * 100.0  # 100m cells
    top = 50.0
    botm = [20.0, 0.0]
    
    # Create model
    mf = Modflow(model_name, model_ws=model_ws, exe_name="/home/danilopezmella/flopy_expert/bin/mf2005")
    
    # Discretization with multiple stress periods for output demonstration
    dis = ModflowDis(
        mf,
        nlay=nlay,
        nrow=nrow, 
        ncol=ncol,
        delr=delr,
        delc=delc,
        top=top,
        botm=botm,
        nper=5,  # Multiple periods to demonstrate output control
        perlen=[365, 365, 365, 365, 365],  # 5 annual periods
        nstp=[1, 12, 12, 4, 1],  # Variable time steps
        steady=[True, False, False, False, True]  # Mixed steady/transient
    )
    
    print(f"  Model grid: {nlay}×{nrow}×{ncol} cells")
    print(f"  Cell size: {delr[0]:.0f}m × {delc[0]:.0f}m")
    print(f"  Domain: {ncol*delr[0]/1000:.1f}km × {nrow*delc[0]/1000:.1f}km")
    print(f"  Simulation: 5 periods with variable time stepping")
    
    # 3. Basic Model Setup
    print(f"\n3. Setting Up Basic Model Components")
    print("-" * 40)
    
    # Basic package
    ibound = np.ones((nlay, nrow, ncol), dtype=int)
    # Inactive boundary cells
    ibound[:, 0, :] = 0   # North boundary
    ibound[:, -1, :] = 0  # South boundary  
    ibound[:, :, 0] = 0   # West boundary
    ibound[:, :, -1] = 0  # East boundary
    
    strt = np.ones((nlay, nrow, ncol)) * 45.0  # Initial heads
    strt[1] = 25.0  # Lower layer initial heads
    
    bas = ModflowBas(mf, ibound=ibound, strt=strt)
    
    # Hydraulic properties
    hk = np.ones((nlay, nrow, ncol)) * 10.0  # Hydraulic conductivity
    hk[1] = 5.0  # Lower K in bottom layer
    vka = np.ones((nlay, nrow, ncol)) * 1.0  # Vertical K
    
    lpf = ModflowLpf(
        mf, 
        hk=hk, 
        vka=vka, 
        sy=0.15,  # Specific yield for unconfined
        ss=1e-5,  # Specific storage
        laytyp=1  # Layer type (convertible)
    )
    
    print(f"  Aquifer system: {nlay} layers")
    print(f"  Layer 1: Unconfined, K = {hk[0, 1, 1]:.0f} m/d")
    print(f"  Layer 2: Confined, K = {hk[1, 1, 1]:.0f} m/d")
    print(f"  Active cells: {np.sum(ibound == 1):,} of {ibound.size:,}")
    
    # Add some pumping wells for dynamic simulation
    wel_data = {
        # Stress period data: [lay, row, col, flux]
        1: [[0, 7, 10, -1000.0]],  # Period 1: single well
        2: [[0, 7, 10, -1500.0], [0, 5, 15, -800.0]],  # Period 2: two wells
        3: [[0, 7, 10, -2000.0], [0, 5, 15, -1200.0]],  # Period 3: higher rates
        4: [[0, 7, 10, -500.0]],   # Period 4: reduced pumping
        # Period 5: No pumping (steady state)
    }
    
    wel = ModflowWel(mf, stress_period_data=wel_data)
    print(f"  Well package: Variable pumping rates across periods")
    
    # 4. Output Control Configuration
    print(f"\n4. Output Control Package Configuration")
    print("-" * 40)
    
    # OC stress period data - controls when output is saved/printed
    # Format: (stress_period, time_step): ['save head', 'print head', 'save budget', 'print budget']
    oc_spd = {
        # Period 0 (steady state): Save and print everything
        (0, 0): ['save head', 'save budget', 'print head', 'print budget'],
        
        # Period 1 (transient): Save monthly, print quarterly
        (1, 2): ['save head', 'save budget'],  # Month 3
        (1, 5): ['save head', 'save budget', 'print head'],  # Month 6
        (1, 8): ['save head', 'save budget'],  # Month 9
        (1, 11): ['save head', 'save budget', 'print head', 'print budget'],  # Month 12
        
        # Period 2: Save every 3 months
        (2, 2): ['save head', 'save budget'],
        (2, 5): ['save head', 'save budget'],
        (2, 8): ['save head', 'save budget'],
        (2, 11): ['save head', 'save budget', 'print budget'],
        
        # Period 3: Save quarterly
        (3, 0): ['save head', 'save budget'],
        (3, 1): ['save head', 'save budget'],
        (3, 2): ['save head', 'save budget'],
        (3, 3): ['save head', 'save budget', 'print head'],
        
        # Period 4 (final steady state): Save final results
        (4, 0): ['save head', 'save budget', 'print head', 'print budget']
    }
    
    # Create OC package
    oc = ModflowOc(
        mf,
        stress_period_data=oc_spd,
        compact=True,  # Compact budget format
        chedfm='(10G13.6)',  # Head print format
        cbudgetfm='(10G13.6)',  # Budget print format
        extension=['hds', 'cbc'],  # File extensions
        unitnumber=[30, 31],  # Unit numbers for head and budget files
    )
    
    print("  Output control configuration:")
    print(f"    • Head saves: {len([k for k, v in oc_spd.items() if 'save head' in v])} time steps")
    print(f"    • Budget saves: {len([k for k, v in oc_spd.items() if 'save budget' in v])} time steps")
    print(f"    • Head prints: {len([k for k, v in oc_spd.items() if 'print head' in v])} time steps")
    print(f"    • Budget prints: {len([k for k, v in oc_spd.items() if 'print budget' in v])} time steps")
    
    # 5. OC Package Options and Features
    print(f"\n5. OC Package Options and Features")
    print("-" * 40)
    
    print("  Key OC package features demonstrated:")
    print("    • Variable output frequency across stress periods")
    print("    • Separate control for heads and budgets")
    print("    • Print vs save options (list file vs binary file)")
    print("    • Custom format specifications for printed output")
    print("    • Compact budget format for efficient storage")
    print("    • Unit number management for output files")
    
    # Demonstrate different output control strategies
    strategies = [
        ("Save All", "Every time step - maximum data, large files"),
        ("Monthly", "Monthly saves - good for long-term analysis"),
        ("Quarterly", "Seasonal saves - water balance analysis"),
        ("Annual", "Yearly saves - long-term trends only"),
        ("Critical", "Key periods only - minimal storage"),
        ("Print Only", "List file output - text format analysis")
    ]
    
    print("\\n  Output control strategies:")
    for strategy, description in strategies:
        print(f"    • {strategy}: {description}")
    
    # 6. Output File Management
    print(f"\n6. Output File Management")
    print("-" * 40)
    
    print("  OC-controlled output files:")
    print("    • .hds: Binary head file (MODFLOW heads)")
    print("    • .cbc: Cell-by-cell budget file (flow terms)")  
    print("    • .lst: List file (printed heads/budgets)")
    print("    • .cbo: Compact budget output (optional)")
    
    # File size considerations
    total_cells = nlay * nrow * ncol
    saves_per_period = [1, 4, 4, 4, 1]  # Based on our oc_spd
    total_saves = sum(saves_per_period)
    
    print(f"\\n  Storage requirements estimate:")
    print(f"    • Grid cells: {total_cells:,}")
    print(f"    • Head saves: {total_saves} time steps")
    print(f"    • Head file size: ~{total_cells * total_saves * 4 / 1024:.1f} KB")
    print(f"    • Budget saves: {total_saves} time steps")
    print(f"    • Budget file size: ~{total_cells * total_saves * 4 * 3 / 1024:.1f} KB")  # ~3x for budget terms
    
    # 7. Advanced OC Features
    print(f"\n7. Advanced Output Control Features")
    print("-" * 40)
    
    print("  Advanced OC capabilities:")
    print("    • IBOUTSYM: Symmetric budget output option")
    print("    • Drawdown calculation and output")
    print("    • Head difference output for comparison")
    print("    • Custom print formats for different data types")
    print("    • Output unit redirection and management")
    print("    • Compact vs full budget formats")
    
    # Example of different print formats
    format_examples = [
        ("(10G13.6)", "General format, 6 decimal places"),
        ("(10F10.3)", "Fixed format, 3 decimal places"),
        ("(8E15.6)", "Scientific notation, 6 significant figures"),
        ("(20F6.2)", "Compact format, 2 decimal places")
    ]
    
    print("\\n  Print format options:")
    for fmt, description in format_examples:
        print(f"    • {fmt}: {description}")
    
    # 8. Professional Applications
    print(f"\n8. Professional Applications")
    print("-" * 40)
    
    applications = [
        "Water balance analysis and budget verification",
        "Time series analysis of heads and flows",
        "Model calibration and parameter estimation",
        "Sensitivity analysis and uncertainty assessment",
        "Environmental impact assessment and monitoring",
        "Groundwater management and optimization",
        "Regulatory compliance and reporting",
        "Climate change impact assessment"
    ]
    
    print("  Professional applications:")
    for app in applications:
        print(f"    • {app}")
    
    # 9. Model Completion
    print(f"\n9. Completing Model Setup")
    print("-" * 40)
    
    # Solver
    pcg = ModflowPcg(mf, mxiter=100, hclose=1e-4, rclose=1e-3)
    
    # Write model files
    try:
        mf.write_input()
        print("  ✓ Model files written successfully")
        
        # Run the model
        print("\n  Running MODFLOW...")
        success, buff = mf.run_model(silent=True)
        if success:
            print("  ✓ Model ran successfully")
            
            # Check for output files
            hds_file = os.path.join(model_ws, f"{model_name}.hds")
            list_file = os.path.join(model_ws, f"{model_name}.list")
            
            if os.path.exists(hds_file):
                print(f"  ✓ Head file created: {os.path.getsize(hds_file)} bytes")
            if os.path.exists(list_file):
                print(f"  ✓ Listing file created: {os.path.getsize(list_file)} bytes")
        else:
            print("  ⚠ Model run failed")
        
        # List generated files
        files = [f for f in os.listdir(model_ws) 
                if f.startswith(model_name) and f.endswith(('.nam', '.dis', '.bas', '.lpf', '.oc', '.pcg', '.wel'))]
        print(f"  Generated {len(files)} model files:")
        for f in sorted(files):
            print(f"    - {f}")
            
        # Show OC file content snippet
        oc_file = os.path.join(model_ws, f"{model_name}.oc")
        if os.path.exists(oc_file):
            print(f"\\n  OC file structure preview:")
            with open(oc_file, 'r') as f:
                lines = f.readlines()[:10]  # First 10 lines
                for i, line in enumerate(lines, 1):
                    print(f"    {i:2d}: {line.strip()}")
            if len(lines) == 10:
                print("    ... (file continues)")
                
    except Exception as e:
        print(f"  ⚠ Model writing error: {str(e)}")
    
    # 10. Output Control Best Practices
    print(f"\n10. Output Control Best Practices")
    print("-" * 40)
    
    best_practices = [
        "Save heads at key time steps for analysis",
        "Balance output frequency with storage requirements", 
        "Use compact budget format for large models",
        "Print critical results to list file for review",
        "Consider post-processing needs when planning output",
        "Document output control strategy in model metadata",
        "Verify output timing matches analysis requirements",
        "Test output control with small models first"
    ]
    
    print("  Best practices:")
    for practice in best_practices:
        print(f"    • {practice}")
    
    print(f"\n✓ MODFLOW Output Control (OC) Package Demonstration Completed!")
    print(f"  - Explained OC package capabilities and output management")
    print(f"  - Demonstrated various output control timing strategies")
    print(f"  - Showed head and budget file management options")
    print(f"  - Covered print formatting and unit number management")
    print(f"  - Provided professional applications and best practices")
    print(f"  - Created comprehensive MODFLOW model with advanced OC setup")
    
    return mf

if __name__ == "__main__":
    model = run_model()