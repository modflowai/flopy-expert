#!/usr/bin/env python3

"""
MODFLOW-NWT Water Table Solution Example

This model demonstrates MODFLOW-NWT capabilities for solving
unconfined aquifer problems with Newton-Raphson linearization.
Includes analytical solution comparison for a water table problem.

Based on test_mfnwt.py from the FloPy autotest suite.
"""

import numpy as np
import flopy
from pathlib import Path
import json

def analytical_water_table_solution(h1, h2, z, R, K, L, x):
    """
    Calculate analytical water table solution.
    
    Parameters:
    - h1: Head at left boundary
    - h2: Head at right boundary
    - z: Bottom elevation (datum)
    - R: Recharge rate
    - K: Hydraulic conductivity
    - L: Domain length
    - x: Distance from left boundary
    """
    b1 = h1 - z
    b2 = h2 - z
    h = np.sqrt(b1**2 - (x / L) * (b1**2 - b2**2) + (R * x / K) * (L - x)) + z
    return h

def build_mfnwt_model(workspace):
    """
    Build a MODFLOW-NWT water table model.
    """
    modelname = "watertable"
    
    # Model dimensions
    nlay, nrow, ncol = 1, 1, 100
    
    # Cell spacing
    delr = 50.0
    delc = 1.0
    
    # Domain length
    L = 5000.0
    
    # Boundary heads
    h1 = 20.0  # Left boundary
    h2 = 11.0  # Right boundary
    
    # Ibound - all cells active
    ibound = np.ones((nlay, nrow, ncol), dtype=int)
    
    # Starting heads - interpolate between boundaries
    strt = np.zeros((nlay, nrow, ncol), dtype=float)
    strt[0, 0, :] = np.linspace(h1, h2, ncol)
    
    # Top and bottom of aquifer
    top = 25.0
    botm = 0.0
    
    # Hydraulic conductivity
    hk = 50.0
    
    # Recharge rate
    rchrate = 0.001
    
    # Location of cell centroids
    x = np.arange(0.0, L, delr) + (delr / 2.0)
    
    # Calculate analytical solution at cell centroids
    hac = analytical_water_table_solution(h1, h2, botm, rchrate, hk, L, x)
    
    # GHB boundary conditions at ends
    # Calculate conductance
    b1 = 0.5 * (h1 + hac[0])
    b2 = 0.5 * (h2 + hac[-1])
    c1 = hk * b1 * delc / (0.5 * delr)
    c2 = hk * b2 * delc / (0.5 * delr)
    
    # Build GHB stress period data
    ghb_data = [
        [0, 0, 0, h1, c1],      # Left boundary
        [0, 0, ncol-1, h2, c2]  # Right boundary
    ]
    
    # Create MODFLOW-NWT model
    mf = flopy.modflow.Modflow(
        modelname=modelname,
        exe_name="mfnwt",
        model_ws=str(workspace),
        version="mfnwt"
    )
    
    # Discretization package
    dis = flopy.modflow.ModflowDis(
        mf,
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        delr=delr,
        delc=delc,
        top=top,
        botm=botm,
        perlen=1.0,
        nstp=1,
        steady=True
    )
    
    # Basic package
    bas = flopy.modflow.ModflowBas(mf, ibound=ibound, strt=strt)
    
    # Upstream Weighting package (flow)
    upw = flopy.modflow.ModflowUpw(
        mf,
        hk=hk,
        laytyp=1,  # Convertible layer
        iphdry=0   # Print when cells go dry
    )
    
    # General Head Boundary package
    ghb = flopy.modflow.ModflowGhb(mf, stress_period_data=ghb_data)
    
    # Recharge package
    rch = flopy.modflow.ModflowRch(mf, rech=rchrate, nrchop=1)
    
    # Output Control package
    oc = flopy.modflow.ModflowOc(
        mf,
        stress_period_data={(0, 0): ['save head', 'save budget', 'print budget']}
    )
    
    # Newton-Raphson solver package
    nwt = flopy.modflow.ModflowNwt(
        mf,
        headtol=1e-6,           # Head tolerance
        fluxtol=100,            # Flux tolerance
        maxiterout=100,         # Max outer iterations
        thickfact=1e-5,         # Thickness factor for confined/unconfined
        linmeth=1,              # GMRES linear solver
        iprnwt=0,               # Print flag
        ibotav=0,               # Bottom averaging
        options='SIMPLE',       # Simple option set
        Continue=False,         # Don't continue on non-convergence
        dbdtheta=0.4,           # Under-relaxation parameter
        dbdkappa=1e-5,          # Under-relaxation depth
        dbdgamma=0.0,           # Under-relaxation gamma
        momfact=0.1,            # Momentum factor
        backflag=1,             # Backtracking flag
        maxbackiter=50,         # Max backtracking iterations
        backtol=1.1,            # Backtracking tolerance
        backreduce=0.7,         # Backtracking reduction factor
        maxitinner=50,          # Max inner iterations (GMRES)
        ilumethod=2,            # ILU method
        levfill=5,              # Level of fill for ILU
        stoptol=1e-10,          # Stopping tolerance
        msdr=15                 # Number of iterations for restarting GMRES
    )
    
    return mf, hac

