#!/usr/bin/env python3
"""
Documentation parser for pyEMU - extracts documented modules from .rst files

pyEMU uses Sphinx autodoc format, so we parse automodule directives.
"""
import re
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class PyEMUModule:
    """Represents a documented pyEMU module"""
    module_path: str        # e.g., "pyemu.sc"
    category: str          # e.g., "core", "utils", "pst", "mat", "plot"
    description: str       # e.g., "Schur complement analysis"
    rst_file: str         # Source .rst file
    
    def to_file_path(self) -> str:
        """Convert module path to file path"""
        # pyemu.sc -> pyemu/sc.py
        # pyemu.utils.geostats -> pyemu/utils/geostats.py
        parts = self.module_path.split('.')
        if parts[0] == 'pyemu':
            parts = parts[1:]  # Remove 'pyemu' prefix
        return 'pyemu/' + '/'.join(parts) + '.py'


class PyEMUDocsParser:
    """Parser for pyEMU documentation structure"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.docs_path = self.repo_path / "docs"
        
        # Core module descriptions based on __init__.py and README
        self.module_descriptions = {
            'en': 'Ensemble classes for Monte Carlo and PEST++ IES',
            'ev': 'Error variance analysis (PREDVAR foundation)',
            'la': 'Linear analysis base class',
            'sc': 'Schur complement for conditional uncertainty (PREDUNC foundation)',
            'mc': 'Monte Carlo analysis utilities',
            'eds': 'Ensemble data space analysis',
            'logger': 'Logging utilities',
            'pyemu_warnings': 'Warning system',
            # Utils
            'geostats': 'Geostatistical tools (variograms, kriging)',
            'gw_utils': 'Groundwater model utilities',
            'helpers': 'General helper functions',
            'optimization': 'Optimization utilities',
            'os_utils': 'Operating system utilities',
            'pp_utils': 'PEST++ specific utilities',
            'pst_from': 'PEST interface generation (100k+ parameters)',
            'smp_utils': 'Sample file utilities',
            # PST
            'pst_handler': 'PEST control file handling',
            'pst_utils': 'PEST file utilities',
            'pst_controldata': 'PEST control data structures',
            'result_handler': 'PEST results processing',
            # Mat
            'mat_handler': 'Matrix handling (Jacobian, Covariance)',
            # Plot
            'plot_utils': 'Visualization utilities',
        }
    
    def parse_rst_files(self) -> List[PyEMUModule]:
        """Parse all .rst files to extract documented modules"""
        modules = []
        
        # Parse main pyemu.rst
        main_rst = self.docs_path / "pyemu.rst"
        if main_rst.exists():
            modules.extend(self._parse_rst_file(main_rst, "core"))
        
        # Parse subpackage .rst files
        subpackages = {
            "pyemu.utils.rst": "utils",
            "pyemu.pst.rst": "pst",
            "pyemu.mat.rst": "mat",
            "pyemu.plot.rst": "plot",
            "pyemu.prototypes.rst": "prototypes"
        }
        
        for rst_file, category in subpackages.items():
            rst_path = self.docs_path / rst_file
            if rst_path.exists():
                modules.extend(self._parse_rst_file(rst_path, category))
        
        return modules
    
    def _parse_rst_file(self, rst_path: Path, category: str) -> List[PyEMUModule]:
        """Parse a single .rst file for automodule directives"""
        modules = []
        content = rst_path.read_text()
        
        # Pattern to match automodule directives
        # .. automodule:: pyemu.sc
        automodule_pattern = r'^\.\. automodule:: (pyemu[\.\w]+)'
        
        for line in content.split('\n'):
            match = re.match(automodule_pattern, line.strip())
            if match:
                module_path = match.group(1)
                # Extract module name from path
                module_name = module_path.split('.')[-1]
                
                # Get description from our mapping
                description = self.module_descriptions.get(
                    module_name, 
                    f"{category.title()} module: {module_name}"
                )
                
                module = PyEMUModule(
                    module_path=module_path,
                    category=category,
                    description=description,
                    rst_file=str(rst_path.relative_to(self.repo_path))
                )
                modules.append(module)
                
        return modules
    
    def create_processing_queue(self) -> Dict[str, List[Tuple[Path, PyEMUModule]]]:
        """Create a processing queue organized by category"""
        modules = self.parse_rst_files()
        queue = {}
        
        for module in modules:
            file_path = self.repo_path / module.to_file_path()
            
            # Only include if file exists
            if file_path.exists():
                category = module.category
                if category not in queue:
                    queue[category] = []
                queue[category].append((file_path, module))
        
        return queue
    
    def print_summary(self):
        """Print a summary of documented modules"""
        modules = self.parse_rst_files()
        
        print("🔍 pyEMU Documentation Analysis")
        print("=" * 60)
        
        # Group by category
        by_category = {}
        for module in modules:
            if module.category not in by_category:
                by_category[module.category] = []
            by_category[module.category].append(module)
        
        total = 0
        for category, mods in sorted(by_category.items()):
            print(f"\n📁 {category.upper()}: {len(mods)} modules")
            for mod in sorted(mods, key=lambda x: x.module_path):
                file_path = self.repo_path / mod.to_file_path()
                exists = "✓" if file_path.exists() else "✗"
                print(f"  {exists} {mod.module_path:<30} - {mod.description}")
                if exists:
                    total += 1
        
        print(f"\n📊 Total documented modules with files: {total}")
        
        # Check for additional Python files not in docs
        all_py_files = set(self.repo_path.glob("pyemu/**/*.py"))
        documented_files = set()
        for module in modules:
            file_path = self.repo_path / module.to_file_path()
            if file_path.exists():
                documented_files.add(file_path)
        
        undocumented = all_py_files - documented_files
        # Filter out __pycache__, tests, and __init__ files
        undocumented = [f for f in undocumented 
                       if '__pycache__' not in str(f) 
                       and '__init__.py' not in str(f)
                       and 'test' not in str(f).lower()]
        
        if undocumented:
            print(f"\n⚠️  Found {len(undocumented)} Python files not in documentation:")
            for f in sorted(undocumented)[:10]:
                print(f"  - {f.relative_to(self.repo_path)}")
            if len(undocumented) > 10:
                print(f"  ... and {len(undocumented) - 10} more")


if __name__ == "__main__":
    # Test the parser
    parser = PyEMUDocsParser("/home/danilopezmella/flopy_expert/pyemu")
    parser.print_summary()
    
    print("\n\n📋 Processing Queue:")
    queue = parser.create_processing_queue()
    for category, files in queue.items():
        print(f"\n{category}: {len(files)} files")
        for file_path, module in files[:3]:
            print(f"  - {file_path.relative_to(parser.repo_path)}")
        if len(files) > 3:
            print(f"  ... and {len(files) - 3} more")