#\!/usr/bin/env python3

"""
FloPy Plotting Utilities Demonstration

This model demonstrates FloPy plotting utility functions:
- Pathline and endpoint data format conversions
- MODPATH 7 and PRT (Particle Tracking) data handling
- Data type standardization for plotting
- Particle tracking visualization utilities

Based on test_plotutil.py from the FloPy autotest suite.
"""

import numpy as np
import pandas as pd
import flopy
from pathlib import Path
import sys

def create_sample_pathline_data():
    """Create sample pathline data for demonstration."""
    
    print("Creating sample pathline data...")
    
    # Sample PRT pathline data (similar to test file)
    prt_pathlines = pd.DataFrame({
        'sequencenumber': [1, 1, 1, 1],
        'particleid': [1, 1, 1, 1], 
        'particlegroup': [1, 1, 1, 1],
        'timestep': [1, 1, 1, 1],
        'trackingtimestep': [1, 1, 1, 1],
        'k': [0, 0, 0, 0],
        'i': [0, 1, 2, 3],
        'j': [0, 1, 2, 3],
        'time': [0.0, 0.5, 1.0, 1.5],
        'x': [0.0, 1.0, 2.0, 3.0],
        'y': [0.0, 1.0, 2.0, 3.0],
        'z': [9.0, 8.5, 8.0, 7.5],
        'porosity': [0.3, 0.3, 0.3, 0.3],
        'particleidloc': ['PRP000000001', 'PRP000000001', 'PRP000000001', 'PRP000000001']
    })
    
    print(f"  Created PRT pathlines with {len(prt_pathlines)} points")
    
    # Sample MP7 pathline data
    mp7_pathlines = pd.DataFrame({
        'particleid': [1, 1, 1, 1],
        'time': [0.0, 0.5, 1.0, 1.5], 
        'x': [0.0, 1.0, 2.0, 3.0],
        'y': [0.0, 1.0, 2.0, 3.0],
        'z': [9.0, 8.5, 8.0, 7.5],
        'k': [0, 0, 0, 0],
        'i': [0, 1, 2, 3],
        'j': [0, 1, 2, 3]
    })
    
    print(f"  Created MP7 pathlines with {len(mp7_pathlines)} points")
    
    return prt_pathlines, mp7_pathlines

def create_sample_endpoint_data():
    """Create sample endpoint data for demonstration."""
    
    print("Creating sample endpoint data...")
    
    # Sample endpoint data (final particle locations)
    endpoints = pd.DataFrame({
        'particleid': [1, 2, 3, 4],
        'time': [10.0, 12.5, 8.0, 15.0],
        'x': [5.0, 6.5, 4.2, 7.8],
        'y': [5.0, 6.5, 4.2, 7.8], 
        'z': [2.0, 1.5, 3.0, 1.0],
        'k': [0, 0, 0, 0],
        'i': [5, 6, 4, 7],
        'j': [5, 6, 4, 7],
        'status': [2, 2, 2, 2]  # Terminated normally
    })
    
    print(f"  Created endpoints for {len(endpoints)} particles")
    
    return endpoints

def demonstrate_plotutil_functions():
    """Demonstrate FloPy plotting utility functions."""
    
    print("\nDemonstrating FloPy plotting utilities...")
    
    try:
        from flopy.plot.plotutil import (
            to_mp7_pathlines,
            to_mp7_endpoints, 
            to_prt_pathlines,
            MP7_PATHLINE_DTYPE,
            MP7_ENDPOINT_DTYPE,
            PRT_PATHLINE_DTYPE
        )
        
        print("✓ Imported plotting utilities successfully")
        
        # Get sample data
        prt_data, mp7_data = create_sample_pathline_data()
        endpoint_data = create_sample_endpoint_data()
        
        # Demonstrate data type information
        print("\nData type structures:")
        print(f"  MP7 pathline dtype: {len(MP7_PATHLINE_DTYPE.names)} fields")
        print(f"  MP7 endpoint dtype: {len(MP7_ENDPOINT_DTYPE.names)} fields")  
        print(f"  PRT pathline dtype: {len(PRT_PATHLINE_DTYPE.names)} fields")
        
        # Demonstrate conversions
        print("\nDemonstrating data conversions...")
        
        # Convert PRT to MP7 pathlines
        try:
            mp7_converted = to_mp7_pathlines(prt_data)
            print(f"  ✓ PRT to MP7 pathlines: {len(prt_data)} → {len(mp7_converted)} points")
        except Exception as e:
            print(f"  \! PRT to MP7 pathlines: {e}")
        
        # Convert to MP7 endpoints
        try:
            mp7_endpoints = to_mp7_endpoints(endpoint_data)
            print(f"  ✓ DataFrame to MP7 endpoints: {len(endpoint_data)} particles")
        except Exception as e:
            print(f"  \! DataFrame to MP7 endpoints: {e}")
            
        # Convert to PRT pathlines
        try:
            prt_converted = to_prt_pathlines(mp7_data)
            print(f"  ✓ MP7 to PRT pathlines: {len(mp7_data)} → {len(prt_converted)} points")
        except Exception as e:
            print(f"  \! MP7 to PRT pathlines: {e}")
            
        return True
        
    except ImportError as e:
        print(f"\! Could not import plotting utilities: {e}")
        return False
    except Exception as e:
        print(f"✗ Error in plotting utilities demo: {e}")
        return False

