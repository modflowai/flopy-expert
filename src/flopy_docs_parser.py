#!/usr/bin/env python3
"""
Documentation Parser for FloPy Semantic Database

Parses .docs/code.rst to extract documented module patterns and create
a curated processing queue following the documentation structure.

This implements Step 1 of our roadmap: Documentation-Driven Discovery
"""
import re
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
import glob


@dataclass
class ModulePattern:
    """Represents a documented module pattern from code.rst"""
    pattern: str  # Original pattern like "flopy.mf6.modflow.mfgwf*"
    section: str  # Section name like "MODFLOW 6 Groundwater Flow Model Packages"
    model_family: str  # Extracted family like "mf6", "modflow", "mt3d"
    description: str  # Description of the section


class FloPyDocsParser:
    """Parser for FloPy documentation structure"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.docs_file = self.repo_path / "flopy" / ".docs" / "code.rst"
        
        if not self.docs_file.exists():
            raise FileNotFoundError(f"Documentation file not found: {self.docs_file}")
    
    def parse_documented_modules(self) -> List[ModulePattern]:
        """
        Parse code.rst and extract all documented module patterns
        
        Returns list of ModulePattern objects with context about each pattern
        """
        patterns = []
        content = self.docs_file.read_text()
        
        # Split into sections by headers
        sections = self._split_into_sections(content)
        
        for section_name, section_content in sections:
            # Extract toctree patterns from this section
            toctree_patterns = self._extract_toctree_patterns(section_content)
            
            for pattern in toctree_patterns:
                # Skip non-module patterns (like exclude-members directives)
                if not pattern.startswith("./source/flopy."):
                    continue
                    
                # Clean up the pattern
                clean_pattern = pattern.replace("./source/", "").replace(".rst", "")
                
                # Extract model family
                model_family = self._extract_model_family(clean_pattern)
                
                patterns.append(ModulePattern(
                    pattern=clean_pattern,
                    section=section_name,
                    model_family=model_family,
                    description=self._extract_section_description(section_content)
                ))
        
        return patterns
    
    def _split_into_sections(self, content: str) -> List[Tuple[str, str]]:
        """Split RST content into sections by headers"""
        sections = []
        lines = content.split('\n')
        
        current_section = ""
        current_content = []
        
        for i, line in enumerate(lines):
            # Check if next line is a header underline
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # RST headers use = or ^ or - as underlines
                if len(next_line) > 0 and all(c in "=^-" for c in next_line) and len(next_line) >= len(line):
                    # Save previous section
                    if current_section:
                        sections.append((current_section, "\n".join(current_content)))
                    
                    # Start new section
                    current_section = line.strip()
                    current_content = []
                    continue
            
            current_content.append(line)
        
        # Add final section
        if current_section:
            sections.append((current_section, "\n".join(current_content)))
        
        return sections
    
    def _extract_toctree_patterns(self, section_content: str) -> List[str]:
        """Extract patterns from toctree directives"""
        patterns = []
        lines = section_content.split('\n')
        
        in_toctree = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Start of toctree
            if stripped.startswith(".. toctree::"):
                in_toctree = True
                continue
            
            # End of toctree - next directive
            if in_toctree and stripped.startswith(".."):
                in_toctree = False
                continue
            
            # Skip toctree options
            if in_toctree and stripped.startswith(":"):
                continue
            
            # Extract pattern
            if in_toctree and stripped and not stripped.startswith(":"):
                patterns.append(stripped)
        
        return patterns
    
    def _extract_model_family(self, pattern: str) -> str:
        """Extract model family from pattern like flopy.mf6.modflow.mfgwf*"""
        parts = pattern.split('.')
        
        if len(parts) >= 2:
            if parts[1] in ['mf6']:
                return 'mf6'
            elif parts[1] in ['modflow']:
                return 'modflow' 
            elif parts[1] in ['mt3d']:
                return 'mt3d'
            elif parts[1] in ['seawat']:
                return 'seawat'
            elif parts[1] in ['modpath']:
                return 'modpath'
            elif parts[1] in ['utils']:
                return 'utils'
            elif parts[1] in ['plot']:
                return 'plot'
            elif parts[1] in ['export']:
                return 'export'
            elif parts[1] in ['pest']:
                return 'pest'
            elif parts[1] in ['discretization']:
                return 'discretization'
        
        return 'unknown'
    
    def _extract_section_description(self, section_content: str) -> str:
        """Extract description from section content"""
        lines = section_content.split('\n')
        description_lines = []
        
        # Look for description before toctree
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(".. toctree::"):
                break
            if stripped and not stripped.startswith("Contents:") and not stripped.startswith("^^"):
                description_lines.append(stripped)
        
        return " ".join(description_lines[:3])  # First 3 meaningful lines
    
    def resolve_patterns_to_files(self, patterns: List[ModulePattern]) -> List[Tuple[Path, ModulePattern]]:
        """
        Convert documentation patterns to actual file paths
        
        Args:
            patterns: List of ModulePattern objects
            
        Returns:
            List of (file_path, pattern) tuples for files that actually exist
        """
        resolved = []
        
        for pattern in patterns:
            # Convert pattern to file glob - need to add 'flopy/' prefix for the actual repo structure
            file_pattern = pattern.pattern.replace('.', '/') + '.py'
            
            # Handle wildcards
            if '*' in file_pattern:
                # Use glob to find matching files
                search_path = self.repo_path / "flopy" / file_pattern
                matches = glob.glob(str(search_path))
                
                for match in matches:
                    file_path = Path(match)
                    if file_path.exists() and file_path.suffix == '.py':
                        resolved.append((file_path, pattern))
            else:
                # Direct file path
                file_path = self.repo_path / "flopy" / file_pattern
                if file_path.exists():
                    resolved.append((file_path, pattern))
        
        return resolved
    
    def create_processing_queue(self) -> Dict[str, List[Tuple[Path, ModulePattern]]]:
        """
        Create organized processing queue grouped by model family
        
        Returns:
            Dictionary with model_family as key and list of (file_path, pattern) as value
        """
        patterns = self.parse_documented_modules()
        resolved_files = self.resolve_patterns_to_files(patterns)
        
        # Group by model family
        queue = {}
        for file_path, pattern in resolved_files:
            family = pattern.model_family
            if family not in queue:
                queue[family] = []
            queue[family].append((file_path, pattern))
        
        return queue
    
    def print_processing_summary(self):
        """Print summary of what will be processed"""
        queue = self.create_processing_queue()
        
        total_files = sum(len(files) for files in queue.values())
        
        print(f"FloPy Documentation-Driven Processing Summary")
        print(f"=" * 50)
        print(f"Total documented modules to process: {total_files}")
        print()
        
        # Sort by priority (MF6 first, then others)
        priority_order = ['mf6', 'modflow', 'mt3d', 'seawat', 'modpath', 'utils', 'plot', 'export', 'pest', 'discretization']
        
        for family in priority_order:
            if family in queue:
                files = queue[family]
                print(f"{family.upper()}: {len(files)} modules")
                
                # Show first few examples
                for i, (file_path, pattern) in enumerate(files[:3]):
                    rel_path = file_path.relative_to(self.repo_path)
                    print(f"  - {rel_path}")
                
                if len(files) > 3:
                    print(f"  ... and {len(files) - 3} more")
                print()
        
        # Show any unknown families
        for family in queue:
            if family not in priority_order:
                files = queue[family]
                print(f"{family.upper()}: {len(files)} modules")


def main():
    """Test the documentation parser"""
    parser = FloPyDocsParser("/home/danilopezmella/flopy_expert")
    
    print("Parsing FloPy documentation structure...")
    parser.print_processing_summary()
    
    # Save the queue for use by processing pipeline
    queue = parser.create_processing_queue()
    
    print(f"\nProcessing queue created with {sum(len(files) for files in queue.values())} total files")
    print("Ready for Step 2: Batch Processing with Checkpoints")


if __name__ == "__main__":
    main()