#!/usr/bin/env python3
"""
PyEmu Workflow Extractor

Extracts uncertainty analysis workflows from PyEmu example notebooks.
Focuses on PEST setup, uncertainty analysis, and optimization patterns.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import ast
import re


@dataclass
class PyEmuWorkflowCell:
    """Single cell from a PyEmu notebook"""
    cell_type: str  # 'code' or 'markdown'
    content: str
    outputs: List[str] = field(default_factory=list)
    execution_count: Optional[int] = None


@dataclass
class PyEmuWorkflowSection:
    """Section of a PyEmu workflow (group of related cells)"""
    title: str
    description: str
    cells: List[PyEmuWorkflowCell]
    
    # PyEmu-specific analysis
    pest_concepts: List[str] = field(default_factory=list)  # PEST concepts used
    uncertainty_methods: List[str] = field(default_factory=list)  # uncertainty analysis methods
    pyemu_classes: List[str] = field(default_factory=list)  # PyEmu classes used
    key_functions: List[str] = field(default_factory=list)  # Important functions
    
    # Code snippets for learning
    code_snippets: List[str] = field(default_factory=list)


@dataclass 
class PyEmuWorkflow:
    """Complete workflow extracted from a PyEmu example notebook"""
    notebook_file: str
    title: str
    description: str
    
    # Workflow classification
    workflow_type: str  # 'uncertainty', 'optimization', 'pest_setup', 'sensitivity'
    sections: List[PyEmuWorkflowSection]
    
    # PyEmu-specific metadata
    pest_concepts: List[str]  # All PEST concepts covered
    uncertainty_methods: List[str]  # Monte Carlo, FOSM, etc.
    pyemu_modules: List[str]  # pyemu modules used
    prerequisites: List[str]  # What user needs to know
    
    # Statistics
    total_cells: int
    code_cells: int
    complexity: str  # 'beginner', 'intermediate', 'advanced'
    tags: List[str]
    
    # File tracking
    file_hash: str
    extracted_at: datetime = field(default_factory=datetime.now)


class PyEmuWorkflowExtractor:
    """Extract uncertainty analysis workflows from PyEmu notebooks"""
    
    def __init__(self, examples_path: str):
        self.examples_path = Path(examples_path)
        
        # PyEmu-specific patterns
        self.pyemu_classes = {
            'Pst', 'ParameterEnsemble', 'ObservationEnsemble',
            'Schur', 'ErrVar', 'Matrix', 'Cov', 'LinearAnalysis',
            'PstFrom', 'helpers'
        }
        
        self.uncertainty_keywords = {
            'uncertainty', 'ensemble', 'monte carlo', 'fosm',
            'schur', 'error variance', 'covariance', 'prior',
            'posterior', 'forecast', 'sensitivity'
        }
        
        self.pest_keywords = {
            'pest', 'parameter', 'observation', 'control file',
            'template', 'instruction', 'jacobian', 'calibration',
            'regularization', 'pilot points'
        }
    
    def extract_workflow(self, notebook_path: Path) -> Optional[PyEmuWorkflow]:
        """Extract workflow from a single notebook"""
        try:
            with open(notebook_path, 'r', encoding='utf-8') as f:
                notebook = json.load(f)
            
            # Extract basic info
            title = self._extract_title(notebook_path, notebook)
            cells = self._extract_cells(notebook)
            
            if not cells:
                return None
            
            # Group cells into sections
            sections = self._group_into_sections(cells)
            
            # Analyze PyEmu content
            pest_concepts = []
            uncertainty_methods = []
            pyemu_modules = set()
            
            for section in sections:
                # Analyze each section
                self._analyze_section(section)
                pest_concepts.extend(section.pest_concepts)
                uncertainty_methods.extend(section.uncertainty_methods)
                pyemu_modules.update(section.pyemu_classes)
            
            # Determine workflow type
            workflow_type = self._determine_workflow_type(
                title, sections, pest_concepts, uncertainty_methods
            )
            
            # Generate tags and metadata
            tags = self._generate_tags(sections, workflow_type)
            complexity = self._assess_complexity(sections, len(cells))
            prerequisites = self._identify_prerequisites(sections)
            
            # Create workflow object
            workflow = PyEmuWorkflow(
                notebook_file=notebook_path.name,
                title=title,
                description=self._generate_description(title, sections),
                workflow_type=workflow_type,
                sections=sections,
                pest_concepts=list(set(pest_concepts)),
                uncertainty_methods=list(set(uncertainty_methods)),
                pyemu_modules=sorted(list(pyemu_modules)),
                prerequisites=prerequisites,
                total_cells=len(cells),
                code_cells=sum(1 for c in cells if c.cell_type == 'code'),
                complexity=complexity,
                tags=tags,
                file_hash=self._calculate_file_hash(notebook_path)
            )
            
            return workflow
            
        except Exception as e:
            print(f"Error extracting {notebook_path}: {e}")
            return None
    
    def _extract_title(self, path: Path, notebook: dict) -> str:
        """Extract notebook title"""
        # Try first few markdown cells for any header
        for cell in notebook.get('cells', [])[:5]:  # Check first 5 cells
            if cell['cell_type'] == 'markdown':
                content = ''.join(cell['source'])
                # Look for any level header
                if match := re.search(r'^#{1,4}\s+(.+)$', content, re.MULTILINE):
                    title = match.group(1).strip()
                    # Clean up common prefixes
                    title = title.replace('Model background', '').strip()
                    if title:
                        return title
        
        # Fallback to filename with better formatting
        name = path.stem
        # Handle common patterns
        if name.startswith('errvarexample_'):
            return f"Error Variance Example: {name.replace('errvarexample_', '').title()}"
        elif name.startswith('Schurexample_'):
            return f"Schur Complement Example: {name.replace('Schurexample_', '').title()}"
        
        return name.replace('_', ' ').replace('-', ' ').title()
    
    def _extract_cells(self, notebook: dict) -> List[PyEmuWorkflowCell]:
        """Extract all cells from notebook"""
        cells = []
        
        for cell in notebook.get('cells', []):
            cell_type = cell['cell_type']
            content = ''.join(cell.get('source', []))
            
            outputs = []
            if cell_type == 'code' and 'outputs' in cell:
                for output in cell['outputs']:
                    if 'text' in output:
                        outputs.append(''.join(output['text']))
                    elif 'data' in output and 'text/plain' in output['data']:
                        outputs.append(''.join(output['data']['text/plain']))
            
            cells.append(PyEmuWorkflowCell(
                cell_type=cell_type,
                content=content,
                outputs=outputs,
                execution_count=cell.get('execution_count')
            ))
        
        return cells
    
    def _group_into_sections(self, cells: List[PyEmuWorkflowCell]) -> List[PyEmuWorkflowSection]:
        """Group cells into logical sections based on markdown headers"""
        sections = []
        current_section = None
        current_cells = []
        
        for cell in cells:
            if cell.cell_type == 'markdown':
                # Check for section header
                if match := re.search(r'^#{1,3}\s+(.+)$', cell.content, re.MULTILINE):
                    # Save previous section
                    if current_section and current_cells:
                        sections.append(PyEmuWorkflowSection(
                            title=current_section,
                            description=self._extract_section_description(current_cells),
                            cells=current_cells
                        ))
                    
                    # Start new section
                    current_section = match.group(1).strip()
                    current_cells = [cell]
                else:
                    current_cells.append(cell)
            else:
                current_cells.append(cell)
        
        # Add last section
        if current_section and current_cells:
            sections.append(PyEmuWorkflowSection(
                title=current_section,
                description=self._extract_section_description(current_cells),
                cells=current_cells
            ))
        
        # If no sections found, create one
        if not sections and cells:
            sections.append(PyEmuWorkflowSection(
                title="Main Workflow",
                description="Complete notebook content",
                cells=cells
            ))
        
        return sections
    
    def _extract_section_description(self, cells: List[PyEmuWorkflowCell]) -> str:
        """Extract description from section cells"""
        for cell in cells:
            if cell.cell_type == 'markdown':
                # Get first paragraph after header
                lines = cell.content.split('\n')
                desc_lines = []
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        desc_lines.append(line)
                    if len(desc_lines) >= 3:
                        break
                return ' '.join(desc_lines)
        return ""
    
    def _analyze_section(self, section: PyEmuWorkflowSection):
        """Analyze PyEmu-specific content in a section"""
        # Analyze code cells
        for cell in section.cells:
            if cell.cell_type == 'code':
                # Extract PyEmu classes and functions
                try:
                    tree = ast.parse(cell.content)
                    
                    for node in ast.walk(tree):
                        # PyEmu class usage
                        if isinstance(node, ast.Name) and node.id in self.pyemu_classes:
                            section.pyemu_classes.append(f"pyemu.{node.id}")
                        
                        # Function calls
                        if isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Attribute):
                                func_name = node.func.attr
                                if hasattr(node.func.value, 'id'):
                                    obj_name = node.func.value.id
                                    # Track pyemu-specific calls
                                    if 'pst' in obj_name.lower() or 'en' in obj_name.lower():
                                        section.key_functions.append(f"{obj_name}.{func_name}")
                                
                                # Track uncertainty methods
                                if any(kw in func_name.lower() for kw in ['schur', 'fosm', 'monte', 'ensemble']):
                                    section.uncertainty_methods.append(func_name)
                
                except:
                    pass
                
                # Extract PEST concepts from content
                content_lower = cell.content.lower()
                for keyword in self.pest_keywords:
                    if keyword in content_lower:
                        section.pest_concepts.append(keyword)
                
                # Save key code snippets
                if len(cell.content.strip()) > 10 and len(section.code_snippets) < 5:
                    section.code_snippets.append(cell.content.strip())
    
    def _determine_workflow_type(self, title: str, sections: List[PyEmuWorkflowSection],
                                pest_concepts: List[str], uncertainty_methods: List[str]) -> str:
        """Determine the primary type of workflow"""
        title_lower = title.lower()
        
        if 'schur' in title_lower or 'schur' in uncertainty_methods:
            return 'schur_complement'
        elif 'ensemble' in title_lower or 'ensemble' in uncertainty_methods:
            return 'ensemble_analysis'
        elif 'error var' in title_lower or 'errvar' in title_lower:
            return 'error_variance'
        elif 'pstfrom' in title_lower:
            return 'pest_setup'
        elif 'matrix' in title_lower or 'covariance' in title_lower:
            return 'covariance_analysis'
        elif 'optimization' in title_lower:
            return 'optimization'
        else:
            return 'uncertainty_analysis'
    
    def _generate_tags(self, sections: List[PyEmuWorkflowSection], workflow_type: str) -> List[str]:
        """Generate searchable tags"""
        tags = [workflow_type]
        
        # Add method tags
        all_methods = []
        for section in sections:
            all_methods.extend(section.uncertainty_methods)
        
        if 'schur' in str(all_methods).lower():
            tags.append('schur-complement')
        if 'ensemble' in str(all_methods).lower():
            tags.append('ensemble-methods')
        if 'fosm' in str(all_methods).lower():
            tags.append('first-order-second-moment')
        
        # Add concept tags
        all_concepts = []
        for section in sections:
            all_concepts.extend(section.pest_concepts)
        
        if 'prior' in str(all_concepts).lower():
            tags.append('prior-information')
        if 'posterior' in str(all_concepts).lower():
            tags.append('posterior-analysis')
        if 'forecast' in str(all_concepts).lower():
            tags.append('forecast-uncertainty')
        
        return list(set(tags))
    
    def _assess_complexity(self, sections: List[PyEmuWorkflowSection], total_cells: int) -> str:
        """Assess workflow complexity"""
        # Count advanced concepts
        advanced_concepts = 0
        for section in sections:
            if any(method in ['schur', 'fosm'] for method in section.uncertainty_methods):
                advanced_concepts += 1
            if len(section.pyemu_classes) > 3:
                advanced_concepts += 1
        
        if advanced_concepts >= 3 or total_cells > 50:
            return 'advanced'
        elif advanced_concepts >= 1 or total_cells > 25:
            return 'intermediate'
        else:
            return 'beginner'
    
    def _identify_prerequisites(self, sections: List[PyEmuWorkflowSection]) -> List[str]:
        """Identify what users need to know before using this workflow"""
        prereqs = set()
        
        # Check for PEST knowledge needed
        pest_concepts = []
        for section in sections:
            pest_concepts.extend(section.pest_concepts)
        
        if pest_concepts:
            prereqs.add("Basic PEST concepts")
        if any('jacobian' in c for c in pest_concepts):
            prereqs.add("Understanding of Jacobian matrix")
        
        # Check for statistical knowledge
        for section in sections:
            if 'covariance' in str(section.uncertainty_methods).lower():
                prereqs.add("Covariance matrix concepts")
            if 'monte carlo' in str(section.uncertainty_methods).lower():
                prereqs.add("Monte Carlo simulation basics")
        
        return sorted(list(prereqs))
    
    def _generate_description(self, title: str, sections: List[PyEmuWorkflowSection]) -> str:
        """Generate workflow description"""
        # Try to get description from first few sections
        for section in sections[:3]:
            if section.description and len(section.description) > 20:
                return section.description
        
        # Look for description in markdown cells
        for section in sections:
            for cell in section.cells[:5]:
                if cell.cell_type == 'markdown' and len(cell.content) > 50:
                    # Get first meaningful paragraph
                    lines = cell.content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#') and len(line) > 30:
                            return line
        
        # Generate from title and content
        desc_parts = [f"PyEmu workflow demonstrating {title}"]
        
        # Add more context from detected methods
        all_methods = []
        for section in sections:
            all_methods.extend(section.uncertainty_methods)
        
        if all_methods:
            desc_parts.append(f"using {', '.join(set(all_methods[:3]))}")
        
        if len(sections) > 1:
            desc_parts.append(f"Covers {len(sections)} main topics")
        
        return ". ".join(desc_parts)
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate file hash for change detection"""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def extract_all_workflows(self) -> List[PyEmuWorkflow]:
        """Extract all PyEmu example workflows"""
        workflows = []
        
        # Find all notebook files
        notebook_files = sorted(self.examples_path.glob("*.ipynb"))
        
        print(f"Found {len(notebook_files)} PyEmu example notebooks")
        
        for nb_file in notebook_files:
            print(f"  Extracting {nb_file.name}...", end='')
            workflow = self.extract_workflow(nb_file)
            if workflow:
                workflows.append(workflow)
                print(" ✓")
            else:
                print(" ✗")
        
        return workflows