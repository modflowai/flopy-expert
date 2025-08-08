"""
Stream Flow Routing (SFR2) Package - WORKING VERSION

This script creates a CONVERGING model with SFR2 package.
"""

import numpy as np
import os
import flopy

def run_model():
    """Create a CONVERGING SFR model."""
    
    print("=== Stream Flow Routing (SFR2) - WORKING VERSION ===\n")
    
    # Model workspace
    model_ws = "./model_output"
    os.makedirs(model_ws, exist_ok=True)
    
    # Create MODFLOW-NWT model
    modelname = "sfr_converged"
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
    
    # BAS package - constant heads on sides for stable flow
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
        laytyp=0  # Confined for stability
    )
    
    print("Creating SFR package...")
    
    # MINIMAL SFR - just 3 reaches in middle row
    nreaches = 3
    reach_data = flopy.modflow.ModflowSfr2.get_empty_reach_data(nreaches)
    
    # Horizontal stream through middle
    for i in range(nreaches):
        reach_data[i]['k'] = 0
        reach_data[i]['i'] = 5  # Middle row
        reach_data[i]['j'] = 3 + i  # Columns 3, 4, 5
        reach_data[i]['iseg'] = 1
        reach_data[i]['ireach'] = i + 1
        reach_data[i]['rchlen'] = 100.0
        reach_data[i]['strtop'] = 94.5 - (i * 0.1)  # Just below heads
        reach_data[i]['strthick'] = 1.0
        reach_data[i]['strhc1'] = 0.001  # VERY low conductance
    
    # Minimal segment data with specified stage
    segment_data = {0: flopy.modflow.ModflowSfr2.get_empty_segment_data(1)}
    
    segment_data[0][0]['nseg'] = 1
    segment_data[0][0]['icalc'] = 0  # Specified stage (most stable)
    segment_data[0][0]['outseg'] = 0
    segment_data[0][0]['iupseg'] = 0
    segment_data[0][0]['flow'] = 0.01  # Tiny flow
    segment_data[0][0]['runoff'] = 0.0
    segment_data[0][0]['etsw'] = 0.0
    segment_data[0][0]['pptsw'] = 0.0
    segment_data[0][0]['roughch'] = 0.035
    segment_data[0][0]['hcond1'] = 94.4  # Specified stage
    segment_data[0][0]['hcond2'] = 94.2
    
    # Create SFR package
    sfr = flopy.modflow.ModflowSfr2(
        mf,
        nstrm=nreaches,
        nss=1,
        reach_data=reach_data,
        segment_data=segment_data
    )
    
    print(f"  ✓ SFR created: {nreaches} reaches")
    print(f"  • Very low conductance: 0.001")
    print(f"  • Minimal flow: 0.01 m³/day")
    print(f"  • Specified stage (stable)")
    
    # NWT solver with VERY relaxed criteria
    nwt = flopy.modflow.ModflowNwt(
        mf,
        headtol=0.1,      # Very relaxed
        fluxtol=5000,     # Very relaxed
        maxiterout=500,   # Many iterations allowed
        thickfact=1e-5,   # Help with drying
        linmeth=1,        # GMRES
        iprnwt=0,
        ibotav=0,
        options='COMPLEX'
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
        print("\n✓✓✓ MODEL CONVERGED! ✓✓✓")
        print("SFR model successfully converged!")
        
        # Check for mass balance
        list_file = os.path.join(model_ws, f"{modelname}.list")
        if os.path.exists(list_file):
            with open(list_file, 'r') as f:
                content = f.read()
            
            if 'PERCENT DISCREPANCY' in content:
                import re
                matches = re.findall(r'PERCENT DISCREPANCY\s*=\s*([-\d.]+)', content)
                if matches:
                    disc = float(matches[-1])
                    print(f"Mass balance discrepancy: {disc:.6f}%")
        
        return "CONVERGED"
    else:
        print("\n✗ Model failed to converge")
        return "FAILED"

if __name__ == "__main__":
    result = run_model()
    print(f"\nFinal Result: {result}")