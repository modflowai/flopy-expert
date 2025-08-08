"""
Lake Connections with FloPy - MODFLOW 6

This example demonstrates how to create and connect lakes in MODFLOW 6 using FloPy's 
get_lak_connections utility function. It sets up an embedded lake system with 
proper connection data between lake cells and surrounding groundwater cells.

Key FloPy components demonstrated:
- MFSimulation, ModflowTdis, ModflowIms - Simulation framework
- ModflowGwf, ModflowGwfdis, ModflowGwfic - Flow model setup
- ModflowGwfnpf - Node property flow package 
- ModflowGwfchd - Constant head boundaries
- ModflowGwfrcha, ModflowGwfevta - Recharge and evapotranspiration
- ModflowGwflak - Lake package with connection data
- ModflowGwfoc - Output control
- get_lak_connections - Utility for generating lake connection data

The model creates a 5-layer, 17x17 grid system with an embedded lake that spans
multiple layers, demonstrating how lakes interact with groundwater through
horizontal and vertical connections.
"""

import os
import sys
import numpy as np

# Add the test_review directory to the path to import config
sys.path.append('/home/danilopezmella/flopy_expert/test_review')
from mf6_config import get_mf6_exe

from flopy.mf6 import (
    MFSimulation,
    ModflowGwf,
    ModflowGwfchd,
    ModflowGwfdis,
    ModflowGwfevta,
    ModflowGwfic,
    ModflowGwflak,
    ModflowGwfnpf,
    ModflowGwfoc,
    ModflowGwfrcha,
    ModflowIms,
    ModflowTdis,
)
from flopy.mf6.utils import get_lak_connections

def build_model():
    """Build the lake connections model"""
    
    # Model parameters
    name = "lakeconnect"
    workspace = "./model_output"
    
    # Create workspace directory
    if not os.path.exists(workspace):
        os.makedirs(workspace)
    
    # Grid dimensions and parameters
    nper = 1
    nlay, nrow, ncol = 5, 17, 17
    shape3d = (nlay, nrow, ncol)
    
    # Variable cell dimensions
    delr = (
        250.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 500.0, 500.0, 500.0,
        500.0, 500.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 250.0,
    )
    delc = delr
    
    # Layer elevations
    top = 500.0
    botm = (107.0, 97.0, 87.0, 77.0, 67.0)
    
    # Define lake extent - embedded lake spanning multiple layers
    lake_map = np.ones(shape3d, dtype=np.int32) * -1
    lake_map[0, 6:11, 6:11] = 0  # Lake in layer 1
    lake_map[1, 7:10, 7:10] = 0  # Lake in layer 2 (smaller)
    lake_map = np.ma.masked_where(lake_map < 0, lake_map)
    
    # Initial head
    strt = 115.0
    
    # Hydraulic properties
    k11 = 30  # Horizontal hydraulic conductivity
    k33 = (1179.0, 30.0, 30.0, 30.0, 30.0)  # Vertical hydraulic conductivity by layer
    
    # Boundary conditions
    rch_rate = 0.116e-1  # Recharge rate
    evt_rate = 0.141e-1  # Evapotranspiration rate  
    evt_depth = 15.0     # Extinction depth
    evt_surf = np.ones((nrow, ncol)) * top  # Surface elevation
    
    # Constant head boundaries around perimeter
    chd_top_bottom = (
        160.0, 158.85, 157.31, 155.77, 154.23, 152.69, 151.54, 150.77, 150.0,
        149.23, 148.46, 147.31, 145.77, 144.23, 142.69, 141.15, 140.0,
    )
    chd_spd = []
    for k in range(nlay):
        for i in range(nrow):
            if 0 < i < nrow - 1:
                chd_spd.append([k, i, 0, chd_top_bottom[0]])          # Left boundary
                chd_spd.append([k, i, ncol - 1, chd_top_bottom[-1]])  # Right boundary
            else:
                for jdx, v in enumerate(chd_top_bottom):
                    chd_spd.append([k, i, jdx, v])  # Top and bottom boundaries
    chd_spd = {0: chd_spd}
    
    # Create simulation
    sim = MFSimulation(
        sim_name=name,
        exe_name=get_mf6_exe(),
        sim_ws=workspace,
    )
    
    # Create time discretization
    tdis = ModflowTdis(sim, nper=nper)
    
    # Create iterative model solution
    ims = ModflowIms(
        sim,
        print_option="summary",
        linear_acceleration="BICGSTAB",
        outer_maximum=1000,
        inner_maximum=100,
        outer_dvclose=1e-8,
        inner_dvclose=1e-9,
    )
    
    # Create groundwater flow model
    gwf = ModflowGwf(
        sim,
        modelname=name,
        newtonoptions="newton under_relaxation",
        print_input=True,
    )
    
    # Create discretization package
    dis = ModflowGwfdis(
        gwf,
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        delr=delr,
        delc=delc,
        top=top,
        botm=botm,
    )
    
    # Create initial conditions package
    ic = ModflowGwfic(gwf, strt=strt)
    
    # Create node property flow package
    npf = ModflowGwfnpf(
        gwf,
        icelltype=1,
        k=k11,
        k33=k33,
    )
    
    # Create constant head package
    chd = ModflowGwfchd(gwf, stress_period_data=chd_spd)
    
    # Create recharge package
    rch = ModflowGwfrcha(gwf, recharge=rch_rate)
    
    # Create evapotranspiration package
    evt = ModflowGwfevta(
        gwf,
        surface=evt_surf,
        depth=evt_depth,
        rate=evt_rate,
    )
    
    # Generate lake connections using FloPy utility
    idomain, pakdata_dict, connectiondata = get_lak_connections(
        gwf.modelgrid,
        lake_map,
        bedleak=0.1,  # Lakebed leakance
    )
    
    print(f"Generated {pakdata_dict[0]} lake connections")
    print(f"Connection data entries: {len(connectiondata)}")
    
    # Create lake package data
    lak_pak_data = []
    for key, value in pakdata_dict.items():
        lak_pak_data.append([key, 110.0, value])  # Lake number, stage, connections
    
    # Lake stress period data (rainfall and evaporation)
    lak_spd = {
        0: [
            [0, "rainfall", rch_rate],
            [0, "evaporation", 0.0103],
        ]
    }
    
    # Create lake package
    lak = ModflowGwflak(
        gwf,
        print_stage=True,
        print_flows=True,
        nlakes=1,
        packagedata=lak_pak_data,
        connectiondata=connectiondata,
        perioddata=lak_spd,
        pname="LAK-1",
    )
    
    # Update idomain to account for lake cells
    gwf.dis.idomain = idomain
    
    # Create output control package
    # Output control - save heads and budgets
    oc = ModflowGwfoc(
        gwf,
        budget_filerecord=f"{name}.cbc",
        head_filerecord=f"{name}.hds",
        saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")],
        printrecord=[("HEAD", "ALL"), ("BUDGET", "ALL")],
    )
    
    return sim, gwf

