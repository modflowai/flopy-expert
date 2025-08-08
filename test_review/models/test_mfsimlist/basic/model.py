#!/usr/bin/env python3

"""
MODFLOW 6 Simulation Listing File Parser

This model demonstrates FloPy's capabilities for parsing and analyzing
MODFLOW 6 simulation listing files (mfsim.lst), extracting runtime
statistics, iterations, memory usage, and convergence information.

Based on test_mfsimlist.py from the FloPy autotest suite.
"""

import numpy as np
import flopy
from pathlib import Path
import json

def create_example_model(workspace):
    """
    Create a simple MODFLOW 6 model that will generate a listing file.
    """
    sim_name = "simlist_demo"
    
    # Create simulation with memory print option
    sim = flopy.mf6.MFSimulation(
        sim_name=sim_name,
        exe_name="mf6",
        version="mf6",
        sim_ws=str(workspace),
        memory_print_option="summary"  # Print memory usage summary
    )
    
    # Time discretization - multiple stress periods for iteration testing
    tdis = flopy.mf6.ModflowTdis(
        sim,
        nper=3,
        perioddata=[
            (1.0, 1, 1.0),  # Period 1: 1 day, 1 time step
            (10.0, 5, 1.2),  # Period 2: 10 days, 5 time steps with multiplier
            (30.0, 10, 1.0)  # Period 3: 30 days, 10 time steps
        ]
    )
    
    # Iterative model solution with detailed output
    ims = flopy.mf6.ModflowIms(
        sim,
        print_option="ALL",  # Print all solver information
        complexity="MODERATE",
        outer_maximum=100,
        outer_dvclose=1e-6,
        inner_maximum=50,
        inner_dvclose=1e-8,
        linear_acceleration="BICGSTAB",
        relaxation_factor=0.97,
        backtracking_number=20,
        backtracking_tolerance=1.1,
        backtracking_reduction_factor=0.2
    )
    
    # Groundwater flow model
    gwf = flopy.mf6.ModflowGwf(
        sim,
        modelname="flow_model",
        save_flows=True,
        print_input=True,
        print_flows=True
    )
    
    # Discretization - larger grid for more iterations
    nlay, nrow, ncol = 2, 20, 25
    dis = flopy.mf6.ModflowGwfdis(
        gwf,
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        delr=100.0,
        delc=100.0,
        top=100.0,
        botm=[50.0, 0.0]
    )
    
    # Initial conditions - variable to create iterations
    strt = np.ones((nlay, nrow, ncol)) * 60.0
    strt[0, :5, :] = 65.0  # Higher heads on one side
    strt[0, -5:, :] = 55.0  # Lower heads on other side
    ic = flopy.mf6.ModflowGwfic(gwf, strt=strt)
    
    # Node property flow - heterogeneous to increase iterations
    k = np.ones((nlay, nrow, ncol)) * 10.0
    k[0, 5:10, :] = 1.0   # Low K zone
    k[1, 10:15, :] = 50.0  # High K zone
    npf = flopy.mf6.ModflowGwfnpf(
        gwf,
        k=k,
        save_specific_discharge=True
    )
    
    # Storage for transient simulation
    sto = flopy.mf6.ModflowGwfsto(
        gwf,
        steady_state={0: True, 1: False, 2: False},  # First period steady
        transient={1: True, 2: True},
        ss=1e-5,
        sy=0.15
    )
    
    # Constant head boundaries
    chd_data = []
    for i in range(nrow):
        chd_data.append([(0, i, 0), 65.0])      # Left edge
        chd_data.append([(0, i, ncol-1), 55.0])  # Right edge
    
    chd = flopy.mf6.ModflowGwfchd(
        gwf,
        stress_period_data=chd_data
    )
    
    # Recharge - varying by stress period
    rch_data = {
        0: 0.001,  # Period 1
        1: 0.002,  # Period 2
        2: 0.0005  # Period 3
    }
    rch = flopy.mf6.ModflowGwfrcha(gwf, recharge=rch_data)
    
    # Output control
    oc = flopy.mf6.ModflowGwfoc(
        gwf,
        head_filerecord="flow_model.hds",
        budget_filerecord="flow_model.cbc",
        saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")],
        printrecord=[("HEAD", "ALL"), ("BUDGET", "ALL")]
    )
    
    return sim

