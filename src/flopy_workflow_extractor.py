#!/usr/bin/env python3
"""
FloPy Jupytext Workflow Extractor

Extracts modeling workflows from FloPy tutorial files in jupytext format.
These files have markdown cells as comments and code cells as Python code.
"""
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import hashlib
from datetime import datetime


@dataclass
class WorkflowCell:
    """Represents a cell in the jupytext notebook"""
    cell_type: str  # 'markdown' or 'code'
    content: str
    cell_number: int


@dataclass
class WorkflowSection:
    """Represents a section in the workflow"""
    title: str
    description: str
    cells: List[WorkflowCell]
    code_snippets: List[str]
    packages_used: List[str]
    key_functions: List[str]


@dataclass
class JupytextWorkflow:
    """Complete workflow extracted from a jupytext tutorial"""
    tutorial_file: str
    title: str
    description: str
    model_type: str  # mf6, mf2005, mt3d, etc.
    sections: List[WorkflowSection]
    packages_used: List[str]
    total_cells: int
    total_lines: int
    complexity: str  # simple, intermediate, advanced
    tags: List[str]
    file_hash: str
    extracted_at: datetime


class JupytextWorkflowExtractor:
    """Extract structured workflows from FloPy jupytext tutorials"""
    
    def __init__(self, tutorials_path: str):
        self.tutorials_path = Path(tutorials_path)
        self.flopy_packages = self._get_flopy_packages()
        
    def _get_flopy_packages(self) -> set:
        """Get a set of known FloPy package names"""
        return {
            'DIS', 'DISV', 'DISU', 'IC', 'NPF', 'HFB', 'STO', 'CSU',
            'WEL', 'DRN', 'RIV', 'GHB', 'RCH', 'EVT', 'MAW', 'SFR',
            'LAK', 'UZF', 'MVR', 'GNC', 'SMS', 'IMS', 'OC', 'OBS',
            'CHD', 'FHB', 'TDIS', 'GWF', 'GWT', 'GWE', 'PRT',
            'ADV', 'DSP', 'MST', 'RCT', 'SSM', 'CNC', 'SRC', 'IST',
            'BTN', 'DCT', 'GCG', 'PCG', 'DE4', 'NWT', 'SIP', 'SOR',
            'LPF', 'BCF', 'UPW', 'HYD', 'HOB', 'MNW', 'SUB', 'SWT',
            'AG', 'STR', 'SWI', 'PCG', 'PCGN', 'GMG', 'VDF', 'VSC'
        }
        
    def extract_workflow(self, tutorial_file: Path) -> Optional[JupytextWorkflow]:
        """Extract workflow from a jupytext Python file"""
        try:
            content = tutorial_file.read_text(encoding='utf-8')
            
            # Parse cells
            cells = self._parse_jupytext_cells(content)
            
            # Extract metadata
            title = self._extract_title(cells)
            description = self._extract_description(cells)
            model_type = self._identify_model_type(content)
            
            # Extract sections
            sections = self._extract_sections(cells)
            
            # Extract all packages used
            packages_used = self._extract_all_packages(content)
            
            # Determine complexity
            complexity = self._determine_complexity(sections, packages_used)
            
            # Extract tags
            tags = self._extract_tags(content, title, model_type)
            
            # Calculate file hash
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            
            return JupytextWorkflow(
                tutorial_file=str(tutorial_file.relative_to(self.tutorials_path.parent)),
                title=title,
                description=description,
                model_type=model_type,
                sections=sections,
                packages_used=packages_used,
                total_cells=len(cells),
                total_lines=len(content.splitlines()),
                complexity=complexity,
                tags=tags,
                file_hash=file_hash,
                extracted_at=datetime.now()
            )
            
        except Exception as e:
            print(f"Error extracting workflow from {tutorial_file}: {e}")
            return None
    
    def _parse_jupytext_cells(self, content: str) -> List[WorkflowCell]:
        """Parse jupytext format into cells"""
        cells = []
        lines = content.splitlines()
        
        # Skip jupytext header
        start_idx = 0
        for i, line in enumerate(lines):
            if line.strip() == '# ---' and i > 0:
                start_idx = i + 1
                break
        
        current_cell_content = []
        current_cell_type = None
        cell_number = 0
        
        i = start_idx
        while i < len(lines):
            line = lines[i]
            
            # Check if this is a markdown line (starts with '# ')
            if line.startswith('# ') or line == '#':
                # If we were in a code cell, save it
                if current_cell_type == 'code' and current_cell_content:
                    cells.append(WorkflowCell(
                        cell_type='code',
                        content='\n'.join(current_cell_content).strip(),
                        cell_number=cell_number
                    ))
                    cell_number += 1
                    current_cell_content = []
                
                current_cell_type = 'markdown'
                # Remove the '# ' prefix
                if line.startswith('# '):
                    current_cell_content.append(line[2:])
                else:
                    current_cell_content.append('')
                
            elif line.strip() == '' and current_cell_type == 'markdown':
                # Empty line might signal end of markdown cell
                if current_cell_content and any(c.strip() for c in current_cell_content):
                    cells.append(WorkflowCell(
                        cell_type='markdown',
                        content='\n'.join(current_cell_content).strip(),
                        cell_number=cell_number
                    ))
                    cell_number += 1
                    current_cell_content = []
                    current_cell_type = None
                    
            elif not line.startswith('#') or (line.startswith('#') and current_cell_type == 'code'):
                # Code line
                if current_cell_type == 'markdown' and current_cell_content:
                    cells.append(WorkflowCell(
                        cell_type='markdown',
                        content='\n'.join(current_cell_content).strip(),
                        cell_number=cell_number
                    ))
                    cell_number += 1
                    current_cell_content = []
                
                current_cell_type = 'code'
                current_cell_content.append(line)
            
            i += 1
        
        # Don't forget the last cell
        if current_cell_content:
            cells.append(WorkflowCell(
                cell_type=current_cell_type or 'code',
                content='\n'.join(current_cell_content).strip(),
                cell_number=cell_number
            ))
        
        return cells
    
    def _extract_title(self, cells: List[WorkflowCell]) -> str:
        """Extract tutorial title from first markdown header"""
        for cell in cells:
            if cell.cell_type == 'markdown' and cell.content.startswith('#'):
                # Extract the title from the first header
                match = re.match(r'^#+\s+(.+)$', cell.content, re.MULTILINE)
                if match:
                    return match.group(1).strip()
        return "FloPy Tutorial"
    
    def _extract_description(self, cells: List[WorkflowCell]) -> str:
        """Extract tutorial description from early markdown cells"""
        description_parts = []
        found_title = False
        
        for cell in cells[:10]:  # Check first 10 cells
            if cell.cell_type == 'markdown':
                if cell.content.startswith('#') and not found_title:
                    found_title = True
                elif found_title and not cell.content.startswith('#'):
                    # This is likely description text
                    description_parts.append(cell.content)
                elif found_title and cell.content.startswith('##'):
                    # Stop at next section
                    break
        
        return ' '.join(description_parts)[:500]  # Limit length
    
    def _identify_model_type(self, content: str) -> str:
        """Identify the primary model type"""
        if 'MFSimulation' in content or 'ModflowGwf' in content:
            return 'mf6'
        elif 'Modflow(' in content and 'mf2005' in content:
            return 'mf2005'
        elif 'ModflowNwt' in content:
            return 'mfnwt'
        elif 'ModflowUsg' in content:
            return 'mfusg'
        elif 'Mt3d' in content:
            return 'mt3d'
        elif 'Seawat' in content:
            return 'seawat'
        elif 'Modpath' in content:
            return 'modpath'
        else:
            return 'unknown'
    
    def _extract_sections(self, cells: List[WorkflowCell]) -> List[WorkflowSection]:
        """Extract logical sections from the tutorial"""
        sections = []
        current_section = None
        current_cells = []
        
        for cell in cells:
            if cell.cell_type == 'markdown' and cell.content.startswith('##'):
                # New section
                if current_section:
                    # Save previous section
                    sections.append(self._create_section(
                        current_section, 
                        current_cells
                    ))
                
                # Start new section
                match = re.match(r'^##\s+(.+)$', cell.content)
                if match:
                    current_section = match.group(1).strip()
                    current_cells = [cell]
            else:
                current_cells.append(cell)
        
        # Don't forget last section
        if current_section and current_cells:
            sections.append(self._create_section(
                current_section,
                current_cells
            ))
        
        # If no sections found, create one main section
        if not sections and cells:
            sections.append(self._create_section(
                "Main Workflow",
                cells
            ))
        
        return sections
    
    def _create_section(self, title: str, cells: List[WorkflowCell]) -> WorkflowSection:
        """Create a workflow section from cells"""
        # Extract description from markdown cells
        description_parts = []
        code_snippets = []
        packages_used = set()
        key_functions = set()
        
        for cell in cells:
            if cell.cell_type == 'markdown' and not cell.content.startswith('#'):
                description_parts.append(cell.content)
            elif cell.cell_type == 'code':
                code_snippets.append(cell.content)
                
                # Extract packages
                for pkg in self.flopy_packages:
                    if pkg in cell.content:
                        packages_used.add(pkg)
                
                # Extract function calls
                func_calls = re.findall(r'(\w+)\s*\(', cell.content)
                key_functions.update(func_calls)
        
        return WorkflowSection(
            title=title,
            description=' '.join(description_parts)[:300],
            cells=cells,
            code_snippets=code_snippets,
            packages_used=sorted(packages_used),
            key_functions=sorted(key_functions)[:10]  # Limit to top 10
        )
    
    def _extract_all_packages(self, content: str) -> List[str]:
        """Extract all FloPy packages used"""
        packages = set()
        
        # Look for package instantiation patterns
        patterns = [
            r'Modflow(\w+)\s*\(',
            r'flopy\.mf6\.Modflow(\w+)\s*\(',
            r'Mt3d(\w+)\s*\(',
            r'\.(\w{3,4})\s*\(',  # Common package codes
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                pkg = match.upper()
                # Clean up
                if pkg.startswith('GWF'):
                    pkg = pkg[3:]
                elif pkg.startswith('GWT'):
                    pkg = pkg[3:]
                
                if pkg in self.flopy_packages:
                    packages.add(pkg)
        
        return sorted(packages)
    
    def _determine_complexity(self, sections: List[WorkflowSection], packages: List[str]) -> str:
        """Determine tutorial complexity"""
        num_sections = len(sections)
        num_packages = len(packages)
        total_code_lines = sum(
            sum(len(snippet.splitlines()) for snippet in section.code_snippets)
            for section in sections
        )
        
        if num_sections <= 3 and num_packages <= 5 and total_code_lines < 100:
            return "simple"
        elif num_sections <= 6 and num_packages <= 10 and total_code_lines < 300:
            return "intermediate"
        else:
            return "advanced"
    
    def _extract_tags(self, content: str, title: str, model_type: str) -> List[str]:
        """Extract descriptive tags"""
        tags = [model_type]
        
        content_lower = content.lower()
        title_lower = title.lower()
        
        # Flow conditions
        if 'steady' in content_lower or 'steady-state' in content_lower:
            tags.append('steady-state')
        if 'transient' in content_lower:
            tags.append('transient')
        
        # Aquifer types
        if 'unconfined' in content_lower or 'unconfined' in title_lower:
            tags.append('unconfined')
        if 'confined' in content_lower:
            tags.append('confined')
        
        # Grid types
        if 'voronoi' in content_lower or 'voronoi' in title_lower:
            tags.append('voronoi')
        if 'triangle' in content_lower or 'triangular' in title_lower:
            tags.append('triangular')
        if 'quadtree' in content_lower:
            tags.append('quadtree')
        if 'unstructured' in content_lower:
            tags.append('unstructured')
        
        # Features
        feature_keywords = {
            'well': 'wells',
            'river': 'rivers',
            'drain': 'drains', 
            'lake': 'lakes',
            'stream': 'streams',
            'recharge': 'recharge',
            'evapotranspiration': 'evapotranspiration',
            'transport': 'transport',
            'particle': 'particle-tracking',
            'budget': 'water-budget',
            'observation': 'observations',
            'boundary': 'boundary-conditions'
        }
        
        for keyword, tag in feature_keywords.items():
            if keyword in content_lower:
                tags.append(tag)
        
        return list(set(tags))
    
    def extract_all_workflows(self) -> List[JupytextWorkflow]:
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
    """Test jupytext workflow extraction"""
    tutorials_path = "/home/danilopezmella/flopy_expert/flopy/.docs/Notebooks"
    extractor = JupytextWorkflowExtractor(tutorials_path)
    
    # Test with multiple tutorial files
    test_files = [
        "mf6_tutorial01.py",
        "dis_triangle_example.py",
        "dis_voronoi_example.py",
        "mf6_complex_model_example.py",
        "groundwater2023_watershed_example.py"
    ]
    
    print("🔍 Testing jupytext workflow extraction on multiple tutorials")
    print("=" * 80)
    
    for test_filename in test_files:
        test_file = Path(tutorials_path) / test_filename
        
        if not test_file.exists():
            print(f"\n⚠️  Skipping {test_filename} (file not found)")
            continue
            
        print(f"\n\n{'='*80}")
        print(f"📄 Processing: {test_filename}")
        print("=" * 80)
        
        workflow = extractor.extract_workflow(test_file)
        if workflow:
            print(f"\n📋 Extracted Workflow")
            print(f"Title: {workflow.title}")
            print(f"Description: {workflow.description[:200]}...")
            print(f"Model Type: {workflow.model_type}")
            print(f"Packages Used: {', '.join(workflow.packages_used)}")
            print(f"Number of Sections: {len(workflow.sections)}")
            print(f"Total Cells: {workflow.total_cells}")
            print(f"Complexity: {workflow.complexity}")
            print(f"Tags: {', '.join(workflow.tags)}")
            
            print("\n📊 Workflow Sections:")
            for i, section in enumerate(workflow.sections[:3]):
                print(f"\n{i+1}. {section.title}")
                print(f"   Description: {section.description[:100]}...")
                print(f"   Code cells: {len(section.code_snippets)}")
                print(f"   Packages: {', '.join(section.packages_used) if section.packages_used else 'None'}")
                print(f"   Key functions: {', '.join(section.key_functions[:5]) if section.key_functions else 'None'}")
            
            if len(workflow.sections) > 3:
                print(f"\n... and {len(workflow.sections) - 3} more sections")
                
            # Show a sample code snippet
            if workflow.sections and workflow.sections[0].code_snippets:
                print("\n📝 Sample code snippet from first section:")
                first_snippet = workflow.sections[0].code_snippets[0]
                snippet_lines = first_snippet.splitlines()[:5]
                for line in snippet_lines:
                    print(f"   {line}")
                if len(first_snippet.splitlines()) > 5:
                    print("   ...")
        else:
            print("❌ Failed to extract workflow")
    
    print("\n\n" + "="*80)
    print("✅ Test completed")


if __name__ == "__main__":
    main()