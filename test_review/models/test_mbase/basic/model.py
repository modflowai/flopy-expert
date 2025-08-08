"""
FloPy Base Model Utilities - Model Execution and Executable Resolution

This example demonstrates FloPy's core base model utilities for MODFLOW executable
resolution and model execution. These utilities form the foundation of FloPy's
ability to run MODFLOW models across different platforms and configurations.

Key FloPy components demonstrated:
- flopy.mbase.resolve_exe() - Executable path resolution
- flopy.run_model() - Model execution utility
- Path handling for executables and model files
- Model workspace management
- Error handling for missing executables
- Cross-platform executable resolution

The model creates a simple MODFLOW 6 simulation and demonstrates various ways
to resolve and execute MODFLOW using FloPy's base utilities.
"""

import os
import sys
import shutil
from pathlib import Path

# Add the test_review directory to the path to import config
sys.path.append('/home/danilopezmella/flopy_expert/test_review')
from mf6_config import get_mf6_exe

from flopy import run_model
from flopy.mbase import resolve_exe
from flopy.mf6 import (
    MFSimulation,
    ModflowGwf,
    ModflowGwfchd,
    ModflowGwfdis,
    ModflowGwfic,
    ModflowGwfnpf,
    ModflowGwfoc,

# Write and run simulation
print("Writing and running model...")
sim.write_simulation()
success, buff = sim.run_simulation(silent=True)
if success:
    print("  ✓ Model ran successfully")
else:
    print("  ⚠ Model run failed")

    ModflowIms,
    ModflowTdis,
)

def demonstrate_resolve_exe():
    """Demonstrate executable resolution functionality"""
    
    print("="*50)
    print("EXECUTABLE RESOLUTION DEMONSTRATION")
    print("="*50)
    
    print("\n1. Testing resolve_exe() function...")
    
    # Get the configured MODFLOW 6 path
    mf6_path = get_mf6_exe()
    print(f"   Configured MF6 path: {mf6_path}")
    
    # Test resolve_exe with different inputs
    test_cases = [
        ("mf6", "Executable name only"),
        (mf6_path, "Absolute path"),
        ("./mf6", "Relative path (if exists)")
    ]
    
    resolved_paths = {}
    
    for exe_input, description in test_cases:
        print(f"\n   Testing: {description}")
        print(f"   Input: {exe_input}")
        
        try:
            resolved_path = resolve_exe(exe_input)
            resolved_paths[exe_input] = resolved_path
            print(f"   ✓ Resolved to: {resolved_path}")
            
            # Check if file exists and is executable
            if Path(resolved_path).exists():
                print(f"   ✓ File exists: {Path(resolved_path).is_file()}")
                print(f"   ✓ Is executable: {os.access(resolved_path, os.X_OK)}")
            else:
                print(f"   ⚠ File not found at resolved path")
                
        except FileNotFoundError as e:
            print(f"   ✗ FileNotFoundError: {e}")
            resolved_paths[exe_input] = None
        except Exception as e:
            print(f"   ✗ Error: {e}")
            resolved_paths[exe_input] = None
    
    # Test with forgive option
    print(f"\n2. Testing resolve_exe() with forgive option...")
    try:
        # Test with non-existent executable
        result = resolve_exe("nonexistent_exe", forgive=True)
        print(f"   resolve_exe('nonexistent_exe', forgive=True): {result}")
        
        # Test without forgive (should raise exception)
        try:
            result = resolve_exe("nonexistent_exe", forgive=False)
            print(f"   resolve_exe('nonexistent_exe', forgive=False): {result}")
        except FileNotFoundError:
            print(f"   ✓ FileNotFoundError raised as expected when forgive=False")
            
    except Exception as e:
        print(f"   Error testing forgive option: {e}")
    
    return resolved_paths

