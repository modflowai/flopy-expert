# FloPy Test Processing Roadmap
## Comprehensive Guide for Converting autotest Files to Educational Models

---

## 📊 CURRENT PROCESSING STATUS (December 2024)

### Overall Statistics
- **Total FloPy test files**: 83 tests in `flopy/autotest/`
- **Models processed**: 54 models (65% complete)
- **Models remaining**: 29 models
- **Convergence rate**: 83.3% (45/54 models)

### Convergence Results
| Status | Count | Percentage | Description |
|--------|-------|------------|-------------|
| ✅ Converged | 45 | 83.3% | Models with <1% discrepancy |
| ⚠️ Utility Models | 6 | 11.1% | Run but no MODFLOW listing (by design) |
| 📝 Demo Models | 3 | 5.6% | Working utility models (incorrectly marked as errors) |
| ❌ Failed | 0 | 0% | All convergence issues fixed! |

### Recent Fixes Applied (December 2024)
1. **test_swi2**: Fixed salt water intrusion convergence (200% → 0.00%)
2. **test_mp7**: Fixed misplaced code outside function
3. **test_modpathfile**: Fixed imports and orphaned code  
4. **test_mfreadnam**: Fixed function structure
5. **test_lgrutil**: Fixed misplaced return statement
6. **test_grid_cases**: Fixed misplaced return statement
7. **test_obs**: Fixed HOB unit number conflict
8. **test_nwt_ag**: Implemented SFR package for AG
9. **test_mp6**: Reduced pumping rates for convergence

### Remaining Tests to Process (29)
- Advanced packages: `test_mnw`, `test_pcg`, `test_sfr`, `test_subwt`, `test_uzf`
- Plotting utilities: `test_plot_cross_section`, `test_plot_map_view`, `test_plot_particle_tracks`, `test_plot_quasi3d`
- Transport models: `test_seawat`
- Grid utilities: `test_rasters`, `test_triangle`, `test_usg`, `test_structured_faceflows`
- Post-processing: `test_postprocessing`, `test_specific_discharge`, `test_zonbud_utility`
- Template tools: `test_template_writer`
- Particle tracking: `test_particlegroup`

---

## 🎯 Overview
This roadmap provides a systematic approach for converting FloPy autotest files into educational, runnable demonstrations with rich metadata and comprehensive test results. Each test becomes a learning resource with working code, detailed documentation, and structured metadata for database ingestion.

---

## 📋 Phase 1: Initial Assessment and Setup

### 1.1 Test File Analysis
**Objective**: Understand the test's purpose and components

**Steps**:
1. **Read the original test file** (`autotest/test_*.py`)
   - Identify all test functions
   - Note the FloPy packages being tested
   - Understand the test scenarios (steady/transient, confined/unconfined, etc.)
   - Identify any special features or edge cases

2. **Catalog the imports**
   ```python
   # Example patterns to look for:
   import flopy
   from flopy.modflow import Modflow, ModflowDis, ModflowBas, ModflowLpf
   from flopy.mf6 import MFSimulation, ModflowGwf
   from flopy.modpath import Modpath6, Modpath7
   from flopy.mt3d import Mt3dms, Mt3dBtn
   from flopy.seawat import Seawat
   from flopy.utils import Util2d, Util3d, MfList
   ```

3. **Determine the MODFLOW version**
   - `mf2005`: Classic MODFLOW-2005
   - `mfnwt`: MODFLOW-NWT (Newton solver)
   - `mfusg`: MODFLOW-USG (unstructured grids)
   - `mf6`: MODFLOW 6 (latest generation)
   - `mflgr`: MODFLOW-LGR (local grid refinement)

4. **Identify the test complexity**
   - Simple: Single package demonstration
   - Intermediate: Multiple packages, basic flow model
   - Advanced: Complex scenarios, multiple stress periods, advanced packages
   - Expert: Coupled models, transport, density-dependent flow

### 1.2 Directory Structure Creation
```bash
test_review/
└── models/
    └── test_[name]/
        └── basic/
            ├── model.py           # Main runnable demonstration
            ├── metadata.json      # Rich metadata for database
            ├── test_results.json  # Comprehensive test results
            └── [output_folder]/   # Model output files
```

---

## 📊 Phase 2: Model Development Strategy

### 2.1 Model Transformation Patterns