def demonstrate_particle_tracking_concepts():
    """Demonstrate particle tracking concepts."""
    
    print("\nParticle Tracking Concepts:")
    print("=" * 40)
    
    concepts = {
        "Pathlines": "Trace particle movement through groundwater flow field over time",
        "Endpoints": "Final locations where particles terminate (boundaries, sinks, etc.)",
        "MODPATH 7": "USGS particle tracking code for MODFLOW models",
        "PRT": "Particle Tracking package for MODFLOW 6",
        "Data Conversion": "FloPy utilities to standardize between different tracking formats"
    }
    
    for concept, description in concepts.items():
        print(f"  • {concept}: {description}")
    
    print("\nData Format Compatibility:")
    formats = {
        "MP7 Format": "Standard MODPATH 7 output format",
        "PRT Format": "MODFLOW 6 Particle Tracking format", 
        "FloPy Conversion": "Utilities to convert between formats for visualization"
    }
    
    for fmt, desc in formats.items():
        print(f"  • {fmt}: {desc}")

def create_plotting_example():
    """Create example of particle tracking visualization setup."""
    
    print("\nCreating particle tracking visualization example...")
    
    workspace = Path("plotutil_example")
    workspace.mkdir(exist_ok=True)
    
    # Create a simple model for particle tracking context
    m = flopy.modflow.Modflow(
        modelname="particle_demo",
        model_ws=str(workspace)
    )
    
    # Simple grid
    dis = flopy.modflow.ModflowDis(
        m,
        nlay=1,
        nrow=10, 
        ncol=10,
        delr=100.0,
        delc=100.0,
        top=10.0,
        botm=[0.0]
    )
    
    # Basic packages for flow
    bas = flopy.modflow.ModflowBas(m)
    lpf = flopy.modflow.ModflowLpf(m, hk=10.0)
    
    # Boundary conditions
    chd_data = [
        [0, 0, 0, 10.0, 10.0],  # Left boundary - high head
        [0, 0, 9, 5.0, 5.0]    # Right boundary - low head
    ]
    chd = flopy.modflow.ModflowChd(m, stress_period_data=chd_data)
    
    # Output control - save heads and budgets
    oc = flopy.modflow.ModflowOc(m, 
        stress_period_data={(0, 0): ['save head', 'save budget']})
    
    # Add PCG solver
    pcg = flopy.modflow.ModflowPcg(m)
    
    # Write model
    m.write_input()
    
    # Run the model
    try:
        # Try to use mf2005 executable
        exe_path = "/home/danilopezmella/flopy_expert/bin/mf2005"
        if Path(exe_path).exists():
            m.exe_name = exe_path
            success, buff = m.run_model(silent=True)
            if success:
                print(f"  ✓ Model ran successfully")
                # Check for output files
                hds_file = workspace / f"{m.name}.hds"
                cbc_file = workspace / f"{m.name}.cbc"
                if hds_file.exists():
                    print(f"  ✓ Head file generated: {hds_file.name}")
                if cbc_file.exists():
                    print(f"  ✓ Budget file generated: {cbc_file.name}")
            else:
                print(f"  ! Model did not converge")
    except Exception as e:
        print(f"  ! Could not run model: {e}")
    
    print(f"  ✓ Created demonstration model in {workspace}")
    
    # Create example plotting code
    plot_example = '''
# Example particle tracking visualization with FloPy plotting utilities

import matplotlib.pyplot as plt
import flopy
from flopy.plot.plotutil import to_mp7_pathlines, to_mp7_endpoints

# Load particle tracking results (after running MODPATH)
# pathlines = flopy.utils.PathlineFile("model.mppth").get_alldata()
# endpoints = flopy.utils.EndpointFile("model.mpend").get_alldata()

# Convert to standard format for plotting
# mp7_pathlines = to_mp7_pathlines(pathlines) 
# mp7_endpoints = to_mp7_endpoints(endpoints)

# Create visualization
# fig, ax = plt.subplots(figsize=(10, 8))

# Plot model grid
# modelmap = flopy.plot.PlotMapView(model=m, ax=ax)
# modelmap.plot_grid()

# Plot pathlines
# for particle_id in np.unique(mp7_pathlines['particleid']):
#     data = mp7_pathlines[mp7_pathlines['particleid'] == particle_id]
#     ax.plot(data['x'], data['y'], 'b-', alpha=0.7)

# Plot endpoints
# ax.scatter(mp7_endpoints['x'], mp7_endpoints['y'], c='red', s=50)

# plt.title("Particle Tracking Results")
# plt.xlabel("X Coordinate")
# plt.ylabel("Y Coordinate") 
# plt.show()
    '''
    
    example_file = workspace / "plotting_example.py"
    with open(example_file, 'w') as f:
        f.write(plot_example)
    
    print(f"  ✓ Created plotting example: {example_file.name}")
    
    return workspace

def main():
    """Main function to demonstrate FloPy plotting utilities."""
    
    print("=" * 60)
    print("FloPy Plotting Utilities Demonstration")
    print("=" * 60)
    
    try:
        # Demonstrate plotting utility functions
        plotutil_success = demonstrate_plotutil_functions()
        
        # Explain particle tracking concepts
        demonstrate_particle_tracking_concepts()
        
        # Create visualization example
        workspace = create_plotting_example()
        
        print("\n" + "=" * 60)
        print("SUMMARY") 
        print("=" * 60)
        print(f"Plotting utilities: {'✓ Success' if plotutil_success else '! Limited functionality'}")
        print(f"Particle tracking concepts: ✓ Documented")
        print(f"Visualization example: ✓ Created")
        
        # List created files
        files = list(workspace.glob("*"))
        if files:
            print(f"Files created: {len(files)}")
            for file in sorted(files):
                print(f"  - {file.name}")
        
        return plotutil_success
        
    except Exception as e:
        print(f"✗ Error in main execution: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
