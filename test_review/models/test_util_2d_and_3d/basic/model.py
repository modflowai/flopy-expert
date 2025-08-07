"""
FloPy 2D and 3D Utilities Demonstration

This script demonstrates FloPy's core array handling utilities for managing
2D and 3D data arrays in MODFLOW models. Key concepts demonstrated:
- Util2d: 2D array handling with external file support
- Util3d: 3D array handling with layer-specific operations
- Transient2d: Time-varying 2D arrays across stress periods
- Transient3d: Time-varying 3D arrays with temporal flexibility
- MfList: List-based data structures for boundary conditions
- Array formatting and file I/O operations

These utilities are the foundation of FloPy's data management system and
handle everything from hydraulic conductivity fields to boundary condition
arrays with support for internal, external, and constant value specifications.
"""

import numpy as np
import os
import flopy
from flopy.utils import Util2d, Util3d, Transient2d, Transient3d, MfList
from flopy.modflow import Modflow, ModflowDis, ModflowBas, ModflowLpf, ModflowWel

def run_model():
    """
    Create comprehensive demonstration of FloPy's 2D and 3D array utilities.
    Shows practical usage patterns for data management in MODFLOW models.
    """
    
    print("=== FloPy 2D and 3D Utilities Demonstration ===\n")
    
    # Create model workspace
    model_ws = "model_output"
    
    # 1. Util2d - 2D Array Management
    print("1. Util2d - 2D Array Handling")
    print("-" * 40)
    
    # Create basic MODFLOW model for context
    ml = flopy.modflow.Modflow("array_demo", model_ws=model_ws)
    dis = flopy.modflow.ModflowDis(ml, nlay=3, nrow=15, ncol=20, nper=4)
    
    # Create 2D array with constant value
    u2d_constant = Util2d(ml, (ml.nrow, ml.ncol), np.float32, 25.0, "hydraulic_conductivity")
    print(f"  Constant 2D array: {u2d_constant.array.shape}, value = {u2d_constant.array[0,0]}")
    
    # Create 2D array with spatial variation
    hk_data = np.ones((ml.nrow, ml.ncol)) * 10.0  # Base conductivity
    # Add high-K zone in center
    hk_data[5:10, 8:12] = 50.0  # High conductivity zone
    # Add low-K barrier
    hk_data[:, 10] = 1.0  # Vertical barrier
    
    u2d_variable = Util2d(ml, hk_data.shape, np.float32, hk_data, "variable_hk")
    print(f"  Variable 2D array: {u2d_variable.array.shape}")
    print(f"    Value range: {u2d_variable.array.min():.1f} - {u2d_variable.array.max():.1f}")
    
    # Demonstrate array operations
    u2d_scaled = u2d_variable * 2.0  # Scale array
    print(f"  Scaled array: max value = {u2d_scaled.array.max():.1f}")
    
    # 2. Util3d - 3D Array Management  
    print(f"\n2. Util3d - 3D Array Handling")
    print("-" * 40)
    
    # Create 3D hydraulic conductivity array
    hk_values = np.array([20.0, 10.0, 5.0])[:, np.newaxis, np.newaxis]
    hk_3d = np.ones((ml.nlay, ml.nrow, ml.ncol)) * hk_values
    
    # Add spatial heterogeneity to each layer
    for lay in range(ml.nlay):
        # Random log-normal distribution for realistic K field
        np.random.seed(42 + lay)  # Reproducible results
        log_k = np.random.normal(0, 0.5, (ml.nrow, ml.ncol))
        hk_3d[lay] = hk_3d[lay] * np.exp(log_k)
        
        # Add preferential flow paths
        if lay == 0:  # Top layer - river channel
            hk_3d[lay, 7, :] *= 5.0  # High-K channel
        elif lay == 1:  # Middle layer - fracture zone
            hk_3d[lay, :, 15] *= 3.0  # Vertical fracture
    
    u3d_hk = Util3d(ml, hk_3d.shape, np.float32, hk_3d, "layered_hk")
    
    print(f"  3D array shape: {u3d_hk.array.shape}")
    for lay in range(ml.nlay):
        layer_data = u3d_hk.array[lay]
        print(f"    Layer {lay}: K range = {layer_data.min():.1f} - {layer_data.max():.1f} m/d")
    
    # Demonstrate layer-specific operations
    multipliers = [1.5, 1.0, 0.8]  # Different scaling per layer
    u3d_scaled = u3d_hk * multipliers
    print(f"  Layer-specific scaling applied")
    
    # Set constant multiplier across all layers
    u3d_hk.cnstnt = 2.0  # Double all values
    print(f"  Constant multiplier (cnstnt=2.0) applied")
    
    # 3. Transient2d - Time-Varying 2D Arrays
    print(f"\n3. Transient2d - Time-Varying 2D Arrays")
    print("-" * 40)
    
    # Create transient recharge array
    t2d_rch = Transient2d(ml, (ml.nrow, ml.ncol), np.float32, 0.001, "recharge")
    
    print(f"  Transient 2D array: {t2d_rch.array.shape}")
    print(f"    (nper, nlay, nrow, ncol) = {t2d_rch.array.shape}")
    
    # Set different recharge rates for different periods
    t2d_rch[0] = 0.0005  # Dry season
    t2d_rch[1] = 0.003   # Wet season  
    t2d_rch[2] = 0.002   # Moderate season
    t2d_rch[3] = 0.0008  # Late season
    
    print("  Seasonal recharge rates:")
    for per in range(ml.nper):
        rch_value = t2d_rch[per].array[0, 0]  # Sample value
        print(f"    Period {per}: {rch_value:.4f} m/d")
    
    # Create spatial variation within time periods
    rch_spatial = np.ones((ml.nrow, ml.ncol)) * 0.002
    rch_spatial[:5, :] = 0.004   # Higher recharge in north
    rch_spatial[-5:, :] = 0.001  # Lower recharge in south
    t2d_rch[1] = rch_spatial     # Apply to wet season
    
    print(f"    Spatial variation in period 1: {rch_spatial.min():.3f} - {rch_spatial.max():.3f} m/d")
    
    # 4. Transient3d - Time-Varying 3D Arrays
    print(f"\n4. Transient3d - Time-Varying 3D Arrays")
    print("-" * 40)
    
    # Create transient 3D storage array
    storage_values = np.array([1e-4, 1e-5, 1e-6])[:, np.newaxis, np.newaxis]
    base_storage = np.ones((ml.nlay, ml.nrow, ml.ncol)) * storage_values
    
    # Different storage for different periods (seasonal effects)
    t3d_storage = {
        0: base_storage * 0.8,    # Dry season - lower storage
        1: base_storage * 1.5,    # Wet season - higher storage  
        2: base_storage,          # Normal storage
        3: base_storage * 1.2     # Elevated storage
    }
    
    t3d_ss = Transient3d(ml, base_storage.shape, np.float32, t3d_storage, "specific_storage")
    
    print(f"  Transient 3D array: {t3d_ss.array.shape}")
    print("  Storage coefficients by period and layer:")
    
    for per in range(ml.nper):
        print(f"    Period {per}:")
        for lay in range(ml.nlay):
            ss_value = t3d_ss[per].array[lay, 0, 0]  # Sample value
            print(f"      Layer {lay}: {ss_value:.2e} 1/m")
    
    # 5. MfList - Boundary Condition Management
    print(f"\n5. MfList - Boundary Condition Data Structures")
    print("-" * 40)
    
    # Create well data using MfList structure
    wel_data = {
        0: [[0, 7, 10, -1500.0], [1, 8, 12, -800.0]],  # Period 0: 2 wells
        1: [[0, 7, 10, -2000.0], [1, 8, 12, -1200.0], [2, 5, 15, -500.0]],  # Period 1: 3 wells
        2: [[0, 7, 10, -1000.0]]  # Period 2: 1 well
        # Period 3: use previous data (default behavior)
    }
    
    wel = flopy.modflow.ModflowWel(ml, stress_period_data=wel_data)
    
    print("  Well stress period data:")
    for per, data in wel_data.items():
        total_rate = sum(row[3] for row in data)
        print(f"    Period {per}: {len(data)} wells, total rate = {total_rate:.0f} m³/d")
    
    # Demonstrate MfList array access
    wel_array = wel.stress_period_data.masked_4D_arrays
    print(f"  MfList 4D array keys: {list(wel_array.keys())}")
    flux_array = wel_array['flux']
    print(f"    Flux array shape: {flux_array.shape}")
    max_pumping = abs(np.nanmax(flux_array))
    print(f"    Max pumping rate: {max_pumping:.0f} m³/d")
    
    # 6. File I/O and External Arrays
    print(f"\n6. File I/O and External Array Support")
    print("-" * 40)
    
    # Write arrays to external files
    hk_file = os.path.join(model_ws, "hydraulic_conductivity.txt")
    rch_file = os.path.join(model_ws, "recharge_rates.dat")
    
    # Save 2D array as text
    u2d_variable.write_txt(u2d_variable.array.shape, hk_file, u2d_variable.array)
    print(f"  2D array saved to: {os.path.basename(hk_file)}")
    
    # Save as binary file
    hk_bin = os.path.join(model_ws, "hk_layer0.bin")
    u2d_variable.write_bin(u2d_variable.array.shape, hk_bin, u2d_variable.array, bintype="head")
    print(f"  2D array saved as binary: {os.path.basename(hk_bin)}")
    
    # Read back from file
    hk_loaded = u2d_variable.load_txt(u2d_variable.array.shape, hk_file, np.float32, "(FREE)")
    print(f"  Array loaded from file - shape: {hk_loaded.shape}")
    print(f"  Data integrity check: {np.array_equal(u2d_variable.array, hk_loaded)}")
    
    # 7. Array Formatting and Control
    print(f"\n7. Array Formatting and Control Records")
    print("-" * 40)
    
    # Demonstrate different array formats
    u2d_demo = Util2d(ml, (5, 5), np.float32, np.arange(25).reshape(5, 5), "demo_array")
    
    # Internal format
    cr_internal = u2d_demo.get_internal_cr()
    print(f"  Internal format control record: {cr_internal.strip()}")
    
    # Constant format
    u2d_constant = Util2d(ml, (5, 5), np.float32, 42.0, "constant_array")
    u2d_constant.how = "constant"
    cr_constant = u2d_constant.get_file_entry()
    print(f"  Constant format entry: {cr_constant.strip()}")
    
    # External file format
    u2d_demo.how = "external"
    cr_external = u2d_demo.get_file_entry() 
    print(f"  External format entry: {cr_external.strip()}")
    
    # 8. Model Integration and Best Practices
    print(f"\n8. Model Integration and Best Practices")
    print("-" * 40)
    
    # Create complete model with all utilities
    bas = flopy.modflow.ModflowBas(ml, ibound=1, strt=50.0)
    lpf = flopy.modflow.ModflowLpf(
        ml, 
        hk=u3d_hk,           # 3D hydraulic conductivity
        vka=u3d_hk * 0.1,    # Vertical anisotropy  
        ss=base_storage,     # Use base storage array (not transient for LPF)
        sy=0.2               # Specific yield
    )
    
    # Add transient recharge
    rch = flopy.modflow.ModflowRch(ml, rech=t2d_rch)
    
    print("  Complete model created with:")
    print(f"    - 3D hydraulic conductivity field ({ml.nlay} layers)")
    print(f"    - Transient specific storage (4 periods)")
    print(f"    - Transient recharge rates (seasonal variation)")
    print(f"    - Well boundary conditions ({sum(len(data) for data in wel_data.values())} total wells)")
    
    # Write model files
    try:
        ml.write_input()
        print(f"\n✓ Model files written successfully")
        
        # Count generated files
        files = os.listdir(model_ws)
        model_files = [f for f in files if f.endswith(('.nam', '.dis', '.bas', '.lpf', '.wel', '.rch'))]
        print(f"  Generated {len(model_files)} model files")
        
    except Exception as e:
        print(f"  ⚠ Model writing error: {str(e)}")
    
    # 9. Advanced Array Operations
    print(f"\n9. Advanced Array Operations and Utilities")
    print("-" * 40)
    
    # Demonstrate array masking and conditional operations
    mask = hk_data > 20.0  # High conductivity zones
    print(f"  High-K zone coverage: {mask.sum()} cells ({100*mask.sum()/mask.size:.1f}% of domain)")
    
    # Statistical analysis
    print("  Hydraulic conductivity statistics:")
    print(f"    Mean: {hk_data.mean():.1f} m/d")
    print(f"    Std:  {hk_data.std():.1f} m/d") 
    print(f"    Geometric mean: {np.exp(np.log(hk_data).mean()):.1f} m/d")
    
    # Layer-specific analysis for 3D arrays
    print("  Layer-wise K statistics:")
    for lay in range(ml.nlay):
        layer_k = u3d_hk.array[lay]
        print(f"    Layer {lay}: mean = {layer_k.mean():.1f} m/d, std = {layer_k.std():.1f} m/d")
    
    print(f"\n✓ FloPy 2D and 3D Utilities Demonstration Completed!")
    print(f"  - Demonstrated Util2d for 2D array management")
    print(f"  - Showed Util3d for 3D array operations")
    print(f"  - Illustrated Transient2d and Transient3d for time-varying data")
    print(f"  - Explained MfList for boundary condition management")
    print(f"  - Covered file I/O and external array support")
    print(f"  - Showed array formatting and control records")
    print(f"  - Demonstrated integration in complete MODFLOW models")
    
    return ml

if __name__ == "__main__":
    model = run_model()