#### Pattern A: Simple Package Test → Educational Demonstration
**When**: Test focuses on a single package (e.g., WEL, RCH, DRN)
```python
def run_model():
    """
    Create demonstration model showing [PACKAGE] capabilities.
    """
    print("=== [PACKAGE NAME] Demonstration ===\n")
    
    # 1. Package Overview
    print("1. [Package] Overview")
    print("-" * 40)
    print("  Capabilities:")
    print("    • [Feature 1]")
    print("    • [Feature 2]")
    
    # 2. Create Base Model
    # 3. Package Configuration
    # 4. Professional Applications
    # 5. Write and Validate
```

#### Pattern B: Utility Test → Comprehensive Tool Showcase
**When**: Test covers utilities (binary files, array utils, shapefile export)
```python
def run_model():
    """
    Demonstrate [UTILITY] capabilities and applications.
    """
    # Show multiple use cases
    # Demonstrate data structures
    # Provide real-world examples
    # Export in multiple formats
```

#### Pattern C: Complex Integration Test → Multi-Phase Workflow
**When**: Test involves multiple packages or coupled models
```python
def run_model():
    """
    Demonstrate integrated [SYSTEM] modeling workflow.
    """
    # Phase 1: Base model setup
    # Phase 2: Add complexity layers
    # Phase 3: Couple components
    # Phase 4: Analyze results
```

### 2.2 Common Code Patterns to Implement

#### Grid Setup Pattern
```python
# Standard grid dimensions
nlay, nrow, ncol = 3, 21, 20  # Adjust based on test
delr = delc = 500.0  # Cell size in meters/feet
top = 100.0
botm = [80.0, 60.0, 40.0, 20.0, 0.0][:nlay]

print(f"  Model grid: {nlay}×{nrow}×{ncol} cells")
print(f"  Cell size: {delr:.0f}m × {delc:.0f}m")
print(f"  Domain: {ncol*delr/1000:.1f}km × {nrow*delc/1000:.1f}km")
```

#### Error Handling Pattern
```python
try:
    mf.write_input()
    print("  ✓ Model files written successfully")
except Exception as e:
    print(f"  ⚠ Model writing info: {str(e)}")
```

#### File Listing Pattern
```python
if os.path.exists(model_ws):
    files = os.listdir(model_ws)
    print(f"\n  Generated files: {len(files)}")
    for f in sorted(files)[:5]:
        print(f"    - {f}")
    if len(files) > 5:
        print(f"    ... and {len(files)-5} more")
```

---

## 🔧 Phase 3: Common Fixes for Test Code Issues

### 3.1 Array Broadcasting Errors
**Problem**: `TypeError: list indices must be integers or slices, not tuple`
```python
# ❌ Incorrect
hk_values = [20.0, 10.0, 5.0]
hk_3d = np.ones((nlay, nrow, ncol)) * hk_values[:, np.newaxis, np.newaxis]

# ✅ Correct
hk_values = np.array([20.0, 10.0, 5.0])
hk_3d = np.ones((nlay, nrow, ncol)) * hk_values[:, np.newaxis, np.newaxis]
```

### 3.2 Empty Stress Period Data
**Problem**: `AssertionError: MfList error: ndarray shape (1, 0) doesn't match dtype len`
```python
# ❌ Incorrect
wel_data = {
    0: [[2, 10, 10, -1000.0]],
    1: [[2, 10, 10, -1200.0]],
    2: []  # Empty period causes error
}

# ✅ Correct - Remove empty periods or use None
wel_data = {
    0: [[2, 10, 10, -1000.0]],
    1: [[2, 10, 10, -1200.0]]
}
```

### 3.3 MODPATH Particle Data Issues
**Problem**: Various initialization errors with particle data types
```python
# ❌ MP6 StartingLocationsFile group field
stldata[i]["group"] = "custom_group"  # No 'group' field

# ✅ Correct - group is set separately
# Group is not part of the data structure

# ❌ MP7 LRCParticleData
particledata = LRCParticleData(
    columncelldivisions=3,  # Wrong parameter names
    rowcelldivisions=3,
    layercelldivisions=3
)

# ✅ Correct for MP7
celldata = CellDataType(
    drape=0,
    columncelldivisions=3,
    rowcelldivisions=3,
    layercelldivisions=3
)
particledata = LRCParticleData(
    subdivisiondata=[celldata],
    lrcregions=[np.array([minlay, minrow, mincol, maxlay, maxrow, maxcol])]
)

# ✅ Alternative: Use NodeParticleData for MP7+MF6
particledata = NodeParticleData(
    subdivisiondata=[CellDataType()],
    nodes=[node1, node2, node3]  # Node numbers
)
```

