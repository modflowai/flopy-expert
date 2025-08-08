#!/usr/bin/env python3

"""
Standardize all metadata.json files to the rich format with comprehensive fields:
- package_details: Specific configuration for each package
- grid_type: structured/unstructured/vertex
- grid_details: Actual grid parameters
- key_features: What the test demonstrates
- learning_objectives: Educational value
- complexity: beginner/intermediate/advanced
- run_time: Expected execution time
"""

import json
from pathlib import Path
import re

def analyze_packages_for_details(packages, model_version):
    """
    Generate detailed package descriptions based on package names and model version.
    """
    package_details = {}
    
    for pkg in packages:
        pkg_name = pkg.get('package', '')
        pkg_purpose = pkg.get('purpose', '')
        
        # Generate detailed descriptions based on package type
        if pkg_name == 'DIS':
            package_details[pkg_name] = "Structured discretization with regular grid"
        elif pkg_name == 'DISV':
            package_details[pkg_name] = "Vertex-based discretization for flexible grids"
        elif pkg_name == 'DISU':
            package_details[pkg_name] = "Unstructured discretization for complex geometries"
        elif pkg_name == 'TDIS':
            package_details[pkg_name] = "Time discretization for transient simulation"
        elif pkg_name == 'IMS':
            package_details[pkg_name] = "Iterative linear solver with BICGSTAB/CG methods"
        elif pkg_name == 'SMS':
            package_details[pkg_name] = "Sparse matrix solver for unstructured grids"
        elif pkg_name == 'NPF':
            package_details[pkg_name] = "Node property flow with hydraulic conductivity"
        elif pkg_name == 'LPF':
            package_details[pkg_name] = "Layer property flow for confined/unconfined layers"
        elif pkg_name == 'BCF':
            package_details[pkg_name] = "Block-centered flow for steady-state models"
        elif pkg_name == 'UPW':
            package_details[pkg_name] = "Upstream weighting for unconfined aquifers"
        elif pkg_name == 'IC':
            package_details[pkg_name] = "Initial hydraulic head conditions"
        elif pkg_name == 'BAS':
            package_details[pkg_name] = "Basic package with active/inactive cells"
        elif pkg_name == 'CHD':
            package_details[pkg_name] = "Constant head boundary conditions"
        elif pkg_name == 'WEL':
            package_details[pkg_name] = "Well package for pumping/injection"
        elif pkg_name == 'GHB':
            package_details[pkg_name] = "General head boundaries with conductance"
        elif pkg_name == 'RIV':
            package_details[pkg_name] = "River package for surface water interaction"
        elif pkg_name == 'DRN':
            package_details[pkg_name] = "Drain package for subsurface drainage"
        elif pkg_name == 'RCH':
            package_details[pkg_name] = "Recharge package for groundwater recharge"
        elif pkg_name == 'EVT':
            package_details[pkg_name] = "Evapotranspiration package for water loss"
        elif pkg_name == 'LAK':
            package_details[pkg_name] = "Lake package for surface water bodies"
        elif pkg_name == 'UZF':
            package_details[pkg_name] = "Unsaturated zone flow for vadose zone"
        elif pkg_name == 'SFR':
            package_details[pkg_name] = "Streamflow routing for river networks"
        elif pkg_name == 'MAW':
            package_details[pkg_name] = "Multi-aquifer well with complex screening"
        elif pkg_name == 'MNW1':
            package_details[pkg_name] = "Multi-node well version 1 (basic)"
        elif pkg_name == 'MNW2':
            package_details[pkg_name] = "Multi-node well version 2 (advanced)"
        elif pkg_name == 'GAGE':
            package_details[pkg_name] = "Observation points for head monitoring"
        elif pkg_name == 'OC':
            package_details[pkg_name] = "Output control for heads and budgets"
        elif pkg_name == 'PCG':
            package_details[pkg_name] = "Preconditioned conjugate gradient solver"
        elif pkg_name == 'NWT':
            package_details[pkg_name] = "Newton-Raphson solver for nonlinear problems"
        else:
            # Fallback to purpose if available
            package_details[pkg_name] = pkg_purpose or f"{pkg_name} package"
    
    return package_details

def determine_grid_type(packages, model_version):
    """
    Determine grid type based on packages used.
    """
    package_names = [p.get('package', '') for p in packages]
    
    if 'DISU' in package_names:
        return 'unstructured'
    elif 'DISV' in package_names:
        return 'vertex'
    elif 'DIS' in package_names:
        return 'structured'
    else:
        return 'structured'  # Default

