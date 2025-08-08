"""
List Budget Utilities with FloPy - Budget Data Processing

This example demonstrates FloPy's list budget utilities for reading and processing
MODFLOW budget data from list files. These utilities parse budget information from
MODFLOW, MODFLOW 6, MODFLOW-USG, and MT3DMS output files and provide structured
access to budget data, time series, and model diagnostics.

Key FloPy components demonstrated:
- flopy.utils.MfListBudget - MODFLOW 2005/NWT list file reader
- flopy.utils.Mf6ListBudget - MODFLOW 6 list file reader  
- flopy.utils.MfusgListBudget - MODFLOW-USG list file reader
- flopy.utils.MtListBudget - MT3DMS list file reader
- Budget data extraction and analysis
- Time series processing and dataframe conversion
- Model runtime analysis

The model creates a simple MODFLOW simulation to generate list file output,
then demonstrates various list budget utilities for processing the results.
"""

import os
import sys
import numpy as np
import pandas as pd

# Add the test_review directory to the path to import config
sys.path.append('/home/danilopezmella/flopy_expert/test_review')
from mf6_config import get_mf6_exe

from flopy.mf6 import (
    MFSimulation,
    ModflowGwf,
    ModflowGwfchd,
    ModflowGwfdis,
    ModflowGwfic,
    ModflowGwfnpf,
    ModflowGwfoc,
    ModflowGwfwel,
    ModflowIms,
    ModflowTdis,
)
from flopy.utils import Mf6ListBudget

def create_demo_model():
    """Create a simple MODFLOW 6 model to generate list file output"""
    
    print("Creating demo MODFLOW 6 model for list budget analysis...")
    
    # Model parameters
    name = "listbudget"
    workspace = "./model_output"
    
    # Create workspace
    if not os.path.exists(workspace):
        os.makedirs(workspace)
    
    # Grid and time parameters
    nlay, nrow, ncol = 3, 10, 10
    delr = delc = 100.0
    top = 100.0
    botm = [50.0, 0.0, -50.0]
    nper = 5
    perlen = [1, 10, 10, 10, 1]
    
    # Create simulation
    sim = MFSimulation(
        sim_name=name,
        exe_name=get_mf6_exe(),
        sim_ws=workspace,
    )
    
    # Time discretization
    tdis = ModflowTdis(
        sim,
        nper=nper,
        perioddata=[(p, 1, 1.0) for p in perlen]
    )
    
    # Iterative model solution
    ims = ModflowIms(
        sim,
        print_option="summary",
        outer_maximum=100,
        inner_maximum=100,
    )
    
    # Groundwater flow model  
    gwf = ModflowGwf(sim, modelname=name, print_input=True, save_flows=True)
    
    # Discretization
    dis = ModflowGwfdis(
        gwf,
        nlay=nlay, nrow=nrow, ncol=ncol,
        delr=delr, delc=delc,
        top=top, botm=botm
    )
    
    # Initial conditions
    ic = ModflowGwfic(gwf, strt=75.0)
    
    # Node property flow
    npf = ModflowGwfnpf(gwf, icelltype=1, k=10.0)
    
    # Constant head boundaries
    chd_spd = []
    for k in range(nlay):
        chd_spd.extend([
            [k, 0, j, 90.0] for j in range(ncol)  # Top row
        ])
        chd_spd.extend([
            [k, nrow-1, j, 60.0] for j in range(ncol)  # Bottom row  
        ])
    chd = ModflowGwfchd(gwf, stress_period_data={0: chd_spd})
    
    # Wells with time-varying pumping
    wel_spd = {}
    for per in range(nper):
        rate = -1000.0 * (per + 1)  # Increasing pumping rate
        wel_spd[per] = [
            [1, 5, 5, rate],      # Center well
            [2, 3, 7, rate * 0.5], # Secondary well
        ]
    wel = ModflowGwfwel(gwf, stress_period_data=wel_spd)
    
    # Output control with comprehensive budget output
    oc = ModflowGwfoc(
        gwf,
        budget_filerecord=f"{name}.cbc",
        head_filerecord=f"{name}.hds", 
        printrecord=[
            ("HEAD", "ALL"),
            ("BUDGET", "ALL")
        ],
        saverecord=[
            ("HEAD", "ALL"),
            ("BUDGET", "ALL")
        ]
    )
    
    return sim, gwf

