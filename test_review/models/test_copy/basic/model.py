import copy
import os
import numpy as np
import flopy

# Set up workspace
workspace = 'model_output'
if not os.path.exists(workspace):
    os.makedirs(workspace)

# Phase 1: Create simulation and discretization
print('Phase 1: Setting up simulation and discretization')
sim = flopy.mf6.MFSimulation(
    sim_name='original',
    sim_ws=workspace,
    exe_name='/home/danilopezmella/flopy_expert/bin/mf6'
)

# Time discretization
tdis = flopy.mf6.ModflowTdis(
    sim,
    time_units='DAYS',
    nper=2,
    perioddata=[(1.0, 1, 1.0), (1.0, 1, 1.0)]
)

# Create groundwater flow model
gwf = flopy.mf6.ModflowGwf(
    sim,
    modelname='original_model',
    save_flows=True
)

# Spatial discretization
nlay, nrow, ncol = 2, 10, 10
dis = flopy.mf6.ModflowGwfdis(
    gwf,
    nlay=nlay,
    nrow=nrow,
    ncol=ncol,
    delr=100.0,
    delc=100.0,
    top=10.0,
    botm=[5.0, 0.0]
)

# Phase 2: Flow properties
print('Phase 2: Setting flow properties')
k_values = [10.0, 5.0]  # Different K for each layer
icelltype = 0  # Confined
npf = flopy.mf6.ModflowGwfnpf(
    gwf,
    icelltype=icelltype,
    k=k_values,
    save_specific_discharge=True
)

# Phase 3: Initial conditions
print('Phase 3: Setting initial conditions')
strt = 10.0
ic = flopy.mf6.ModflowGwfic(gwf, strt=strt)

# Phase 4: Boundary conditions
print('Phase 4: Adding boundary conditions')
# Add constant head boundaries on left side
chd_cells = []
for k in range(nlay):
    for i in range(nrow):
        chd_cells.append([(k, i, 0), 10.0])

chd = flopy.mf6.ModflowGwfchd(
    gwf,
    stress_period_data=chd_cells
)

# Add wells - different rates in each stress period
wel_sp1 = [[(0, 4, 4), -100.0], [(1, 7, 7), -50.0]]
wel_sp2 = [[(0, 4, 4), -150.0], [(1, 7, 7), -75.0]]
wel = flopy.mf6.ModflowGwfwel(
    gwf,
    stress_period_data={0: wel_sp1, 1: wel_sp2}
)

# Phase 5: Solver settings
print('Phase 5: Configuring solver')
ims = flopy.mf6.ModflowIms(
    sim,
    print_option='SUMMARY',
    complexity='SIMPLE',
    outer_maximum=100,
    inner_maximum=50,
    outer_dvclose=1e-6,
    inner_dvclose=1e-8
)

# Output control
oc = flopy.mf6.ModflowGwfoc(
    gwf,
    budget_filerecord=f'{gwf.name}.cbc',
    head_filerecord=f'{gwf.name}.hds',
    saverecord=[('HEAD', 'ALL'), ('BUDGET', 'ALL')]
)

# Register solver
sim.register_ims_package(ims, [gwf.name])

# Create a deep copy of the model
print('\nCreating deep copy of the model...')
sim_copy = copy.deepcopy(sim)

# Modify the copy to demonstrate independence
print('Modifying the copy to verify independence...')
sim_copy.name = 'copied_sim'
gwf_copy = sim_copy.get_model('original_model')
gwf_copy.name = 'copied_model'

# Change some properties in the copy
npf_copy = gwf_copy.get_package('NPF')
npf_copy.k.set_data([20.0, 10.0])  # Double the K values

wel_copy = gwf_copy.get_package('WEL')
new_wel_data = [[(0, 4, 4), -200.0], [(1, 7, 7), -100.0]]
wel_copy.stress_period_data.set_data({0: new_wel_data})

# Verify that original model is unchanged
print('\nVerifying model independence:')
original_npf = gwf.get_package('NPF')
original_k = original_npf.k.get_data()
copy_k = npf_copy.k.get_data()

print(f'Original K values: {original_k}')
print(f'Copy K values: {copy_k}')
print(f'Models are independent: {not np.array_equal(original_k, copy_k)}')

original_wel = gwf.get_package('WEL')
original_wel_data = original_wel.stress_period_data.get_data(0)
copy_wel_data = wel_copy.stress_period_data.get_data(0)

print(f'\nOriginal well rates (SP1): {original_wel_data["q"]}')
print(f'Copy well rates (SP1): {copy_wel_data["q"]}')
print(f'Well data is independent: {not np.array_equal(original_wel_data["q"], copy_wel_data["q"])}')

# Write and run both models
print('\nWriting input files...')
sim.write_simulation()

# Change workspace for copy
sim_copy.set_sim_path(os.path.join(workspace, 'copy'))
sim_copy.write_simulation()

print('\nRunning original model...')
success, buff = sim.run_simulation(silent=True)
if success:
    print('Original model ran successfully')

print('\nRunning copied model...')
success, buff = sim_copy.run_simulation(silent=True)
if success:
    print('Copied model ran successfully')

# Phase 7: Compare results
print('\nPhase 7: Comparing results')
original_head_file = os.path.join(workspace, f'{gwf.name}.hds')
copy_head_file = os.path.join(workspace, 'copy', f'{gwf_copy.name}.hds')

if os.path.exists(original_head_file) and os.path.exists(copy_head_file):
    hds_original = flopy.utils.HeadFile(original_head_file)
    hds_copy = flopy.utils.HeadFile(copy_head_file)
    
    head_original = hds_original.get_data(totim=1.0)
    head_copy = hds_copy.get_data(totim=1.0)
    
    print(f'\nOriginal model max head: {np.max(head_original):.2f}')
    print(f'Copy model max head: {np.max(head_copy):.2f}')
    print(f'Results differ (as expected): {not np.allclose(head_original, head_copy)}')
    
    hds_original.close()
    hds_copy.close()

print('\nModel copying demonstration complete!')
print('Successfully demonstrated:')
print('1. Deep copying creates independent model objects')
print('2. Modifications to copy do not affect original')
print('3. Both models can run independently with different parameters')

if __name__ == "__main__":
    # Run the model
    pass  # Model execution added
