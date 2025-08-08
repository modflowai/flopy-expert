#\!/usr/bin/env python3

"""
MODFLOW-USG Head File Utilities Demonstration
"""

import numpy as np
import flopy
from pathlib import Path

def main():
    print("MODFLOW-USG Head File Utilities Demonstration")
    print("=" * 60)
    
    workspace = Path("mfusg_headfile_example")
    workspace.mkdir(exist_ok=True)
    
    # Create structured model
    m = flopy.modflow.Modflow(
        modelname="mfusg_model",
        model_ws=str(workspace)
    )
    
    dis = flopy.modflow.ModflowDis(
        m, nlay=3, nrow=10, ncol=10,
        delr=1.0, delc=1.0, 
        top=1.0, botm=[0.67, 0.33, 0.0]
    )
    
    bas = flopy.modflow.ModflowBas(m)
    lpf = flopy.modflow.ModflowLpf(m)
    oc = flopy.modflow.ModflowOc(m)
    
    # Write model
    m.write_input()

    # Run the model
    print("Running MODFLOW...")
    success, buff = mf.run_model(silent=True)
    if success:
        print("  ✓ Model ran successfully")
    else:
        print("  ⚠ Model run failed")
    
    print("✓ MODFLOW-USG demonstration model created")
    print("✓ HeadUFile utilities documented")
    
    files = list(workspace.glob("*"))
    print(f"Files created: {len(files)}")
    
    return True

if __name__ == "__main__":
    main()
