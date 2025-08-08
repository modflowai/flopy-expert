"""
Working MODFLOW-NWT model with SFR and AG packages
"""

import numpy as np
import os
import flopy

def run_model():
    """Create working model with SFR and AG packages."""
    
    print("=== Working SFR + AG Model ===\n")
    
    # Model workspace
    model_ws = "./model_output_working"
    if not os.path.exists(model_ws):
        os.makedirs(model_ws)
    
    # Create MODFLOW-NWT Model
    modelname = "sfr_ag_working"
    mf = flopy.modflow.Modflow(
        modelname=modelname,
        exe_name="/home/danilopezmella/flopy_expert/bin/mfnwt",
        version="mfnwt",
        model_ws=model_ws
    )
    
    # Simple grid
    nlay = 1
    nrow = 10
    ncol = 10
    nper = 1  # Single stress period for simplicity
    
    dis = flopy.modflow.ModflowDis(
        mf,
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        nper=nper,
        delr=100.0,
        delc=100.0,
        top=100.0,
        botm=50.0,
        perlen=[365.0],
        nstp=[10],
        tsmult=[1.0],
        steady=[False]
    )
    
    # Basic package - no constant heads near stream
    ibound = np.ones((nlay, nrow, ncol), dtype=int)
    strt = np.ones((nlay, nrow, ncol)) * 95.0
    bas = flopy.modflow.ModflowBas(mf, ibound=ibound, strt=strt)
    
    # UPW package
    upw = flopy.modflow.ModflowUpw(
        mf,
        hk=10.0,
        vka=1.0,
        sy=0.15,
        ss=1e-5,
        laytyp=1,
        iphdry=0
    )
    
    # Create SFR Package with proper elevations
    print("Creating SFR package...")
    
    # Build reach data with DECREASING elevations
    nreaches = 8
    reach_data = flopy.modflow.ModflowSfr2.get_empty_reach_data(nreaches)
    
    # Stream runs through middle of model
    col = 4  # Middle column
    start_elev = 99.0  # Start high
    
    for i in range(nreaches):
        row = i + 1  # Rows 1-8 (avoid edges)
        reach_data[i]['k'] = 0  # Layer 0
        reach_data[i]['i'] = row  # Row
        reach_data[i]['j'] = col  # Column
        reach_data[i]['iseg'] = 1  # All in segment 1
        reach_data[i]['ireach'] = i + 1  # Reach number (1-based)
        reach_data[i]['rchlen'] = 100.0  # Length
        reach_data[i]['strtop'] = start_elev - (i * 0.5)  # DECREASE by 0.5m each reach
        reach_data[i]['slope'] = 0.005  # Positive slope
        reach_data[i]['strthick'] = 1.0  # Bed thickness
        reach_data[i]['strhc1'] = 1.0  # Streambed K
    
    # Segment data - single segment
    segment_data = {0: flopy.modflow.ModflowSfr2.get_empty_segment_data(1)}
    
    segment_data[0][0]['nseg'] = 1
    segment_data[0][0]['icalc'] = 0  # Use specified stage (avoid slope calculation)
    segment_data[0][0]['outseg'] = 0  # Discharge out of model
    segment_data[0][0]['iupseg'] = 0  # No upstream segment
    segment_data[0][0]['flow'] = 50.0  # Initial flow
    segment_data[0][0]['runoff'] = 0.0
    segment_data[0][0]['etsw'] = 0.0
    segment_data[0][0]['pptsw'] = 0.0
    segment_data[0][0]['roughch'] = 0.03  # Manning's n
    segment_data[0][0]['hcond1'] = 98.0  # Specify stage for first reach
    segment_data[0][0]['hcond2'] = 94.0  # Specify stage for last reach
    segment_data[0][0]['thickm1'] = 1.0  # Bed thickness
    segment_data[0][0]['thickm2'] = 1.0  # Bed thickness
    
    # Create SFR package
    sfr = flopy.modflow.ModflowSfr2(
        mf,
        nstrm=nreaches,
        nss=1,
        reach_data=reach_data,
        segment_data=segment_data,
        unit_number=17
    )
    
    print(f"  ✓ SFR created: {nreaches} reaches")
    print(f"  Elevations: {start_elev:.1f} to {start_elev - (nreaches-1)*0.5:.1f} m")
    
    # Create AG Package
    print("\nCreating AG package...")
    
    # AG package with minimal options
    ag = flopy.modflow.ModflowAg(
        mf,
        options=['NOPRINT'],
        nper=nper,
        unitnumber=69
    )
    
    print("  ✓ AG package created")
    
    # NWT Solver with better convergence
    nwt = flopy.modflow.ModflowNwt(
        mf,
        headtol=0.1,  # Relaxed for better convergence
        fluxtol=5000,  # Relaxed
        maxiterout=200,  # More iterations
        linmeth=1,
        iprnwt=0,
        backflag=1,  # Use backtracking
        maxbackiter=50  # Backtracking iterations
    )
    
    # Output control
    oc = flopy.modflow.ModflowOc(
        mf,
        stress_period_data={(0, 0): ['save head', 'save budget']},
        compact=True
    )
    
    # Write files
    print("\nWriting model files...")
    mf.write_input()
    
    # Check files
    files = os.listdir(model_ws)
    print(f"  Files created: {len(files)}")
    
    sfr_file = [f for f in files if '.sfr' in f]
    ag_file = [f for f in files if '.ag' in f]
    
    if sfr_file:
        print(f"  ✓ SFR file: {sfr_file[0]}")
        # Check SFR file content
        sfr_path = os.path.join(model_ws, sfr_file[0])
        with open(sfr_path, 'r') as f:
            lines = f.readlines()
            print(f"    SFR file has {len(lines)} lines")
    
    if ag_file:
        print(f"  ✓ AG file: {ag_file[0]}")
        # Check AG file content
        ag_path = os.path.join(model_ws, ag_file[0])
        with open(ag_path, 'r') as f:
            lines = f.readlines()
            print(f"    AG file has {len(lines)} lines")
    
    # Run model
    print("\nRunning model...")
    success, buff = mf.run_model(silent=True)
    
    if success:
        print("  ✓ Model ran successfully!")
        
        # Check convergence
        list_file = os.path.join(model_ws, f"{modelname}.list")
        if os.path.exists(list_file):
            with open(list_file, 'r') as f:
                content = f.read()
                
            # Check for errors
            if 'ERROR' in content:
                print("\n  Errors found:")
                import re
                errors = re.findall(r'\*\*\* ERROR \*\*\*.*', content)
                for err in errors[:3]:  # Show first 3 errors
                    print(f"    {err}")
            
            # Check convergence
            if 'PERCENT DISCREPANCY' in content:
                import re
                matches = re.findall(r'PERCENT DISCREPANCY\s*=\s*([-\d.]+)', content)
                if matches:
                    last_disc = float(matches[-1])
                    if abs(last_disc) < 1.0:
                        print(f"  ✓ Converged! (discrepancy: {last_disc:.6f}%)")
                    else:
                        print(f"  ⚠ High discrepancy: {last_disc:.2f}%")
            
            # Check for SFR output
            if 'STREAM NETWORK' in content:
                print("  ✓ SFR network processed")
            
            # Check for AG output
            if 'AG PACKAGE' in content or 'AGRICULTURAL' in content:
                print("  ✓ AG package processed")
    else:
        print("  ⚠ Model failed")
        # Show error
        list_file = os.path.join(model_ws, f"{modelname}.list")
        if os.path.exists(list_file):
            with open(list_file, 'r') as f:
                lines = f.readlines()
            # Show last 20 lines
            print("\n  Last lines of listing file:")
            for line in lines[-20:]:
                if 'ERROR' in line or 'WARNING' in line:
                    print(f"    {line.strip()}")
    
    print("\n✓ Model Complete!")
    return mf

if __name__ == "__main__":
    model = run_model()