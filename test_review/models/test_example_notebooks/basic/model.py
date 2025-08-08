#!/usr/bin/env python
"""
Simple MODFLOW 6 groundwater flow model demonstrating the 7 phases of model development.
This represents the type of model that would be tested in notebook examples.
"""

import os
import numpy as np
import flopy

# Model configuration
name = 'tutorial_model'
ws = './model_output'
sim_name = 'sim'

# Create workspace
if not os.path.exists(ws):
    os.makedirs(ws)

# ==============================================================================
# Phase 1: DISCRETIZATION - Define the grid and time
# ==============================================================================
print('Phase 1: Setting up discretization...')

# Spatial discretization
nlay = 3  # Number of layers
nrow = 10  # Number of rows
ncol = 10  # Number of columns
delr = 100.0  # Column width (m)
delc = 100.0  # Row width (m)
top = 0.0  # Top of model (m)
botm = [-10.0, -20.0, -30.0]  # Bottom elevations for each layer

# Temporal discretization
nper = 3  # Number of stress periods
perlen = [1.0, 100.0, 100.0]  # Length of each stress period (days)
nstp = [1, 10, 10]  # Number of time steps in each period
tsmult = [1.0, 1.0, 1.0]  # Time step multiplier

# ==============================================================================
# Phase 2: PROPERTIES - Define aquifer properties
# ==============================================================================
print('Phase 2: Setting up aquifer properties...')

# Hydraulic conductivity (m/day)
hk = 10.0  # Horizontal hydraulic conductivity
vk = 1.0   # Vertical hydraulic conductivity

# Storage properties
sy = 0.15  # Specific yield (dimensionless)
ss = 1e-5  # Specific storage (1/m)
iconvert = 1  # Flag for convertible layers

# ==============================================================================
# Phase 3: INITIAL CONDITIONS - Set starting heads
# ==============================================================================
print('Phase 3: Setting up initial conditions...')

# Initial heads
strt = -5.0  # Starting head (m)

# ==============================================================================
# Phase 4: BOUNDARY CONDITIONS - Define sources/sinks
# ==============================================================================
print('Phase 4: Setting up boundary conditions...')

# Constant head boundary (left side of model)
chd_rec = []
for k in range(nlay):
    for i in range(nrow):
        # Left boundary (column 0)
        chd_rec.append([(k, i, 0), 0.0])  # Layer, row, col, head

# Well package (pumping well)
wel_rec = [
    # Layer, row, col, pumping rate (negative for extraction)
    [(1, 4, 4), -500.0],  # Pumping well in layer 2, center of model
]

# Recharge package
rech = 0.001  # Recharge rate (m/day)

# ==============================================================================
# Phase 5: SOLVER CONFIGURATION - Set up numerical solver
# ==============================================================================
print('Phase 5: Setting up solver...')

# IMS solver parameters
inner_maximum = 100
outer_maximum = 50
inner_dvclose = 1e-6
outer_dvclose = 1e-6

# ==============================================================================
# CREATE AND BUILD MODEL
# ==============================================================================
print('\nBuilding MODFLOW 6 model...')

# Create simulation
sim = flopy.mf6.MFSimulation(
    sim_name=sim_name,
    version='mf6',
    exe_name='/home/danilopezmella/flopy_expert/bin/mf6',
    sim_ws=ws,
    memory_print_option='all'
)

# Create temporal discretization
tdis = flopy.mf6.ModflowTdis(
    sim,
    time_units='DAYS',
    nper=nper,
    perioddata=[(perlen[i], nstp[i], tsmult[i]) for i in range(nper)]
)

# Create groundwater flow model
gwf = flopy.mf6.ModflowGwf(
    sim,
    modelname=name,
    save_flows=True,
    newtonoptions='NEWTON',
    print_input=True,
    print_flows=True
)

