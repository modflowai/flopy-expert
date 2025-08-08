#!/usr/bin/env python3
"""
Interactive CLI for reviewing FloPy tests and generating standalone models.
Each test can produce multiple working model variants organized by conceptual phases.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
import ast
import re

class TestReviewCLI:
    def __init__(self):
        self.test_dir = Path("/home/danilopezmella/flopy_expert/flopy/autotest")
        self.review_dir = Path("test_review")
        self.prompts_dir = self.review_dir / "prompts"
        self.results_dir = self.review_dir / "results"
        self.models_dir = self.review_dir / "models"
        self.status_file = self.review_dir / "status.json"
        
        # Create directories
        for dir in [self.review_dir, self.prompts_dir, self.results_dir, self.models_dir]:
            dir.mkdir(exist_ok=True)
        
        # 7-phase conceptual structure
        self.phases = {
            1: "Discretization",
            2: "Properties", 
            3: "Initial_Conditions",
            4: "Boundary_Conditions",
            5: "Solver_Configuration",
            6: "Observations",
            7: "Post_processing"
        }
        
        self.load_tests()
        self.load_status()
    
    def load_tests(self):
        """Load all test files from autotest directory"""
        self.test_files = sorted([
            f for f in self.test_dir.glob("test_*.py")
            if f.name not in ["test_conftest.py", "__init__.py"]
        ])
        print(f"Found {len(self.test_files)} test files")
    
    def load_status(self):
        """Load progress from previous session"""
        if self.status_file.exists():
            with open(self.status_file) as f:
                self.status = json.load(f)
        else:
            self.status = {
                "current_index": 0,
                "total_tests": len(self.test_files),
                "completed": [],
                "skipped": [],
                "models_created": {}
            }
    
    def save_status(self):
        """Save current progress"""
        with open(self.status_file, 'w') as f:
            json.dump(self.status, f, indent=2)
    
    def extract_model_code(self, test_file: Path) -> Dict:
        """Extract FloPy model building code from test file"""
        with open(test_file) as f:
            content = f.read()
        
        # Parse AST to find simulation/model creation functions
        tree = ast.parse(content)
        
        model_functions = []
        imports = []
        
        for node in ast.walk(tree):
            # Find imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if 'flopy' in alias.name:
                        imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and 'flopy' in node.module:
                    names = [n.name for n in node.names]
                    imports.append(f"from {node.module} import {', '.join(names)}")
            
            # Find functions that create simulations
            elif isinstance(node, ast.FunctionDef):
                if any(x in node.name.lower() for x in ['sim', 'model', 'build', 'create']):
                    # Get function source
                    start_line = node.lineno - 1
                    end_line = node.end_lineno
                    lines = content.split('\n')[start_line:end_line]
                    func_code = '\n'.join(lines)
                    
                    # Analyze what packages are used
                    packages_used = self.analyze_packages_in_code(func_code)
                    
                    model_functions.append({
                        'name': node.name,
                        'code': func_code,
                        'packages': packages_used
                    })
        
        return {
            'test_name': test_file.name,
            'imports': imports,
            'model_functions': model_functions
        }
    
    def analyze_packages_in_code(self, code: str) -> Dict[int, List[str]]:
        """Categorize packages by conceptual phase"""
        phase_packages = {phase: [] for phase in range(1, 8)}
        
        # Phase 1: Discretization
        if any(x in code for x in ['ModflowGwfdis', 'ModflowGwfdisv', 'ModflowGwfdisu', 'ModflowTdis']):
            phase_packages[1].extend(re.findall(r'Modflow\w*dis\w*', code))
        
        # Phase 2: Properties
        if any(x in code for x in ['ModflowGwfnpf', 'ModflowGwfsto', 'hydraulic', 'porosity']):
            phase_packages[2].extend(re.findall(r'ModflowGwf(?:npf|sto)', code))
        
        # Phase 3: Initial Conditions
        if 'ModflowGwfic' in code:
            phase_packages[3].append('ModflowGwfic')
        
        # Phase 4: Boundary Conditions
        bc_patterns = ['chd', 'wel', 'rch', 'drn', 'riv', 'ghb', 'lak', 'sfr', 'maw', 'uzf']
        for bc in bc_patterns:
            if f'ModflowGwf{bc}' in code.lower():
                phase_packages[4].append(f'ModflowGwf{bc}')
        
        # Phase 5: Solver
        if any(x in code for x in ['ModflowIms', 'ModflowSms', 'solver']):
            phase_packages[5].extend(re.findall(r'Modflow(?:Ims|Sms)', code))
        
        # Phase 6: Observations
        if 'ModflowGwfobs' in code or 'observation' in code.lower():
            phase_packages[6].append('ModflowGwfobs')
        
        # Phase 7: Post-processing
        if any(x in code for x in ['HeadFile', 'CellBudgetFile', 'plot', 'output']):
            phase_packages[7].extend(re.findall(r'(?:HeadFile|CellBudgetFile)', code))
        
        # Remove empty phases
        return {k: v for k, v in phase_packages.items() if v}
    
    def create_standalone_model(self, test_file: Path, model_func: Dict, variant: str = "basic") -> str:
        """Generate a standalone, runnable model from test code"""
        
        # Extract the core model building logic
        func_code = model_func['code']
        
        # Create standalone script
        standalone = f'''#!/usr/bin/env python3
"""
Standalone FloPy model extracted from {test_file.name}
Variant: {variant}
Demonstrates: {', '.join(f"Phase {p}: {self.phases[p]}" for p in model_func['packages'].keys())}
"""

import flopy
import numpy as np
from pathlib import Path
import sys
sys.path.append('/home/danilopezmella/flopy_expert/test_review')
from mf6_config import get_mf6_exe

def build_model(ws="./model_output"):
    """Build the model with clear phase organization"""
    
    # Ensure workspace exists
    Path(ws).mkdir(exist_ok=True)
    
    # === PHASE 1: DISCRETIZATION ===
    sim = flopy.mf6.MFSimulation(sim_name="model", sim_ws=ws, exe_name=get_mf6_exe())
    tdis = flopy.mf6.ModflowTdis(sim, nper=1, perioddata=[(1.0, 1, 1.0)])
    
    # === PHASE 5: SOLVER CONFIGURATION ===
    ims = flopy.mf6.ModflowIms(sim, print_option="ALL")
    
    # Create groundwater flow model
    gwf = flopy.mf6.ModflowGwf(sim, modelname="model", save_flows=True)
    
'''
        
        # Add discretization based on variant
        if variant == "dis":
            standalone += '''    # Structured grid (DIS)
    dis = flopy.mf6.ModflowGwfdis(gwf, nlay=1, nrow=10, ncol=10)
'''
        elif variant == "disv":
            standalone += '''    # Vertex grid (DISV) 
    from flopy.utils.gridutil import get_disv_kwargs
    dis = flopy.mf6.ModflowGwfdisv(gwf, **get_disv_kwargs(1, 10, 10, 1.0, 1.0, 10.0))
'''
        elif variant == "disu":
            standalone += '''    # Unstructured grid (DISU)
    # Simplified DISU setup for demonstration
    nodes = 100
    iac = [4] * nodes  # 4 connections per node (simplified)
    # [Additional DISU setup would go here]
'''
        
        # Continue with other phases
        standalone += '''
    # === PHASE 2: PROPERTIES ===
    npf = flopy.mf6.ModflowGwfnpf(gwf, save_specific_discharge=True, 
                                  icelltype=1, k=10.0)
    
    # === PHASE 3: INITIAL CONDITIONS ===
    ic = flopy.mf6.ModflowGwfic(gwf, strt=1.0)
    
    # === PHASE 4: BOUNDARY CONDITIONS ===
    # Constant head boundaries
    chd = flopy.mf6.ModflowGwfchd(gwf, 
                                   stress_period_data=[[(0, 0, 0), 1.0], 
                                                       [(0, 9, 9), 0.0]])
    
    # === PHASE 6: OBSERVATIONS (optional) ===
    # obs = flopy.mf6.ModflowGwfobs(gwf, ...)
    
    # === OUTPUT CONTROL ===
    oc = flopy.mf6.ModflowGwfoc(gwf,
                                budget_filerecord="model.bud",
                                head_filerecord="model.hds",
                                saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")])
    
    return sim, gwf

def run_model():
    """Run the model and basic post-processing"""
    
    # Build model
    sim, gwf = build_model()
    
    # Write and run
    sim.write_simulation()
    success, buff = sim.run_simulation()
    
    if not success:
        print("Model failed to converge")
        return None
    
    # === PHASE 7: POST-PROCESSING ===
    print("Model ran successfully!")
    
    # Read outputs
    head = gwf.output.head().get_data()
    print(f"Head range: {head.min():.2f} to {head.max():.2f}")
    
    # Budget
    bud = gwf.output.budget()
    print(f"\\nBudget records: {bud.get_unique_record_names()}")
    
    return sim, gwf

if __name__ == "__main__":
    run_model()
'''
        
        return standalone
    
    def create_prompt_template(self, test_file: Path) -> str:
        """Create Claude prompt template for analyzing test"""
        
        with open(test_file) as f:
            test_code = f.read()
        
        prompt = f'''# Analyze FloPy Test: {test_file.name}

## Test Code
```python
{test_code[:3000]}...  # Truncated for brevity
```

## Task: Extract Metadata AND Generate Standalone Model

Analyze this test and provide BOTH:
1. Metadata for semantic search database
2. Standalone, runnable FloPy model(s)

### Part 1: METADATA EXTRACTION

Extract the following for database/search:

1. **Test Analysis**:
   - `true_purpose`: What is this test ACTUALLY testing?
   - `is_useful_example`: Would this make a good example? (true/false)
   - `example_demonstrates`: One-line description of what it shows

2. **Documentation**:
   - `purpose`: Clear 1-2 sentence description for users
   - `key_concepts`: List of concepts demonstrated
   - `questions_answered`: 3-5 specific questions this example answers
   - `common_use_cases`: Real-world scenarios where this applies

3. **Classification**:
   - `primary_phase`: Which of the 7 phases is PRIMARY (1-7)
   - `secondary_phases`: Other phases involved
   - `modflow_version`: mf6/mf2005/mfnwt/mfusg/mt3d
   - `packages_used`: List all FloPy packages/modules used

4. **Search Metadata**:
   - `keywords`: 5-10 search terms
   - `embedding_string`: ~150 word description combining purpose + questions + concepts

### Part 2: STANDALONE MODEL GENERATION

Create runnable FloPy model(s):

1. **Model Requirements**:
   - Only create multiple models if test actually tests different discretizations
   - For example, test_binaryfile_reverse tests dis/disv/disu, so create 3 models
   - Most tests will only need 1 model

2. **Phase Organization** - Structure following the 7 phases:
   - Phase 1: Discretization (DIS/DISV/DISU, TDIS)
   - Phase 2: Properties (NPF, STO)
   - Phase 3: Initial Conditions (IC)
   - Phase 4: Boundary Conditions (CHD, WEL, etc.)
   - Phase 5: Solver Configuration (IMS)
   - Phase 6: Observations (optional)
   - Phase 7: Post-processing

3. **Code Quality**:
   - Remove all test assertions and pytest code
   - Add clear phase comments
   - Must be runnable standalone
   - Include basic verification

Return EXACTLY this JSON structure:
{{
  "metadata": {{
    "purpose": "Brief description of what this example demonstrates",
    "primary_phase": 1-7,
    "modflow_version": "mf6" or "mf2005", 
    "packages_used": ["list", "of", "packages"],
    "keywords": ["relevant", "keywords"]
  }},
  "models": [
    {{
      "name": "model_name",
      "description": "What this model demonstrates", 
      "code": "complete_python_code_here"
    }}
  ]
}}
'''
        
        return prompt
    
    def test_model(self, model_file: Path, work_dir: Path) -> Dict:
        """Test if the generated model runs successfully"""
        print(f"\n  Testing model: {model_file.name}")
        
        result = {
            "runs": False,
            "converges": False,
            "output_exists": False,
            "error": None,
            "outputs": []
        }
        
        try:
            # Run the model in its directory
            import subprocess
            process = subprocess.run(
                ["python3", model_file.name],  # Use just the filename, not full path
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            # Check if it ran without Python errors
            if process.returncode == 0:
                result["runs"] = True
                print("    ✓ Model runs without errors")
                
                # Check for MODFLOW output files
                # Search recursively in all subdirectories
                output_files = []
                for pattern in ["*.hds", "*.bud", "*.cbb", "*.cbc", "*.lst"]:
                    output_files.extend(work_dir.rglob(pattern))
                
                hds_files = [f for f in output_files if f.suffix in ['.hds']]
                bud_files = [f for f in output_files if f.suffix in ['.bud', '.cbc', '.cbb']]
                lst_files = [f for f in output_files if f.suffix in ['.lst']]
                
                if hds_files or bud_files or lst_files:
                    result["output_exists"] = True
                    result["outputs"] = [
                        str(f.name) for f in hds_files + bud_files + lst_files
                    ]
                    print(f"    ✓ Output files created: {', '.join(result['outputs'])}")
                
                # Check for convergence in output
                if "successfully" in process.stdout.lower() or "normal termination" in process.stdout.lower():
                    result["converges"] = True
                    print("    ✓ Model converged successfully")
                elif "failed" in process.stdout.lower() or "not converge" in process.stdout.lower():
                    print("    ✗ Model failed to converge")
                
                # Look for specific results in stdout
                if "head range" in process.stdout.lower():
                    # Extract head range if printed
                    import re
                    match = re.search(r'head range.*?([\d.-]+).*?to.*?([\d.-]+)', process.stdout.lower())
                    if match:
                        print(f"    ✓ Head range: {match.group(1)} to {match.group(2)}")
                
            else:
                result["error"] = process.stderr
                print(f"    ✗ Model failed with error")
                print(f"    Error: {process.stderr[:200]}...")
                
        except subprocess.TimeoutExpired:
            result["error"] = "Model execution timeout (>60s)"
            print(f"    ✗ Model timeout - took too long to run")
        except Exception as e:
            result["error"] = str(e)
            print(f"    ✗ Exception: {e}")
        
        # Save test results
        test_result_file = work_dir / "test_results.json"
        with open(test_result_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        return result
    
    def validate_all_models(self):
        """Validate all generated models"""
        print("\n" + "="*60)
        print("VALIDATING ALL GENERATED MODELS")
        print("="*60)
        
        results = {}
        models_path = self.models_dir
        
        for test_dir in models_path.iterdir():
            if test_dir.is_dir():
                print(f"\nTest: {test_dir.name}")
                test_results = {}
                
                for variant_dir in test_dir.iterdir():
                    if variant_dir.is_dir():
                        model_file = variant_dir / "model.py"
                        if model_file.exists():
                            result = self.test_model(model_file, variant_dir)
                            test_results[variant_dir.name] = result
                
                results[test_dir.name] = test_results
        
        # Summary
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        
        total = 0
        successful = 0
        
        for test_name, variants in results.items():
            for variant, result in variants.items():
                total += 1
                if result["runs"] and result["converges"]:
                    successful += 1
                    status = "✓ PASS"
                else:
                    status = "✗ FAIL"
                print(f"{status} {test_name}/{variant}")
        
        print(f"\nTotal: {successful}/{total} models run successfully")
        
        # Save validation report
        report_file = self.review_dir / "validation_report.json"
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nValidation report saved to: {report_file}")
        
        return results
    
    def analyze_with_claude(self, test_file: Path, auto_mode: bool = False):
        """Send test to Claude for analysis and model generation"""
        prompt_file = self.prompts_dir / f"{test_file.stem}.md"
        
        # Create or load prompt
        if not prompt_file.exists():
            prompt = self.create_prompt_template(test_file)
            prompt_file.write_text(prompt)
        else:
            prompt = prompt_file.read_text()
        
        if auto_mode:
            # Use Claude SDK directly
            print(f"\nAnalyzing {test_file.name} with Claude SDK...")
            result_data = self.call_claude_sdk(prompt)
            if result_data:
                result_file = self.results_dir / f"{test_file.stem}.json"
                with open(result_file, 'w') as f:
                    json.dump(result_data, f, indent=2)
                print(f"✓ Analysis complete, saved to {result_file.name}")
                return result_data
        else:
            # Manual mode - save prompt for copy/paste
            print(f"\nPrompt saved to: {prompt_file}")
            print("Please analyze with Claude Code SDK and paste result:")
            print("-" * 50)
            
            result = input("Paste JSON result (or 'skip'): ")
            
            if result.lower() != 'skip':
                try:
                    result_data = json.loads(result)
                    result_file = self.results_dir / f"{test_file.stem}.json"
                    with open(result_file, 'w') as f:
                        json.dump(result_data, f, indent=2)
                    return result_data
                except:
                    print("Invalid JSON")
                    return None
        return None
    
    def check_claude_cli(self) -> bool:
        """Check if Claude CLI is available"""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def batch_process(self, start_idx: int = None, count: int = 5):
        """Process multiple tests automatically"""
        if not self.check_claude_cli():
            print("Claude CLI not available. Install with: pip install anthropic")
            return
        
        if start_idx is None:
            start_idx = self.status['current_index']
        
        end_idx = min(start_idx + count, len(self.test_files))
        
        print(f"\n{'='*60}")
        print(f"BATCH PROCESSING: Tests {start_idx+1} to {end_idx}")
        print(f"{'='*60}")
        
        for idx in range(start_idx, end_idx):
            test_file = self.test_files[idx]
            
            # Skip if already processed
            if test_file.name in self.status['completed']:
                print(f"\n[{idx+1}/{len(self.test_files)}] {test_file.name} - Already completed ✓")
                continue
            
            print(f"\n[{idx+1}/{len(self.test_files)}] Processing {test_file.name}...")
            
            # Analyze with Claude
            result = self.analyze_with_claude(test_file, auto_mode=True)
            
            if result:
                # Generate model files
                self.generate_model_files(test_file, result)
                
                # Mark as completed
                self.status['completed'].append(test_file.name)
                if 'models' in result:
                    variants = [m.get('variant', 'basic') for m in result['models']]
                    self.status['models_created'][test_file.name] = variants
                
                self.save_status()
                print(f"✓ {test_file.name} processed successfully")
            else:
                print(f"✗ {test_file.name} failed to process")
        
        # Run validation on batch
        print(f"\n{'='*60}")
        print("Running validation on batch...")
        self.validate_all_models()
        
        print(f"\n{'='*60}")
        print(f"Batch processing complete!")
        print(f"Processed: {len(self.status['completed'])}/{len(self.test_files)} tests")
    
    def call_claude_sdk(self, prompt: str) -> Dict:
        """Call Claude SDK directly to analyze test"""
        try:
            # Use subprocess to call Claude CLI
            process = subprocess.run(
                ["claude", "--json"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if process.returncode == 0:
                # Parse Claude's response
                response = process.stdout
                
                # Extract JSON from response
                # Claude might return markdown with JSON code block
                import re
                json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Try to parse entire response as JSON
                    json_str = response
                
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    print(f"Failed to parse Claude response as JSON")
                    # Save raw response for debugging
                    debug_file = self.results_dir / f"debug_{Path(prompt[:20]).stem}.txt"
                    debug_file.write_text(response)
                    print(f"Raw response saved to {debug_file}")
                    return None
            else:
                print(f"Claude CLI error: {process.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print("Claude SDK timeout")
            return None
        except FileNotFoundError:
            print("Claude CLI not found. Please install: pip install claude-cli")
            return None
        except Exception as e:
            print(f"Error calling Claude SDK: {e}")
            return None
    
    def generate_model_files(self, test_file: Path, result_data: Dict):
        """Create actual model files from analysis results"""
        test_name = test_file.stem
        
        # Handle both list and dict formats for models
        models = result_data.get('models', [])
        
        # If models is a list of model objects
        if isinstance(models, list):
            for model in models:
                variant = model.get('variant', 'basic')
                variant_dir = self.models_dir / test_name / variant
                variant_dir.mkdir(parents=True, exist_ok=True)
                
                # Write model script
                model_file = variant_dir / "model.py"
                model_file.write_text(model['code'])
                model_file.chmod(0o755)
                
                # Write metadata
                meta_file = variant_dir / "metadata.json"
                metadata = result_data.get('metadata', {})
                with open(meta_file, 'w') as f:
                    json.dump({
                        'source_test': test_name,
                        'variant': variant,
                        'description': model.get('description', ''),
                        'primary_phase': metadata.get('classification', {}).get('primary_phase'),
                        'phase_name': metadata.get('classification', {}).get('phase_name'),
                        'purpose': metadata.get('documentation', {}).get('purpose'),
                        'packages': metadata.get('classification', {}).get('packages_used', [])
                    }, f, indent=2)
                
                print(f"Created model: {variant_dir}/model.py")
                
                # Test the model
                self.test_model(model_file, variant_dir)
                
        # If models is a dict with variant keys
        elif isinstance(models, dict):
            for variant, model_data in models.items():
                variant_dir = self.models_dir / test_name / variant
                variant_dir.mkdir(parents=True, exist_ok=True)
                
                # Write model script
                model_file = variant_dir / "model.py"
                model_file.write_text(model_data['code'])
                model_file.chmod(0o755)
                
                # Write metadata
                meta_file = variant_dir / "metadata.json"
                with open(meta_file, 'w') as f:
                    json.dump({
                        'source_test': test_name,
                        'variant': variant,
                        'phases': model_data.get('phases', []),
                        'purpose': model_data.get('purpose', ''),
                        'packages': model_data.get('packages', [])
                    }, f, indent=2)
                
                print(f"Created model: {variant_dir}/model.py")
                
                # Test the model
                self.test_model(model_file, variant_dir)
    
    def run_cli(self):
        """Main CLI loop"""
        while True:
            current_test = self.test_files[self.status['current_index']]
            
            print(f"\n{'='*60}")
            print(f"FloPy Test Review CLI")
            print(f"{'='*60}")
            print(f"[{self.status['current_index']+1}/{len(self.test_files)}] {current_test.name}")
            
            # Show extracted info
            extracted = self.extract_model_code(current_test)
            if extracted['model_functions']:
                print(f"\nFound {len(extracted['model_functions'])} model functions:")
                for func in extracted['model_functions']:
                    phases = func['packages']
                    print(f"  - {func['name']}: Phases {list(phases.keys())}")
            
            print("\nOptions:")
            print("1. Generate standalone models with Claude")
            print("2. Create models manually") 
            print("3. Skip (not useful for examples)")
            print("4. View test code")
            print("5. Test current model (if exists)")
            print("6. Validate ALL models")
            print("7. Next test")
            print("8. Previous test")
            print("9. Jump to test #")
            print("10. Show progress")
            print("0. Exit")
            
            choice = input("\nChoice: ")
            
            if choice == '1':
                # Check if Claude CLI is available
                auto_mode = self.check_claude_cli()
                result = self.analyze_with_claude(current_test, auto_mode=auto_mode)
                if result:
                    self.generate_model_files(current_test, result)
                    self.status['completed'].append(current_test.name)
                    self.status['models_created'][current_test.name] = list(result.get('variants', []))
                    self.save_status()
                    
            elif choice == '2':
                # Manual model creation
                print("\nCreating models manually...")
                for variant in ['dis', 'disv']:
                    extracted = self.extract_model_code(current_test)
                    if extracted['model_functions']:
                        model_code = self.create_standalone_model(
                            current_test, 
                            extracted['model_functions'][0],
                            variant
                        )
                        
                        variant_dir = self.models_dir / current_test.stem / variant
                        variant_dir.mkdir(parents=True, exist_ok=True)
                        model_file = variant_dir / "model.py"
                        model_file.write_text(model_code)
                        model_file.chmod(0o755)
                        print(f"Created: {model_file}")
                
                self.status['completed'].append(current_test.name)
                self.save_status()
                
            elif choice == '3':
                self.status['skipped'].append(current_test.name)
                self.status['current_index'] += 1
                self.save_status()
                
            elif choice == '4':
                # View test code
                print(f"\n{current_test}:")
                with open(current_test) as f:
                    print(f.read()[:2000])
                input("\nPress Enter to continue...")
                
            elif choice == '5':
                # Test current model if it exists
                test_name = current_test.stem
                model_dir = self.models_dir / test_name
                if model_dir.exists():
                    print(f"\nTesting models for {test_name}...")
                    for variant_dir in model_dir.iterdir():
                        if variant_dir.is_dir():
                            model_file = variant_dir / "model.py"
                            if model_file.exists():
                                self.test_model(model_file, variant_dir)
                else:
                    print("No models found for current test")
                input("\nPress Enter to continue...")
                
            elif choice == '6':
                # Validate all models
                self.validate_all_models()
                input("\nPress Enter to continue...")
                
            elif choice == '7':
                if self.status['current_index'] < len(self.test_files) - 1:
                    self.status['current_index'] += 1
                    self.save_status()
                    
            elif choice == '8':
                if self.status['current_index'] > 0:
                    self.status['current_index'] -= 1
                    self.save_status()
                    
            elif choice == '9':
                try:
                    idx = int(input("Test number (1-based): ")) - 1
                    if 0 <= idx < len(self.test_files):
                        self.status['current_index'] = idx
                        self.save_status()
                except:
                    print("Invalid number")
                    
            elif choice == '10':
                print(f"\nProgress:")
                print(f"  Completed: {len(self.status['completed'])}")
                print(f"  Skipped: {len(self.status['skipped'])}")
                print(f"  Models created: {len(self.status['models_created'])}")
                for test, variants in self.status['models_created'].items():
                    print(f"    - {test}: {variants}")
                    
            elif choice == '0':
                print("Exiting...")
                break

if __name__ == "__main__":
    cli = TestReviewCLI()
    cli.run_cli()