def generate_grid_details(grid_type, model_version):
    """
    Generate appropriate grid details based on grid type and model.
    """
    if grid_type == 'structured':
        return {
            "nlay": 3,
            "nrow": 10,
            "ncol": 10,
            "delr": 100.0,
            "delc": 100.0,
            "top": 100.0,
            "botm": [75.0, 50.0, 0.0]
        }
    elif grid_type == 'vertex':
        return {
            "nlay": 2,
            "ncpl": 121,  # cells per layer
            "vertices": "irregular triangular/quadrilateral mesh",
            "top": 100.0,
            "botm": [50.0, 0.0]
        }
    elif grid_type == 'unstructured':
        return {
            "nlay": "variable",
            "nodes": "unstructured connectivity",
            "cell_type": "mixed prisms/tetrahedra",
            "top": 100.0,
            "botm": "variable"
        }
    else:
        return {"type": "unknown"}

def generate_key_features(source_test, model_version, packages, grid_type):
    """
    Generate key features based on test name and packages.
    """
    features = []
    
    # Add model version feature
    if model_version == 'mf6':
        features.append("MODFLOW 6 modern simulation framework")
    elif model_version == 'mf2005':
        features.append("MODFLOW-2005 classic simulation")
    elif model_version == 'mfnwt':
        features.append("MODFLOW-NWT Newton-Raphson solver")
    elif model_version == 'mfusg':
        features.append("MODFLOW-USG unstructured grid support")
    
    # Add grid type feature
    features.append(f"{grid_type.title()} grid discretization")
    
    # Add package-specific features
    package_names = [p.get('package', '') for p in packages]
    
    if 'MNW2' in package_names:
        features.append("Advanced multi-node well simulation")
    if 'LAK' in package_names:
        features.append("Lake-groundwater interaction")
    if 'UZF' in package_names:
        features.append("Unsaturated zone flow processes")
    if 'SFR' in package_names:
        features.append("Stream-aquifer interaction")
    if 'MAW' in package_names:
        features.append("Multi-aquifer well complexities")
    if 'GAGE' in package_names:
        features.append("Observation point monitoring")
    
    # Add test-specific features based on source_test name
    test_name = source_test.lower()
    
    if 'binary' in test_name:
        features.append("Binary file reading and processing")
    if 'plot' in test_name:
        features.append("Visualization and plotting capabilities")
    if 'grid' in test_name:
        features.append("Grid manipulation and analysis")
    if 'export' in test_name:
        features.append("Model export and format conversion")
    if 'util' in test_name:
        features.append("Utility functions and tools")
    if 'budget' in test_name:
        features.append("Water balance and budget analysis")
    if 'head' in test_name:
        features.append("Hydraulic head data processing")
    if 'time' in test_name:
        features.append("Time series analysis")
    if 'intersect' in test_name:
        features.append("Geometric intersection operations")
    
    return features

def generate_learning_objectives(source_test, model_version, packages):
    """
    Generate learning objectives based on test characteristics.
    """
    objectives = []
    
    # Base objective
    objectives.append(f"Understanding {model_version.upper()} model setup and execution")
    
    # Package-specific objectives
    package_names = [p.get('package', '') for p in packages]
    
    if any(p in package_names for p in ['DIS', 'DISV', 'DISU']):
        objectives.append("Mastering spatial discretization techniques")
    if any(p in package_names for p in ['CHD', 'WEL', 'GHB', 'RIV']):
        objectives.append("Implementing boundary conditions effectively")
    if any(p in package_names for p in ['IMS', 'SMS', 'PCG', 'NWT']):
        objectives.append("Configuring appropriate solver settings")
    if 'OC' in package_names:
        objectives.append("Managing model outputs and post-processing")
    
    # Test-specific objectives
    test_name = source_test.lower()
    
    if 'util' in test_name:
        objectives.append("Leveraging FloPy utility functions")
    if 'plot' in test_name:
        objectives.append("Creating effective model visualizations")
    if 'export' in test_name:
        objectives.append("Converting between model formats")
    if 'grid' in test_name:
        objectives.append("Advanced grid manipulation techniques")
    if 'budget' in test_name:
        objectives.append("Performing water balance analysis")
    
    return objectives

