#!/usr/bin/env python3

"""
MODFLOW 6 Core Functionality Demonstration

This model demonstrates essential MODFLOW 6 capabilities using FloPy:
- Basic groundwater flow simulation setup
- Package creation and configuration  
- Model writing and execution
- Binary output file handling
- Flow budget analysis

Based on test_mf6.py from the FloPy autotest suite.
"""

import numpy as np
import flopy
from pathlib import Path
import os
import sys

# Add the config directory to the path to import mf6_config
config_dir = Path(__file__).parent.parent.parent.parent / "config"
sys.path.append(str(config_dir))

try:
    from mf6_config import mf6_exe_path
except ImportError:
    # Use the actual mf6 executable path
    mf6_exe_path = "/home/danilopezmella/flopy_expert/bin/mf6"
    if not Path(mf6_exe_path).exists():
        mf6_exe_path = "mf6"
        print(f"Warning: Using default mf6 executable name.")

def create_mf6_model():
    """Create a comprehensive MODFLOW 6 model demonstrating core functionality."""
    
    # Model setup
    name = "mf6_demo"
    workspace = Path("mf6_example")
    workspace.mkdir(exist_ok=True)
    
    print(f"Creating MODFLOW 6 demonstration model: {name}")
    
    # Create simulation
    sim = flopy.mf6.MFSimulation(
        sim_name=name, 
        sim_ws=workspace, 
        exe_name=mf6_exe_path
    )
    
    # Time discretization
    pd = [(1.0, 1, 1.0), (10.0, 5, 1.2)]  # (perlen, nstp, tsmult)
    tdis = flopy.mf6.ModflowTdis(
        sim, 
        nper=len(pd), 
        perioddata=pd, 
        time_units="DAYS"
    )
    
    # Iterative model solution
    ims = flopy.mf6.ModflowIms(
        sim,
        print_option="SUMMARY",
        complexity="SIMPLE",
        outer_dvclose=1.0e-4,
        inner_dvclose=1.0e-5,
        rcloserecord=[1.0e-4, "STRICT"]
    )
    
    # Groundwater flow model
    gwf = flopy.mf6.ModflowGwf(
        sim, 
        modelname=name, 
        save_flows=True,
        print_input=True,
        print_flows=True
    )
    
    # Spatial discretization
    nrow, ncol, nlay = 20, 30, 3
    delr = 100.0  # meters
    delc = 100.0  # meters 
    top = 100.0
    botm = [80.0, 60.0, 40.0]
    
    dis = flopy.mf6.ModflowGwfdis(
        gwf,
        nlay=nlay,
        nrow=nrow, 
        ncol=ncol,
        delr=delr,
        delc=delc,
        top=top,
        botm=botm,
        length_units="METERS"
    )
    
    # Initial conditions
    strt = np.ones((nlay, nrow, ncol)) * 90.0
    ic = flopy.mf6.ModflowGwfic(gwf, strt=strt)
    
    # Node property flow package
    k = [10.0, 5.0, 1.0]  # Different K for each layer
    k33 = [1.0, 0.5, 0.1]  # Vertical conductivity
    
    npf = flopy.mf6.ModflowGwfnpf(
        gwf, 
        icelltype=1,  # Convertible layers
        k=k,
        k33=k33,
        save_specific_discharge=True,
        save_saturation=True
    )
    
    # Storage package
    sy = 0.1  # Specific yield
    ss = 1e-5  # Specific storage
    
    sto = flopy.mf6.ModflowGwfsto(
        gwf,
        iconvert=1,
        sy=sy,
        ss=ss,
        steady_state={0: True},
        transient={1: True}
    )
    
    # Constant head boundary conditions
    # Left and right boundaries
    chd_spd = []
    for i in range(nrow):
        # Left boundary (high head)
        chd_spd.append([(0, i, 0), 95.0])
        # Right boundary (low head) 
        chd_spd.append([(0, i, ncol-1), 85.0])
    
    chd = flopy.mf6.ModflowGwfchd(
        gwf,
        stress_period_data=chd_spd,
        print_input=True,
        print_flows=True,
        save_flows=False
    )
    
    # Well package - pumping and injection
    wel_spd = {}
    # Steady state period - injection well
    wel_spd[0] = [
        [(1, 10, 15), 500.0]  # Injection well (positive = injection)
    ]
    # Transient period - pumping well
    wel_spd[1] = [
        [(1, 10, 15), -800.0]  # Pumping well (negative = extraction)  
    ]
    
    wel = flopy.mf6.ModflowGwfwel(
        gwf,
        stress_period_data=wel_spd,
        print_input=True,
        print_flows=True,
        save_flows=False
    )
    
    # Recharge package
    rch_spd = {}
    rch_spd[0] = [[(0, i, j), 0.001] for i in range(nrow) for j in range(ncol)]
    rch_spd[1] = [[(0, i, j), 0.003] for i in range(nrow) for j in range(ncol)]
    
    rch = flopy.mf6.ModflowGwfrch(
        gwf,
        stress_period_data=rch_spd,
        print_input=True,
        print_flows=True
    )
    
    # Output control
    oc = flopy.mf6.ModflowGwfoc(
        gwf,
        budget_filerecord=f"{name}.cbc",
        head_filerecord=f"{name}.hds",
        headprintrecord=[("COLUMNS", 10, "WIDTH", 15, "DIGITS", 6, "GENERAL")],
        saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")],
        printrecord=[("HEAD", "LAST"), ("BUDGET", "ALL")]
    )
    
    print("Writing simulation files...")
    sim.write_simulation()
    print(f"Files written to: {workspace}")
    
    return sim, workspace

