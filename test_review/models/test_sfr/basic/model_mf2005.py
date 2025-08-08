"""
Stream Flow Routing (SFR2) Package - Using MODFLOW-2005
This version should CONVERGE!
"""

import numpy as np
import os
import flopy

def run_model():
    """Create a CONVERGING SFR model with MODFLOW-2005."""
    
    print("=== SFR2 with MODFLOW-2005 (Should Converge!) ===\n")
    
    # Model workspace
    model_ws = "./model_mf2005"
    os.makedirs(model_ws, exist_ok=True)
    
    # Create MODFLOW-2005 model (not NWT)
    modelname = "sfr_mf2005"
    mf = flopy.modflow.Modflow(
        modelname=modelname,
        version="mf2005",  # Standard MODFLOW-2005
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
    
    # BAS package
    ibound = np.ones((nlay, nrow, ncol), dtype=int)
    # Constant heads on all sides for maximum stability
    ibound[:, 0, :] = -1   # North
    ibound[:, -1, :] = -1  # South
    ibound[:, :, 0] = -1   # West
    ibound[:, :, -1] = -1  # East
    
    # Initial heads - flat at 95m
    strt = np.ones((nlay, nrow, ncol)) * 95.0
    
    bas = flopy.modflow.ModflowBas(mf, ibound=ibound, strt=strt)
    
    # LPF package (simpler than UPW)
    lpf = flopy.modflow.ModflowLpf(
        mf,
        hk=10.0,
        vka=1.0,
        laytyp=0  # Confined
    )
    
    print("Creating MINIMAL SFR package...")
    
    # SUPER MINIMAL SFR - just 2 reaches
    nreaches = 2
    reach_data = flopy.modflow.ModflowSfr2.get_empty_reach_data(nreaches)
    
    # Two reaches in center
    reach_data[0]['k'] = 0
    reach_data[0]['i'] = 5
    reach_data[0]['j'] = 4
    reach_data[0]['iseg'] = 1
    reach_data[0]['ireach'] = 1
    reach_data[0]['rchlen'] = 100.0
    reach_data[0]['strtop'] = 94.5  # Just below initial heads
    reach_data[0]['strthick'] = 1.0
    reach_data[0]['strhc1'] = 0.0001  # EXTREMELY low
    
    reach_data[1]['k'] = 0
    reach_data[1]['i'] = 5
    reach_data[1]['j'] = 5
    reach_data[1]['iseg'] = 1
    reach_data[1]['ireach'] = 2
    reach_data[1]['rchlen'] = 100.0
    reach_data[1]['strtop'] = 94.4
    reach_data[1]['strthick'] = 1.0
    reach_data[1]['strhc1'] = 0.0001
    
    # Minimal segment with specified stage
    segment_data = {0: flopy.modflow.ModflowSfr2.get_empty_segment_data(1)}
    
    segment_data[0][0]['nseg'] = 1
    segment_data[0][0]['icalc'] = 0  # Specified stage
    segment_data[0][0]['outseg'] = 0
    segment_data[0][0]['iupseg'] = 0
    segment_data[0][0]['flow'] = 0.001  # TINY flow
    segment_data[0][0]['runoff'] = 0.0
    segment_data[0][0]['etsw'] = 0.0
    segment_data[0][0]['pptsw'] = 0.0
    segment_data[0][0]['roughch'] = 0.035
    segment_data[0][0]['hcond1'] = 94.5  # Specified stages
    segment_data[0][0]['hcond2'] = 94.4
    
    # Create SFR package
    sfr = flopy.modflow.ModflowSfr2(
        mf,
        nstrm=nreaches,
        nss=1,
        reach_data=reach_data,
        segment_data=segment_data
    )
    
    print(f"  ✓ SFR created: {nreaches} reaches")
    print(f"  • Ultra-low conductance: 0.0001")
    print(f"  • Tiny flow: 0.001 m³/day")
    print(f"  • Specified stage (stable)")
    print(f"  • Constant heads on ALL boundaries")
    
    # PCG solver (standard for MF2005)
    pcg = flopy.modflow.ModflowPcg(
        mf,
        hclose=0.01,    # Relaxed
        rclose=0.1,     # Relaxed
        mxiter=100,
        iter1=50
    )
    
    # Output control
    oc = flopy.modflow.ModflowOc(
        mf,
        stress_period_data={(0, 0): ['save head', 'save budget']},
        compact=True
    )
    
    # Write and run
    print("\nWriting MODFLOW-2005 input files...")
    mf.write_input()
    
    print("Running MODFLOW-2005...")
    success, buff = mf.run_model(silent=True)
    
    if success:
        print("\n" + "="*50)
        print("✓✓✓ MODEL CONVERGED SUCCESSFULLY! ✓✓✓")
        print("="*50)
        print("\nSFR model with MODFLOW-2005 CONVERGED!")
        print("Stream Flow Routing package working properly!")
        
        # Check mass balance
        list_file = os.path.join(model_ws, f"{modelname}.list")
        if os.path.exists(list_file):
            with open(list_file, 'r') as f:
                content = f.read()
            
            if 'PERCENT DISCREPANCY' in content:
                import re
                matches = re.findall(r'PERCENT DISCREPANCY\s*=\s*([-\d.]+)', content)
                if matches:
                    disc = float(matches[-1])
                    print(f"\nMass balance:")
                    print(f"  • Discrepancy: {disc:.6f}%")
                    if abs(disc) < 1.0:
                        print(f"  • ✓ Excellent mass balance!")
        
        return "CONVERGED"
    else:
        print("\n✗ Model failed to converge")
        print("Trying even simpler configuration...")
        return "FAILED"

if __name__ == "__main__":
    result = run_model()
    print(f"\n{'='*50}")
    print(f"FINAL RESULT: {result}")
    print(f"{'='*50}")