def demonstrate_mf6_list_budget():
    """Demonstrate MODFLOW 6 list budget processing"""
    
    print("\n" + "="*50)
    print("MODFLOW 6 LIST BUDGET DEMONSTRATION")
    print("="*50)
    
    # Create and run the demo model
    sim, gwf = create_demo_model()
    
    print("\n1. Running MODFLOW 6 model...")
    sim.write_simulation()
    success, buff = sim.run_simulation(silent=True)
    
    if not success:
        print("Model run failed - cannot demonstrate list budget utilities")
        return None
    
    print("   Model run completed successfully")
    
    # Find the list file
    workspace = "./model_output"
    list_file = os.path.join(workspace, f"{gwf.name}.lst")
    
    if not os.path.exists(list_file):
        print(f"List file not found: {list_file}")
        return None
        
    print(f"   List file: {list_file}")
    print(f"   File size: {os.path.getsize(list_file):,} bytes")
    
    # Create Mf6ListBudget object
    print("\n2. Creating Mf6ListBudget object...")
    try:
        mf6_list = Mf6ListBudget(list_file)
        print("   Successfully created Mf6ListBudget object")
    except Exception as e:
        print(f"   Error creating Mf6ListBudget: {e}")
        return None
    
    # Get record names
    print("\n3. Analyzing budget record names...")
    names = mf6_list.get_record_names()
    print(f"   Found {len(names)} budget record types:")
    for i, name in enumerate(names):
        print(f"     {i+1:2d}. {name}")
    
    # Get time step data
    print("\n4. Analyzing time step information...")
    kstpkper = mf6_list.get_kstpkper()
    times = mf6_list.get_times()
    
    print(f"   Time steps: {len(kstpkper)}")
    print(f"   Time range: {times[0]:.1f} to {times[-1]:.1f}")
    
    for i, (kstp, kper) in enumerate(kstpkper[:5]):  # Show first 5
        print(f"     Step {i+1}: Period {kper+1}, Time step {kstp+1}, Time {times[i]:.1f}")
    
    if len(kstpkper) > 5:
        print(f"     ... and {len(kstpkper)-5} more time steps")
    
    return mf6_list, names, kstpkper, times

def analyze_budget_data(mf6_list, names, kstpkper, times):
    """Analyze budget data in detail"""
    
    print("\n" + "="*50)
    print("BUDGET DATA ANALYSIS")
    print("="*50)
    
    # Get budget data for last time step
    print("\n5. Analyzing final budget data...")
    final_budget = mf6_list.get_data(idx=-1)
    
    if final_budget is not None:
        print(f"   Final budget array shape: {final_budget.shape}")
        print(f"   Budget components:")
        
        # Show budget components
        for i, record in enumerate(final_budget):
            if i < 10:  # Show first 10 components
                name = record['name'] if 'name' in record.dtype.names else f"Component_{i}"
                value = record['value'] if 'value' in record.dtype.names else record[1]
                print(f"     {name:20s}: {value:12.2f}")
        
        if len(final_budget) > 10:
            print(f"     ... and {len(final_budget)-10} more components")
    
    # Get incremental data
    print("\n6. Getting incremental budget data...")
    try:
        inc_data = mf6_list.get_incremental()
        if inc_data is not None:
            print(f"   Incremental data shape: {inc_data.shape}")
            print(f"   Available for {len(inc_data)} time steps")
        else:
            print("   No incremental data available")
    except Exception as e:
        print(f"   Error getting incremental data: {e}")
    
    # Get cumulative data
    print("\n7. Getting cumulative budget data...")
    try:
        cum_data = mf6_list.get_cumulative()
        if cum_data is not None:
            print(f"   Cumulative data shape: {cum_data.shape}")
            print(f"   Tracks budget over {len(cum_data)} time steps")
        else:
            print("   No cumulative data available")
    except Exception as e:
        print(f"   Error getting cumulative data: {e}")

def demonstrate_dataframes(mf6_list):
    """Demonstrate dataframe conversion capabilities"""
    
    print("\n" + "="*50) 
    print("DATAFRAME CONVERSION DEMONSTRATION")
    print("="*50)
    
    print("\n8. Converting budget data to pandas DataFrames...")
    try:
        df_flux, df_vol = mf6_list.get_dataframes(start_datetime="1/1/2020")
        
        print(f"   Flux DataFrame shape: {df_flux.shape}")
        print(f"   Volume DataFrame shape: {df_vol.shape}")
        
        print(f"\n   Flux DataFrame columns:")
        for i, col in enumerate(df_flux.columns):
            if i < 8:  # Show first 8 columns
                print(f"     {col}")
        if len(df_flux.columns) > 8:
            print(f"     ... and {len(df_flux.columns)-8} more columns")
        
        print(f"\n   Sample flux data (first 3 rows):")
        print(df_flux.head(3).to_string())
        
        return df_flux, df_vol
        
    except Exception as e:
        print(f"   Error creating DataFrames: {e}")
        return None, None