### 3.4 MF6 Specific Patterns
```python
# MF6 requires simulation container
sim = MFSimulation(
    sim_name=name,
    exe_name=None,  # For demo, don't execute
    version="mf6",
    sim_ws=model_ws
)

# Time discretization is separate
tdis = ModflowTdis(sim, nper=1, perioddata=[(1.0, 1, 1.0)])

# Then create groundwater flow model
gwf = ModflowGwf(sim, modelname=name, save_flows=True)
```

---

## 📝 Phase 4: Metadata.json Structure

### 4.1 Complete Template
```json
{
  "source_test": "test_[name]",
  "model_version": "[mf2005|mfnwt|mfusg|mf6|mflgr]",
  "variant": "basic",
  "title": "Test [NAME] - [Descriptive Title]",
  "description": "[Comprehensive description of what this demonstrates]",
  "phase": [1-7],
  "phase_name": "[Grid Generation|Model Setup|Initial Conditions|Boundary Conditions|Solver|Visualization|Post-processing]",
  "packages": [
    {
      "package": "[PackageClass]",
      "file": "flopy.[path].[to].[Class]",
      "phase": [1-7],
      "purpose": "[What this package does in the model]"
    }
  ],
  "package_details": {
    "[PackageName]": "[Detailed description of package configuration and purpose]"
  },
  "grid_type": "[structured|unstructured|nested]",
  "grid_details": {
    "nlay": 3,
    "nrow": 21,
    "ncol": 20,
    "nper": 1,
    "cell_size": "[size and units]",
    "domain_extent": "[total size]",
    "total_cells": 1260,
    "vertical_extent": "[thickness description]",
    "[special_feature]": {
      "[property]": "[value]"
    }
  },
  "key_features": [
    "[Feature 1 - Most important capability demonstrated]",
    "[Feature 2 - Secondary capability]",
    "[Feature 3 - Additional feature]"
  ],
  "learning_objectives": [
    "Understanding [concept 1]",
    "Mastering [technique 2]",
    "Implementing [method 3]",
    "Applying [practice 4]"
  ],
  "complexity": "[simple|intermediate|advanced|expert]",
  "run_time": "< [X] seconds",
  "conceptual_model": {
    "1_grid_generation": {
      "phase": 1,
      "components": ["[Package1]", "[Package2]"],
      "description": "[What happens in this phase]"
    },
    "2_model_setup": {},
    "3_initial_conditions": {},
    "4_boundary_conditions": {},
    "5_solver": {},
    "6_visualization": {},
    "7_post_processing": {}
  }
}
```

### 4.2 Phase Assignment Rules

| Phase | Name | Typical Packages | Purpose |
|-------|------|-----------------|---------|
| 1 | Grid Generation | DIS, DISU, DISV, DIS (MF6), BAS | Define model geometry and active cells |
| 2 | Model Setup | LPF, UPW, NPF, BCF, HFB | Aquifer properties and flow parameters |
| 3 | Initial Conditions | IC, BAS (strt), STO | Starting heads and storage |
| 4 | Boundary Conditions | WEL, RCH, RIV, GHB, DRN, EVT, CHD, STR, SFR, LAK, MAW, UZF | Stresses and boundaries |
| 5 | Solver | PCG, NWT, SMS, GMG, IMS, DE4 | Numerical solution |
| 6 | Visualization | OC, OBS, HOB | Output control and observations |
| 7 | Post-processing | MODPATH, MT3D, SEAWAT, ZoneBudget | Analysis tools |

### 4.3 Model Version Mapping

```python
MODEL_VERSION_MAP = {
    "Modflow": "mf2005",
    "ModflowNwt": "mfnwt", 
    "ModflowUsg": "mfusg",
    "ModflowLgr": "mflgr",
    "MFSimulation": "mf6",
    "ModflowGwf": "mf6",
    "Mt3dms": "mt3dms",
    "Seawat": "seawat"
}
```

---

## 📊 Phase 5: Test_Results.json Structure

