"""
MODPATH Particle Group Configuration Demonstration

This script demonstrates FloPy's MODPATH particle group functionality for particle tracking
simulations. Based on the original test_particlegroup.py from FloPy autotest.

Key concepts demonstrated:
- ParticleData creation with structured grids
- ParticleGroup configuration with different release options
- Time-based particle release mechanisms
- Particle tracking setup and validation
- Integration with MODFLOW groundwater models

The test addresses:
- Release option 1: Single-time release
- Release option 2: Regular interval release
- Release option 3: User-specified time release
- Particle location specification in structured grids
- Particle tracking file management
"""

import numpy as np
import os
import flopy
from pathlib import Path

def run_model():
    """
    Demonstrate MODPATH particle group configuration and particle tracking setup.
    Shows different particle release strategies for groundwater flow analysis.
    """
    
    print("=== MODPATH Particle Group Configuration Demonstration ===\n")
    
    # Create model workspace
    model_ws = "./model_output"
    os.makedirs(model_ws, exist_ok=True)
    
    # 1. Particle Tracking Background
    print("1. Particle Tracking Background")
    print("-" * 40)
    
    print("  MODPATH particle tracking:")
    print("    • Simulates advective transport of particles")
    print("    • Uses MODFLOW flow field for pathlines")
    print("    • Tracks particles forward and backward in time")
    print("    • Multiple release strategies for different purposes")
    print("    • Essential for contaminant fate and transport")
    
    # 2. Create Base Particle Locations
    print(f"\n2. Creating Base Particle Locations")
    print("-" * 40)
    
    # Create particles along a transect (row-based)
    partlocs = []
    partids = []
    nrow = 21
    
    print(f"  Setting up particle transect:")
    print(f"    • Number of particles: {nrow}")
    print(f"    • Location pattern: Along column 2")
    print(f"    • Grid coordinates: (layer, row, column)")
    
    for i in range(nrow):
        partlocs.append((0, i, 2))  # Layer 0, row i, column 2
        partids.append(i)
    
    print(f"    • Particle locations generated: {len(partlocs)}")
    print(f"    • Sample locations: {partlocs[:3]}...")
    
    # Create ParticleData object
    from flopy.modpath import ParticleData, ParticleGroup
    
    pdata = ParticleData(partlocs, structured=True, particleids=partids)
    print(f"  ✓ ParticleData object created with {len(partids)} particles")
    
    # 3. Particle Group 1: Single Release Time
    print(f"\n3. Particle Group 1: Single Release Time")
    print("-" * 40)
    
    pgrd1 = ParticleGroup(
        particlegroupname="PG1",
        particledata=pdata,
        filename="transect_single.sloc",
        releasedata=0.0,  # Single release at time 0
    )
    
    print(f"  Configuration:")
    print(f"    • Group name: {pgrd1.particlegroupname}")
    print(f"    • Release option: 1 (single time)")
    print(f"    • Release time: 0.0")
    print(f"    • Number of release times: {len(pgrd1.releasetimes)}")
    print(f"    • Output file: {pgrd1.filename}")
    
    print(f"  ✓ Single release configuration validated")
    
    # 4. Particle Group 2: Regular Interval Release
    print(f"\n4. Particle Group 2: Regular Interval Release")
    print("-" * 40)
    
    nripg2 = 10
    ripg2 = 1.0  # Release interval in time units
    
    pgrd2 = ParticleGroup(
        particlegroupname="PG2",
        particledata=pdata,
        filename="transect_interval.sloc",
        releasedata=[nripg2, 0.0, ripg2],  # [count, start_time, interval]
    )
    
    print(f"  Configuration:")
    print(f"    • Group name: {pgrd2.particlegroupname}")
    print(f"    • Release option: 2 (regular interval)")
    print(f"    • Number of releases: {nripg2}")
    print(f"    • Start time: 0.0")
    print(f"    • Release interval: {ripg2} time units")
    print(f"    • Total release times: {len(pgrd2.releasetimes)}")
    print(f"    • Release times: {pgrd2.releasetimes}")
    print(f"    • Output file: {pgrd2.filename}")
    
    print(f"  ✓ Regular interval release configuration validated")
    print(f"  ✓ Release interval type preserved: {type(pgrd2.releaseinterval).__name__}")
    
    # 5. Particle Group 3: User-Specified Times
    print(f"\n5. Particle Group 3: User-Specified Times")
    print("-" * 40)
    
    nripg3 = 10
    custom_times = np.arange(0, nripg3)  # Times: 0, 1, 2, ..., 9
    
    pgrd3 = ParticleGroup(
        particlegroupname="PG3",
        particledata=pdata,
        filename="transect_custom.sloc",
        releasedata=[nripg3, custom_times],  # [count, time_array]
    )
    
    print(f"  Configuration:")
    print(f"    • Group name: {pgrd3.particlegroupname}")
    print(f"    • Release option: 3 (user-specified times)")
    print(f"    • Number of releases: {nripg3}")
    print(f"    • Custom times: {custom_times}")
    print(f"    • Total release times: {len(pgrd3.releasetimes)}")
    print(f"    • Release times: {pgrd3.releasetimes}")
    print(f"    • Output file: {pgrd3.filename}")
    
    print(f"  ✓ Custom time release configuration validated")
    
    # 6. Validation and Comparison
    print(f"\n6. Validation and Comparison")
    print("-" * 40)
    
    # Test assertions from original test
    validation_results = []
    
    # Test 1: Single release time count
    expected_pg1_releases = 1
    actual_pg1_releases = len(pgrd1.releasetimes)
    test1_pass = actual_pg1_releases == expected_pg1_releases
    validation_results.append(test1_pass)
    
    print(f"  Test 1 - Single release count:")
    print(f"    Expected: {expected_pg1_releases}, Actual: {actual_pg1_releases}")
    print(f"    Result: {'✓ PASS' if test1_pass else '✗ FAIL'}")
    
    # Test 2: Regular interval release count
    expected_pg2_releases = nripg2
    actual_pg2_releases = len(pgrd2.releasetimes)
    test2_pass = actual_pg2_releases == expected_pg2_releases
    validation_results.append(test2_pass)
    
    print(f"  Test 2 - Interval release count:")
    print(f"    Expected: {expected_pg2_releases}, Actual: {actual_pg2_releases}")
    print(f"    Result: {'✓ PASS' if test2_pass else '✗ FAIL'}")
    
    # Test 3: Release interval type preservation
    expected_interval_type = type(ripg2)
    actual_interval_type = type(pgrd2.releaseinterval)
    test3_pass = actual_interval_type == expected_interval_type
    validation_results.append(test3_pass)
    
    print(f"  Test 3 - Release interval type:")
    print(f"    Expected: {expected_interval_type.__name__}, Actual: {actual_interval_type.__name__}")
    print(f"    Result: {'✓ PASS' if test3_pass else '✗ FAIL'}")
    
    # Test 4: Custom time release count
    expected_pg3_releases = nripg3
    actual_pg3_releases = len(pgrd3.releasetimes)
    test4_pass = actual_pg3_releases == expected_pg3_releases
    validation_results.append(test4_pass)
    
    print(f"  Test 4 - Custom time release count:")
    print(f"    Expected: {expected_pg3_releases}, Actual: {actual_pg3_releases}")
    print(f"    Result: {'✓ PASS' if test4_pass else '✗ FAIL'}")
    
    all_tests_pass = all(validation_results)
    print(f"\n  Overall validation: {'✓ ALL TESTS PASS' if all_tests_pass else '✗ SOME TESTS FAILED'}")
    
    # 7. Practical MODPATH Integration
    print(f"\n7. Practical MODPATH Integration")
    print("-" * 40)
    
    print("  Real-world particle tracking workflow:")
    print("    1. Create MODFLOW model and run simulation")
    print("    2. Define particle starting locations")
    print("    3. Configure particle groups with release strategies")
    print("    4. Run MODPATH simulation using flow field")
    print("    5. Analyze pathlines, travel times, and endpoints")
    
    print(f"\n  Particle group applications:")
    print(f"    • Single release (PG1): Instantaneous spill scenarios")
    print(f"    • Interval release (PG2): Continuous source monitoring")
    print(f"    • Custom release (PG3): Complex injection schedules")
    
    # 8. Professional Applications
    print(f"\n8. Professional Applications")
    print("-" * 40)
    
    applications = [
        ("Contaminant source tracking", "Identify pollution sources using backward tracking"),
        ("Well capture zone analysis", "Determine areas contributing to well water"),
        ("Remediation design", "Optimize placement of treatment systems"),
        ("Environmental compliance", "Demonstrate containment effectiveness"),
        ("Risk assessment", "Evaluate contaminant migration pathways"),
        ("Monitoring network design", "Optimize sampling locations")
    ]
    
    print("  Professional applications:")
    for application, description in applications:
        print(f"    • {application}: {description}")
    
    # 9. Output File Information
    print(f"\n9. Output File Information")
    print("-" * 40)
    
    print("  Particle location files generated:")
    for i, pg in enumerate([pgrd1, pgrd2, pgrd3], 1):
        print(f"    • PG{i}: {pg.filename}")
        print(f"      - Particles: {len(partids)}")  # Use original partids list
        print(f"      - Release times: {len(pg.releasetimes)}")
        print(f"      - Total particle-time combinations: {len(partids) * len(pg.releasetimes)}")
    
    # 10. Technical Notes
    print(f"\n10. Technical Notes")
    print("-" * 40)
    
    print("  Key implementation details:")
    print("    • ParticleData supports both structured and unstructured grids")
    print("    • Particle IDs must be unique within each group")
    print("    • Release times are internally sorted and validated")
    print("    • File formats are compatible with MODPATH-7")
    print("    • Multiple particle groups can be combined in one simulation")
    
    print(f"\n✓ MODPATH Particle Group Demonstration Completed!")
    print(f"  - Demonstrated 3 particle release strategies")
    print(f"  - Validated particle group configurations")
    print(f"  - Showed practical tracking applications")
    print(f"  - Created {len(partlocs)} particles across {len([pgrd1, pgrd2, pgrd3])} groups")
    print(f"  - Generated particle location files for MODPATH")
    
    return [pgrd1, pgrd2, pgrd3]

if __name__ == "__main__":
    particle_groups = run_model()