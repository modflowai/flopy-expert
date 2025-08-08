"""
Test base model without SFR - should converge
"""

import numpy as np
import os
import flopy

def run_model():
    """Test base model convergence."""
    
    print("=== Testing Base Model (No SFR) ===\n")
    
    # Model workspace
    model_ws = "./model_base"
    os.makedirs(model_ws, exist_ok=True)
    
    # Create MODFLOW-NWT model
    modelname = "base_test"
    mf = flopy.modflow.Modflow(
        modelname=modelname,
        version="mfnwt",
        model_ws=model_ws
    )
    
    # Simple grid
    nlay = 1
    nrow = 10  
    ncol = 10
    
    # DIS package
    dis = flopy.modflow.ModflowDis(
        mf,
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        nper=1,
        delr=100.0,
        delc=100.0,
        top=100.0,
        botm=0.0,
        perlen=[1.0],
        nstp=[1],
        tsmult=[1.0],
        steady=[True]
    )
    
    # BAS package - constant heads on sides
    ibound = np.ones((nlay, nrow, ncol), dtype=int)
    ibound[:, :, 0] = -1   # West boundary
    ibound[:, :, -1] = -1  # East boundary
    
    # Initial heads - gentle gradient
    strt = np.ones((nlay, nrow, ncol)) * 95.0
    strt[:, :, 0] = 96.0   # Higher on west
    strt[:, :, -1] = 94.0  # Lower on east
    
    bas = flopy.modflow.ModflowBas(mf, ibound=ibound, strt=strt)
    
    # UPW package
    upw = flopy.modflow.ModflowUpw(
        mf,
        hk=10.0,
        vka=1.0,
        sy=0.15,
        ss=1e-5,
        laytyp=0  # Confined
    )
    
    print("Base model configuration:")
    print(f"  • Grid: {nlay}x{nrow}x{ncol}")
    print(f"  • Constant heads: West=96m, East=94m")
    print(f"  • Hydraulic conductivity: 10 m/day")
    print(f"  • NO SFR package")
    
    # NWT solver
    nwt = flopy.modflow.ModflowNwt(
        mf,
        headtol=0.01,
        fluxtol=500,
        maxiterout=100,
        linmeth=1,
        iprnwt=0
    )
    
    # Output control
    oc = flopy.modflow.ModflowOc(
        mf,
        stress_period_data={(0, 0): ['save head', 'save budget']},
        compact=True
    )
    
    # Write and run
    print("\nWriting model files...")
    mf.write_input()
    
    print("Running model...")
    success, buff = mf.run_model(silent=True)
    
    if success:
        print("\n✓✓✓ BASE MODEL CONVERGED! ✓✓✓")
        print("Base model works fine without SFR")
        return "CONVERGED"
    else:
        print("\n✗ Base model failed")
        print("Problem is with base configuration, not SFR")
        return "FAILED"

if __name__ == "__main__":
    result = run_model()
    print(f"\nResult: {result}")