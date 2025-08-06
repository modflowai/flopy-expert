#!/usr/bin/env python3
"""
Enrich GitHub issues with FloPy module references using heuristic matching

This script matches GitHub issues against the flopy_modules database to identify
which modules are referenced in each issue.
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass, asdict
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))
from utils.logging_config import setup_logging


@dataclass
class ModuleMatch:
    """Represents a matched FloPy module"""
    class_name: str
    package_code: str
    file_path: str
    model_family: str
    confidence: str  # high, medium, low
    match_type: str  # class_name_exact, package_code_exact, etc.
    match_context: str  # The actual text that matched


class FloPyModuleMatcher:
    """Matches GitHub issues to FloPy modules using various heuristics"""
    
    def __init__(self, connection_string: str):
        """Initialize with database connection"""
        self.conn = psycopg2.connect(connection_string)
        self.logger = setup_logging("module_matcher")
        self.modules_cache = self._load_modules_cache()
        
    def _load_modules_cache(self) -> Dict[str, Dict]:
        """Load all flopy_modules into memory for fast matching"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, file_path, relative_path, model_family, 
                       package_code, semantic_purpose
                FROM flopy_modules
            """)
            modules = cur.fetchall()
            
        # Create multiple lookup indexes
        self.by_package_code = {}
        self.by_class_name = {}
        self.by_file_path = {}
        self.all_modules = []
        
        for module in modules:
            # Extract class name from file path
            class_name = self._extract_class_name(module['file_path'])
            if class_name:
                module['class_name'] = class_name
                self.by_class_name[class_name.lower()] = module
            
            # Index by package code
            if module['package_code']:
                self.by_package_code[module['package_code'].lower()] = module
            
            # Index by file path
            self.by_file_path[module['file_path']] = module
            
            self.all_modules.append(module)
            
        self.logger.info(f"Loaded {len(self.all_modules)} modules into cache")
        return {m['id']: m for m in modules}
    
    def _extract_class_name(self, file_path: str) -> Optional[str]:
        """Extract class name from file path
        
        Examples:
        - flopy/mf6/modflow/mfgwfmaw.py -> ModflowGwfmaw
        - flopy/modflow/mfwel.py -> ModflowWel
        - flopy/mf6/modflow/mfutlobs.py -> ModflowUtlobs
        """
        # Remove .py extension and get filename
        if not file_path.endswith('.py'):
            return None
            
        filename = Path(file_path).stem
        
        # Skip non-module files
        if filename.startswith('__') or filename in ['test', 'utils', 'common']:
            return None
        
        # Handle different patterns
        if 'mf6' in file_path:
            # mf6 pattern: mfgwfmaw -> ModflowGwfmaw
            if filename.startswith('mf'):
                # Split at model type boundary (mf-gwf-maw)
                parts = []
                if filename.startswith('mfgwf'):
                    parts = ['modflow', 'gwf', filename[5:]]
                elif filename.startswith('mfgwt'):
                    parts = ['modflow', 'gwt', filename[5:]]
                elif filename.startswith('mfutl'):
                    parts = ['modflow', 'utl', filename[5:]]
                elif filename.startswith('mfsim'):
                    parts = ['modflow', 'sim', filename[5:]]
                else:
                    parts = ['modflow', filename[2:]]
                
                # Capitalize and join
                return ''.join(p.capitalize() for p in parts)
        else:
            # Classic pattern: mfwel -> ModflowWel
            if filename.startswith('mf'):
                return 'Modflow' + filename[2:].capitalize()
            elif filename.startswith('mt'):
                return 'Mt3d' + filename[2:].capitalize()
                
        return None
    
    def find_matches(self, issue: Dict) -> List[ModuleMatch]:
        """Find all module matches in an issue"""
        matches = []
        seen = set()  # Avoid duplicates
        
        # Combine all text to search
        search_text = f"{issue.get('title', '')} {issue.get('body', '')}"
        
        # Add comments
        for comment in issue.get('comments', []):
            search_text += f" {comment.get('body', '')}"
        
        # 1. Look for class names (highest confidence)
        matches.extend(self._match_class_names(search_text, seen))
        
        # 2. Look for package codes
        matches.extend(self._match_package_codes(search_text, seen))
        
        # 3. Look for file paths
        matches.extend(self._match_file_paths(search_text, seen))
        
        # 4. Look for error traces
        matches.extend(self._match_error_traces(search_text, seen))
        
        # 5. Look for import statements
        matches.extend(self._match_imports(search_text, seen))
        
        # 6. Natural language matching
        matches.extend(self._match_natural_language(search_text, seen))
        
        return matches
    
    def _match_class_names(self, text: str, seen: Set[str]) -> List[ModuleMatch]:
        """Match exact class names like ModflowGwfmaw"""
        matches = []
        
        # Look for CamelCase patterns that might be class names
        class_patterns = re.findall(r'\b(Modflow[A-Z][a-z]+[a-zA-Z]*)\b', text)
        
        for class_name in class_patterns:
            key = class_name.lower()
            if key in self.by_class_name and key not in seen:
                module = self.by_class_name[key]
                seen.add(key)
                matches.append(ModuleMatch(
                    class_name=class_name,
                    package_code=module['package_code'] or '',
                    file_path=module['file_path'],
                    model_family=module['model_family'],
                    confidence='high',
                    match_type='class_name_exact',
                    match_context=class_name
                ))
        
        return matches
    
    def _match_package_codes(self, text: str, seen: Set[str]) -> List[ModuleMatch]:
        """Match package codes like WEL, MAW, CHD"""
        matches = []
        
        # Common patterns: "WEL package", "MAW module", "CHD boundary"
        package_patterns = [
            r'\b([A-Z]{3,4})\s+(?:package|module|boundary|model)',
            r'(?:package|module)\s+([A-Z]{3,4})\b',
            r'\b([A-Z]{3,4})\b(?:\s+error|\s+issue|\s+problem)'
        ]
        
        for pattern in package_patterns:
            for match in re.finditer(pattern, text):
                code = match.group(1).upper()
                if code in self.by_package_code and code.lower() not in seen:
                    module = self.by_package_code[code.lower()]
                    class_name = module.get('class_name', '')
                    if class_name and class_name.lower() not in seen:
                        seen.add(class_name.lower())
                        seen.add(code.lower())
                        matches.append(ModuleMatch(
                            class_name=class_name,
                            package_code=code,
                            file_path=module['file_path'],
                            model_family=module['model_family'],
                            confidence='high',
                            match_type='package_code_exact',
                            match_context=match.group(0)
                        ))
        
        return matches
    
    def _match_file_paths(self, text: str, seen: Set[str]) -> List[ModuleMatch]:
        """Match file paths mentioned in issues"""
        matches = []
        
        # Look for file paths
        path_pattern = r'(?:flopy[/\\][\w/\\]+\.py)'
        
        for match in re.finditer(path_pattern, text):
            file_path = match.group(0).replace('\\', '/')
            if file_path in self.by_file_path:
                module = self.by_file_path[file_path]
                class_name = module.get('class_name', '')
                if class_name and class_name.lower() not in seen:
                    seen.add(class_name.lower())
                    matches.append(ModuleMatch(
                        class_name=class_name,
                        package_code=module['package_code'] or '',
                        file_path=file_path,
                        model_family=module['model_family'],
                        confidence='high',
                        match_type='file_path_exact',
                        match_context=file_path
                    ))
        
        return matches
    
    def _match_error_traces(self, text: str, seen: Set[str]) -> List[ModuleMatch]:
        """Match modules in error stack traces"""
        matches = []
        
        # Look for traceback patterns
        trace_pattern = r'File\s+"([^"]+flopy[^"]+\.py)"'
        
        for match in re.finditer(trace_pattern, text):
            file_path = match.group(1)
            # Normalize the path
            file_path = file_path.split('site-packages/')[-1]
            file_path = file_path.split('flopy/')[-1]
            file_path = 'flopy/' + file_path
            
            if file_path in self.by_file_path:
                module = self.by_file_path[file_path]
                class_name = module.get('class_name', '')
                if class_name and class_name.lower() not in seen:
                    seen.add(class_name.lower())
                    matches.append(ModuleMatch(
                        class_name=class_name,
                        package_code=module['package_code'] or '',
                        file_path=file_path,
                        model_family=module['model_family'],
                        confidence='high',
                        match_type='error_trace',
                        match_context=match.group(0)
                    ))
        
        return matches
    
    def _match_imports(self, text: str, seen: Set[str]) -> List[ModuleMatch]:
        """Match import statements"""
        matches = []
        
        # Import patterns
        import_patterns = [
            r'from\s+flopy[.\w]*\s+import\s+(\w+)',
            r'import\s+flopy[.\w]*\.(\w+)'
        ]
        
        for pattern in import_patterns:
            for match in re.finditer(pattern, text):
                class_name = match.group(1)
                if class_name.lower() in self.by_class_name and class_name.lower() not in seen:
                    module = self.by_class_name[class_name.lower()]
                    seen.add(class_name.lower())
                    matches.append(ModuleMatch(
                        class_name=class_name,
                        package_code=module['package_code'] or '',
                        file_path=module['file_path'],
                        model_family=module['model_family'],
                        confidence='high',
                        match_type='import_statement',
                        match_context=match.group(0)
                    ))
        
        return matches
    
    def _match_natural_language(self, text: str, seen: Set[str]) -> List[ModuleMatch]:
        """Match natural language descriptions"""
        matches = []
        text_lower = text.lower()
        
        # Natural language mappings
        nl_mappings = {
            'well': ['WEL', 'MAW'],
            'multi-aquifer well': ['MAW'],
            'multiaquifer well': ['MAW'],
            'constant head': ['CHD'],
            'drain': ['DRN'],
            'river': ['RIV'],
            'general head': ['GHB'],
            'recharge': ['RCH', 'RCA'],
            'evapotranspiration': ['EVT', 'ETA'],
            'stream': ['SFR', 'STR'],
            'lake': ['LAK'],
            'unsaturated zone': ['UZF'],
            'storage': ['STO'],
            'specific storage': ['STO'],
            'node property flow': ['NPF'],
            'horizontal flow barrier': ['HFB'],
            'ghost node': ['GNC'],
            'buoyancy': ['BUY'],
            'subsidence': ['CSUB'],
            'discretization': ['DIS', 'DISV', 'DISU']
        }
        
        for term, codes in nl_mappings.items():
            if term in text_lower:
                for code in codes:
                    if code.lower() in self.by_package_code and code.lower() not in seen:
                        module = self.by_package_code[code.lower()]
                        class_name = module.get('class_name', '')
                        if class_name and class_name.lower() not in seen:
                            seen.add(class_name.lower())
                            matches.append(ModuleMatch(
                                class_name=class_name,
                                package_code=code,
                                file_path=module['file_path'],
                                model_family=module['model_family'],
                                confidence='medium',
                                match_type='natural_language',
                                match_context=term
                            ))
        
        return matches
    
    def enrich_issues(self, issues: List[Dict]) -> List[Dict]:
        """Enrich a list of issues with module matches"""
        enriched = []
        
        for i, issue in enumerate(issues):
            if (i + 1) % 10 == 0:
                self.logger.info(f"Processing issue {i + 1}/{len(issues)}")
            
            matches = self.find_matches(issue)
            
            enriched_issue = {
                'issue_number': issue['number'],
                'title': issue['title'],
                'matched_modules': [asdict(m) for m in matches],
                'match_count': len(matches),
                'has_high_confidence': any(m.confidence == 'high' for m in matches),
                'original_issue': issue
            }
            
            enriched.append(enriched_issue)
        
        return enriched
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Enrich GitHub issues with FloPy module references")
    parser.add_argument("--input", required=True, help="Input JSON file pattern")
    parser.add_argument("--output", default="../data/enriched/", help="Output directory")
    
    args = parser.parse_args()
    
    # Set up output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    connection_string = os.getenv("NEON_CONNECTION_STRING")
    if not connection_string:
        print("Error: NEON_CONNECTION_STRING not set in .env")
        sys.exit(1)
    
    # Initialize matcher
    matcher = FloPyModuleMatcher(connection_string)
    
    # Find input files
    input_pattern = Path(args.input)
    input_files = list(input_pattern.parent.glob(input_pattern.name))
    
    if not input_files:
        print(f"No files found matching pattern: {args.input}")
        sys.exit(1)
    
    for input_file in input_files:
        print(f"\nProcessing: {input_file}")
        
        # Load issues
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        issues = data.get('issues', [])
        print(f"Found {len(issues)} issues to process")
        
        # Enrich with module matches
        enriched = matcher.enrich_issues(issues)
        
        # Calculate statistics
        stats = {
            'total_issues': len(enriched),
            'issues_with_matches': sum(1 for e in enriched if e['match_count'] > 0),
            'total_matches': sum(e['match_count'] for e in enriched),
            'high_confidence_issues': sum(1 for e in enriched if e['has_high_confidence']),
            'avg_matches_per_issue': sum(e['match_count'] for e in enriched) / len(enriched) if enriched else 0
        }
        
        # Save enriched data
        output_file = output_dir / f"enriched_{input_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_data = {
            'metadata': {
                'source_file': str(input_file),
                'enrichment_date': datetime.now().isoformat(),
                'statistics': stats
            },
            'enriched_issues': enriched
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"Saved enriched data to: {output_file}")
        print(f"Statistics:")
        print(f"  Issues with matches: {stats['issues_with_matches']}/{stats['total_issues']}")
        print(f"  Total matches: {stats['total_matches']}")
        print(f"  High confidence: {stats['high_confidence_issues']}")
        print(f"  Avg matches/issue: {stats['avg_matches_per_issue']:.1f}")
    
    matcher.close()


if __name__ == "__main__":
    main()