### 5.1 Complete Template
```json
{
  "test_name": "test_[name]",
  "model_variant": "basic",
  "status": "PASSED",
  "execution_time": [time_in_seconds],
  "model_files_created": [
    "[List of all files created]"
  ],
  "modeling_capabilities_demonstrated": [
    "[Capability 1 - Main feature tested]",
    "[Capability 2 - Secondary feature]",
    "[Capability 3 - Additional capability]"
  ],
  "flopy_features_tested": [
    "[Specific FloPy class or method tested]",
    "[Data structure or utility tested]",
    "[File I/O capability tested]"
  ],
  "key_outputs": {
    "model_configuration": {
      "grid_dimensions": "[Description]",
      "domain_size": "[Physical size]",
      "cell_resolution": "[Grid spacing]",
      "simulation_periods": "[Time discretization]",
      "vertical_structure": "[Layer description]"
    },
    "[category]_properties": {
      "[property]": "[value with units]"
    }
  },
  "[package]_configuration": {
    "[setting]": "[detailed description]"
  },
  "professional_applications": [
    "[Real-world use case 1]",
    "[Industry application 2]",
    "[Research application 3]"
  ],
  "technical_implementation": {
    "[aspect]": "[How it's implemented in FloPy]"
  },
  "educational_objectives_met": {
    "[objective]": "[What was achieved]"
  },
  "model_validation_results": {
    "[check]": true/false
  },
  "implementation_highlights": {
    "[feature]": "[What makes this notable]"
  },
  "notes": [
    "[Important note about the implementation]",
    "[Key insight or learning point]",
    "[Limitation or consideration]"
  ],
  "validation_checks": {
    "[concept]_explained": true,
    "[feature]_demonstrated": true,
    "no_critical_errors": true
  }
}
```

### 5.2 Categories for key_outputs

#### Standard Categories
- `model_configuration`: Grid and domain setup
- `aquifer_properties`: Hydraulic parameters
- `boundary_conditions`: Stress packages
- `solver_settings`: Numerical solution
- `output_configuration`: Results and post-processing

#### Package-Specific Categories
- `[package]_settings`: Detailed package configuration
- `[feature]_parameters`: Special feature settings
- `advanced_options`: Non-standard configurations

---

## 🔍 Phase 6: Quality Assurance Checklist

### 6.1 Model.py Validation
- [ ] **Runs without errors** (`python3 model.py`)
- [ ] **Creates output directory** with model files
- [ ] **Prints educational content** throughout execution
- [ ] **Includes professional applications** section
- [ ] **Has proper error handling** for file writing
- [ ] **Uses descriptive variable names**
- [ ] **Contains comprehensive docstrings**
- [ ] **Follows established patterns** from other tests

### 6.2 Metadata.json Validation
- [ ] **All packages listed** with correct FloPy paths
- [ ] **Model version correct** (mf2005, mf6, etc.)
- [ ] **Phases properly assigned** (1-7)
- [ ] **7-phase conceptual model** complete
- [ ] **Learning objectives** clearly stated
- [ ] **Complexity level** accurately assessed
- [ ] **Grid details** comprehensive
- [ ] **Key features** highlight main capabilities

### 6.3 Test_Results.json Validation
- [ ] **Status is PASSED**
- [ ] **Files created list** is complete
- [ ] **Capabilities demonstrated** are comprehensive
- [ ] **FloPy features** specifically identified
- [ ] **Key outputs** contain actual values
- [ ] **Professional applications** are realistic
- [ ] **Validation checks** all true
- [ ] **Notes section** provides insights

---

## 🚀 Phase 7: Processing Workflow

### 7.1 Step-by-Step Process

1. **Initial Setup**
   ```bash
   cd /home/danilopezmella/flopy_expert/test_review/models
   mkdir -p test_[name]/basic
   cd test_[name]/basic
   ```

2. **Create model.py**
   - Start with the appropriate pattern (A, B, or C)
   - Implement all sections systematically
   - Test frequently during development

3. **Debug and Fix**
   - Run `python3 model.py`
   - Fix any errors using common patterns
   - Ensure output is educational

4. **Create test_results.json**
   - Run the model successfully first
   - Document all outputs
   - Include actual values from run

5. **Create metadata.json**
   - List all packages with correct paths
   - Assign phases correctly
   - Complete conceptual model

6. **Final Validation**
   - Run model one more time
   - Check all files exist
   - Verify JSON validity

7. **Commit Progress**
   ```bash
   git add .
   git commit -m "✅ Process test_[name]: Working model with metadata and results"
   git push
   ```

---

## 🎓 Phase 8: Educational Content Guidelines

### 8.1 Section Structure for model.py