def demonstrate_listing_parser_features():
    """
    Demonstrate MfSimulationList parser capabilities.
    """
    print("\nMODFLOW 6 Listing File Parser Features:")
    print("=" * 60)
    
    features = {
        "Runtime Extraction": "Get elapsed, formulate, and solution times",
        "Iteration Tracking": "Count outer and total iterations",
        "Memory Usage": "Extract memory allocation statistics",
        "Convergence Check": "Verify normal termination",
        "Solver Performance": "Analyze solver efficiency"
    }
    
    for feature, description in features.items():
        print(f"  • {feature}: {description}")
    
    print("\nExtractable Metrics:")
    metrics = {
        "Elapsed Time": "Total simulation runtime",
        "Formulate Time": "Time to build matrix equations",
        "Solution Time": "Time spent in solver",
        "Outer Iterations": "Newton-Raphson iterations",
        "Inner Iterations": "Linear solver iterations",
        "Memory Usage": "MB allocated by simulation"
    }
    
    for metric, desc in metrics.items():
        print(f"  • {metric}: {desc}")

def parse_listing_file(lst_file):
    """
    Parse the simulation listing file and extract statistics.
    """
    print(f"\nParsing listing file: {lst_file.name}")
    
    try:
        from flopy.mf6.utils import MfSimulationList
        
        # Create parser object
        mfsimlist = MfSimulationList(str(lst_file))
        
        # Check normal termination
        normal_term = mfsimlist.normal_termination
        print(f"  Normal termination: {'✓ Yes' if normal_term else '✗ No'}")
        
        # Extract runtime statistics
        print("\nRuntime Statistics:")
        for timer in ["elapsed", "formulate", "solution"]:
            runtime_sec = mfsimlist.get_runtime(simulation_timer=timer)
            if not np.isnan(runtime_sec):
                print(f"  • {timer.capitalize()} time: {runtime_sec:.4f} seconds")
        
        # Extract iteration counts
        try:
            outer_iter = mfsimlist.get_outer_iterations()
            total_iter = mfsimlist.get_total_iterations()
            print(f"\nIteration Counts:")
            print(f"  • Outer iterations: {outer_iter}")
            print(f"  • Total iterations: {total_iter}")
            if outer_iter > 0:
                print(f"  • Average inner/outer: {total_iter/outer_iter:.1f}")
        except:
            print("  ! Could not extract iteration counts")
        
        # Extract memory usage
        try:
            memory_mb = mfsimlist.get_memory_usage()
            if memory_mb > 0:
                print(f"\nMemory Usage:")
                print(f"  • Total: {memory_mb:.2f} MB")
                memory_kb = mfsimlist.get_memory_usage(units="kilobytes")
                print(f"  • Total: {memory_kb:.0f} KB")
        except:
            print("  ! Could not extract memory usage")
        
        return normal_term
        
    except Exception as e:
        print(f"  ! Error parsing listing file: {e}")
        return False

def run_model(workspace):
    """
    Run MODFLOW 6 model and parse listing file.
    """
    results = {
        "runs": False,
        "converges": False,
        "output_exists": False,
        "error": None,
        "outputs": []
    }
    
    try:
        # Create model
        sim = create_example_model(workspace)
        
        # Write simulation
        sim.write_simulation()
        
        # Check for mf6 executable
        exe_path = Path("/home/danilopezmella/flopy_expert/bin/mf6")
        if exe_path.exists():
            sim.exe_name = str(exe_path)
        
        # Run simulation
        success, buff = sim.run_simulation(silent=False)
        results["runs"] = success
        
        if success:
            # Check for listing file
            lst_file = workspace / "mfsim.lst"
            if lst_file.exists():
                results["outputs"].append(lst_file.name)
                results["output_exists"] = True
                
                # Parse listing file
                converged = parse_listing_file(lst_file)
                results["converges"] = converged
            
            # Check for other output files
            for pattern in ["*.hds", "*.cbc", "*.lst", "*.ims"]:
                for file in workspace.glob(pattern):
                    if file.name not in results["outputs"]:
                        results["outputs"].append(file.name)
        else:
            results["error"] = "Model did not run successfully"
            
    except Exception as e:
        results["error"] = str(e)
    
    return results

def main():
    """
    Main function to demonstrate MfSimulationList parser.
    """
    print("=" * 60)
    print("MODFLOW 6 Simulation Listing File Parser")
    print("=" * 60)
    
    # Create workspace
    workspace = Path("simlist_example")
    workspace.mkdir(exist_ok=True)
    
    # Demonstrate features
    demonstrate_listing_parser_features()
    
    # Run model and parse listing
    print("\nRunning MODFLOW 6 simulation...")
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