def create_demo_model():
    """Create a simple MODFLOW 6 model for execution testing"""
    
    print("\n" + "="*50)
    print("CREATING DEMO MODEL")
    print("="*50)
    
    # Model parameters
    name = "mbase_demo"
    workspace = "./model_output"
    
    print(f"\n3. Creating model '{name}' in workspace '{workspace}'...")
    
    # Create workspace
    if os.path.exists(workspace):
        shutil.rmtree(workspace)
    os.makedirs(workspace)
    
    # Grid parameters
    nlay, nrow, ncol = 1, 5, 5
    delr = delc = 100.0
    top = 100.0
    botm = [0.0]
    
    # Create simulation
    sim = MFSimulation(
        sim_name=name,
        exe_name=get_mf6_exe(),
        sim_ws=workspace,
    )
    
    # Time discretization
    tdis = ModflowTdis(sim, nper=1, perioddata=[(1.0, 1, 1.0)])
    
    # Iterative model solution  
    ims = ModflowIms(sim, print_option="summary")
    
    # Groundwater flow model
    gwf = ModflowGwf(sim, modelname=name, save_flows=True)
    
    # Discretization
    dis = ModflowGwfdis(
        gwf,
        nlay=nlay, nrow=nrow, ncol=ncol,
        delr=delr, delc=delc,
        top=top, botm=botm
    )
    
    # Initial conditions
    ic = ModflowGwfic(gwf, strt=50.0)
    
    # Node property flow
    npf = ModflowGwfnpf(gwf, k=10.0)
    
    # Constant head boundaries
    chd_spd = [
        [0, 0, 0, 80.0],  # Left boundary
        [0, 0, ncol-1, 60.0],  # Right boundary  
    ]
    chd = ModflowGwfchd(gwf, stress_period_data={0: chd_spd})
    
    # Output control
    oc = ModflowGwfoc(
        gwf,
        head_filerecord=f"{name}.hds",
        budget_filerecord=f"{name}.cbc",
        saverecord=[("HEAD", "LAST"), ("BUDGET", "LAST")],
        printrecord=[("HEAD", "LAST"), ("BUDGET", "LAST")]
    )
    
    print(f"   ✓ Model created successfully")
    print(f"   ✓ Grid: {nlay}L × {nrow}R × {ncol}C")
    print(f"   ✓ Workspace: {workspace}")
    
    return sim, workspace

def demonstrate_run_model(resolved_paths, workspace):
    """Demonstrate run_model() functionality"""
    
    print("\n" + "="*50)
    print("MODEL EXECUTION DEMONSTRATION")
    print("="*50)
    
    print("\n4. Testing run_model() function...")
    
    # Test different ways to specify executables
    exe_tests = []
    
    # Add successful resolved paths
    for input_path, resolved_path in resolved_paths.items():
        if resolved_path is not None:
            exe_tests.append((resolved_path, f"Resolved path from {input_path}"))
    
    # Add direct path
    exe_tests.append((get_mf6_exe(), "Direct configured path"))
    
    results = []
    
    for i, (exe_path, description) in enumerate(exe_tests[:2]):  # Test first 2 to avoid redundancy
        print(f"\n   Test {i+1}: {description}")
        print(f"   Executable: {exe_path}")
        
        try:
            # Run the model - use positional arguments to avoid keyword issues
            success, buff = run_model(
                exe_path,           # exe_name
                "mfsim.nam",        # namefile  
                workspace,          # model_ws
                True,               # silent
                False,              # pause
                True                # report
            )
            
            results.append((description, success, len(buff) if buff else 0))
            
            if success:
                print(f"   ✓ Model run successful")
                print(f"   ✓ Output lines: {len(buff) if buff else 0}")
                
                # Check for output files
                output_files = []
                for ext in ['.lst', '.hds', '.cbc']:
                    files = list(Path(workspace).glob(f"*{ext}"))
                    output_files.extend(files)
                
                print(f"   ✓ Output files: {len(output_files)}")
                for f in output_files[:3]:  # Show first 3
                    size = f.stat().st_size
                    print(f"     - {f.name}: {size:,} bytes")
                    
            else:
                print(f"   ✗ Model run failed")
                if buff:
                    print(f"   Error output lines: {len(buff)}")
                    # Show first few error lines
                    for line in buff[:3]:
                        print(f"     {line.strip()}")
                        
        except Exception as e:
            print(f"   ✗ Exception during run: {e}")
            results.append((description, False, 0))
    
    return results

