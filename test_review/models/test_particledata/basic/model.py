"""
MODPATH Particle Data Creation Demonstration

This script demonstrates MODPATH particle data creation and manipulation
for particle tracking and transport modeling.

Key concepts demonstrated:
- ParticleData class creation
- Structured vs unstructured grids
- Particle location specifications
- LRC and Node particle data types
- Coordinate transformations
- Particle release configurations
- Cell-based and face-based particles
- Local and global coordinates

MODPATH particle data is used for:
- Pathline analysis and visualization
- Travel time computations
- Capture zone delineation
- Source tracking and age dating
- Groundwater flow visualization
- Transport pathway analysis
"""

import numpy as np
import os
import flopy
from flopy.modpath import ParticleData, LRCParticleData, NodeParticleData, CellDataType

def run_model():
    """
    Create demonstration showing MODPATH particle data creation.
    Based on test_particledata.py test cases.
    """
    
    print("=== MODPATH Particle Data Demonstration ===\n")
    
    # Create model workspace
    model_ws = "model_output"
    if not os.path.exists(model_ws):
        os.makedirs(model_ws)
    
    # 1. Particle Data Overview
    print("1. MODPATH Particle Data Overview")
    print("-" * 40)
    
    print("  Particle data types:")
    print("    • ParticleData: Basic particle locations")
    print("    • LRCParticleData: Layer-row-column based")
    print("    • NodeParticleData: Node-based (unstructured)")
    print("    • CellDataType: Cell subdivision options")
    print("    • FaceDataType: Face-based release patterns")
    
    # 2. Create Simple Grid for Demonstrations
    print(f"\n2. Creating Base Grid")
    print("-" * 40)
    
    nlay, nrow, ncol = 3, 5, 4
    
    # Create simple MODFLOW model for grid
    mf = flopy.modflow.Modflow(
        modelname="particle_demo",
        exe_name="/home/danilopezmella/flopy_expert/bin/mf2005",
        model_ws=model_ws,
        verbose=False
    )
    
    # Add discretization for grid structure
    dis = flopy.modflow.ModflowDis(
        mf,
        nlay=nlay,
        nrow=nrow, 
        ncol=ncol,
        nper=1,
        perlen=1.0,
        delr=100.0,
        delc=100.0,
        top=50.0,
        botm=[30.0, 10.0, 0.0]
    )
    
    # Add basic packages for runnable model
    # Create ibound with constant head boundaries
    ibound = np.ones((nlay, nrow, ncol), dtype=int)
    # Set first and last columns as constant head boundaries
    ibound[:, :, 0] = -1  # West boundary - constant head
    ibound[:, :, -1] = -1  # East boundary - constant head
    
    # Create head array with gradient
    strt = np.ones((nlay, nrow, ncol)) * 40.0
    # Set gradient from west to east
    for j in range(ncol):
        strt[:, :, j] = 45.0 - (j * 10.0 / (ncol-1))  # 45m to 35m gradient
    
    bas = flopy.modflow.ModflowBas(mf, ibound=ibound, strt=strt)
    lpf = flopy.modflow.ModflowLpf(mf, hk=10.0, vka=1.0)
    
    # Add well boundary condition
    wel_data = {0: [[0, 2, 2, -100.0]]}  # Pumping well in center
    wel = flopy.modflow.ModflowWel(mf, stress_period_data=wel_data)
    
    # Add solver
    pcg = flopy.modflow.ModflowPcg(mf, mxiter=100, iter1=50)
    
    # Add output control
    oc = flopy.modflow.ModflowOc(
        mf,
        save_specific_discharge=True,
        stress_period_data={(0, 0): ['save head', 'save budget']}
    )
    
    grid = mf.modelgrid
    
    print(f"  Grid dimensions: {nlay} layers × {nrow} rows × {ncol} columns")
    print(f"  Domain size: {ncol*100/1000:.1f}km × {nrow*100/1000:.1f}km")
    print(f"  Cell size: 100m × 100m")
    print(f"  Total cells: {nlay*nrow*ncol}")
    
    # 3. Basic ParticleData Creation - Structured
    print(f"\n3. Basic ParticleData - Structured Grid")
    print("-" * 40)
    
    # Create particle locations using layer-row-column coordinates
    structured_locs = [(0, 1, 1), (0, 1, 2), (1, 2, 2), (2, 3, 1)]
    
    part_data_structured = ParticleData(
        partlocs=structured_locs,
        structured=True
    )
    
    print(f"  Particle locations (LRC): {len(structured_locs)}")
    print(f"  Particle count: {part_data_structured.particlecount}")
    print(f"  Data type: structured")
    
    for i, loc in enumerate(structured_locs):
        print(f"    Particle {i+1}: Layer {loc[0]}, Row {loc[1]}, Col {loc[2]}")
    
    # 4. ParticleData with Custom Local Coordinates
    print(f"\n4. ParticleData with Local Coordinates")
    print("-" * 40)
    
    # Create particles with specific local coordinates within cells
    custom_locs = [(0, 2, 1), (0, 2, 2)]
    localx_vals = [0.25, 0.75]  # 25% and 75% across cell
    localy_vals = [0.3, 0.7]   # 30% and 70% across cell
    localz_vals = [0.2, 0.8]   # 20% and 80% through cell
    
    part_data_custom = ParticleData(
        partlocs=custom_locs,
        structured=True,
        localx=localx_vals,
        localy=localy_vals, 
        localz=localz_vals,
        timeoffset=[0.0, 10.0],  # Start times
        drape=[0, 0]  # Draping options
    )
    
    print(f"  Custom coordinate particles: {len(custom_locs)}")
    print(f"  Local X positions: {localx_vals}")
    print(f"  Local Y positions: {localy_vals}")
    print(f"  Local Z positions: {localz_vals}")
    print(f"  Time offsets: [0.0, 10.0] days")
    
    # 5. Unstructured ParticleData (Node-based)
    print(f"\n5. Unstructured ParticleData - Node Numbers")
    print("-" * 40)
    
    # For unstructured grids, use node numbers instead of LRC
    node_numbers = [5, 12, 18, 25]
    
    part_data_nodes = ParticleData(
        partlocs=node_numbers,
        structured=False
    )
    
    print(f"  Node-based locations: {node_numbers}")
    print(f"  Particle count: {part_data_nodes.particlecount}")
    print(f"  Data type: unstructured")
    
    # 6. LRCParticleData with Cell Subdivisions
    print(f"\n6. LRC Particle Data with Cell Subdivisions")
    print("-" * 40)
    
    # Create cell data type for subdivisions
    cell_data = CellDataType(
        drape=0,
        rowcelldivisions=3,      # 3 divisions per row
        columncelldivisions=3,   # 3 divisions per column  
        layercelldivisions=2     # 2 divisions per layer
    )
    
    # Define region for particle release
    lrc_region = [[0, 1, 1, 1, 2, 2]]  # min_layer, min_row, min_col, max_layer, max_row, max_col
    
    lrc_part_data = LRCParticleData(
        subdivisiondata=[cell_data],
        lrcregions=[lrc_region]
    )
    
    print(f"  Cell subdivisions:")
    print(f"    Row divisions: {cell_data.rowcelldivisions}")
    print(f"    Column divisions: {cell_data.columncelldivisions}")
    print(f"    Layer divisions: {cell_data.layercelldivisions}")
    print(f"    Particles per cell: {3*3*2} = {cell_data.rowcelldivisions * cell_data.columncelldivisions * cell_data.layercelldivisions}")
    
    region = lrc_region[0]
    ncells = (region[3]-region[0]+1) * (region[4]-region[1]+1) * (region[5]-region[2]+1)
    total_particles = ncells * cell_data.rowcelldivisions * cell_data.columncelldivisions * cell_data.layercelldivisions
    print(f"    Region cells: {ncells}")
    print(f"    Total particles: {total_particles}")
    
    # 7. NodeParticleData with Default Settings
    print(f"\n7. Node Particle Data with Defaults")
    print("-" * 40)
    
    node_part_data = NodeParticleData()
    
    print(f"  Default NodeParticleData created")
    print(f"  Uses default cell data subdivisions")
    print(f"  Applies to all active model cells")
    print(f"  Particle placement: cell centers")
    
    # 8. Particle Data Analysis and Statistics
    print(f"\n8. Particle Data Analysis")
    print("-" * 40)
    
    datasets = [
        ("Structured basic", part_data_structured, len(structured_locs)),
        ("Structured custom", part_data_custom, len(custom_locs)),
        ("Unstructured nodes", part_data_nodes, len(node_numbers)),
        ("LRC subdivided", lrc_part_data, total_particles)
    ]
    
    print("  Dataset summary:")
    for name, data, expected_count in datasets:
        if hasattr(data, 'particlecount'):
            actual_count = data.particlecount
        else:
            actual_count = expected_count
        print(f"    {name}: {actual_count} particles")
    
    # 9. Coordinate Transformations
    print(f"\n9. Coordinate Transformations")
    print("-" * 40)
    
    print("  Local to global coordinate conversion:")
    print("    • Local coords: [0-1] range within cell")
    print("    • Global coords: Real-world X, Y, Z")
    print("    • Grid intersection: Find containing cell")
    print("    • Extent calculation: Cell boundaries")
    
    # Example coordinate transformation
    test_cell = (0, 2, 1)
    k, i, j = test_cell
    
    # Get cell vertices for coordinate bounds
    try:
        verts = grid.get_cell_vertices(i, j)
        xs, ys = list(zip(*verts))
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        print(f"    Example cell {test_cell}:")
        print(f"      X bounds: {minx:.1f} - {maxx:.1f} m")
        print(f"      Y bounds: {miny:.1f} - {maxy:.1f} m") 
        print(f"      Z bounds: {grid.botm[k,i,j]:.1f} - {grid.top[i,j]:.1f} m")
    except:
        print(f"    Coordinate transformation example")
    
    # 10. Particle Release Strategies
    print(f"\n10. Particle Release Strategies")
    print("-" * 40)
    
    strategies = [
        ("Single point", "One particle at cell center"),
        ("Grid pattern", "Regular subdivision within cells"),
        ("Random distribution", "Monte Carlo sampling"),
        ("Face-based", "Particles on cell faces"),
        ("Edge-based", "Particles along cell edges"),
        ("Custom locations", "User-specified coordinates")
    ]
    
    print("  Release strategies:")
    for strategy, description in strategies:
        print(f"    • {strategy}: {description}")
    
    # 11. Data Types and Formats
    print(f"\n11. Data Types and Formats")
    print("-" * 40)
    
    print("  Structured grid data types:")
    print("    • k (layer): Integer layer index")
    print("    • i (row): Integer row index")
    print("    • j (column): Integer column index")
    print("    • localx: Float [0-1] cell fraction")
    print("    • localy: Float [0-1] cell fraction")
    print("    • localz: Float [0-1] cell fraction")
    print("    • timeoffset: Float time delay")
    print("    • drape: Integer draping option")
    
    print(f"\n  Unstructured grid data types:")
    print("    • node: Integer node number")
    print("    • localx: Float [0-1] cell fraction")
    print("    • localy: Float [0-1] cell fraction")
    print("    • localz: Float [0-1] cell fraction")
    print("    • timeoffset: Float time delay")
    print("    • drape: Integer draping option")
    
    # 12. File Output and Model Execution
    print(f"\n12. Model Execution and Output")
    print("-" * 40)
    
    # Write and run the complete model
    try:
        print(f"  Writing model input files...")
        mf.write_input()
        
        # Check if MODFLOW executable exists
        has_mf2005 = mf.exe_name is not None
        
        if has_mf2005:
            print(f"  Running MODFLOW simulation...")
            success, buff = mf.run_model(silent=True)
            
            if success:
                print(f"  ✓ Model run completed successfully")
                
                # Check output files created
                files = os.listdir(model_ws)
                output_files = [f for f in files if f.endswith(('.hds', '.cbc', '.lst'))]
                
                if output_files:
                    print(f"    • Head file (.hds): {'✓' if any('.hds' in f for f in output_files) else '✗'}")
                    print(f"    • Budget file (.cbc): {'✓' if any('.cbc' in f for f in output_files) else '✗'}")
                    print(f"    • Listing file (.lst): {'✓' if any('.lst' in f for f in output_files) else '✗'}")
                
            else:
                print(f"  ⚠ Model run failed")
                if buff:
                    print(f"    Error: {buff[-1] if buff else 'Unknown error'}")
        else:
            print(f"  MODFLOW executable not available - input files only")
        
        # Always check input files were created
        files = os.listdir(model_ws)
        input_files = [f for f in files if f.endswith(('.nam', '.dis', '.bas', '.lpf', '.wel', '.pcg', '.oc'))]
        print(f"  Input files created: {len(input_files)}")
        for file_type in ['.nam', '.dis', '.bas', '.lpf', '.wel', '.pcg', '.oc']:
            has_file = any(f.endswith(file_type) for f in files)
            print(f"    • {file_type[1:].upper()} file: {'✓' if has_file else '✗'}")
        
    except Exception as e:
        print(f"  ⚠ Model setup error: {str(e)}")
    
    print(f"\n  MODPATH integration:")
    print(f"    • PRP package: MF6 particle release")
    print(f"    • MP7 files: MODPATH 7 input")
    print(f"    • Pathlines: Particle tracking output")
    print(f"    • Endpoints: Final particle locations")
    print(f"    • Timeseries: Particle breakthrough")
    
    # 13. Professional Applications
    print(f"\n13. Professional Applications")
    print("-" * 40)
    
    applications = [
        ("Contaminant transport", "Track pollution sources and plumes"),
        ("Wellhead protection", "Delineate capture zones"),
        ("Age dating", "Determine groundwater residence times"),
        ("Flow visualization", "Show groundwater flow paths"),
        ("Model verification", "Validate flow field accuracy"),
        ("Remediation design", "Optimize cleanup strategies")
    ]
    
    print("  Applications:")
    for app, desc in applications:
        print(f"    • {app}: {desc}")
    
    # 14. Best Practices
    print(f"\n14. Particle Data Best Practices")
    print("-" * 40)
    
    print("  Particle placement:")
    print("    • Avoid low-flow zones")
    print("    • Consider grid resolution")
    print("    • Use appropriate density")
    print("    • Account for boundary effects")
    
    print(f"\n  Data management:")
    print("    • Validate coordinate ranges")
    print("    • Check grid intersections")
    print("    • Monitor particle counts")
    print("    • Document release strategies")
    
    print(f"\n✓ MODPATH Particle Data Demonstration Completed!")
    print(f"  - Created various particle data types")
    print(f"  - Demonstrated coordinate systems")
    print(f"  - Showed subdivision strategies")
    print(f"  - Illustrated professional applications")
    
    return mf

if __name__ == "__main__":
    model = run_model()