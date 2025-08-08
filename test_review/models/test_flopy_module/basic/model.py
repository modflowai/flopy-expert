#!/usr/bin/env python3
"""
Unstructured MFUSG Model with Gridgen
Based on test_gridgen.py - demonstrates creating an unstructured grid with refinement
"""
import numpy as np
import flopy
from flopy.utils.gridgen import Gridgen
from shapely.geometry import Polygon
import os

# Create workspace
ws = './model_output'
if not os.path.exists(ws):
    os.makedirs(ws)

print('=== Building Unstructured MFUSG Model ===')
print('Phase 1: Create initial structured grid for Gridgen')

# Create dummy structured model for gridgen
name = 'dummy'
nlay = 3
nrow = 10
ncol = 10
delr = delc = 1.0
top = 1
bot = 0
dz = (top - bot) / nlay
botm = [top - k * dz for k in range(1, nlay + 1)]

# Temporary model for gridgen
m_temp = flopy.modflow.Modflow(modelname=name, model_ws=ws, exe_name='/home/danilopezmella/flopy_expert/bin/mf2005')
dis = flopy.modflow.ModflowDis(
    m_temp,
    nlay=nlay,
    nrow=nrow,
    ncol=ncol,
    delr=delr,
    delc=delc,
    top=top,
    botm=botm,
)

print('Phase 2: Build refined grid with Gridgen')
# Create and build the gridgen model with a refined area in the middle
g = Gridgen(m_temp.modelgrid, model_ws=ws, exe_name='/home/danilopezmella/flopy_expert/bin/gridgen')
polys = [Polygon([(4, 4), (6, 4), (6, 6), (4, 6)])]
g.add_refinement_features(polys, 'polygon', 3, layers=[0])
g.build()

# Set up boundary conditions for refined grid
chdspd = []
for x, y, head in [(0, 10, 1.0), (10, 0, 0.0)]:
    ra = g.intersect([(x, y)], 'point', 0)
    if len(ra['nodenumber']) > 0:
        ic = ra['nodenumber'][0]
        chdspd.append([ic, head, head])

# Get grid properties for DISU package
gridprops = g.get_gridprops_disu5()

print('Phase 3: Create MFUSG model with unstructured discretization')
# Create the MFUSG model
name = 'usg_model'
mf = flopy.mfusg.MfUsg(
    modelname=name,
    model_ws=ws,
    exe_name='/home/danilopezmella/flopy_expert/bin/mfusg',
    structured=False,
)

# Phase 1: Unstructured discretization
disu = flopy.mfusg.MfUsgDisU(mf, **gridprops)

# Phase 2: Basic package (initial conditions)
bas = flopy.modflow.ModflowBas(mf)

# Phase 3: Layer property flow
lpf = flopy.mfusg.MfUsgLpf(mf, hk=10.0, vka=10.0)

# Phase 4: Boundary conditions - CHD at corners
if len(chdspd) > 0:
    chd = flopy.modflow.ModflowChd(mf, stress_period_data=chdspd)
    print(f'Added {len(chdspd)} CHD boundary conditions')

# Phase 5: SMS solver package
sms = flopy.mfusg.MfUsgSms(mf, options='simple', hclose=1e-6, hiclose=1e-6)

# Phase 6: Output control
oc = flopy.modflow.ModflowOc(mf, stress_period_data={(0, 0): ['save head']})

print('\nPhase 7: Model Verification')
print(f'Model name: {mf.name}')
print(f'Model type: MODFLOW-USG (unstructured)')
print(f'Number of nodes: {disu.nodes}')
print(f'Number of layers: {disu.nlay}')
print(f'Total connections: {disu.njag}')
print(f'Has refinement: Yes (in center of domain)')

# Write input files
print('\nWriting input files...')
mf.write_input()
# Run the model
success, buff = mf.run_model(silent=True)
if success:
    print("  ✓ Model ran successfully")
    # Check for output files
    if os.path.exists(os.path.join(model_output_path, f"{modelname}.hds")):
        print("  ✓ Head file created")
else:
    print("  ⚠ Model failed to run")

if __name__ == "__main__":
    # Run the model
    pass  # Model execution added