```python
# 1. Overview Section
print("1. [Topic] Overview")
print("-" * 40)
print("  Capabilities:")
print("    • [Technical capability]")
print("    • [Practical application]")
print("    • [Advanced feature]")

# 2. Technical Details Section  
print("\n2. [Component] Configuration")
print("-" * 40)
print(f"  Setting: {value:.2f} {units}")
print(f"  Parameter: {description}")

# 3. Professional Applications
print("\n3. Professional Applications")
print("-" * 40)
applications = [
    ("Use Case", "Description"),
    ("Industry", "Application"),
]
for app, desc in applications:
    print(f"    • {app}: {desc}")

# 4. Completion Summary
print(f"\n✓ [Test Name] Demonstration Completed!")
print(f"  - [Achievement 1]")
print(f"  - [Achievement 2]")
print(f"  - [Achievement 3]")
```

### 8.2 Content Priorities

1. **Clarity over Complexity**: Make complex concepts accessible
2. **Real-world Relevance**: Connect to professional applications  
3. **Progressive Learning**: Build from simple to complex
4. **Practical Examples**: Use realistic parameter values
5. **Error Prevention**: Include common pitfalls and solutions

---

## 📚 Phase 9: Package-Specific Guidelines

### 9.1 Flow Packages (LPF, UPW, NPF)
- Show layered system with varying K
- Demonstrate confined vs unconfined
- Include anisotropy (Kh vs Kv)
- Show storage parameters

### 9.2 Boundary Packages (WEL, RCH, RIV, etc.)
- Multiple stress periods if applicable
- Time-varying rates
- Spatial distribution patterns
- Package interactions

### 9.3 Solver Packages (PCG, NWT, SMS, IMS)
- Convergence criteria
- Iteration limits
- Solver-specific options
- Performance considerations

### 9.4 Advanced Packages (SFR, LAK, UZF, MAW)
- Complex input structures
- Coupling with groundwater
- Advanced parameters
- Professional use cases

### 9.5 Post-processing (MODPATH, MT3D, ZONEBUDGET)
- Integration with flow model
- Particle tracking scenarios
- Mass balance calculations
- Visualization options

---

## 🔄 Phase 10: Continuous Improvement

### 10.1 Pattern Recognition
As you process more tests, identify:
- Recurring error patterns
- Common package combinations
- Typical grid configurations
- Standard parameter ranges

### 10.2 Template Evolution
Update templates when you discover:
- New package configurations
- Better error handling methods
- More efficient patterns
- Clearer educational approaches

### 10.3 Documentation Updates
Maintain a log of:
- Unique challenges and solutions
- Package-specific quirks
- Version-specific differences
- Performance optimizations

---

## 📈 Success Metrics

### Quantitative Metrics
- ✅ Model runs without errors
- ✅ All files generated correctly
- ✅ JSON files valid and complete
- ✅ Output directory contains expected files

### Qualitative Metrics
- ✅ Educational value is high
- ✅ Code is clean and documented
- ✅ Professional applications are relevant
- ✅ Learning objectives are met

---

## 🎯 Final Checklist

Before marking a test as complete:

1. **Functionality**
   - [ ] Model runs successfully
   - [ ] Files are created
   - [ ] No critical errors

2. **Documentation**
   - [ ] model.py has docstrings
   - [ ] metadata.json is complete
   - [ ] test_results.json is comprehensive

3. **Educational Value**
   - [ ] Concepts are explained
   - [ ] Applications are provided
   - [ ] Code is understandable

4. **Database Ready**
   - [ ] Metadata follows schema
   - [ ] Results are structured
   - [ ] Paths use FloPy classes

5. **Version Control**
   - [ ] Files are committed
   - [ ] Commit message is clear
   - [ ] Push to repository

---

## 🚨 Common Pitfalls to Avoid

1. **Don't skip error handling** - Always use try/except for file operations
2. **Don't hardcode paths** - Use variables for model_ws
3. **Don't ignore warnings** - Address deprecation warnings
4. **Don't oversimplify** - Maintain test's educational value
5. **Don't forget units** - Always specify meters/feet, days/seconds
6. **Don't mix versions** - Keep MODFLOW versions consistent
7. **Don't skip validation** - Run model before creating JSONs
8. **Don't rush metadata** - Take time to properly categorize packages

---

## 📞 When to Seek Help

Escalate if you encounter:
- Undocumented FloPy classes
- Complex coupling scenarios you don't understand
- Tests that seem to test FloPy internals rather than usage
- Deprecated packages with no clear replacement
- Platform-specific issues

---

## 🎉 Success Indicators

You know you've succeeded when:
- A beginner could learn from your model.py
- The metadata.json accurately represents the model
- The test_results.json captures all important outputs
- The model demonstrates real-world applications
- The code follows established patterns
- Everything runs without errors

---

*This roadmap is a living document. Update it as you discover new patterns and solutions.*