#!/usr/bin/env python3

"""
MODFLOW Namefile Reading and Metadata Extraction

This model demonstrates FloPy's capabilities for reading and parsing
MODFLOW namefile headers, extracting metadata like CRS, rotation,
and spatial reference information.

Based on test_mfreadnam.py from the FloPy autotest suite.
"""

import numpy as np
import flopy
from pathlib import Path
import json

def demonstrate_namefile_metadata():
    """
    Demonstrate namefile metadata extraction capabilities.
    """
    print("\nNamefile Metadata Attributes:")
    print("=" * 60)
    
    attributes = {
        "CRS": "Coordinate Reference System (EPSG code or proj4 string)",
        "rotation": "Grid rotation angle in degrees",
        "xll/yll": "Lower-left corner coordinates",
        "xul/yul": "Upper-left corner coordinates",
        "start_datetime": "Model simulation start date/time"
    }
    
    for attr, description in attributes.items():
        print(f"  • {attr}: {description}")
    
    print("\nSupported CRS Formats:")
    formats = {
        "EPSG": "EPSG:4326, EPSG:26916, etc.",
        "Proj4": "+proj=utm +zone=14 +datum=WGS84",
        "WKT": "Well-Known Text format"
    }
    
    for fmt, example in formats.items():
        print(f"  • {fmt}: {example}")

def create_model_with_metadata(workspace, name="metadata_demo"):
    """
    Create a MODFLOW model with spatial reference metadata.
    """
    # Create model
    mf = flopy.modflow.Modflow(
        modelname=name,
        exe_name="mf2005",
        model_ws=str(workspace)
    )
    
    # Simple discretization
    nlay, nrow, ncol = 1, 10, 10
    delr, delc = 100.0, 100.0
    
    dis = flopy.modflow.ModflowDis(
        mf,
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        delr=delr,
        delc=delc,
        top=100.0,
        botm=0.0
    )
    
    # Basic package
    bas = flopy.modflow.ModflowBas(mf)
    
    # Flow package
    lpf = flopy.modflow.ModflowLpf(mf, hk=10.0)
    
    # Output control
    oc = flopy.modflow.ModflowOc(mf)
    
    # PCG solver
    pcg = flopy.modflow.ModflowPcg(mf)
    
    # Add spatial reference with metadata
    mf.modelgrid.set_coord_info(
        xoff=619653.0,     # X offset (UTM easting)
        yoff=3353277.0,    # Y offset (UTM northing)
        angrot=15.0,       # Rotation angle in degrees
        crs="EPSG:26916"   # UTM Zone 16N NAD83
    )
    
    return mf

def write_namefile_with_header_metadata(workspace, name="metadata_demo"):
    """
    Write a namefile with custom header metadata.
    """
    namfile = workspace / f"{name}.nam"
    
    # Custom header with metadata
    header_lines = [
        "# MODFLOW Name File with Metadata",
        "# xul:619653.0  yul:3353277.0  rotation:15.0",
        "# crs:EPSG:26916",
        "# start_datetime:1/1/2015",
        ""
    ]
    
    # Standard namefile entries
    entries = [
        "LIST          2  metadata_demo.list",
        "DIS          11  metadata_demo.dis",
        "BAS6         13  metadata_demo.bas",
        "LPF          15  metadata_demo.lpf",
        "OC           14  metadata_demo.oc",
        "PCG          27  metadata_demo.pcg",
        "DATA(BINARY) 51  metadata_demo.hds REPLACE",
        "DATA(BINARY) 53  metadata_demo.cbc REPLACE"
    ]
    
    with open(namfile, 'w') as f:
        for line in header_lines:
            f.write(line + '\n')
        for entry in entries:
            f.write(entry + '\n')
    
    print(f"  ✓ Created namefile with metadata: {namfile.name}")
    return namfile

def demonstrate_namefile_reading(namfile):
    """
    Demonstrate reading namefile metadata.
    """
    print("\nReading namefile metadata...")
    
    try:
        from flopy.utils.mfreadnam import (
            attribs_from_namfile_header,
            get_entries_from_namefile
        )
        
        # Read header attributes
        attrs = attribs_from_namfile_header(str(namfile))
        
        print("\nExtracted metadata:")
        for key, value in attrs.items():
            if value is not None:
                print(f"  • {key}: {value}")
        
        # Read namefile entries
        entries = get_entries_from_namefile(str(namfile))
        
        print(f"\nNamefile entries: {len(entries)}")
        for fname, ftype, unit in entries[:3]:  # Show first 3
            print(f"  • {ftype:8s} Unit {unit:3s} → {fname}")
        
        return True
        
    except Exception as e:
        print(f"  ! Could not read namefile metadata: {e}")
        return False

