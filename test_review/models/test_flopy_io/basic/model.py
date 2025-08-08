import os
import numpy as np
from pathlib import Path
import flopy
from flopy.utils.flopy_io import line_parse, relpath_safe

# Working directory setup
workspace = Path('model_output')
workspace.mkdir(exist_ok=True)

# ============================================
# Phase 7: Post-processing - I/O Utilities
# ============================================

# Demonstrate line_parse functionality
print("\n=== Line Parse Examples ===")
print("Line parsing is used internally by FloPy to read MODFLOW input files")
print("It handles comments and splits lines into tokens\n")

# Example 1: Parse a line with comment (MNW2 format)
line1 = "Well-A  -1                   ; 2a. WELLID,NNODES"
parsed1 = line_parse(line1)
print(f"Input line: {line1}")
print(f"Parsed tokens: {parsed1}")
print(f"Well ID: {parsed1[0]}, Number of nodes: {parsed1[1]}\n")

# Example 2: Parse a line without comment
line2 = "100.0  200.0  50.0"
parsed2 = line_parse(line2)
print(f"Input line: {line2}")
print(f"Parsed tokens: {parsed2}\n")

# Example 3: Parse with multiple spaces and tabs
line3 = "LAYER\t1\t\t10    20    ;comment here"
parsed3 = line_parse(line3)
print(f"Input line with tabs: {line3}")
print(f"Parsed tokens: {parsed3}\n")

# Demonstrate relpath_safe functionality
print("\n=== Safe Relative Path Examples ===")
print("relpath_safe handles cross-platform path issues\n")

# Create some test directories
model_dir = workspace / 'model'
model_dir.mkdir(exist_ok=True)
output_dir = workspace / 'output'
output_dir.mkdir(exist_ok=True)

# Example 1: Get relative path from parent
rel_path1 = relpath_safe(str(model_dir), str(workspace))
print(f"Full path: {model_dir}")
print(f"Relative to parent: {rel_path1}\n")

# Example 2: Get relative path from different directory
rel_path2 = relpath_safe(str(output_dir), str(model_dir))
print(f"Output dir: {output_dir}")
print(f"Relative to model dir: {rel_path2}\n")

# Example 3: Handle Path objects
rel_path3 = relpath_safe(output_dir, workspace)
print(f"Using Path objects:")
print(f"Output dir relative to workspace: {rel_path3}\n")

# Create a simple MODFLOW 6 model to demonstrate practical usage
print("\n=== Practical Example with MODFLOW 6 Model ===")
print("Creating a simple model to show how these utilities are used\n")

name = 'io_demo'
sim = flopy.mf6.MFSimulation(
    sim_name=name,
    sim_ws=str(model_dir),
    exe_name='/home/danilopezmella/flopy_expert/bin/mf6'
)

# Phase 1: Time discretization
tdis = flopy.mf6.ModflowTdis(
    sim,
    time_units='DAYS',
    nper=1,
    perioddata=[(1.0, 1, 1.0)]
)

# Create groundwater flow model
gwf = flopy.mf6.ModflowGwf(sim, modelname=name)

# Phase 1: Spatial discretization
dis = flopy.mf6.ModflowGwfdis(
    gwf,
    nlay=1,
    nrow=10,
    ncol=10,
    delr=100.0,
    delc=100.0,
    top=10.0,
    botm=0.0
)

# Phase 2: Flow properties
npf = flopy.mf6.ModflowGwfnpf(
    gwf,
    save_flows=True,
    icelltype=1,
    k=10.0
)

# Phase 3: Initial conditions
ic = flopy.mf6.ModflowGwfic(gwf, strt=5.0)

# Phase 4: Boundary conditions
chd_spd = [[(0, 0, 0), 5.0], [(0, 9, 9), 4.0]]
chd = flopy.mf6.ModflowGwfchd(gwf, stress_period_data=chd_spd)

# Phase 5: Solver
ims = flopy.mf6.ModflowIms(
    sim,
    print_option='SUMMARY',
    complexity='SIMPLE'
)

# Phase 7: Output control
oc = flopy.mf6.ModflowGwfoc(
    gwf,
    budget_filerecord=f'{name}.cbc',
    head_filerecord=f'{name}.hds',
    saverecord=[('HEAD', 'ALL'), ('BUDGET', 'ALL')]
)

# Write model files
sim.write_simulation()

# Demonstrate how FloPy uses these utilities internally
print(f"Model workspace: {model_dir}")
print(f"Relative path handling is used for file references in name files")

# Show how line_parse would be used to read a package file
name_file = model_dir / f'{name}.nam'
if name_file.exists():
    print(f"\nReading name file to demonstrate line parsing:")
    with open(name_file, 'r') as f:
        for i, line in enumerate(f):
            if i < 5 and line.strip() and not line.startswith('#'):
                parsed = line_parse(line)
                if parsed:
                    print(f"  Line {i+1}: {parsed}")

# Run the model
print("\n=== Running Model ===")
success, buff = sim.run_simulation(silent=True)
if success:
    print("Model ran successfully!")
    # Read heads
    head = gwf.output.head().get_data()
    print(f"Head shape: {head.shape}")
    print(f"Head range: {head.min():.2f} to {head.max():.2f} m")
else:
    print("Model failed to run")

print("\n=== Summary ===")
print("1. line_parse() handles comment removal and tokenization")
print("2. relpath_safe() provides cross-platform path handling")
print("3. These utilities are used internally by FloPy for file I/O")
print("4. Understanding them helps with debugging and custom file operations")

# Cleanup - commented out to preserve output files
# import shutil
# if workspace.exists():
#     shutil.rmtree(workspace)
#     print("\nTemporary files cleaned up.")
print("\nModel files preserved in", workspace)

if __name__ == "__main__":
    # Run the model
    pass  # Model execution added