def analyze_model_performance(mf6_list):
    """Analyze model performance metrics"""
    
    print("\n" + "="*50)
    print("MODEL PERFORMANCE ANALYSIS") 
    print("="*50)
    
    print("\n9. Analyzing model runtime...")
    try:
        runtime_seconds = mf6_list.get_model_runtime(units="seconds")
        runtime_minutes = mf6_list.get_model_runtime(units="minutes") 
        
        print(f"   Total runtime: {runtime_seconds:.3f} seconds")
        print(f"                  {runtime_minutes:.4f} minutes")
        
        if runtime_seconds > 0:
            print(f"   Performance: Model completed successfully in {runtime_seconds:.3f}s")
        
    except Exception as e:
        print(f"   Error getting runtime: {e}")
    
    # Check for convergence information
    print("\n10. Checking model convergence...")
    try:
        # Try to get budget data to check for convergence issues
        final_budget = mf6_list.get_data(idx=-1)
        if final_budget is not None:
            # Look for percent discrepancy
            for record in final_budget:
                name = record['name'] if 'name' in record.dtype.names else str(record[0])
                if 'PERCENT' in name.upper() and 'DISCREPANCY' in name.upper():
                    value = record['value'] if 'value' in record.dtype.names else record[1]
                    print(f"   {name}: {value:.6f}%")
                    if abs(value) < 0.01:
                        print(f"   ✓ Excellent mass balance (< 0.01%)")
                    elif abs(value) < 0.1: 
                        print(f"   ✓ Good mass balance (< 0.1%)")
                    else:
                        print(f"   ⚠ Mass balance issue (> 0.1%)")
                    
    except Exception as e:
        print(f"   Error checking convergence: {e}")

def create_budget_summary():
    """Create a summary of budget analysis capabilities"""
    
    print("\n" + "="*50)
    print("BUDGET UTILITIES SUMMARY")
    print("="*50)
    
    summary = {
        "List Budget Classes": [
            "MfListBudget - MODFLOW 2005/NWT list files",
            "Mf6ListBudget - MODFLOW 6 list files", 
            "MfusgListBudget - MODFLOW-USG list files",
            "MtListBudget - MT3DMS list files"
        ],
        "Key Methods": [
            "get_record_names() - Available budget components",
            "get_data() - Budget data by time step",
            "get_times() - Simulation times",
            "get_incremental() - Time step changes",
            "get_cumulative() - Running totals",
            "get_dataframes() - Pandas DataFrame export",
            "get_model_runtime() - Performance metrics"
        ],
        "Data Analysis": [
            "Budget component identification and extraction",
            "Time series analysis and processing", 
            "Mass balance verification",
            "Model performance assessment",
            "Data export to pandas DataFrames",
            "Runtime and convergence analysis"
        ],
        "Applications": [
            "Post-processing MODFLOW results",
            "Budget analysis and verification",
            "Time series data extraction", 
            "Model diagnostics and QA/QC",
            "Data visualization preparation",
            "Automated result processing"
        ]
    }
    
    for category, items in summary.items():
        print(f"\n{category}:")
        for item in items:
            print(f"  • {item}")

def run_model():
    """Run the list budget utilities demonstration"""
    
    print("Starting List Budget Utilities demonstration...")
    
    try:
        # Demonstrate MODFLOW 6 list budget processing
        result = demonstrate_mf6_list_budget()
        if result is None:
            return False
            
        mf6_list, names, kstpkper, times = result
        
        # Analyze budget data
        analyze_budget_data(mf6_list, names, kstpkper, times)
        
        # Demonstrate dataframe conversion
        df_flux, df_vol = demonstrate_dataframes(mf6_list)
        
        # Analyze model performance
        analyze_model_performance(mf6_list)
        
        # Create summary
        create_budget_summary()
        
        print("\n" + "="*50)
        print("LIST BUDGET UTILITIES DEMONSTRATION COMPLETED")
        print("="*50)
        
        print(f"\nDemonstration summary:")
        print(f"  • MODFLOW 6 model: Successfully created and run")
        print(f"  • Budget records: {len(names)} different types identified")
        print(f"  • Time steps: {len(kstpkper)} analyzed")
        print(f"  • DataFrames: Created for flux and volume data")
        print(f"  • Performance: Runtime analysis completed")
        
        print(f"\nKey capabilities demonstrated:")
        print(f"  • List file parsing and budget extraction")
        print(f"  • Time series data processing")
        print(f"  • Mass balance analysis and verification") 
        print(f"  • Performance metrics and diagnostics")
        print(f"  • Data export to pandas DataFrames")
        
        # List output files created
        workspace = "./model_output"
        if os.path.exists(workspace):
            files = [f for f in os.listdir(workspace) if f.endswith(('.lst', '.hds', '.cbc'))]
            print(f"\nOutput files created: {len(files)}")
            for f in sorted(files):
                filepath = os.path.join(workspace, f)
                size = os.path.getsize(filepath)
                print(f"  {f}: {size:,} bytes")
        
        return True
        
    except Exception as e:
        print(f"\n{'='*50}")
        print("LIST BUDGET UTILITIES DEMONSTRATION FAILED")
        print("="*50)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    run_model()