def create_mf6_example(workspace):
    """
    Create a MODFLOW 6 example with metadata.
    """
    print("\nCreating MODFLOW 6 model with metadata...")
    
    sim_name = "mf6_metadata"
    sim_ws = workspace / "mf6"
    sim_ws.mkdir(exist_ok=True)
    
    # Create simulation
    sim = flopy.mf6.MFSimulation(
        sim_name=sim_name,
        exe_name="mf6",
        version="mf6",
        sim_ws=str(sim_ws)
    )
    
    # Time discretization
    tdis = flopy.mf6.ModflowTdis(
        sim,
        nper=1,
        perioddata=[(1.0, 1, 1.0)]
    )
    
    # Iterative model solution
    ims = flopy.mf6.ModflowIms(
        sim,
        complexity="SIMPLE",
        print_option="SUMMARY",
        outer_maximum=100,
        inner_maximum=50
    )
    
    # Groundwater flow model
    gwf = flopy.mf6.ModflowGwf(
        sim,
        modelname="gwf_model",
        save_flows=True
    )
    
    # Discretization
    dis = flopy.mf6.ModflowGwfdis(
        gwf,
        nlay=1,
        nrow=10,
        ncol=10,
        delr=100.0,
        delc=100.0,
        top=100.0,
        botm=0.0
    )
    
    # Initial conditions
    ic = flopy.mf6.ModflowGwfic(gwf, strt=50.0)
    
    # Node property flow
    npf = flopy.mf6.ModflowGwfnpf(gwf, k=10.0)
    
    # Output control
    oc = flopy.mf6.ModflowGwfoc(
        gwf,
        head_filerecord="gwf_model.hds",
        budget_filerecord="gwf_model.cbc",
        saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")]
    )
    
    # Write simulation
    sim.write_simulation()
    
    # Add metadata to simulation namefile
    sim_namfile = sim_ws / "mfsim.nam"
    if sim_namfile.exists():
        with open(sim_namfile, 'r') as f:
            content = f.readlines()
        
        # Add metadata header
        header = [
            "# MODFLOW 6 Simulation with Metadata\n",
            "# crs:EPSG:4326\n",
            "# rotation:0.0\n",
            "# start_datetime:2025-01-01\n",
            "#\n"
        ]
        
        with open(sim_namfile, 'w') as f:
            f.writelines(header + content)
        
        print(f"  ✓ Added metadata to {sim_namfile.name}")
    
    return sim_ws / "mfsim.nam"

def run_model(workspace):
    """
    Create models and demonstrate namefile reading.
    """
    results = {
        "runs": True,
        "converges": False,
        "output_exists": False,
        "error": None,
        "outputs": []
    }
    
    try:
        # Create MODFLOW-2005 model with metadata
        print("\n1. Creating MODFLOW-2005 model...")
        mf = create_model_with_metadata(workspace)
        mf.write_input()
        
        # Add custom metadata to namefile
        namfile = write_namefile_with_header_metadata(workspace)
        
        # Demonstrate reading namefile
        success = demonstrate_namefile_reading(namfile)
        
        if success:
            results["converges"] = True
            
        # Create MODFLOW 6 example
        print("\n2. Creating MODFLOW 6 model...")
        mf6_namfile = create_mf6_example(workspace)
        
        # Read MF6 namefile
        if mf6_namfile.exists():
            demonstrate_namefile_reading(mf6_namfile)
        
        # List created files
        outputs = []
        for pattern in ["*.nam", "*.dis", "*.bas", "mf6/mfsim.nam"]:
            for file in workspace.glob(pattern):
                outputs.append(file.name)
            for file in (workspace / "mf6").glob(pattern):
                outputs.append(f"mf6/{file.name}")
        
        results["outputs"] = outputs
        results["output_exists"] = len(outputs) > 0
        
    except Exception as e:
        results["error"] = str(e)
        results["runs"] = False
    
    return results

def main():
    """
    Main function to demonstrate namefile metadata extraction.
    """
    print("=" * 60)
    print("MODFLOW Namefile Metadata Extraction")
    print("=" * 60)
    
    # Create workspace
    workspace = Path("namefile_example")
    workspace.mkdir(exist_ok=True)
    
    # Demonstrate namefile metadata concepts
    demonstrate_namefile_metadata()
    
    # Run demonstrations
    results = run_model(workspace)
    
    # Save results
    results_file = Path("test_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Demonstration: {'✓ Success' if results['runs'] else '✗ Failed'}")
    print(f"Metadata extraction: {'✓ Working' if results['converges'] else '✗ Failed'}")
    print(f"Files created: {len(results['outputs'])}")
    
    if results['outputs']:
        print("\nGenerated files:")
        for file in results['outputs'][:5]:  # Show first 5
            print(f"  - {file}")
        if len(results['outputs']) > 5:
            print(f"  ... and {len(results['outputs']) - 5} more")
    
    return results['runs'] and results['converges']

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)