def run_model(sim, workspace):
    """Run the MODFLOW 6 model."""
    print("Running MODFLOW 6 simulation...")
    
    try:
        success, buff = sim.run_simulation(silent=False, report=True)
        if success:
            print("✓ Model completed successfully")
            return True
        else:
            print("✗ Model failed to complete")
            print("Buffer output:")
            for line in buff:
                print(line.decode().strip())
            return False
    except Exception as e:
        print(f"✗ Error running model: {e}")
        return False

def analyze_results(workspace, name):
    """Analyze model results."""
    print("\nAnalyzing results...")
    
    # Check output files
    lst_file = workspace / f"{name}.lst"
    hds_file = workspace / f"{name}.hds"
    cbc_file = workspace / f"{name}.cbc"
    
    results = {
        "listing_file": lst_file.exists(),
        "head_file": hds_file.exists(), 
        "budget_file": cbc_file.exists(),
        "convergence": False,
        "outputs": []
    }
    
    # Read output files if they exist
    if results["listing_file"]:
        print(f"✓ Listing file found: {lst_file.name}")
        results["outputs"].append(lst_file.name)
        
        # Check convergence
        try:
            with open(lst_file, 'r') as f:
                content = f.read()
                if "Normal termination of simulation" in content:
                    results["convergence"] = True
                    print("✓ Model converged successfully")
        except Exception as e:
            print(f"Could not read listing file: {e}")
    
    if results["head_file"]:
        print(f"✓ Head file found: {hds_file.name}")
        results["outputs"].append(hds_file.name)
        
        try:
            # Read heads using FloPy
            hds = flopy.utils.HeadFile(hds_file)
            times = hds.get_times()
            print(f"  Head data available for {len(times)} time steps")
            
            # Get heads for last time step
            heads = hds.get_data(totim=times[-1])
            print(f"  Head range: {heads.min():.2f} to {heads.max():.2f} m")
            
        except Exception as e:
            print(f"Could not read head file: {e}")
    
    if results["budget_file"]:
        print(f"✓ Budget file found: {cbc_file.name}")
        results["outputs"].append(cbc_file.name)
        
        try:
            # Read budget using FloPy
            cbc = flopy.utils.CellBudgetFile(cbc_file)
            records = cbc.get_unique_record_names()
            print(f"  Budget records: {', '.join(records)}")
            
            # Get volumetric budget
            volumetric_budget = cbc.get_volumetric_budget()
            if volumetric_budget is not None:
                print(f"  Volumetric budget calculated")
                
        except Exception as e:
            print(f"Could not read budget file: {e}")
    
    # Check other output files
    for file in workspace.glob("*"):
        if file.is_file() and file.suffix in ['.lst', '.hds', '.cbc']:
            continue
        elif file.is_file():
            results["outputs"].append(file.name)
    
    return results

def main():
    """Main function to demonstrate MODFLOW 6 functionality."""
    print("=" * 60)
    print("MODFLOW 6 Core Functionality Demonstration")
    print("=" * 60)
    
    try:
        # Create model
        sim, workspace = create_mf6_model()
        
        # Run model
        success = run_model(sim, workspace)
        
        # Analyze results
        results = analyze_results(workspace, "mf6_demo")
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Model execution: {'✓ Success' if success else '✗ Failed'}")
        print(f"Model convergence: {'✓ Converged' if results['convergence'] else '✗ Did not converge'}")
        print(f"Output files generated: {len(results['outputs'])}")
        
        if results["outputs"]:
            print("Output files:")
            for output in sorted(results["outputs"]):
                print(f"  - {output}")
        
        return success and results["convergence"]
        
    except Exception as e:
        print(f"✗ Error in main execution: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)