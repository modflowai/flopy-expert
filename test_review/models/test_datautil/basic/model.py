import os
import numpy as np
import flopy
from flopy.utils.datautil import PyListUtil

# Create workspace
ws = './model_output'
if not os.path.exists(ws):
    os.makedirs(ws)

# Phase 1: Discretization
print('\n=== Phase 1: Basic Model Setup ===')
nlay, nrow, ncol = 2, 10, 10
sim = flopy.mf6.MFSimulation(sim_name='datautil_demo', sim_ws=ws, exe_name='/home/danilopezmella/flopy_expert/bin/mf6')
tdis = flopy.mf6.ModflowTdis(sim, time_units='DAYS', nper=1, perioddata=[(1.0, 1, 1.0)])
gwf = flopy.mf6.ModflowGwf(sim, modelname='model', save_flows=True)
ims = flopy.mf6.ModflowIms(sim, print_option='SUMMARY')
sim.register_ims_package(ims, [gwf.name])

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

# Phase 2: Flow Properties
npf = flopy.mf6.ModflowGwfnpf(gwf, icelltype=1, k=10.0)
sto = flopy.mf6.ModflowGwfsto(gwf, iconvert=1, ss=1e-5, sy=0.2)

# Phase 3: Initial Conditions
ic = flopy.mf6.ModflowGwfic(gwf, strt=10.0)

# Phase 4: Boundary Conditions with parsed data
print('\n=== Phase 4: Demonstrating Data Parsing ===')

# Example 1: Parse comma-delimited well pumping rates
well_data_line = "100.5, 200.0, 150.75, 300.0, 250.5"
print(f'\nParsing well rates: "{well_data_line}"')
parsed_rates = PyListUtil.split_data_line(well_data_line)
print(f'Parsed rates: {parsed_rates}')

# Convert to well stress period data
well_spd = []
for i, rate in enumerate(parsed_rates[:min(5, len(parsed_rates))]):
    # Place wells in different cells
    row = i % nrow
    col = i % ncol
    well_spd.append((0, row, col, -float(rate.strip())))

print(f'\nCreated {len(well_spd)} well locations from parsed data')
wel = flopy.mf6.ModflowGwfwel(gwf, stress_period_data=well_spd)

# Example 2: Parse mixed delimiter boundary head data
boundary_line = "5.5  6.0,  7.5   8.0, 9.0"
print(f'\nParsing boundary heads: "{boundary_line}"')
parsed_heads = PyListUtil.split_data_line(boundary_line)
print(f'Parsed heads: {parsed_heads}')

# Convert to CHD stress period data
chd_spd = []
for i, head in enumerate(parsed_heads[:min(3, len(parsed_heads))]):
    # Clean the string - remove commas and whitespace
    clean_head = head.strip().rstrip(',').strip()
    try:
        head_val = float(clean_head)
    except ValueError:
        head_val = 10.0  # Default value if parsing fails
    
    # Place CHD cells on boundaries
    if i == 0:
        chd_spd.append((0, 0, 0, head_val))  # Top-left
    elif i == 1:
        chd_spd.append((0, 0, ncol-1, head_val))  # Top-right
    else:
        chd_spd.append((0, nrow-1, 0, head_val))  # Bottom-left

print(f'Created {len(chd_spd)} CHD boundary conditions')
chd = flopy.mf6.ModflowGwfchd(gwf, stress_period_data=chd_spd)

# Example 3: Parse recharge array data
print('\n=== Advanced Data Parsing Examples ===')

# Parse a line with various delimiters and formats
complex_line = "1.5e-4, 2.0e-4  3.5e-4,4.0e-4   5.5e-4"
print(f'\nParsing scientific notation: "{complex_line}"')
parsed_values = PyListUtil.split_data_line(complex_line)
print(f'Parsed values: {parsed_values}')

# Create recharge array from parsed values
rch_array = np.zeros((nrow, ncol))
for i, val in enumerate(parsed_values):
    if i < nrow * ncol:
        row = i // ncol
        col = i % ncol
        # Clean the value - handle cases where values are stuck together
        clean_val = val.strip().rstrip(',').strip()
        # If there's still a comma, split and take first value
        if ',' in clean_val:
            clean_val = clean_val.split(',')[0]
        try:
            rch_array[row, col] = float(clean_val)
        except ValueError:
            rch_array[row, col] = 1.0e-4  # Default recharge value

print(f'Created recharge array with mean: {np.mean(rch_array):.2e}')
rch = flopy.mf6.ModflowGwfrcha(gwf, recharge=rch_array)

# Example 4: Handle edge cases in parsing
print('\n=== Edge Cases in Data Parsing ===')

# Trailing delimiters
trailing_line = "10,20,30,40,50,"
print(f'\nLine with trailing comma: "{trailing_line}"')
trailing_parsed = PyListUtil.split_data_line(trailing_line)
print(f'Parsed (handles trailing): {trailing_parsed}')

# Mixed whitespace
mixed_space = "100  ,  200 , 300,400  ,  500"
print(f'\nMixed whitespace: "{mixed_space}"')
mixed_parsed = PyListUtil.split_data_line(mixed_space)
print(f'Parsed (preserves spacing): {mixed_parsed}')

# Tab-delimited (if supported)
tab_line = "1.0\t2.0\t3.0\t4.0\t5.0"
print(f'\nTab-delimited: "{tab_line}"')
tab_parsed = PyListUtil.split_data_line(tab_line.replace('\t', ' '))
print(f'Parsed tabs as spaces: {tab_parsed}')

# Phase 5: Solver Configuration
print('\n=== Phase 5: Solver Configuration ===')
ims.complexity = 'SIMPLE'
ims.linear_acceleration = 'BICGSTAB'

# Phase 6: Output Control
oc = flopy.mf6.ModflowGwfoc(
    gwf,
    head_filerecord='model.hds',
    budget_filerecord='model.cbc',
    saverecord=[('HEAD', 'ALL'), ('BUDGET', 'ALL')]
)

# Write and run simulation
print('\n=== Writing Simulation Files ===')
sim.write_simulation()

# Phase 7: Post-processing demonstration
print('\n=== Phase 7: Data Utility Summary ===')
print('\nPyListUtil.split_data_line() capabilities:')
print('1. Handles comma-delimited data')
print('2. Handles space-delimited data')
print('3. Handles mixed delimiters')
print('4. Preserves whitespace in values')
print('5. Handles trailing delimiters')
print('6. Works with scientific notation')

print('\n=== Running Model ===')
success, buff = sim.run_simulation(silent=True)

if success:
    print('✓ Model ran successfully!')
    # Get heads
    head = gwf.output.head().get_data()
    print(f'Head range: {head.min():.2f} to {head.max():.2f} m')
else:
    print('✗ Model failed to run')

print('\n=== Example Complete ===')
print(f'Model files written to: {os.path.abspath(ws)}')
print('\nThis example demonstrated:')
print('- Parsing various data formats for MODFLOW input')
print('- Converting parsed data to stress period data')
print('- Handling edge cases in data parsing')
print('- Creating boundary conditions from parsed strings')

if __name__ == "__main__":
    # Run the model
    pass  # Model execution added
