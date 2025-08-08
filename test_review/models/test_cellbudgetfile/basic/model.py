import os
import numpy as np
import flopy
from flopy.utils.binaryfile import CellBudgetFile
import sys
sys.path.append('../../../')  # Add test_review directory to path
try:
    from mf6_config import get_mf6_exe
    MF6_EXE = get_mf6_exe()
except (ImportError, FileNotFoundError):
    MF6_EXE = 'mf6'  # fallback

# Create a simple MODFLOW 6 model that will generate budget files
name = 'budget_example'
ws = './model_output'
sim_ws = ws  # Use model_output directly

if not os.path.exists(sim_ws):
    os.makedirs(sim_ws)

# Phase 1: Discretization
print('Phase 1: Setting up model discretization')
nlay, nrow, ncol = 3, 10, 10
delr = delc = 100.0
top = 100.0
botm = [80.0, 60.0, 40.0]

# Create simulation
sim = flopy.mf6.MFSimulation(
    sim_name=name,
    sim_ws=sim_ws,
    exe_name=MF6_EXE
)

# Create temporal discretization
perlen = [1.0, 100.0]
nper = len(perlen)
tdis = flopy.mf6.ModflowTdis(
    sim,
    nper=nper,
    perioddata=[(p, 1, 1.0) for p in perlen]
)

# Create groundwater flow model
gwf = flopy.mf6.ModflowGwf(
    sim,
    modelname=name,
    save_flows=True,
    newtonoptions='NEWTON'
)

# Create iterative model solution
ims = flopy.mf6.ModflowIms(
    sim,
    linear_acceleration='BICGSTAB',  # Use BICGSTAB instead of CG
    outer_dvclose=1.0e-5,
    inner_dvclose=1.0e-6
)
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

# Phase 2: Flow Properties
print('Phase 2: Setting flow properties')
icelltype = 1  # Convertible layers
k = [10.0, 5.0, 1.0]  # Hydraulic conductivity for each layer

npf = flopy.mf6.ModflowGwfnpf(
    gwf,
    save_flows=True,
    icelltype=icelltype,
    k=k
)

# Storage
sto = flopy.mf6.ModflowGwfsto(
    gwf,
    save_flows=True,
    iconvert=icelltype,
    ss=1e-5,
    sy=0.2
)

# Phase 3: Initial Conditions
print('Phase 3: Setting initial conditions')
strt = 95.0
ic = flopy.mf6.ModflowGwfic(gwf, strt=strt)

# Phase 4: Boundary Conditions
print('Phase 4: Adding boundary conditions')
# Add constant head boundaries
chd_spd = []
for k in range(nlay):
    for i in range(nrow):
        # Left boundary
        chd_spd.append([(k, i, 0), 95.0])
        # Right boundary  
        chd_spd.append([(k, i, ncol-1), 90.0])

chd = flopy.mf6.ModflowGwfchd(
    gwf,
    stress_period_data=chd_spd,
    save_flows=True
)

# Add wells
wel_spd = [
    [(1, 4, 4), -100.0],  # Layer 2, row 5, col 5
    [(2, 7, 7), -50.0],   # Layer 3, row 8, col 8
]
wel = flopy.mf6.ModflowGwfwel(
    gwf,
    stress_period_data=wel_spd,
    save_flows=True
)

# Phase 5: Solver Configuration
print('Phase 5: Configuring output')
# Output control
budget_file = f'{name}.cbc'
head_file = f'{name}.hds'
oc = flopy.mf6.ModflowGwfoc(
    gwf,
    budget_filerecord=budget_file,
    head_filerecord=head_file,
    saverecord=[('HEAD', 'ALL'), ('BUDGET', 'ALL')]
)

# Write and run the model
print('\nWriting and running model...')
sim.write_simulation()
print(f'Using MF6 executable: {MF6_EXE}')
success, buff = sim.run_simulation(silent=False)

if not success:
    print('Model failed to run')
    print(buff)
else:
    print('Model ran successfully')
    
    # Phase 7: Post-processing - Read and analyze budget file
    print('\nPhase 7: Reading and analyzing budget file')
    
    budget_path = os.path.join(sim_ws, budget_file)
    
    if os.path.exists(budget_path):
        # Open and read the budget file
        with CellBudgetFile(budget_path) as cbc:
            # Display budget file properties
            print(f'\nBudget File Properties:')
            print(f'  Dimensions: {cbc.nlay} layers, {cbc.nrow} rows, {cbc.ncol} columns')
            print(f'  Number of stress periods: {cbc.nper}')
            print(f'  Total file size: {cbc.totalbytes:,} bytes')
            print(f'  Number of records: {len(cbc.recordarray)}')
            
            # Display available budget terms
            print(f'\nAvailable budget terms:')
            unique_texts = list(set(cbc.textlist))
            for text in unique_texts:
                print(f'  - {text.decode().strip()}')
            
            # Display time steps
            print(f'\nTime steps (kstp, kper):')
            for kstp, kper in cbc.kstpkper[:5]:  # Show first 5
                print(f'  Step {kstp}, Period {kper}')
            if len(cbc.kstpkper) > 5:
                print(f'  ... and {len(cbc.kstpkper) - 5} more')
            
            # Get data for a specific budget term
            print(f'\nReading FLOW-JA-FACE data for last time step...')
            try:
                flow_ja_face = cbc.get_data(text='FLOW-JA-FACE')[-1]
                if isinstance(flow_ja_face, list):
                    print(f'  Number of flow connections: {len(flow_ja_face[0])}')
                    # Show first few connections
                    for i, (node1, node2, q) in enumerate(flow_ja_face[0][:5]):
                        print(f'    Connection {i+1}: Node {node1} -> Node {node2}, Flow = {q:.4f}')
                else:
                    print(f'  Flow array shape: {flow_ja_face.shape}')
            except:
                print('  FLOW-JA-FACE data not available')
            
            # Get data for CHD package
            print(f'\nReading CHD package flows...')
            try:
                chd_flows = cbc.get_data(text='CHD')[-1]
                if isinstance(chd_flows, list):
                    total_chd_flow = sum([q for _, _, q in chd_flows[0]])
                    print(f'  Total CHD flow: {total_chd_flow:.4f}')
                else:
                    print(f'  CHD flow array shape: {chd_flows.shape}')
                    print(f'  Total CHD flow: {np.sum(chd_flows):.4f}')
            except:
                print('  CHD data not available')
            
            # Get data for WEL package
            print(f'\nReading WEL package flows...')
            try:
                wel_flows = cbc.get_data(text='WEL')[-1]
                if isinstance(wel_flows, list):
                    total_wel_flow = sum([q for _, _, q in wel_flows[0]])
                    print(f'  Total WEL flow: {total_wel_flow:.4f}')
                else:
                    print(f'  WEL flow array shape: {wel_flows.shape}')
                    print(f'  Total WEL flow: {np.sum(wel_flows):.4f}')
            except:
                print('  WEL data not available')
            
            # Display headers dataframe if available
            print(f'\nBudget file headers summary:')
            if hasattr(cbc, 'headers'):
                print(f'  Number of header records: {len(cbc.headers)}')
                print(f'  Header columns: {list(cbc.headers.columns)}')
            
            # Check if compact or classic format
            print(f'\nFile format detection:')
            if any(i > 0 for i in cbc.imethlist):
                print('  Format: COMPACT BUDGET')
            else:
                print('  Format: CLASSIC')
    else:
        print(f'Budget file not found: {budget_path}')

print('\nExample complete!')

if __name__ == "__main__":
    # Run the model
    pass  # Model execution added