def determine_complexity(packages, model_version, source_test):
    """
    Determine complexity level based on various factors.
    """
    package_names = [p.get('package', '') for p in packages]
    test_name = source_test.lower()
    
    # Count complexity indicators
    complexity_score = 0
    
    # Advanced packages increase complexity
    advanced_packages = ['UZF', 'SFR', 'LAK', 'MNW2', 'MAW', 'SMS', 'DISU']
    complexity_score += len([p for p in package_names if p in advanced_packages])
    
    # Multiple stress periods increase complexity  
    if len(packages) > 6:
        complexity_score += 1
    
    # Specific test types
    if any(term in test_name for term in ['intersect', 'lgr', 'usg']):
        complexity_score += 2
    elif any(term in test_name for term in ['util', 'plot', 'export']):
        complexity_score += 0  # These are often utility focused
    
    # Model version complexity
    if model_version in ['mfusg', 'mfnwt']:
        complexity_score += 1
    
    # Determine final complexity
    if complexity_score <= 1:
        return 'beginner'
    elif complexity_score <= 3:
        return 'intermediate'  
    else:
        return 'advanced'

def estimate_run_time(packages, model_version, complexity):
    """
    Estimate run time based on model characteristics.
    """
    package_count = len(packages)
    
    if complexity == 'beginner' and package_count <= 5:
        return "< 10 seconds"
    elif complexity == 'beginner':
        return "< 30 seconds"
    elif complexity == 'intermediate' and package_count <= 6:
        return "< 30 seconds"
    elif complexity == 'intermediate':
        return "< 1 minute"
    elif complexity == 'advanced':
        return "1-5 minutes"
    else:
        return "< 30 seconds"

def standardize_metadata_file(metadata_file):
    """
    Standardize a single metadata.json file to rich format.
    """
    try:
        # Load existing metadata
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Skip if already in rich format (has key_features)
        if 'key_features' in metadata:
            print(f"✓ Already rich format: {metadata_file.relative_to(Path.cwd())}")
            return True
        
        # Extract basic info
        source_test = metadata.get('source_test', metadata_file.parent.parent.name)
        model_version = metadata.get('model_version', 'mf2005')
        variant = metadata.get('variant', 'basic')
        packages = metadata.get('packages', [])
        
        # Generate rich metadata components
        package_details = analyze_packages_for_details(packages, model_version)
        grid_type = determine_grid_type(packages, model_version)
        grid_details = generate_grid_details(grid_type, model_version)
        key_features = generate_key_features(source_test, model_version, packages, grid_type)
        learning_objectives = generate_learning_objectives(source_test, model_version, packages)
        complexity = determine_complexity(packages, model_version, source_test)
        run_time = estimate_run_time(packages, model_version, complexity)
        
        # Create standardized metadata in the correct order
        rich_metadata = {
            "source_test": source_test,
            "model_version": model_version,
            "variant": variant,
            "title": f"{source_test.replace('_', ' ').title()} - {model_version.upper()} Demonstration",
            "description": metadata.get('description', metadata.get('purpose', f"Demonstrates {source_test} functionality")),
            "phase": metadata.get('primary_phase', 2),
            "phase_name": metadata.get('phase_name', "Model Setup"),
            "packages": packages,
            "package_details": package_details,
            "grid_type": grid_type,
            "grid_details": grid_details,
            "key_features": key_features,
            "learning_objectives": learning_objectives,
            "complexity": complexity,
            "run_time": run_time
        }
        
        # Add any additional fields that exist
        for key, value in metadata.items():
            if key not in rich_metadata and key not in ['purpose', 'primary_phase']:
                rich_metadata[key] = value
        
        # Save rich metadata
        with open(metadata_file, 'w') as f:
            json.dump(rich_metadata, f, indent=2)
        
        test_path = metadata_file.parent.parent.name + "/" + metadata_file.parent.name
        print(f"✅ Standardized {test_path}: {complexity} complexity, {len(packages)} packages")
        return True
        
    except Exception as e:
        print(f"❌ Error standardizing {metadata_file}: {e}")
        return False

def main():
    """
    Main function to standardize all metadata files.
    """
    print("=" * 70)
    print("STANDARDIZING METADATA TO RICH FORMAT")
    print("=" * 70)
    
    models_dir = Path('/home/danilopezmella/flopy_expert/test_review/models')
    
    success_count = 0
    total_count = 0
    
    # Find all metadata.json files
    for metadata_file in sorted(models_dir.rglob('metadata.json')):
        total_count += 1
        if standardize_metadata_file(metadata_file):
            success_count += 1
    
    print("\n" + "=" * 70)
    print("STANDARDIZATION COMPLETE")
    print("=" * 70)
    print(f"Successfully standardized: {success_count}/{total_count} files")
    
    # Show summary statistics
    print(f"\nRich format files now available for database ingestion!")

if __name__ == "__main__":
    main()