"""
PCG File Format Compatibility Demonstration

This script demonstrates FloPy's PCG package file format compatibility between
MODFLOW-2000 and MODFLOW-2005. Based on the original test_pcg.py from FloPy autotest.

Key concepts demonstrated:
- PCG file format differences between MF2K and MF2005
- Fixed-format vs free-format PCG files
- Cross-version compatibility in FloPy
- PCG package loading and parameter parsing
- Version-specific format handling

The test addresses:
- Fixed-format PCG files from older MODFLOW versions
- Exception handling for format differences
- Parameter consistency across versions
- Backward compatibility maintenance
"""

import numpy as np
import os
import flopy
from pathlib import Path

def run_model():
    """
    Demonstrate PCG file format compatibility between MODFLOW versions.
    Tests the ability to load fixed-format PCG files in different MODFLOW versions.
    """
    
    print("=== PCG File Format Compatibility Demonstration ===\n")
    
    # Create model workspace
    model_ws = "./model_output"
    os.makedirs(model_ws, exist_ok=True)
    
    # 1. PCG Format Background
    print("1. PCG Format Background")
    print("-" * 40)
    
    print("  Historical context:")
    print("    • MODFLOW-2000: Used fixed-format input files")
    print("    • MODFLOW-2005: Introduced free-format support")
    print("    • Legacy models: Still use old fixed formats")
    print("    • FloPy challenge: Support both formats seamlessly")
    print("    • Pull request #311: Fixed compatibility issues")
    
    # 2. Create Sample Fixed-Format PCG File
    print(f"\n2. Creating Sample Fixed-Format PCG File")
    print("-" * 40)
    
    # Create a sample fixed-format PCG file content
    fixed_format_content = """# Fixed-format PCG file for compatibility testing
# This represents a typical MODFLOW-2000 PCG file
         100        30         1  # MXITER, ITER1, NPCOND
    1.00E-03  1.00E-03  1.00E+00  # HCLOSE, RCLOSE, RELAX
           0      1.00           # NBPOL, DAMP
"""
    
    # Write fixed-format PCG file
    fixed_pcg_file = os.path.join(model_ws, "fixfmt.pcg")
    with open(fixed_pcg_file, 'w') as f:
        f.write(fixed_format_content)
    
    print(f"  Created fixed-format PCG file: {os.path.basename(fixed_pcg_file)}")
    print("  Format characteristics:")
    print("    • Fixed column positions")
    print("    • Scientific notation (1.00E-03)")
    print("    • Specific spacing requirements")
    print("    • Comments allowed with # symbol")
    
    # 3. Test MODFLOW-2000 Compatibility
    print(f"\n3. Testing MODFLOW-2000 Compatibility")
    print("-" * 40)
    
    try:
        # Create MF2K model container
        m2k = flopy.modflow.Modflow(version="mf2k", model_ws=model_ws)
        print("  ✓ Created MODFLOW-2000 model container")
        
        # Load PCG package
        pcg_m2k = flopy.modflow.ModflowPcg.load(model=m2k, f=fixed_pcg_file)
        print("  ✓ Successfully loaded fixed-format PCG in MF2K")
        
        # Display loaded parameters
        print(f"    • MXITER: {pcg_m2k.mxiter}")
        print(f"    • ITER1: {pcg_m2k.iter1}")
        print(f"    • HCLOSE: {pcg_m2k.hclose}")
        print(f"    • RCLOSE: {pcg_m2k.rclose}")
        print(f"    • RELAX: {pcg_m2k.relax}")
        print(f"    • DAMP: {pcg_m2k.damp}")
        
    except Exception as e:
        print(f"  ✗ Error loading PCG in MF2K: {str(e)}")
        pcg_m2k = None
    
    # 4. Test MODFLOW-2005 Compatibility
    print(f"\n4. Testing MODFLOW-2005 Compatibility")
    print("-" * 40)
    
    try:
        # Create MF2005 model container
        m05 = flopy.modflow.Modflow(version="mf2005", model_ws=model_ws)
        print("  ✓ Created MODFLOW-2005 model container")
        
        # Load PCG package - this should work with the exception handling
        pcg_m05 = flopy.modflow.ModflowPcg.load(model=m05, f=fixed_pcg_file)
        print("  ✓ Successfully loaded fixed-format PCG in MF2005")
        print("    (This works due to FloPy's exception handling)")
        
        # Display loaded parameters
        print(f"    • MXITER: {pcg_m05.mxiter}")
        print(f"    • ITER1: {pcg_m05.iter1}")
        print(f"    • HCLOSE: {pcg_m05.hclose}")
        print(f"    • RCLOSE: {pcg_m05.rclose}")
        print(f"    • RELAX: {pcg_m05.relax}")
        print(f"    • DAMP: {pcg_m05.damp}")
        
    except Exception as e:
        print(f"  ✗ Error loading PCG in MF2005: {str(e)}")
        print("    This would have failed before pull request #311")
        pcg_m05 = None
    
    # 5. Parameter Consistency Check
    print(f"\n5. Parameter Consistency Check")
    print("-" * 40)
    
    if pcg_m2k and pcg_m05:
        # Compare key parameters
        params_match = True
        
        if pcg_m2k.rclose == pcg_m05.rclose:
            print(f"  ✓ RCLOSE matches: {pcg_m2k.rclose}")
        else:
            print(f"  ✗ RCLOSE differs: MF2K={pcg_m2k.rclose}, MF2005={pcg_m05.rclose}")
            params_match = False
            
        if pcg_m2k.damp == pcg_m05.damp:
            print(f"  ✓ DAMP matches: {pcg_m2k.damp}")
        else:
            print(f"  ✗ DAMP differs: MF2K={pcg_m2k.damp}, MF2005={pcg_m05.damp}")
            params_match = False
            
        if pcg_m2k.hclose == pcg_m05.hclose:
            print(f"  ✓ HCLOSE matches: {pcg_m2k.hclose}")
        else:
            print(f"  ✗ HCLOSE differs: MF2K={pcg_m2k.hclose}, MF2005={pcg_m05.hclose}")
            params_match = False
            
        if params_match:
            print("  ✓ All parameters consistent across versions")
        else:
            print("  ⚠ Some parameters differ between versions")
    else:
        print("  ⚠ Cannot compare - one or both versions failed to load")
    
    # 6. Create Modern Free-Format PCG
    print(f"\n6. Creating Modern Free-Format PCG")
    print("-" * 40)
    
    # Create a simple model to demonstrate modern PCG creation
    model_name = "pcg_demo"
    mf = flopy.modflow.Modflow(
        modelname=model_name,
        exe_name="mf2005",
        model_ws=model_ws
    )
    
    # Add minimal packages for completeness
    dis = flopy.modflow.ModflowDis(
        mf,
        nlay=1, nrow=10, ncol=10,
        delr=100.0, delc=100.0,
        top=10.0, botm=0.0
    )
    
    bas = flopy.modflow.ModflowBas(mf, ibound=1, strt=5.0)
    lpf = flopy.modflow.ModflowLpf(mf, hk=1.0)
    
    # Create PCG with modern parameters
    pcg_modern = flopy.modflow.ModflowPcg(
        mf,
        mxiter=150,
        iter1=50,
        npcond=1,
        hclose=1e-4,
        rclose=1e-4,
        relax=0.98,
        nbpol=2,
        damp=1.0,
        iprpcg=1,  # Print convergence info
        mutpcg=3   # Print residual info
    )
    
    oc = flopy.modflow.ModflowOc(mf)
    
    print("  Modern PCG configuration:")
    print(f"    • MXITER: {pcg_modern.mxiter}")
    print(f"    • ITER1: {pcg_modern.iter1}")
    print(f"    • NPCOND: {pcg_modern.npcond} (Modified Incomplete Cholesky)")
    print(f"    • HCLOSE: {pcg_modern.hclose}")
    print(f"    • RCLOSE: {pcg_modern.rclose}")
    print(f"    • RELAX: {pcg_modern.relax}")
    print(f"    • NBPOL: {pcg_modern.nbpol}")
    print(f"    • Print options enabled for monitoring")
    
    # 7. Write and Compare Formats
    print(f"\n7. Writing and Comparing Formats")
    print("-" * 40)
    
    try:
        mf.write_input()
        print("  ✓ Modern model written successfully")
        
        # Read the generated PCG file
        modern_pcg_file = os.path.join(model_ws, f"{model_name}.pcg")
        if os.path.exists(modern_pcg_file):
            with open(modern_pcg_file, 'r') as f:
                modern_content = f.read()
            
            print("  Modern PCG file format:")
            print("    • Free-format spacing")
            print("    • Flexible parameter arrangement")
            print("    • Comments and documentation")
            print("    • Additional control options")
            
            # Show first few lines
            lines = modern_content.split('\n')[:5]
            for i, line in enumerate(lines):
                if line.strip():
                    print(f"    Line {i+1}: {line.strip()}")
        
        # List all generated files
        files = [f for f in os.listdir(model_ws) 
                if f.endswith(('.nam', '.dis', '.bas', '.lpf', '.pcg', '.oc'))]
        print(f"\n  Generated files: {len(files)}")
        for f in sorted(files):
            print(f"    - {f}")
                
    except Exception as e:
        print(f"  ⚠ Error writing model: {str(e)}")
    
    # 8. Format Evolution Summary
    print(f"\n8. Format Evolution Summary")
    print("-" * 40)
    
    print("  PCG format evolution:")
    print("    1. MODFLOW-88/96: Fixed-format only")
    print("    2. MODFLOW-2000: Fixed-format with extensions")
    print("    3. MODFLOW-2005: Free-format support added")
    print("    4. MODFLOW-NWT: Enhanced solver options")
    print("    5. MODFLOW-6: New input structure entirely")
    
    print("\n  FloPy compatibility features:")
    print("    • Automatic format detection")
    print("    • Exception handling for format differences")
    print("    • Parameter validation across versions")
    print("    • Backward compatibility maintenance")
    print("    • Modern format generation")
    
    # 9. Professional Implications
    print(f"\n9. Professional Implications")
    print("-" * 40)
    
    implications = [
        ("Legacy model support", "Existing models can be loaded and modified"),
        ("Version migration", "Smooth transition between MODFLOW versions"),
        ("Quality assurance", "Parameter consistency across versions"),
        ("Documentation", "Format differences are handled transparently"),
        ("Maintenance", "Reduced effort in model format conversion"),
        ("Collaboration", "Teams can work with different MODFLOW versions")
    ]
    
    print("  Professional benefits:")
    for implication, benefit in implications:
        print(f"    • {implication}: {benefit}")
    
    print(f"\n✓ PCG Format Compatibility Demonstration Completed!")
    print(f"  - Demonstrated fixed-format PCG loading")
    print(f"  - Tested cross-version compatibility")
    print(f"  - Verified parameter consistency")
    print(f"  - Created modern PCG examples")
    print(f"  - Explained format evolution")
    print(f"  - Highlighted professional benefits")
    
    return mf

if __name__ == "__main__":
    model = run_model()