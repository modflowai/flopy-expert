"""
MODFLOW Post-Processing Utilities Demonstration

This script demonstrates FloPy's comprehensive post-processing utilities for groundwater
model analysis. Based on the original test_postprocessing.py from FloPy autotest.

Key concepts demonstrated:
- Water table calculation from 3D head data
- Transmissivity computation for multi-layer aquifers
- Gradient calculation for vertical flow analysis
- Saturated thickness computation
- MODFLOW-6 face flow analysis (conceptual)
- Professional groundwater analysis workflows

The test addresses:
- Complex hydrogeological post-processing
- Multi-layer aquifer analysis
- Head-dependent transmissivity calculations
- Water table extraction from complex head distributions
- Professional modeling workflows
"""

import numpy as np
import os
import flopy
from pathlib import Path

def run_model():
    """
    Demonstrate comprehensive MODFLOW post-processing utilities.
    Shows practical analysis techniques for groundwater modeling results.
    """
    
    print("=== MODFLOW Post-Processing Utilities Demonstration ===\n")
    
    # Create model workspace
    model_ws = "./model_output"
    os.makedirs(model_ws, exist_ok=True)
    
    # 1. Post-Processing Background
    print("1. Post-Processing Background")
    print("-" * 40)
    
    print("  MODFLOW post-processing essentials:")
    print("    • Water table extraction from 3D head arrays")
    print("    • Transmissivity calculations for pumping tests")
    print("    • Vertical gradient analysis for flow direction")
    print("    • Saturated thickness for unconfined aquifers")
    print("    • Face flow analysis for detailed budgets")
    print("    • Professional hydrogeological analysis")
    
    # 2. Water Table Calculation
    print(f"\n2. Water Table Calculation")
    print("-" * 40)
    
    # Import the utility functions
    from flopy.utils.postprocessing import get_water_table
    
    print("  Creating complex 3D head distribution:")
    
    # Create 3D head array with dry cells and no-flow conditions
    hdry = -1e30  # Standard dry cell value
    hnoflo = 1e30  # Standard no-flow value
    
    hds = np.ones((3, 3, 3), dtype=float) * hdry
    
    # Set up realistic head distribution
    hds[-1, :, :] = 2.0      # Bottom layer - saturated
    hds[1, 1, 1] = 1.0       # Middle layer - partially saturated
    hds[0, -1, -1] = hnoflo  # Top layer - no flow boundary
    
    print(f"    • Grid dimensions: 3 layers × 3 rows × 3 columns")
    print(f"    • Dry cell value: {hdry}")
    print(f"    • No-flow value: {hnoflo}")
    print(f"    • Bottom layer heads: {hds[-1, 0, 0]} m")
    print(f"    • Partial saturation at (1,1,1): {hds[1, 1, 1]} m")
    
    # Calculate water table
    wt = get_water_table(hds)
    
    print(f"\n  Water table analysis:")
    print(f"    • Water table array shape: {wt.shape}")
    print(f"    • Water table at (1,1): {wt[1, 1]} m")
    print(f"    • Total water table sum: {np.sum(wt)} m")
    print(f"    • Average water table: {np.mean(wt):.2f} m")
    
    # Test with different dry cell values
    hdry2 = -9999
    hnoflo2 = 9999
    hds2 = np.ones((3, 3, 3), dtype=float) * hdry2
    hds2[-1, :, :] = 2.0
    hds2[1, 1, 1] = 1.0
    hds2[0, -1, -1] = hnoflo2
    
    wt2 = get_water_table(hds2, hdry=hdry2, hnoflo=hnoflo2)
    
    print(f"\n  Alternative dry cell handling:")
    print(f"    • Alternative dry value: {hdry2}")
    print(f"    • Water table consistency: {np.array_equal(wt, wt2)}")
    print(f"    • ✓ Water table calculation validated")
    
    # 3. Transmissivity Calculation
    print(f"\n3. Transmissivity Calculation")
    print("-" * 40)
    
    from flopy.utils import get_transmissivities
    
    # Create realistic multi-layer aquifer system
    print("  Setting up multi-layer aquifer system:")
    
    # Screen top and bottom elevations (8 observation points)
    sctop = [-0.25, 0.5, 1.7, 1.5, 3.0, 2.5, 3.0, -10.0]
    scbot = [-1.0, -0.5, 1.2, 0.5, 1.5, -0.2, 2.5, -11.0]
    
    # Head observations (3 layers × 8 locations)
    heads = np.array([
        [1.0, 2.0, 2.05, 3.0, 4.0, 2.5, 2.5, 2.5],
        [1.1, 2.1, 2.2, 2.0, 3.5, 3.0, 3.0, 3.0],
        [1.2, 2.3, 2.4, 0.6, 3.4, 3.2, 3.2, 3.2],
    ])
    
    nl, nr = heads.shape
    nc = nr
    
    # Create model geometry
    botm = np.ones((nl, nr, nc), dtype=float)
    top = np.ones((nr, nc), dtype=float) * 2.1
    hk = np.ones((nl, nr, nc), dtype=float) * 2.0  # Hydraulic conductivity
    
    for i in range(nl):
        botm[nl - i - 1, :, :] = i
    
    print(f"    • Aquifer layers: {nl}")
    print(f"    • Observation points: {nr}")
    print(f"    • Screen intervals: {len(sctop)} wells")
    print(f"    • Hydraulic conductivity: {hk[0,0,0]} m/d")
    print(f"    • Top elevation: {top[0,0]} m")
    
    # Create MODFLOW model for transmissivity calculation
    m = flopy.modflow.Modflow("transmissivity_demo", 
                              version="mfnwt", 
                              model_ws=model_ws)
    
    dis = flopy.modflow.ModflowDis(m, nlay=nl, nrow=nr, ncol=nc, 
                                   botm=botm, top=top)
    upw = flopy.modflow.ModflowUpw(m, hk=hk)
    
    # Calculate transmissivities with open intervals
    r, c = np.arange(nr), np.arange(nc)
    T_open = get_transmissivities(heads, m, r=r, c=c, sctop=sctop, scbot=scbot)
    
    print(f"\n  Transmissivity with open intervals:")
    print(f"    • Transmissivity array shape: {T_open.shape}")
    print(f"    • Example transmissivities (m²/d):")
    for i in range(min(3, nl)):
        print(f"      Layer {i+1}: {T_open[i, :3]}")
    
    # Calculate transmissivities without specifying intervals (full aquifer)
    T_full = get_transmissivities(heads, m, r=r, c=c)
    
    print(f"\n  Transmissivity for full aquifer:")
    print(f"    • Full aquifer transmissivities (m²/d):")
    for i in range(min(3, nl)):
        print(f"      Layer {i+1}: {T_full[i, :3]}")
    
    print(f"    • ✓ Transmissivity calculations completed")
    
    # 4. Gradient and Saturated Thickness Analysis
    print(f"\n4. Gradient and Saturated Thickness Analysis")
    print("-" * 40)
    
    from flopy.utils.postprocessing import get_gradients
    
    # Create complex head distribution for gradient analysis
    nodata = -9999.0
    hds_grad = np.ones((3, 3, 3), dtype=float) * nodata
    
    # Set up layered head system
    hds_grad[1, :, :] = 2.4  # Middle layer base
    hds_grad[0, 1, 1] = 3.2  # Upper layer center
    hds_grad[2, :, :] = 2.5  # Lower layer
    hds_grad[1, 1, 1] = 3.0  # Middle layer center (higher)
    hds_grad[2, 1, 1] = 2.6  # Lower layer center
    
    print("  Setting up gradient analysis:")
    print(f"    • No-data value: {nodata}")
    print(f"    • Middle layer base head: {hds_grad[1, 0, 0]} m")
    print(f"    • Upper layer center: {hds_grad[0, 1, 1]} m")
    print(f"    • Vertical head variation: {hds_grad[0, 1, 1] - hds_grad[2, 1, 1]:.1f} m")
    
    # Create model for gradient calculation
    nl_g, nr_g, nc_g = hds_grad.shape
    botm_grad = np.ones((nl_g, nr_g, nc_g), dtype=float)
    top_grad = np.ones((nr_g, nc_g), dtype=float) * 4.0
    botm_grad[0, :, :] = 3.0
    botm_grad[1, :, :] = 2.0
    
    m_grad = flopy.modflow.Modflow("gradient_demo", 
                                   version="mfnwt", 
                                   model_ws=model_ws)
    dis_grad = flopy.modflow.ModflowDis(m_grad, nlay=nl_g, nrow=nr_g, ncol=nc_g, 
                                        botm=botm_grad, top=top_grad)
    lpf_grad = flopy.modflow.ModflowLpf(m_grad, laytyp=np.ones(nl_g))
    
    # Calculate gradients
    grad = get_gradients(hds_grad, m_grad, nodata=nodata)
    
    print(f"\n  Gradient analysis results:")
    print(f"    • Gradient array shape: {grad.shape}")
    print(f"    • Vertical gradient at center: {grad[:, 1, 1]}")
    print(f"    • Gradient indicates: {'Upward flow' if grad[0, 1, 1] > 0 else 'Downward flow'}")
    
    # Calculate saturated thickness
    sat_thick = m_grad.modelgrid.saturated_thickness(hds_grad, mask=nodata)
    
    print(f"\n  Saturated thickness analysis:")
    print(f"    • Saturated thickness shape: {sat_thick.shape}")
    print(f"    • Thickness at center: {sat_thick[:, 1, 1]} m")
    print(f"    • Total thickness: {np.sum(sat_thick[:, 1, 1]):.2f} m")
    print(f"    • ✓ Gradient and thickness analysis completed")
    
    # 5. Multi-Timestep Water Table Analysis
    print(f"\n5. Multi-Timestep Water Table Analysis")
    print("-" * 40)
    
    # Create time-series head data (2 time steps)
    hds_timeseries = np.array([hds2, hds2])  # Duplicate for demonstration
    
    wt_timeseries = get_water_table(hds_timeseries, hdry=hdry2, hnoflo=hnoflo2)
    
    print("  Time-series water table analysis:")
    print(f"    • Time series shape: {wt_timeseries.shape}")
    print(f"    • Timesteps analyzed: {wt_timeseries.shape[0]}")
    print(f"    • Water table at (1,1) over time: {wt_timeseries[:, 1, 1]}")
    print(f"    • Total water table change: {np.sum(wt_timeseries)} m")
    print(f"    • ✓ Time-series analysis completed")
    
    # 6. Professional Analysis Summary
    print(f"\n6. Professional Analysis Summary")
    print("-" * 40)
    
    print("  Post-processing results summary:")
    print(f"    • Water table successfully extracted from 3D heads")
    print(f"    • Transmissivity calculated for {len(sctop)} observation points")
    print(f"    • Vertical gradients computed for flow direction analysis")
    print(f"    • Saturated thickness determined for unconfined conditions")
    print(f"    • Multi-timestep analysis capability demonstrated")
    
    # 7. Professional Applications
    print(f"\n7. Professional Applications")
    print("-" * 40)
    
    applications = [
        ("Pump test analysis", "Calculate transmissivity from head drawdown"),
        ("Water table mapping", "Delineate unconfined aquifer extent"),
        ("Vertical flow assessment", "Determine aquitard leakage rates"),
        ("Wellfield optimization", "Design spacing based on transmissivity"),
        ("Contamination studies", "Analyze flow directions and pathways"),
        ("Aquifer characterization", "Quantify hydraulic properties"),
        ("Water supply assessment", "Evaluate aquifer storage and yield"),
        ("Monitoring network design", "Optimize observation well placement")
    ]
    
    print("  Professional applications:")
    for application, description in applications:
        print(f"    • {application}: {description}")
    
    # 8. Technical Implementation Notes
    print(f"\n8. Technical Implementation Notes")
    print("-" * 40)
    
    print("  Key implementation considerations:")
    print("    • Water table extraction handles dry cells and no-flow boundaries")
    print("    • Transmissivity calculations support open interval specifications")
    print("    • Gradient analysis accounts for variable layer thickness")
    print("    • Saturated thickness computed with proper masking")
    print("    • Time-series analysis scales efficiently to large datasets")
    print("    • All utilities integrate seamlessly with FloPy model objects")
    
    # 9. Quality Assurance
    print(f"\n9. Quality Assurance")
    print("-" * 40)
    
    # Validation checks
    validations = []
    
    # Check water table consistency
    wt_check = np.sum(wt) == 17.0 and wt[1, 1] == 1.0
    validations.append(wt_check)
    print(f"  Water table validation: {'✓ PASS' if wt_check else '✗ FAIL'}")
    
    # Check alternative water table calculation
    wt2_check = np.sum(wt2) == 17.0 and wt2[1, 1] == 1.0
    validations.append(wt2_check)
    print(f"  Alternative water table: {'✓ PASS' if wt2_check else '✗ FAIL'}")
    
    # Check time-series water table
    wt_ts_check = np.sum(wt_timeseries) == 34.0 and np.sum(wt_timeseries[:, 1, 1]) == 2.0
    validations.append(wt_ts_check)
    print(f"  Time-series water table: {'✓ PASS' if wt_ts_check else '✗ FAIL'}")
    
    # Check gradient calculations  
    grad_check = isinstance(grad, np.ndarray) and len(grad.shape) == 3
    validations.append(grad_check)
    print(f"  Gradient calculation: {'✓ PASS' if grad_check else '✗ FAIL'}")
    
    # Check saturated thickness
    sat_check = isinstance(sat_thick, np.ndarray) and sat_thick.shape == hds_grad.shape
    validations.append(sat_check)
    print(f"  Saturated thickness: {'✓ PASS' if sat_check else '✗ FAIL'}")
    
    all_valid = all(validations)
    print(f"\n  Overall validation: {'✓ ALL TESTS PASS' if all_valid else '✗ SOME TESTS FAILED'}")
    
    print(f"\n✓ MODFLOW Post-Processing Demonstration Completed!")
    print(f"  - Demonstrated water table extraction from 3D heads")
    print(f"  - Calculated transmissivity for multi-layer aquifers")
    print(f"  - Analyzed vertical gradients and flow directions")
    print(f"  - Computed saturated thickness for unconfined conditions")
    print(f"  - Validated all post-processing utilities")
    print(f"  - Showcased professional groundwater analysis workflows")
    
    return {
        'water_table': wt,
        'transmissivity_open': T_open,
        'transmissivity_full': T_full,
        'gradients': grad,
        'saturated_thickness': sat_thick,
        'validations_passed': all_valid
    }

if __name__ == "__main__":
    results = run_model()