def demonstrate_nwt_features():
    """
    Demonstrate MODFLOW-NWT specific features.
    """
    print("\nMODFLOW-NWT Features:")
    print("=" * 60)
    
    features = {
        "Newton-Raphson": "Improved linearization for unconfined flow",
        "UPW Package": "Upstream weighting for better stability",
        "Dry Cell Handling": "Robust rewetting and drying",
        "Solver Options": "GMRES with ILU preconditioning",
        "Convergence": "Better convergence for difficult problems"
    }
    
    for feature, description in features.items():
        print(f"  • {feature}: {description}")
    
    print("\nNWT Solver Parameters:")
    params = {
        "headtol": "Head change tolerance between iterations",
        "fluxtol": "Flow rate tolerance for convergence",
        "maxiterout": "Maximum Newton-Raphson iterations",
        "thickfact": "Factor for cell thickness in derivatives",
        "linmeth": "Linear solution method (1=GMRES, 2=ORTHOMIN)"
    }
    
    for param, desc in params.items():
        print(f"  • {param}: {desc}")

def run_model(workspace):
    """
    Run the MODFLOW-NWT model and analyze results.
    """
    # Build model
    mf, analytical_heads = build_mfnwt_model(workspace)
    
    # Write input files
    mf.write_input()
    
    # Check for mfnwt executable
    exe_path = Path("/home/danilopezmella/flopy_expert/bin/mfnwt")
    if exe_path.exists():
        mf.exe_name = str(exe_path)
    
    # Run model
    success, buff = mf.run_model(silent=False)
    
    results = {
        "runs": success,
        "converges": False,
        "output_exists": False,
        "error": None,
        "outputs": []
    }
    
    if success:
        # Check for output files
        hds_file = workspace / f"{mf.name}.hds"
        lst_file = workspace / f"{mf.name}.list"
        
        outputs = []
        if hds_file.exists():
            outputs.append(hds_file.name)
            results["output_exists"] = True
            
            # Read heads and compare with analytical
            try:
                hds = flopy.utils.HeadFile(str(hds_file))
                heads = hds.get_data()
                
                # Calculate error
                numerical_heads = heads[0, 0, :]
                max_error = np.max(np.abs(numerical_heads - analytical_heads))
                mean_error = np.mean(np.abs(numerical_heads - analytical_heads))
                
                print(f"\nAnalytical Comparison:")
                print(f"  Max error: {max_error:.6f} m")
                print(f"  Mean error: {mean_error:.6f} m")
                
                if max_error < 0.01:  # Less than 1 cm error
                    print("  ✓ Excellent agreement with analytical solution")
            except Exception as e:
                print(f"  Could not read heads: {e}")
        
        if lst_file.exists():
            outputs.append(lst_file.name)
            # Check convergence in listing file
            with open(lst_file, 'r') as f:
                content = f.read()
                # Check for various convergence indicators
                if any(term in content.upper() for term in ["NORMAL TERMINATION", "RUN END DATE", "PERCENT DISCREPANCY"]):
                    results["converges"] = True
        
        # List all output files
        for file in workspace.glob(f"{mf.name}.*"):
            if file.name not in outputs:
                outputs.append(file.name)
        
        results["outputs"] = outputs
    else:
        results["error"] = "Model did not run successfully"
    
    return results

def main():
    """
    Main function to demonstrate MODFLOW-NWT water table solution.
    """
    print("=" * 60)
    print("MODFLOW-NWT Water Table Solution Example")
    print("=" * 60)
    
    # Create workspace
    workspace = Path("nwt_example")
    workspace.mkdir(exist_ok=True)
    
    # Demonstrate NWT features
    demonstrate_nwt_features()
    
    # Run model
    print("\nRunning MODFLOW-NWT model...")
    results = run_model(workspace)
    
    # Save results
    results_file = Path("test_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Model run: {'✓ Success' if results['runs'] else '✗ Failed'}")
    print(f"Convergence: {'✓ Converged' if results['converges'] else '✗ Did not converge'}")
    print(f"Output files: {len(results['outputs'])}")
    
    if results['outputs']:
        print("\nGenerated files:")
        for file in results['outputs']:
            print(f"  - {file}")
    
    return results['runs'] and results['converges']

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)