import os
import sys
import numpy as np
from flopy.modflow import Modflow, ModflowDis, ModflowGage, ModflowOc, ModflowBas, ModflowLpf, ModflowPcg

# Add parent directory to path for config
sys.path.append('/home/danilopezmella/flopy_expert/test_review')
from mf2005_config import get_mf2005_exe

# Create model workspace
model_ws = './model_output'
if not os.path.exists(model_ws):
    os.makedirs(model_ws)

# Phase 1: Model setup and discretization
print('Phase 1: Setting up model and discretization...')
mf = Modflow(modelname='gage_model', model_ws=model_ws, exe_name=get_mf2005_exe())

# Define grid dimensions
nlay, nrow, ncol = 1, 10, 10
delr = delc = 100.0  # 100 m spacing
top = 10.0
botm = [0.0]

# Create discretization package
dis = ModflowDis(mf, nlay=nlay, nrow=nrow, ncol=ncol,
                 delr=delr, delc=delc, top=top, botm=botm,
                 nper=10, perlen=100.0, nstp=10, steady=False)

# Phase 2: Flow properties
print('Phase 2: Setting flow properties...')
# Basic package with initial heads and active cells
ibound = np.ones((nlay, nrow, ncol), dtype=int)
ibound[0, 0, :] = -1  # Constant head boundary on one side
ibound[0, -1, :] = -1  # Constant head boundary on other side

strt = np.ones((nlay, nrow, ncol), dtype=float) * 5.0
strt[0, 0, :] = 10.0  # Higher head on one side
strt[0, -1, :] = 2.0  # Lower head on other side

bas = ModflowBas(mf, ibound=ibound, strt=strt)

# Layer property flow package
lpf = ModflowLpf(mf, hk=10.0, vka=10.0, sy=0.1, ss=1e-5, laytyp=1)

# Phase 3: Initial conditions handled by BAS package strt array
print('Phase 3: Initial conditions set in BAS package')

# Phase 4: Boundary conditions set through ibound in BAS
print('Phase 4: Boundary conditions defined through ibound')

# Phase 5: Solver configuration
print('Phase 5: Configuring solver...')
pcg = ModflowPcg(mf, hclose=1e-3, rclose=1e-3, mxiter=300, iter1=50)

# Phase 6: Observations - GAGE package setup
print('Phase 6: Setting up GAGE observations...')
# Define output control for specific stress periods
spd = {
    (0, 0): ['print head'],
    (2, 0): ['print head'],
    (4, 0): ['print head', 'save head'],
    (6, 0): ['print head'],
    (9, 0): ['print head', 'save head', 'save budget']
}
oc = ModflowOc(mf, stress_period_data=spd)

# GAGE package - monitor two observation points
# Format: [gage_num, gage_unit, layer] for head observations
# Negative gage_num indicates head observation
# gage_unit is the unit number for output file (must be negative for separate file)
gages = [
    [-1, -26, 1],  # Gage 1: monitor head at layer 1, output to unit 26
    [-2, -28, 1]   # Gage 2: monitor head at layer 1, output to unit 28 (changed from 27 to avoid conflict with PCG)
]

# Specify output file names for each gage
files = ['gage1_heads.out', 'gage2_heads.out']

# Create GAGE package
gage = ModflowGage(mf, numgage=2, gage_data=gages, files=files)

print(f'  Added {len(gages)} observation gages')
print(f'  Gage 1 will output to: {files[0]}')
print(f'  Gage 2 will output to: {files[1]}')

# Write input files
print('\nWriting model input files...')
mf.write_input()
# Run the model
success, buff = mf.run_model(silent=True)
if success:
    print("  ✓ Model ran successfully")
    # Check for output files
    if os.path.exists(os.path.join(model_ws, "gage_model.hds")):
        print("  ✓ Head file created")
else:
    print("  ⚠ Model failed to run")