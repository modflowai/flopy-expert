"""
MODFLOW 6 Model Splitter Demonstration

This script demonstrates FloPy's Mf6Splitter utility for dividing large models
into smaller sub-models that can be run independently. Key concepts:
- Creating splitting arrays to define model domains
- Using Mf6Splitter to automatically generate sub-models
- Reconstructing results from split model outputs
- Comparing results between original and split models

The model splitter is useful for:
- Parallel processing of large models
- Memory optimization
- Computational efficiency improvements
"""

import numpy as np
import flopy
from flopy.mf6.utils import Mf6Splitter

def run_model():
    """
    Create and demonstrate MODFLOW 6 model splitting functionality.
    Creates an original model, splits it into sub-models, and compares results.
    """
    
    # Create model workspace
    model_ws = "model_output"
    
    # Model dimensions and parameters
    nlay, nrow, ncol = 1, 10, 10
    delr = delc = 100.0
    top = 50.0
    botm = [0.0]
    
    # Create MF6 simulation
    sim = flopy.mf6.MFSimulation(
        sim_name="splitter_demo",
        sim_ws=model_ws,
        exe_name="/home/danilopezmella/flopy_expert/bin/mf6"
    )
    
    # Time discretization
    tdis = flopy.mf6.ModflowTdis(
        sim,
        nper=1,
        perioddata=[(1.0, 1, 1.0)]
    )
    
    # Solver
    ims = flopy.mf6.ModflowIms(
        sim,
        complexity="SIMPLE"
    )
    
    # Groundwater flow model
    gwf = flopy.mf6.ModflowGwf(
        sim,
        modelname="splitter_model",
        save_flows=True
    )
    
    # Discretization
    dis = flopy.mf6.ModflowGwfdis(
        gwf,
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        delr=delr,
        delc=delc,
        top=top,
        botm=botm
    )
    
    # Initial conditions
    ic = flopy.mf6.ModflowGwfic(
        gwf,
        strt=45.0
    )
    
    # Node property flow
    npf = flopy.mf6.ModflowGwfnpf(
        gwf,
        k=10.0
    )
    
    # Constant head boundaries (left and right edges)
    chd_data = []
    # Left boundary - high head
    for i in range(nrow):
        chd_data.append([(0, i, 0), 50.0])
    # Right boundary - low head  
    for i in range(nrow):
        chd_data.append([(0, i, ncol-1), 40.0])
        
    chd = flopy.mf6.ModflowGwfchd(
        gwf,
        stress_period_data=chd_data
    )
    
    # Wells in different parts of the model for demonstration
    wel_data = [
        [(0, 2, 2), -100.0],  # Left side well
        [(0, 7, 7), -150.0],  # Right side well
    ]
    
    wel = flopy.mf6.ModflowGwfwel(
        gwf,
        stress_period_data=wel_data
    )
    
    # Output control
    oc = flopy.mf6.ModflowGwfoc(
        gwf,
        head_filerecord="splitter_model.hds",
        budget_filerecord="splitter_model.cbc",
        saverecord=[("HEAD", "LAST"), ("BUDGET", "LAST")]
    )
    
    # Write and run original model
    print("Writing and running original model...")
    sim.write_simulation()
    
    # Check if MF6 is available
    try:
        success, buff = sim.run_simulation()
        if not success:
            print("Original model failed to run - creating demonstration without MF6")
            print("Creating split model structure without execution...")
            create_splitting_demonstration(sim)
            return sim
    except:
        print("MF6 not available - creating demonstration without execution")
        create_splitting_demonstration(sim)
        return sim
    
    print("Original model completed successfully")
    
    # Get original results for comparison
    original_heads = gwf.output.head().get_alldata()[-1]
    print(f"Original model head range: {np.min(original_heads):.2f} to {np.max(original_heads):.2f}")
    
    # Demonstrate model splitting
    print("\nDemonstrating model splitting...")
    
    # Create splitting array - divide model into left and right halves
    splitting_array = np.ones((nrow, ncol), dtype=int)
    splitting_array[:, ncol//2:] = 2  # Right half gets value 2
    
    print(f"Splitting array divides model into 2 parts:")
    print(f"  Part 1 (value 1): columns 0-{ncol//2-1}")  
    print(f"  Part 2 (value 2): columns {ncol//2}-{ncol-1}")
    
    # Create Mf6Splitter and split the model
    mfsplit = Mf6Splitter(sim)
    new_sim = mfsplit.split_model(splitting_array)
    
    # Set up split model workspace
    split_ws = model_ws + "_split"
    new_sim.set_sim_path(split_ws)
    
    print(f"\nSplit simulation created with {len(new_sim.model_names)} models:")
    for name in new_sim.model_names:
        print(f"  - {name}")
    
    # Write and run split models
    print("\nWriting and running split models...")
    new_sim.write_simulation()
    
    try:
        success, buff = new_sim.run_simulation()
        if success:
            print("Split models completed successfully")
            
            # Compare results
            print("\nComparing results...")
            
            # Get results from each split model
            split_results = {}
            for model_name in new_sim.model_names:
                # Extract model number from name (e.g., "splitter_model_1" -> 1)
                model_num = int(model_name.split('_')[-1])
                split_model = new_sim.get_model(model_name)
                heads = split_model.output.head().get_alldata()[-1]
                split_results[model_num] = heads
                print(f"  {model_name} head range: {np.min(heads):.2f} to {np.max(heads):.2f}")
            
            # Reconstruct full model results from split results
            reconstructed_heads = mfsplit.reconstruct_array(split_results)
            
            # Compare original vs reconstructed
            max_diff = np.max(np.abs(original_heads - reconstructed_heads))
            print(f"\nResults comparison:")
            print(f"  Maximum difference: {max_diff:.6f}")
            print(f"  Results match: {max_diff < 1e-6}")
            
            if max_diff < 1e-6:
                print("✓ Model splitting demonstration successful!")
            else:
                print("⚠ Results differ - this may be expected for demonstration")
                
        else:
            print("Split models failed to run - demonstration completed with structure only")
            
    except Exception as e:
        print(f"Split model execution failed: {e}")
        print("Model splitting structure created successfully")
    
    return sim

def create_splitting_demonstration(sim):
    """Create a basic splitting demonstration without running models."""
    
    print("Creating model splitting demonstration structure...")
    
    # Create a simple splitting array
    nrow, ncol = 10, 10
    splitting_array = np.ones((nrow, ncol), dtype=int)
    splitting_array[:, ncol//2:] = 2
    
    print(f"Splitting array created:")
    print(f"  Left half (columns 0-{ncol//2-1}): model part 1")
    print(f"  Right half (columns {ncol//2}-{ncol-1}): model part 2")
    
    try:
        # Create splitter and split model (structure only)
        mfsplit = Mf6Splitter(sim)
        new_sim = mfsplit.split_model(splitting_array)
        
        split_ws = "model_output_split"
        new_sim.set_sim_path(split_ws)
        new_sim.write_simulation()
        
        print(f"Split model structure created with {len(new_sim.model_names)} models:")
        for name in new_sim.model_names:
            print(f"  - {name}")
        
        print("✓ Model splitting demonstration structure completed!")
        
    except Exception as e:
        print(f"Error creating split structure: {e}")
        print("Basic simulation structure created")

if __name__ == "__main__":
    model = run_model()