# Create iterative model solution
ims = flopy.mf6.ModflowIms(
    sim,
    print_option='SUMMARY',
    complexity='SIMPLE',
    outer_dvclose=outer_dvclose,
    outer_maximum=outer_maximum,
    under_relaxation='NONE',
    inner_maximum=inner_maximum,
    inner_dvclose=inner_dvclose,
    rcloserecord=0.001,
    linear_acceleration='BICGSTAB',
    scaling_method='NONE',
    reordering_method='NONE',
    relaxation_factor=0.97
)

# Register solver
sim.register_ims_package(ims, [gwf.name])

# Discretization package
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

# Node property flow package
npf = flopy.mf6.ModflowGwfnpf(
    gwf,
    save_specific_discharge=True,
    icelltype=iconvert,
    k=hk,
    k33=vk
)

# Storage package
sto = flopy.mf6.ModflowGwfsto(
    gwf,
    save_flows=True,
    iconvert=iconvert,
    ss=ss,
    sy=sy,
    steady_state={0: True, 1: False, 2: False},
    transient={0: False, 1: True, 2: True}
)

# Initial conditions package
ic = flopy.mf6.ModflowGwfic(gwf, strt=strt)

# Constant head package
chd = flopy.mf6.ModflowGwfchd(
    gwf,
    stress_period_data=chd_rec,
    save_flows=True
)

# Well package
wel = flopy.mf6.ModflowGwfwel(
    gwf,
    stress_period_data=wel_rec,
    save_flows=True
)

# Recharge package
rch = flopy.mf6.ModflowGwfrcha(
    gwf,
    recharge=rech,
    save_flows=True
)

# Output control
oc = flopy.mf6.ModflowGwfoc(
    gwf,
    head_filerecord=f'{name}.hds',
    budget_filerecord=f'{name}.cbc',
    headprintrecord=[('COLUMNS', 10, 'WIDTH', 15, 'DIGITS', 6, 'GENERAL')],
    saverecord=[('HEAD', 'ALL'), ('BUDGET', 'ALL')],
    printrecord=[('HEAD', 'LAST'), ('BUDGET', 'LAST')]
)

# ==============================================================================
# Phase 6: OBSERVATIONS (Optional) - Monitor specific locations
# ==============================================================================
print('Phase 6: Setting up observations...')

# Observation package
obs_data = [
    ('obs1', 'HEAD', (1, 4, 4)),  # Observe head at pumping well location
    ('obs2', 'HEAD', (1, 0, 0)),  # Observe head at corner
]

obs = flopy.mf6.ModflowUtlobs(
    gwf,
    filename=f'{name}.obs',
    print_input=True,
    continuous={'obs.csv': obs_data}
)

# ==============================================================================
# RUN MODEL
# ==============================================================================
print('\nWriting input files...')
sim.write_simulation()

print('Running model...')
success, buff = sim.run_simulation(silent=False)

if success:
    print('\nModel ran successfully!')
else:
    print('\nModel failed to run')
    for line in buff:
        print(line)

# ==============================================================================
# Phase 7: POST-PROCESSING - Analyze results
# ==============================================================================
if success:
    print('\nPhase 7: Post-processing results...')
    
    # Read head results
    head_file = os.path.join(ws, f'{name}.hds')
    hds = flopy.utils.HeadFile(head_file)
    
    # Get heads for last time step
    heads = hds.get_data()
    
    # Print summary statistics
    print(f'\nHead Statistics (final time step):')
    print(f'  Minimum head: {heads.min():.2f} m')
    print(f'  Maximum head: {heads.max():.2f} m')
    print(f'  Mean head: {heads.mean():.2f} m')
    
    # Read budget file
    budget_file = os.path.join(ws, f'{name}.cbc')
    cbc = flopy.utils.CellBudgetFile(budget_file)
    
    # Get budget terms
    budget_terms = cbc.get_unique_record_names()
    print(f'\nAvailable budget terms: {budget_terms}')
    
    # Read observations
    obs_file = os.path.join(ws, 'obs.csv')
    if os.path.exists(obs_file):
        print('\nObservation results saved to obs.csv')
    
    print('\nModel completed successfully!')
    print(f'Results saved in: {ws}')

if __name__ == "__main__":
    # Run the model
    pass  # Model execution added
