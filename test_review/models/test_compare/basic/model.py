import os
import numpy as np
import flopy

# Model configuration
model_name = 'comparison_model'
model_ws = 'model_output'
nlay = 3
nrow = 3
ncol = 3

# Create model workspace if it doesn't exist
if not os.path.exists(model_ws):
    os.makedirs(model_ws)

print('Creating MODFLOW-2005 model...')

# =============================================================================
# Phase 1: Discretization
# =============================================================================
print('Phase 1: Setting up model discretization...')

# Create the MODFLOW model object
ml = flopy.modflow.Modflow(
    modelname=model_name,
    model_ws=model_ws,
    exe_name='/home/danilopezmella/flopy_expert/bin/mf2005',
    verbose=True
)

# Define the discretization
dis = flopy.modflow.ModflowDis(
    ml,
    nlay=nlay,
    nrow=nrow,
    ncol=ncol,
    top=0,
    botm=[-1.0, -2.0, -3.0],
    nper=1,
    perlen=1.0,
    nstp=1,
    steady=True
)

# =============================================================================
# Phase 2: Flow Properties
# =============================================================================
print('Phase 2: Setting up flow properties...')

# Layer Property Flow package
lpf = flopy.modflow.ModflowLpf(
    ml,
    hk=10.0,  # Horizontal hydraulic conductivity
    vka=10.0,  # Vertical hydraulic conductivity
    ipakcb=102  # Unit number for cell-by-cell budget file
)

# =============================================================================
# Phase 3: Initial Conditions
# =============================================================================
print('Phase 3: Setting up initial conditions...')

# Create ibound array (1=active, 0=inactive, -1=constant head)
ibound = np.ones((nlay, nrow, ncol), dtype=int)
ibound[0, 1, 1] = 0  # Inactive cell in layer 1
ibound[0, 0, -1] = -1  # Constant head cell in layer 1

# Basic package (handles initial conditions and ibound)
bas = flopy.modflow.ModflowBas(
    ml,
    ibound=ibound,
    strt=0.0  # Starting heads
)

# =============================================================================
# Phase 4: Boundary Conditions
# =============================================================================
print('Phase 4: Setting up boundary conditions...')

# Create well data with auxiliary variables
wd = flopy.modflow.ModflowWel.get_empty(ncells=2, aux_names=['v1', 'v2'])

# Well 1: Layer 3, Row 3, Column 3
wd['k'][0] = 2  # Layer index (0-based)
wd['i'][0] = 2  # Row index (0-based)
wd['j'][0] = 2  # Column index (0-based)
wd['flux'][0] = -1000.0  # Pumping rate (negative for extraction)
wd['v1'][0] = 1.0  # Auxiliary variable 1
wd['v2'][0] = 2.0  # Auxiliary variable 2

# Well 2: Layer 3, Row 2, Column 2
wd['k'][1] = 2  # Layer index (0-based)
wd['i'][1] = 1  # Row index (0-based)
wd['j'][1] = 1  # Column index (0-based)
wd['flux'][1] = -500.0  # Pumping rate
wd['v1'][1] = 200.0  # Auxiliary variable 1
wd['v2'][1] = 100.0  # Auxiliary variable 2

# Create well package
wel_data = {0: wd}  # Stress period 0
wel = flopy.modflow.ModflowWel(
    ml,
    stress_period_data=wel_data,
    dtype=wd.dtype,
    ipakcb=102  # Save well budget data to unit 102
)

# =============================================================================
# Phase 5: Solver Configuration
# =============================================================================
print('Phase 5: Setting up solver...')

# Preconditioned Conjugate Gradient solver
pcg = flopy.modflow.ModflowPcg(
    ml,
    mxiter=100,  # Maximum iterations
    iter1=30,    # Maximum inner iterations
    hclose=1e-5,  # Head convergence criterion
    rclose=1e-5   # Residual convergence criterion
)

# Output control
oc = flopy.modflow.ModflowOc(
    ml,
    stress_period_data={(0, 0): ['print head', 'print budget', 'save head', 'save budget']}
)