def test_path_handling():
    """Test various path handling scenarios"""
    
    print("\n" + "="*50)
    print("PATH HANDLING TESTS")
    print("="*50)
    
    print("\n5. Testing path handling scenarios...")
    
    # Test relative paths
    print(f"\n   Current working directory: {os.getcwd()}")
    
    # Test pathlib.Path vs string inputs
    mf6_path = get_mf6_exe()
    path_tests = [
        (mf6_path, "String path"),
        (Path(mf6_path), "Path object"),
    ]
    
    for path_input, description in path_tests:
        print(f"\n   Testing: {description}")
        print(f"   Input type: {type(path_input)}")
        print(f"   Input value: {path_input}")
        
        try:
            resolved = resolve_exe(path_input)
            print(f"   ✓ Resolved: {resolved}")
            print(f"   ✓ Type: {type(resolved)}")
        except Exception as e:
            print(f"   ✗ Error: {e}")

def analyze_workspace():
    """Analyze the created workspace and files"""
    
    print("\n" + "="*50)
    print("WORKSPACE ANALYSIS")
    print("="*50)
    
    workspace = "./model_output"
    
    print(f"\n6. Analyzing workspace: {workspace}")
    
    if not os.path.exists(workspace):
        print(f"   ⚠ Workspace not found: {workspace}")
        return
    
    # List all files
    all_files = []
    for root, dirs, files in os.walk(workspace):
        for file in files:
            filepath = os.path.join(root, file)
            size = os.path.getsize(filepath)
            all_files.append((filepath, size))
    
    print(f"   Total files: {len(all_files)}")
    
    # Group by file type
    file_types = {}
    for filepath, size in all_files:
        ext = Path(filepath).suffix.lower()
        if ext not in file_types:
            file_types[ext] = []
        file_types[ext].append((filepath, size))
    
    print(f"   File types found: {len(file_types)}")
    
    for ext, files in file_types.items():
        print(f"     {ext if ext else '(no extension)'}: {len(files)} files")
        total_size = sum(size for _, size in files)
        print(f"       Total size: {total_size:,} bytes")
        
        # Show largest file of each type
        if files:
            largest = max(files, key=lambda x: x[1])
            print(f"       Largest: {os.path.basename(largest[0])} ({largest[1]:,} bytes)")

def run_model():
    """Run the mbase utilities demonstration"""
    
    print("Starting FloPy mbase utilities demonstration...")
    
    try:
        # Demonstrate executable resolution
        resolved_paths = demonstrate_resolve_exe()
        
        # Create demo model
        sim, workspace = create_demo_model()
        
        # Write simulation files
        print(f"\n   Writing simulation files...")
        sim.write_simulation()
        print(f"   ✓ Files written to {workspace}")
        
        # Demonstrate model execution
        results = demonstrate_run_model(resolved_paths, workspace)
        
        # Test path handling
        test_path_handling()
        
        # Analyze workspace
        analyze_workspace()
        
        print("\n" + "="*50)
        print("MBASE UTILITIES DEMONSTRATION COMPLETED")
        print("="*50)
        
        print(f"\nSummary:")
        print(f"  • Executable resolution: {len([p for p in resolved_paths.values() if p is not None])} successful")
        print(f"  • Model execution tests: {len(results)}")
        print(f"  • Successful runs: {sum(1 for _, success, _ in results if success)}")
        
        print(f"\nKey capabilities demonstrated:")
        print(f"  • resolve_exe() for finding MODFLOW executables")
        print(f"  • run_model() for executing MODFLOW simulations")
        print(f"  • Path handling across different input types")
        print(f"  • Error handling for missing executables")
        print(f"  • Workspace and file management")
        print(f"  • Cross-platform executable resolution")
        
        # Check if any runs were successful
        successful_runs = sum(1 for _, success, _ in results if success)
        return successful_runs > 0
        
    except Exception as e:
        print(f"\n{'='*50}")
        print("MBASE UTILITIES DEMONSTRATION FAILED")
        print("="*50)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    run_model()