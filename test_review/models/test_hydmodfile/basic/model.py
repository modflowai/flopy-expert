import numpy as np
import flopy
import os

# Create workspace
workspace = './model_output'
if not os.path.exists(workspace):
    os.makedirs(workspace)

# Phase 1: Model Setup and Discretization
modelname = 'hydmod_model'
mf = flopy.modflow.Modflow(modelname, model_ws=workspace, exe_name='/home/danilopezmella/flopy_expert/bin/mf2005')

# Grid dimensions
nlay, nrow, ncol = 3, 10, 10
delr = delc = 100.0  # 100 m cell size
top = 50.0
botm = np.array([30.0, 20.0, 0.0])

# Create DIS package
dis = flopy.modflow.ModflowDis(
    mf,
    nlay=nlay,
    nrow=nrow,
    ncol=ncol,
    delr=delr,
    delc=delc,
    top=top,
    botm=botm,
    nper=10,
    perlen=1.0,
    nstp=1,
    steady=False
)

# Phase 2: Flow Properties
# Layer properties
hk = 10.0  # Horizontal hydraulic conductivity
vka = 0.1  # Vertical anisotropy
sy = 0.15  # Specific yield
ss = 1e-5  # Specific storage

lpf = flopy.modflow.ModflowLpf(
    mf,
    hk=hk,
    vka=vka,
    sy=sy,
    ss=ss,
    laytyp=1,  # Convertible layers
    hdry=-999.0
)

# Phase 3: Initial Conditions
# Set initial heads
ibound = np.ones((nlay, nrow, ncol), dtype=int)
strt = 45.0 * np.ones((nlay, nrow, ncol))

bas = flopy.modflow.ModflowBas(mf, ibound=ibound, strt=strt)

# Phase 4: Boundary Conditions
# Add constant head boundaries on left side
chd_data = []
for k in range(nlay):
    for i in range(nrow):
        chd_data.append([k, i, 0, 45.0, 45.0])  # Layer, row, col, shead, ehead

chd = flopy.modflow.ModflowChd(mf, stress_period_data=chd_data)

# Add pumping well
wel_data = {0: [[1, 5, 5, -500.0]]}  # Layer 2, center of model, pumping 500 m³/day
wel = flopy.modflow.ModflowWel(mf, stress_period_data=wel_data)

# Phase 5: Solver
pcg = flopy.modflow.ModflowPcg(mf, hclose=1e-5, rclose=1e-5)

# Phase 6: Observations - HYDMOD Package
# Define observation locations
# Format: [pckg, arr, intyp, klay, xl, yl, hydlbl]
# pckg: Package name (BAS for basic, STR for stream, etc.)
# arr: Array type (HD for head, DD for drawdown)
# intyp: Interpolation type (I for interpolated, C for cell)
# klay: Layer number (1-based)
# xl, yl: X and Y coordinates
# hydlbl: Label for the observation

obsdata = [
    ['BAS', 'HD', 'I', 1, 250.0, 750.0, 'OBS_1'],  # Observation in layer 1
    ['BAS', 'HD', 'I', 2, 550.0, 550.0, 'WELL_OBS'],  # Near pumping well
    ['BAS', 'DD', 'I', 2, 550.0, 550.0, 'WELL_DD'],  # Drawdown at well
    ['BAS', 'HD', 'C', 1, 450.0, 450.0, 'CELL_HD1'],  # Cell value
    ['BAS', 'HD', 'I', 3, 350.0, 650.0, 'OBS_L3'],  # Layer 3 observation
]

# Create HYDMOD package
hyd = flopy.modflow.ModflowHyd(
    mf,
    nhyd=len(obsdata),
    ihydun=50,  # Unit number for binary output
    hydnoh=-999.0,  # No-flow value
    obsdata=obsdata
)

# Output control
oc = flopy.modflow.ModflowOc(mf, stress_period_data={(0, 0): ['save head', 'save budget']})

# Write model files
mf.write_input()

# Run the model
print('Running model...')
success, buff = mf.run_model(silent=False)

if success:
    print('Model ran successfully!')
    
    # Phase 7: Post-processing
    # Read HYDMOD output
    hydmod_file = os.path.join(workspace, f'{modelname}.hyd.bin')
    
    if os.path.exists(hydmod_file):
        from flopy.utils import HydmodObs
        
        # Load HYDMOD observations
        hydobs = HydmodObs(hydmod_file)
        
        # Get observation information
        print(f'\nNumber of observations: {hydobs.get_nobs()}')
        print(f'Number of time steps: {hydobs.get_ntimes()}')
        print(f'Observation labels: {hydobs.get_obsnames()}')
        
        # Get times
        times = hydobs.get_times()
        print(f'\nSimulation times: {times}')
        
        # Extract data for specific observation (using actual label name)
        actual_labels = hydobs.get_obsnames()
        well_label = [l for l in actual_labels if 'WELL_OBS' in l]
        if well_label:
            well_data = hydobs.get_data(obsname=well_label[0])
            print(f'\nHead at pumping well over time:')
            for t, head in zip(times, well_data[well_label[0]]):
                print(f'  Time {t:5.1f}: Head = {head:8.3f} m')
        
        # Extract drawdown data
        dd_label = [l for l in actual_labels if 'WELL_DD' in l]
        if dd_label:
            dd_data = hydobs.get_data(obsname=dd_label[0])
            print(f'\nDrawdown at pumping well over time:')
            for t, dd in zip(times, dd_data[dd_label[0]]):
                print(f'  Time {t:5.1f}: Drawdown = {dd:8.3f} m')
        
        # Get all data at final time
        final_data = hydobs.get_data(idx=-1)
        print(f'\nFinal observation values:')
        for label in hydobs.get_obsnames():
            try:
                if label in final_data:
                    value = final_data[label]
                    if hasattr(value, '__len__') and len(value) > 0:
                        print(f'  {label}: {value[0]:.3f}')
                    else:
                        print(f'  {label}: {value:.3f}')
            except:
                pass
    else:
        print('HYDMOD output file not found. Check model execution.')
else:
    print('Model did not converge.')