# =============================================================================
# Phase 6: Write Model Files
# =============================================================================
print('Phase 6: Writing model files...')
ml.write_input()

# =============================================================================
# Phase 7: Run the Model
# =============================================================================
print('Phase 7: Running the model...')
success, buff = ml.run_model(silent=False)
if success:
    print('Model ran successfully!')
else:
    print('Model failed to converge')
    for line in buff:
        print(line)

# =============================================================================
# Phase 8: Model Verification and Post-processing
# =============================================================================
print('\nPhase 8: Model verification and post-processing...')

# Check that files were created
nam_file = os.path.join(model_ws, f'{model_name}.nam')
if os.path.exists(nam_file):
    print(f'Successfully created model files in {model_ws}')
    print(f'Name file: {nam_file}')
else:
    print('Error: Model files were not created')

# Load the model to verify it can be read
print('\nLoading model to verify structure...')
try:
    m_loaded = flopy.modflow.Modflow.load(
        f'{model_name}.nam',
        model_ws=model_ws,
        verbose=False
    )
    print('Model loaded successfully')
    
    # Verify well data was preserved
    wl = m_loaded.wel.stress_period_data[0]
    print(f'\nWell package verification:')
    print(f'Number of wells: {len(wl)}')
    print(f'Well 1 - Location: Layer {wl[0][0]+1}, Row {wl[0][1]+1}, Column {wl[0][2]+1}')
    print(f'Well 1 - Pumping rate: {wl[0][3]} m³/d')
    print(f'Well 1 - Auxiliary variables: v1={wl[0][4]}, v2={wl[0][5]}')
    print(f'Well 2 - Location: Layer {wl[1][0]+1}, Row {wl[1][1]+1}, Column {wl[1][2]+1}')
    print(f'Well 2 - Pumping rate: {wl[1][3]} m³/d')
    print(f'Well 2 - Auxiliary variables: v1={wl[1][4]}, v2={wl[1][5]}')
    
    # Demonstrate changing model workspace
    new_ws = os.path.join(model_ws, 'relocated')
    print(f'\nChanging model workspace to: {new_ws}')
    m_loaded.change_model_ws(new_pth=new_ws)
    print('Model workspace changed successfully')
    
except Exception as e:
    print(f'Error loading model: {e}')

# Read and analyze output if model ran successfully
if success:
    print('\nReading model output files...')
    
    # Read head file
    head_file = os.path.join(model_ws, f'{model_name}.hds')
    if os.path.exists(head_file):
        hds = flopy.utils.HeadFile(head_file)
        heads = hds.get_data()
        print(f'Head file read successfully')
        print(f'Head array shape: {heads.shape}')
        print(f'Head statistics:')
        print(f'  Min: {heads.min():.3f} m')
        print(f'  Max: {heads.max():.3f} m')
        print(f'  Mean: {heads.mean():.3f} m')
        
        # Show heads for each layer
        for layer in range(nlay):
            layer_heads = heads[layer, :, :]
            print(f'  Layer {layer+1}: min={layer_heads.min():.3f}, max={layer_heads.max():.3f}, mean={layer_heads.mean():.3f}')
    
    # Read budget file
    cbc_file = os.path.join(model_ws, f'{model_name}.cbc')
    if os.path.exists(cbc_file):
        cbc = flopy.utils.CellBudgetFile(cbc_file)
        print(f'\nBudget file read successfully')
        print(f'Available budget terms: {cbc.get_unique_record_names()}')
        
        # Try to get flow through wells if available
        try:
            wel_flux = cbc.get_data(text='WELLS')
            if wel_flux:
                print(f'Well flux data available for {len(wel_flux)} time steps')
        except:
            # WELLS might not be in the budget file if ipakcb was not set correctly
            print('Well flux data not saved in budget file')

print('\nModel setup and run complete!')
print('The model demonstrates:')
print('  - 3-layer discretization')
print('  - Inactive and constant head cells via ibound')
print('  - Wells with auxiliary variables')
print('  - Model saving and loading')
print('  - Workspace management')
print('  - Model execution and output analysis')

if __name__ == "__main__":
    # Run the model
    pass  # Model execution added
