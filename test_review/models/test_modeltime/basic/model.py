"""
MODFLOW ModelTime Demonstration

This script demonstrates FloPy's ModelTime class capabilities for handling
temporal aspects of groundwater models. Key features demonstrated:
- Time unit parsing and conversion
- DateTime handling and parsing  
- Stress period and timestep calculations
- Time intersection methods
- Both MF2005 and MF6 time handling approaches

ModelTime is essential for:
- Converting between different time representations
- Mapping simulation time to calendar dates
- Handling transient boundary conditions
- Post-processing time series data
"""

import numpy as np
import datetime
import flopy
from flopy.discretization.modeltime import ModelTime

def run_model():
    """
    Create and demonstrate MODFLOW ModelTime capabilities.
    Shows various time handling features in both MF2005 and MF6.
    """
    
    # Create model workspace
    model_ws = "model_output"
    
    print("=== MODFLOW ModelTime Demonstration ===\n")
    
    # 1. Basic ModelTime Creation and Parsing
    print("1. Basic ModelTime Creation and DateTime Parsing")
    print("-" * 50)
    
    # Test different date formats
    date_formats = [
        "2024-01-01",
        "01/01/2024", 
        "2024/01/01",
        datetime.datetime(2024, 1, 1),
    ]
    
    for date_format in date_formats:
        parsed_date = ModelTime.parse_datetime(date_format)
        print(f"  Input: {date_format} -> Parsed: {parsed_date}")
    
    # Test time unit parsing
    print(f"\n  Time unit parsing examples:")
    time_units = ["days", "D", "hours", "h", "years", "y", "seconds", "s"]
    for unit in time_units:
        parsed_unit = ModelTime.parse_timeunits(unit)
        print(f"    '{unit}' -> '{parsed_unit}'")
    
    # 2. Create ModelTime object for transient simulation
    print(f"\n2. Creating ModelTime for Transient Simulation")
    print("-" * 50)
    
    # Define stress periods (monthly simulation for one year)
    nper = 12
    perlen = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]  # Days in each month
    nstp = [5, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]  # Timesteps per period
    start_date = "2024-01-01"
    
    mt = ModelTime(
        perlen=perlen,
        nstp=nstp,
        time_units="days",
        start_datetime=start_date
    )
    
    print(f"  Simulation period: {mt.start_datetime} to {mt.get_datetime(nper-1)}")
    print(f"  Total simulation time: {sum(perlen)} days")
    print(f"  Number of stress periods: {nper}")
    print(f"  Total timesteps: {sum(nstp)}")
    
    # 3. Time calculations and intersections
    print(f"\n3. Time Calculations and Intersections")
    print("-" * 50)
    
    # Get elapsed time for specific stress periods
    test_periods = [0, 3, 6, 11]
    for kper in test_periods:
        elapsed_time = mt.get_elapsed_time(kper)
        end_date = mt.get_datetime(kper)
        print(f"  End of period {kper}: {elapsed_time:.1f} days, {end_date.strftime('%Y-%m-%d')}")
    
    # Test time intersection - find stress period for specific dates
    print(f"\n  Time intersection examples:")
    test_dates = ["2024-02-15", "2024-07-04", "2024-12-25"]
    for test_date in test_dates:
        kper, kstp = mt.intersect(test_date)
        print(f"    Date {test_date}: Period {kper}, Timestep {kstp}")
    
    # 4. MF2005 Model with ModelTime
    print(f"\n4. MF2005 Model with ModelTime")
    print("-" * 50)
    
    # Model dimensions
    nlay, nrow, ncol = 1, 10, 10
    delr = delc = 100.0
    top = 50.0
    botm = [0.0]
    
    # Create MF2005 model
    mf = flopy.modflow.Modflow(
        modelname="modeltime_demo",
        model_ws=model_ws,
        exe_name="/home/danilopezmella/flopy_expert/bin/mf2005"
    )
    
    # Discretization with time information
    dis = flopy.modflow.ModflowDis(
        mf,
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        nper=nper,
        delr=delr,
        delc=delc,
        top=top,
        botm=botm,
        perlen=perlen,
        nstp=nstp,
        steady=[False] * nper,  # All transient
        itmuni=4,  # Time units: 4 = days
        lenuni=2,  # Length units: 2 = meters
        start_datetime=start_date
    )
    
    # Basic package
    ibound = np.ones((nlay, nrow, ncol), dtype=int)
    strt = np.ones((nlay, nrow, ncol)) * 45.0
    
    bas = flopy.modflow.ModflowBas(mf, ibound=ibound, strt=strt)
    
    # Layer property flow
    lpf = flopy.modflow.ModflowLpf(mf, hk=10.0, vka=1.0, ss=1e-5, sy=0.2)
    
    # Time-varying boundary conditions
    # Constant head - seasonal variation
    chd_data = {}
    for kper in range(nper):
        # Seasonal head variation (higher in winter, lower in summer)
        seasonal_factor = 1.0 + 0.1 * np.cos(2 * np.pi * kper / 12)
        heads = []
        # Left boundary
        for i in range(nrow):
            heads.append([0, i, 0, 50.0 * seasonal_factor, 50.0 * seasonal_factor])
        # Right boundary  
        for i in range(nrow):
            heads.append([0, i, ncol-1, 40.0 * seasonal_factor, 40.0 * seasonal_factor])
        chd_data[kper] = heads
    
    chd = flopy.modflow.ModflowChd(mf, stress_period_data=chd_data)
    
    # Time-varying wells - simulate seasonal pumping
    wel_data = {}
    for kper in range(nper):
        # Summer months (May-Sept) have higher pumping
        if 4 <= kper <= 8:  # May through September (0-indexed)
            pumping_rate = -200.0
        else:
            pumping_rate = -50.0  # Lower winter pumping
        
        wel_data[kper] = [[0, 5, 5, pumping_rate]]
    
    wel = flopy.modflow.ModflowWel(mf, stress_period_data=wel_data)
    
    # Output control - save results for each stress period
    spd = {}
    for kper in range(nper):
        spd[(kper, nstp[kper]-1)] = ["save head", "save budget"]
    
    oc = flopy.modflow.ModflowOc(mf, stress_period_data=spd, compact=True)
    
    # Solver
    pcg = flopy.modflow.ModflowPcg(mf, mxiter=50, iter1=30)
    
    print(f"  Created MF2005 model with {nper} stress periods")
    
    # Access ModelTime from the model
    modeltime = mf.modeltime
    print(f"  Model start date: {modeltime.start_datetime}")
    print(f"  Model time units: {modeltime.time_units}")
    print(f"  Total simulation time: {sum(modeltime.perlen)} {modeltime.time_units}")
    
    # 5. MF6 Model with ModelTime
    print(f"\n5. MF6 Model with ModelTime")
    print("-" * 50)
    
    # Create MF6 simulation
    sim = flopy.mf6.MFSimulation(
        sim_name="modeltime_mf6",
        sim_ws=model_ws + "_mf6",
        exe_name="/home/danilopezmella/flopy_expert/bin/mf6"
    )
    
    # Time discretization with start date
    period_data = [(perlen[i], nstp[i], 1.0) for i in range(nper)]
    
    tdis = flopy.mf6.ModflowTdis(
        sim,
        time_units="days",
        start_date_time="2024-01-01T00:00:00",
        nper=nper,
        perioddata=period_data
    )
    
    # Solver
    ims = flopy.mf6.ModflowIms(sim, complexity="SIMPLE")
    
    # Groundwater flow model
    gwf = flopy.mf6.ModflowGwf(sim, modelname="time_demo", save_flows=True)
    
    # Discretization
    dis_mf6 = flopy.mf6.ModflowGwfdis(
        gwf,
        nlay=nlay, nrow=nrow, ncol=ncol,
        delr=delr, delc=delc, top=top, botm=botm
    )
    
    # Initial conditions
    ic = flopy.mf6.ModflowGwfic(gwf, strt=45.0)
    
    # Node property flow
    npf = flopy.mf6.ModflowGwfnpf(gwf, k=10.0)
    
    # Storage
    sto = flopy.mf6.ModflowGwfsto(gwf, ss=1e-5, sy=0.2)
    
    # Output control
    oc_mf6 = flopy.mf6.ModflowGwfoc(
        gwf,
        head_filerecord="time_demo.hds",
        budget_filerecord="time_demo.cbc",
        saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")]
    )
    
    print(f"  Created MF6 simulation with time discretization")
    
    # Access ModelTime from MF6 model
    modeltime_mf6 = gwf.modeltime
    print(f"  MF6 start date: {modeltime_mf6.start_datetime}")
    print(f"  MF6 time units: {modeltime_mf6.time_units}")
    
    # Write models
    print(f"\n6. Writing Model Files")
    print("-" * 50)
    
    print("  Writing MF2005 model...")
    mf.write_input()
    
    print("  Running MF2005 model...")
    success, buff = mf.run_model(silent=True)
    if success:
        print("  ✓ MF2005 model completed successfully")
    else:
        print("  ⚠ MF2005 model failed")
    
    print("  Writing MF6 model...")
    sim.write_simulation()
    
    print("  Running MF6 model...")
    success, buff = sim.run_simulation(silent=True)
    if success:
        print("  ✓ MF6 model completed successfully")
    else:
        print("  ⚠ MF6 model failed")
    
    # 6. Demonstrate ModelTime utilities
    print(f"\n7. ModelTime Utility Demonstrations")
    print("-" * 50)
    
    # Time range calculations
    print(f"  Simulation spans {(modeltime.get_datetime(nper-1) - modeltime.start_datetime).days} days")
    
    # Find specific time periods
    summer_start = modeltime.intersect("2024-06-21")  # Summer solstice
    winter_start = modeltime.intersect("2024-12-21")  # Winter solstice
    
    print(f"  Summer solstice (2024-06-21): Period {summer_start[0]}, Timestep {summer_start[1]}")
    print(f"  Winter solstice (2024-12-21): Period {winter_start[0]}, Timestep {winter_start[1]}")
    
    # Demonstrate stress period boundaries
    print(f"\n  Stress period end dates:")
    for kper in range(min(6, nper)):  # Show first 6 periods
        end_date = modeltime.get_datetime(kper)
        elapsed = modeltime.get_elapsed_time(kper)
        print(f"    Period {kper}: {end_date.strftime('%Y-%m-%d')} ({elapsed:.1f} days)")
    
    print(f"\n✓ ModelTime demonstration completed successfully!")
    print(f"  - Demonstrated date/time parsing")
    print(f"  - Created transient MF2005 and MF6 models")
    print(f"  - Showed time intersection and calculation methods")
    print(f"  - Illustrated seasonal boundary conditions")
    
    return mf, sim

if __name__ == "__main__":
    mf2005_model, mf6_sim = run_model()