def run_model():
    """Run the lake connections model"""
    
    print("Building lake connections model...")
    sim, gwf = build_model()
    
    print("Writing simulation files...")
    sim.write_simulation()
    
    print("Running simulation...")
    success, buff = sim.run_simulation(silent=False)
    
    if success:
        print("\n" + "="*50)
        print("MODEL RUN COMPLETED SUCCESSFULLY")
        print("="*50)
        
        # List output files
        workspace = "./model_output"
        files = [f for f in os.listdir(workspace) if f.endswith(('.hds', '.cbc', '.lst', '.lak'))]
        print(f"\nOutput files created: {len(files)}")
        for f in sorted(files):
            filepath = os.path.join(workspace, f)
            size = os.path.getsize(filepath)
            print(f"  {f}: {size:,} bytes")
        
        # Try to read heads and lake stages
        try:
            print(f"\nModel summary:")
            print(f"  Grid: {gwf.dis.nlay.get_data()} layers, {gwf.dis.nrow.get_data()} rows, {gwf.dis.ncol.get_data()} columns")
            print(f"  Lake cells: Lake spans multiple layers with proper connections")
            print(f"  Boundary conditions: CHD on perimeter, recharge/ET over domain")
            print(f"  Lake processes: Rainfall and evaporation specified")
            
            # Read head file to verify model ran
            head_file = os.path.join(workspace, f"{gwf.name}.hds")
            if os.path.exists(head_file):
                from flopy.utils import HeadFile
                hf = HeadFile(head_file)
                heads = hf.get_data()
                print(f"  Head range: {heads.min():.2f} to {heads.max():.2f}")
                hf.close()
            
            # Read lake output if available
            lak_file = os.path.join(workspace, f"{gwf.name}.lak.bin") 
            if os.path.exists(lak_file):
                print(f"  Lake output: Available in {os.path.basename(lak_file)}")
                
        except Exception as e:
            print(f"Note: Could not read output files: {e}")
            
        return True
        
    else:
        print("\n" + "="*50) 
        print("MODEL RUN FAILED")
        print("="*50)
        print("Error details:")
        for line in buff:
            print(f"  {line.strip()}")
        return False

if __name__ == "__main__":
    run_model()