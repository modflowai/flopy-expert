#!/usr/bin/env python3
"""
FloPy Workflow Extractor

Extracts modeling workflows from FloPy tutorial files to create
a searchable database of common modeling patterns.
"""
import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import hashlib
from datetime import datetime


@dataclass
class WorkflowStep:
    """Represents a single step in a modeling workflow"""
    step_number: int
    description: str
    code_snippet: str
    imports: List[str]
    flopy_classes: List[str]
    key_functions: List[str]
    parameters: Dict[str, Any]


@dataclass
class WorkflowPattern:
    """Complete workflow extracted from a tutorial"""
    tutorial_file: str
    title: str
    description: str
    model_type: str  # mf6, mf2005, mt3d, etc.
    packages_used: List[str]
    workflow_steps: List[WorkflowStep]
    total_lines: int
    complexity: str  # simple, intermediate, advanced
    tags: List[str]  # e.g., steady-state, transient, unconfined, etc.
    file_hash: str
    extracted_at: datetime


class WorkflowExtractor:
    """Extract structured workflows from FloPy tutorials"""
    
    def __init__(self, tutorials_path: str):
        self.tutorials_path = Path(tutorials_path)
        self.flopy_classes = self._get_flopy_classes()
        
    def _get_flopy_classes(self) -> set:
        """Get a set of known FloPy class names for identification"""
        # Common FloPy classes across versions
        return {
            # Simulations and models
            'MFSimulation', 'Modflow', 'Mt3dms', 'Seawat',
            # MF6 specific
            'ModflowGwf', 'ModflowGwt', 'ModflowGwe',
            # Packages
            'ModflowDis', 'ModflowDisu', 'ModflowDisv',
            'ModflowBas', 'ModflowBas6', 'ModflowIc',
            'ModflowNpf', 'ModflowLpf', 'ModflowUpw',
            'ModflowWel', 'ModflowDrn', 'ModflowRiv',
            'ModflowGhb', 'ModflowRch', 'ModflowEvt',
            'ModflowOc', 'ModflowSms', 'ModflowIms',
            'ModflowSfr', 'ModflowLak', 'ModflowMaw',
            'ModflowUzf', 'ModflowMvr', 'ModflowGnc',
            # Solvers
            'ModflowPcg', 'ModflowNwt', 'ModflowDe4',
            # Transport
            'Mt3dBtn', 'Mt3dAdv', 'Mt3dDsp', 'Mt3dSsm',
            'Mt3dRct', 'Mt3dGcg', 'Mt3dUzt',
        }
        
    def extract_workflow(self, tutorial_file: Path) -> Optional[WorkflowPattern]:
        """Extract workflow pattern from a single tutorial file"""
        try:
            content = tutorial_file.read_text(encoding='utf-8')
            
            # Extract metadata
            title = self._extract_title(content)
            description = self._extract_description(content)
            model_type = self._identify_model_type(content)
            
            # Parse code structure
            tree = ast.parse(content)
            
            # Extract workflow steps
            steps = self._extract_steps(content, tree)
            
            # Extract packages used
            packages_used = self._extract_packages(content, tree)
            
            # Determine complexity
            complexity = self._determine_complexity(steps, packages_used)
            
            # Extract tags
            tags = self._extract_tags(content, title, model_type)
            
            # Calculate file hash
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            
            return WorkflowPattern(
                tutorial_file=str(tutorial_file.relative_to(self.tutorials_path.parent)),
                title=title,
                description=description,
                model_type=model_type,
                packages_used=packages_used,
                workflow_steps=steps,
                total_lines=len(content.splitlines()),
                complexity=complexity,
                tags=tags,
                file_hash=file_hash,
                extracted_at=datetime.now()
            )
            
        except Exception as e:
            print(f"Error extracting workflow from {tutorial_file}: {e}")
            return None
    
    def _extract_title(self, content: str) -> str:
        """Extract tutorial title from comments or first heading"""
        # Look for markdown-style headings (but not jupytext metadata)
        lines = content.splitlines()
        for i, line in enumerate(lines):
            # Skip the jupytext metadata section
            if i < 15 and ('jupyter:' in line or 'jupytext:' in line or '---' in line):
                continue
                
            if line.strip().startswith('# ') and line.strip() != '# ---':
                # Found a heading - extract the title
                title = line.strip('# ').strip()
                # Make sure it's not a section marker
                if title and not title.startswith('#'):
                    return title
        
        # Fallback to filename
        return "FloPy Tutorial"
    
    def _extract_description(self, content: str) -> str:
        """Extract tutorial description"""
        # Look for description after title
        lines = content.splitlines()
        in_description = False
        description_lines = []
        
        for line in lines[:50]:  # Check first 50 lines
            if re.match(r'^#\s+[A-Z]', line):  # Main heading
                in_description = True
                continue
            elif in_description and line.strip().startswith('#'):
                # Still in comments
                clean_line = line.strip('#').strip()
                if clean_line:
                    description_lines.append(clean_line)
            elif in_description and not line.strip().startswith('#'):
                # End of description
                break
        
        return ' '.join(description_lines)[:500]  # Limit length
    
    def _identify_model_type(self, content: str) -> str:
        """Identify the primary model type used"""
        if 'MFSimulation' in content or 'ModflowGwf' in content:
            return 'mf6'
        elif 'Modflow(' in content and 'version="mf2005"' in content:
            return 'mf2005'
        elif 'Modflow(' in content and 'version="mfnwt"' in content:
            return 'mfnwt'
        elif 'ModflowUsg' in content:
            return 'mfusg'
        elif 'Mt3dms' in content:
            return 'mt3d'
        elif 'Seawat' in content:
            return 'seawat'
        elif 'Modpath' in content:
            return 'modpath'
        else:
            return 'unknown'
    
    def _extract_steps(self, content: str, tree: ast.AST) -> List[WorkflowStep]:
        """Extract workflow steps from code structure and comments"""
        steps = []
        lines = content.splitlines()
        
        # Find sections marked by comments
        section_pattern = re.compile(r'^#\s*#+\s*(.+?)$|^#\s*Step\s*\d+[:.]?\s*(.+?)$', re.IGNORECASE)
        
        current_section = None
        current_code = []
        current_imports = set()
        current_classes = set()
        current_functions = set()
        step_number = 0
        
        for i, line in enumerate(lines):
            # Check for section header
            match = section_pattern.match(line)
            if match:
                # Save previous section if exists
                if current_section and current_code:
                    step_number += 1
                    steps.append(self._create_workflow_step(
                        step_number,
                        current_section,
                        '\n'.join(current_code),
                        list(current_imports),
                        list(current_classes),
                        list(current_functions)
                    ))
                
                # Start new section
                current_section = (match.group(1) or match.group(2)).strip()
                current_code = []
                current_imports = set()
                current_classes = set()
                current_functions = set()
            
            elif current_section and line.strip() and not line.strip().startswith('#'):
                # Accumulate code
                current_code.append(line)
                
                # Track imports
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    current_imports.add(line.strip())
                
                # Track FloPy usage
                for cls in self.flopy_classes:
                    if cls in line:
                        current_classes.add(cls)
                
                # Track function calls
                func_calls = re.findall(r'(\w+)\s*\(', line)
                current_functions.update(func_calls)
        
        # Don't forget last section
        if current_section and current_code:
            step_number += 1
            steps.append(self._create_workflow_step(
                step_number,
                current_section,
                '\n'.join(current_code),
                list(current_imports),
                list(current_classes),
                list(current_functions)
            ))
        
        return steps
    
    def _create_workflow_step(self, step_number: int, description: str, 
                            code: str, imports: List[str], 
                            classes: List[str], functions: List[str]) -> WorkflowStep:
        """Create a workflow step with extracted parameters"""
        # Extract key parameters from code
        parameters = {}
        
        # Look for variable assignments that look like parameters
        param_pattern = re.compile(r'^(\w+)\s*=\s*(.+?)$', re.MULTILINE)
        for match in param_pattern.finditer(code):
            var_name = match.group(1)
            var_value = match.group(2).strip()
            
            # Filter to likely parameters
            if (var_name.isupper() or  # Constants like NLAY, NROW
                var_name in ['nlay', 'nrow', 'ncol', 'delr', 'delc', 'top', 'bot'] or
                var_name.startswith(('k', 'q', 'h', 'r', 's'))):  # Common parameter prefixes
                try:
                    # Try to evaluate simple values
                    if var_value.replace('.', '').replace('-', '').isdigit():
                        parameters[var_name] = float(var_value) if '.' in var_value else int(var_value)
                    else:
                        parameters[var_name] = var_value
                except:
                    parameters[var_name] = var_value
        
        return WorkflowStep(
            step_number=step_number,
            description=description,
            code_snippet=code[:1000],  # Limit code length
            imports=imports,
            flopy_classes=classes,
            key_functions=functions,
            parameters=parameters
        )
    
    def _extract_packages(self, content: str, tree: ast.AST) -> List[str]:
        """Extract FloPy packages used in the tutorial"""
        packages = set()
        
        # Pattern to match package creation
        package_patterns = [
            r'Modflow(\w+)\s*\(',  # Classic MODFLOW packages
            r'flopy\.mf6\.Modflow(\w+)\s*\(',  # MF6 packages
            r'Mt3d(\w+)\s*\(',  # MT3D packages
            r'\.(\w+)\.(\w+)\s*\(',  # General pattern
        ]
        
        for pattern in package_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    package = ''.join(match).upper()
                else:
                    package = match.upper()
                
                # Clean up common variations
                if package.startswith('GWF'):
                    package = package[3:]
                elif package.startswith('GWT'):
                    package = package[3:]
                
                # Filter to valid package codes
                if len(package) <= 4 and package.isalpha():
                    packages.add(package)
        
        return sorted(packages)
    
    def _determine_complexity(self, steps: List[WorkflowStep], packages: List[str]) -> str:
        """Determine tutorial complexity based on steps and packages"""
        num_steps = len(steps)
        num_packages = len(packages)
        
        # Calculate code complexity
        total_code_lines = sum(len(step.code_snippet.splitlines()) for step in steps)
        
        if num_steps <= 5 and num_packages <= 3:
            return "simple"
        elif num_steps <= 10 and num_packages <= 6:
            return "intermediate"
        else:
            return "advanced"
    
    def _extract_tags(self, content: str, title: str, model_type: str) -> List[str]:
        """Extract descriptive tags from tutorial content"""
        tags = [model_type]
        
        # Check for flow conditions
        if 'steady' in content.lower() or 'steady-state' in content.lower():
            tags.append('steady-state')
        if 'transient' in content.lower():
            tags.append('transient')
        
        # Check for aquifer types
        if 'unconfined' in content.lower():
            tags.append('unconfined')
        if 'confined' in content.lower():
            tags.append('confined')
        
        # Check for specific packages/features
        feature_keywords = {
            'well': 'wells',
            'river': 'rivers',
            'drain': 'drains',
            'lake': 'lakes',
            'stream': 'streams',
            'sfr': 'sfr',
            'uzf': 'unsaturated-zone',
            'transport': 'transport',
            'multiaquifer': 'maw',
            'lgr': 'local-grid-refinement',
            'newton': 'newton-solver',
            'parallel': 'parallel',
            'voronoi': 'unstructured-grid',
            'triangle': 'unstructured-grid',
        }
        
        content_lower = content.lower()
        for keyword, tag in feature_keywords.items():
            if keyword in content_lower:
                tags.append(tag)
        
        return list(set(tags))  # Remove duplicates
    
    def extract_all_workflows(self) -> List[WorkflowPattern]:
        """Extract workflows from all tutorial files"""
        workflows = []
        tutorial_files = sorted(self.tutorials_path.glob("*.py"))
        
        print(f"Found {len(tutorial_files)} tutorial files")
        
        for i, tutorial_file in enumerate(tutorial_files):
            print(f"Processing {i+1}/{len(tutorial_files)}: {tutorial_file.name}")
            workflow = self.extract_workflow(tutorial_file)
            if workflow:
                workflows.append(workflow)
        
        return workflows


def main():
    """Test workflow extraction"""
    tutorials_path = "/home/danilopezmella/flopy_expert/flopy/.docs/Notebooks"
    extractor = WorkflowExtractor(tutorials_path)
    
    # Test with one file
    test_file = Path(tutorials_path) / "mf6_tutorial01.py"
    if test_file.exists():
        workflow = extractor.extract_workflow(test_file)
        if workflow:
            print(f"\nExtracted workflow: {workflow.title}")
            print(f"Description: {workflow.description}")
            print(f"Model type: {workflow.model_type}")
            print(f"Packages: {workflow.packages_used}")
            print(f"Steps: {len(workflow.workflow_steps)}")
            print(f"Complexity: {workflow.complexity}")
            print(f"Tags: {workflow.tags}")
            
            print("\nWorkflow steps:")
            for step in workflow.workflow_steps:
                print(f"\n{step.step_number}. {step.description}")
                print(f"   Classes: {step.flopy_classes}")
                print(f"   Parameters: {list(step.parameters.keys())[:5]}...")


if __name__ == "__main__":
    main()