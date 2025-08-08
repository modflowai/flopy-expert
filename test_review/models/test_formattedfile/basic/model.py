#!/usr/bin/env python3
"""
Formatted Head File Example

This example demonstrates how to:
1. Create a simple MODFLOW 6 model that writes formatted head output
2. Read and process the formatted head file
3. Extract data by time, stress period, or index
4. Access file metadata and headers
"""

import os
import numpy as np
import flopy
from flopy.utils import FormattedHeadFile

# Model setup
model_name = 'formhead'
model_ws = './model_output'

# Create model workspace
if not os.path.exists(model_ws):
    os.makedirs(model_ws)

# Phase 1: Discretization
print('Phase 1: Setting up model discretization...')
nlay = 1
nrow = 15
ncol = 10
delr = 100.0
delc = 100.0
top = 10.0
botm = 0.0

# Create simulation
sim = flopy.mf6.MFSimulation(
    sim_name=model_name,
    sim_ws=model_ws,
    exe_name='/home/danilopezmella/flopy_expert/bin/mf6'
)

# Create temporal discretization (TDIS)
period_data = [(1.0, 1, 1.0), (86400.0, 50, 1.0)]  # 2 stress periods
tdis = flopy.mf6.ModflowTdis(
    sim,
    nper=2,
    perioddata=period_data
)

# Create groundwater flow model
gwf = flopy.mf6.ModflowGwf(
    sim,
    modelname=model_name,
    save_flows=True
)

# Create discretization package (DIS)
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

# Phase 2: Flow properties (NPF)
print('Phase 2: Setting flow properties...')
hk = 10.0
vk = 1.0
npf = flopy.mf6.ModflowGwfnpf(
    gwf,
    save_specific_discharge=True,
    k=hk,
    k33=vk
)

# Phase 3: Initial conditions (IC)
print('Phase 3: Setting initial conditions...')
strt = 10.0
ic = flopy.mf6.ModflowGwfic(gwf, strt=strt)

# Phase 4: Boundary conditions (CHD)
print('Phase 4: Setting boundary conditions...')
# Add constant heads on left and right boundaries
chd_data = []
for row in range(nrow):
    # Left boundary (column 0)
    chd_data.append([(0, row, 0), 10.0])
    # Right boundary (last column)
    chd_data.append([(0, row, ncol-1), 5.0])

chd = flopy.mf6.ModflowGwfchd(
    gwf,
    stress_period_data=chd_data
)

# Phase 5: Solver configuration (IMS)
print('Phase 5: Configuring solver...')
ims = flopy.mf6.ModflowIms(
    sim,
    print_option='SUMMARY',
    complexity='SIMPLE',
    outer_maximum=100,
    inner_maximum=50,
    outer_dvclose=1e-6,
    inner_dvclose=1e-6
)
sim.register_ims_package(ims, [gwf.name])

# Phase 6: Output control
print('Phase 6: Setting up output control...')
head_file = f'{model_name}.hds'
budget_file = f'{model_name}.cbc'

oc = flopy.mf6.ModflowGwfoc(
    gwf,
    head_filerecord=head_file,
    budget_filerecord=budget_file,
    saverecord=[('HEAD', 'ALL'), ('BUDGET', 'ALL')],
    printrecord=[('HEAD', 'LAST'), ('BUDGET', 'LAST')]
)

# Write and run the model
print('\nWriting and running model...')
sim.write_simulation()
success, buff = sim.run_simulation(silent=True)

if not success:
    print('Model run failed!')
    for line in buff:
        print(line)
else:
    print('Model run successful!')
    
    # Phase 7: Post-processing - Read formatted head file
    print('\nPhase 7: Post-processing formatted head file...')
    
    # Open the head file
    head_path = os.path.join(model_ws, head_file)
    hds = flopy.utils.HeadFile(head_path)
    
    # Get basic information
    print(f'\nHead file information:')
    print(f'  Number of layers: {hds.nlay}')
    print(f'  Number of rows: {hds.nrow}')
    print(f'  Number of columns: {hds.ncol}')
    print(f'  Number of records: {len(hds)}')
    
    # Get available times
    times = hds.get_times()
    print(f'\n  Available times: {times}')
    
    # Get stress period/time step information
    kstpkper = hds.get_kstpkper()
    print(f'  Stress periods/time steps: {kstpkper}')
    
    # Extract head data different ways
    print('\nExtracting head data...')
    
    # Method 1: Get data by time
    if len(times) > 0:
        head_by_time = hds.get_data(totim=times[0])
        print(f'  Heads at time {times[0]}:')
        print(f'    Shape: {head_by_time.shape}')
        print(f'    Min: {np.min(head_by_time):.3f}')
        print(f'    Max: {np.max(head_by_time):.3f}')
        print(f'    Mean: {np.mean(head_by_time):.3f}')
    
    # Method 2: Get data by stress period/time step
    if len(kstpkper) > 0:
        head_by_kstpkper = hds.get_data(kstpkper=kstpkper[0])
        print(f'\n  Heads at kstp/kper {kstpkper[0]}:')
        print(f'    Shape: {head_by_kstpkper.shape}')
        print(f'    Min: {np.min(head_by_kstpkper):.3f}')
        print(f'    Max: {np.max(head_by_kstpkper):.3f}')
    
    # Method 3: Get data by index
    head_by_idx = hds.get_data(idx=0)
    print(f'\n  Heads at index 0:')
    print(f'    Shape: {head_by_idx.shape}')
    
    # Get all heads for time series analysis
    all_heads = hds.get_alldata()
    print(f'\n  All heads shape: {all_heads.shape}')
    print(f'  Dimensions: (ntimes, nlay, nrow, ncol)')
    
    # Calculate head differences between stress periods
    if len(times) > 1:
        head_diff = hds.get_data(totim=times[-1]) - hds.get_data(totim=times[0])
        print(f'\n  Head change from first to last time:')
        print(f'    Max increase: {np.max(head_diff):.3f}')
        print(f'    Max decrease: {np.min(head_diff):.3f}')
    
    # Close the file
    hds.close()
    
    print('\nFormatted head file processing complete!')

# Clean up
print('\nExample complete!')

if __name__ == "__main__":
    # Run the model
    pass  # Model execution added
