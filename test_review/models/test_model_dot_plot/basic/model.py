"""
MODFLOW Model Plotting Demonstration

This script demonstrates FloPy's model plotting capabilities including:
- Model.plot() method for plotting all model packages
- Dataset plotting for specific parameters
- Layer-specific plotting with mflay parameter
- Export functionality to save plots as images

The test creates a simple MODFLOW model and uses matplotlib through FloPy
to generate plots of the model grid and parameter datasets.
"""

import numpy as np
import flopy
import matplotlib.pyplot as plt

def run_model():
    """
    Create and run a MODFLOW model for plotting demonstration.
    Demonstrates various plotting capabilities available in FloPy.
    """
    
    # Create model workspace
    model_ws = "model_output"
    
    # Model dimensions and parameters
    nlay, nrow, ncol = 3, 10, 10
    delr = delc = 100.0
    top = 100.0
    botm = [75.0, 50.0, 25.0]
    
    # Create MODFLOW model
    mf = flopy.modflow.Modflow(
        modelname="plot_demo",
        model_ws=model_ws,
        exe_name='/home/danilopezmella/flopy_expert/pyemu/verification/10par_xsec/master_opt0/model/mf2005.exe'
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
        nper=3,
        perlen=[1, 100, 100],
        nstp=[1, 10, 10],
        steady=[True, False, False]
    )
    
    # Basic package
    ibound = np.ones((nlay, nrow, ncol), dtype=int)
    strt = np.ones((nlay, nrow, ncol)) * 95.0
    
    bas = flopy.modflow.ModflowBas(
        mf,
        ibound=ibound,
        strt=strt
    )
    
    # Layer Property Flow package with variable hydraulic conductivity
    # Create zones for plotting demonstration
    hk = np.ones((nlay, nrow, ncol))
    hk[:, 0:3, :] = 50.0      # High K zone
    hk[:, 3:7, :] = 10.0      # Medium K zone  
    hk[:, 7:10, :] = 1.0      # Low K zone
    
    lpf = flopy.modflow.ModflowLpf(
        mf,
        hk=hk,
        vka=0.1,
        ipakcb=53
    )
    
    # Well package for stress visualization
    wel_data = []
    # Add pumping wells in different locations
    for i in range(3):
        wel_data.append([i, 2, 2, -500.0])  # Pumping wells
        wel_data.append([i, 7, 7, -300.0])  # More pumping wells
    
    wel = flopy.modflow.ModflowWel(
        mf,
        stress_period_data={0: wel_data, 1: wel_data, 2: wel_data},
        ipakcb=53
    )
    
    # Constant head package for boundary conditions
    chd_data = []
    # Left boundary - high heads
    for j in range(nrow):
        for k in range(nlay):
            chd_data.append([k, j, 0, 100.0, 100.0])
    
    # Right boundary - low heads  
    for j in range(nrow):
        for k in range(nlay):
            chd_data.append([k, j, ncol-1, 90.0, 90.0])
    
    chd = flopy.modflow.ModflowChd(
        mf,
        stress_period_data={0: chd_data, 1: chd_data, 2: chd_data},
        ipakcb=53
    )
    
    # Output control
    spd = {
        (0, 0): ["print head", "print budget", "save head", "save budget"],
        (1, 9): ["print head", "print budget", "save head", "save budget"],
        (2, 9): ["print head", "print budget", "save head", "save budget"]
    }
    oc = flopy.modflow.ModflowOc(mf, stress_period_data=spd, compact=True)
    
    # Solver
    pcg = flopy.modflow.ModflowPcg(mf, mxiter=50, iter1=30)
    
    # Write and run model
    print("Writing MODFLOW files...")
    mf.write_input()
    
    print("Running MODFLOW...")
    success, buff = mf.run_model(silent=True)
    
    if success:
        print("MODFLOW completed successfully")
        
        # Demonstrate plotting capabilities
        print("\nDemonstrating FloPy plotting capabilities...")
        
        try:
            # 1. Model plot - plots all packages
            print("Creating model plot...")
            ax = mf.plot()
            if isinstance(ax, list):
                print(f"Model plot created with {len(ax)} subplots")
                plt.close('all')  # Close to prevent memory issues
            
            # 2. Layer-specific plot
            print("Creating layer-specific plot...")
            ax = mf.plot(mflay=0)  # Plot only layer 0
            if isinstance(ax, list):
                print(f"Layer 0 plot created with {len(ax)} subplots")
                plt.close('all')
            
            # 3. Dataset plot - hydraulic conductivity
            print("Creating hydraulic conductivity plot...")
            ax = mf.lpf.hk.plot()
            if isinstance(ax, list):
                print(f"Hydraulic conductivity plot created with {len(ax)} subplots")
                plt.close('all')
            
            # 4. Save plots to files
            print("Saving plots to files...")
            mf.plot(mflay=0, filename_base="plot_demo", file_extension="png")
            print("Plots saved as PNG files")
            
            print("Plot demonstration completed successfully!")
            
        except Exception as e:
            print(f"Plotting error (expected in headless environments): {e}")
            print("Model completed successfully - plotting may not work without display")
    
    else:
        print("MODFLOW failed to run")
        print("".join(buff))
        raise RuntimeError("MODFLOW simulation failed")
    
    return mf

if __name__ == "__main__":
    model = run_model()