#!/usr/bin/env python3
"""
Comprehensive MODFLOW 6 Examples Processor with Claude Code SDK Integration

This script creates rich workflow records by combining:
1. LaTeX documentation analysis (/doc/sections/*.tex)
2. Python script code analysis (/scripts/*.py)  
3. Claude Code SDK comprehensive groundwater expertise
4. Precise FloPy module usage extraction

Generates question-oriented, domain-expert semantic database entries optimized for search.
Uses Claude Code SDK for rich analysis with fallback to heuristic analysis.
"""

import os
import re
import glob
import hashlib
import psycopg2
from psycopg2.extras import execute_values
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
from scripts.claude_simple_integration import SimpleClaudeAnalyzer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MODFLOW6ExamplesProcessor:
    """Process MODFLOW 6 examples with multi-source intelligence."""
    
    def __init__(self, base_path: str = "/home/danilopezmella/flopy_expert/modflow6-examples"):
        self.base_path = base_path
        self.doc_path = os.path.join(base_path, "doc", "sections")
        self.script_path = os.path.join(base_path, "scripts")
        self.github_base = "https://github.com/MODFLOW-USGS/modflow6-examples/blob/master/scripts/"
        
        # Initialize Claude analyzer for comprehensive analysis
        try:
            self.claude_analyzer = SimpleClaudeAnalyzer()
            logger.info("Simple Claude analyzer initialized")
        except Exception as e:
            logger.warning(f"Claude analyzer initialization failed: {e}. Will use fallback analysis.")
            self.claude_analyzer = None
    
    def discover_and_map_files(self) -> List[Dict]:
        """Discover and map documentation files to Python scripts."""
        logger.info("Discovering and mapping files...")
        
        # Find all LaTeX documentation files
        doc_pattern = os.path.join(self.doc_path, "ex-*.tex")
        doc_files = glob.glob(doc_pattern)
        
        mappings = []
        for doc_file in doc_files:
            # Extract example name (ex-gwf-bump)
            base_name = os.path.basename(doc_file).replace('.tex', '')
            script_file = os.path.join(self.script_path, f"{base_name}.py")
            
            if os.path.exists(script_file):
                mappings.append({
                    'example_name': base_name,
                    'doc_path': doc_file,
                    'script_path': script_file,
                    'relative_script_path': f"scripts/{base_name}.py",
                    'github_url': f"{self.github_base}{base_name}.py"
                })
            else:
                logger.warning(f"No script found for documentation: {base_name}")
        
        logger.info(f"Found {len(mappings)} valid example mappings")
        return mappings
    
    def parse_latex_doc(self, tex_file: str) -> Dict:
        """Extract structured content from LaTeX documentation."""
        logger.debug(f"Parsing LaTeX: {tex_file}")
        
        try:
            with open(tex_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read {tex_file}: {e}")
            return {}
        
        # Extract sections using regex patterns
        sections = {
            'title': self._extract_section_title(content),
            'description': self._extract_description(content),
            'parameters': self._extract_parameter_references(content),
            'equations': self._extract_equations(content),
            'figures': self._extract_figure_references(content),
            'citations': self._extract_citations(content),
            'scenarios': self._extract_scenarios(content),
            'raw_content': content[:2000]  # First 2000 chars for context
        }
        
        return sections
    
    def _extract_section_title(self, content: str) -> str:
        """Extract the main section title."""
        match = re.search(r'\\section\{([^}]+)\}', content)
        return match.group(1) if match else "Unknown Example"
    
    def _extract_description(self, content: str) -> str:
        """Extract problem description paragraph."""
        # Find content after section title but before first subsection
        pattern = r'\\section\{[^}]+\}\s*\n\s*%?[^\n]*\n(.*?)(?=\\subsection|\\begin\{|$)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            description = match.group(1).strip()
            # Clean up LaTeX formatting
            description = re.sub(r'%.*?\n', '', description)  # Remove comments
            description = re.sub(r'\\cite\{[^}]+\}', '[citation]', description)  # Simplify citations
            description = re.sub(r'\s+', ' ', description)  # Normalize whitespace
            return description[:500]  # Limit length
        return "Description not found"
    
    def _extract_parameter_references(self, content: str) -> List[str]:
        """Extract parameter table references."""
        pattern = r'\\input\{[^}]*tables/([^}]+)\}'
        return re.findall(pattern, content)
    
    def _extract_equations(self, content: str) -> List[str]:
        """Extract equation blocks."""
        pattern = r'\\begin\{equation\}(.*?)\\end\{equation\}'
        equations = re.findall(pattern, content, re.DOTALL)
        return [eq.strip() for eq in equations]
    
    def _extract_figure_references(self, content: str) -> List[str]:
        """Extract figure references."""
        pattern = r'\\begin\{StandardFigure\}.*?\{([^}]+)\}'
        return re.findall(pattern, content, re.DOTALL)
    
    def _extract_citations(self, content: str) -> List[str]:
        """Extract citations."""
        pattern = r'\\cite\{([^}]+)\}'
        return re.findall(pattern, content)
    
    def _extract_scenarios(self, content: str) -> List[str]:
        """Extract scenario/subsection information."""
        pattern = r'\\subsection\{([^}]+)\}'
        return re.findall(pattern, content)
    
    def analyze_python_script(self, script_file: str) -> Dict:
        """Analyze Python script for technical details."""
        logger.debug(f"Analyzing script: {script_file}")
        
        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            logger.error(f"Failed to read {script_file}: {e}")
            return {}
        
        analysis = {
            'source_code': source_code,
            'file_hash': hashlib.sha256(source_code.encode()).hexdigest(),
            'total_lines': len(source_code.splitlines()),
            'packages_used': self._extract_package_codes(source_code),
            'modules_used': self._extract_flopy_modules(source_code),
            'num_steps': self._count_workflow_steps(source_code),
            'model_type': self._detect_model_type(source_code),
            'complexity_score': self._assess_code_complexity(source_code)
        }
        
        return analysis
    
    def _extract_package_codes(self, source_code: str) -> List[str]:
        """Extract MODFLOW package codes from source."""
        # Look for common package patterns
        patterns = [
            r'mf\.([A-Z]{2,4})\(',  # mf.DIS(, mf.WEL(
            r'ModflowGwf([A-Za-z]+)\(',  # ModflowGwfDis(
            r'pname=[\"\']([a-z]+)[\"\']'  # pname="dis"
        ]
        
        packages = set()
        for pattern in patterns:
            matches = re.findall(pattern, source_code, re.IGNORECASE)
            packages.update([m.upper() for m in matches])
        
        return sorted(list(packages))
    
    def _extract_flopy_modules(self, source_code: str) -> List[str]:
        """Extract FloPy module usage patterns."""
        # Reuse the logic from our module extraction system
        patterns = set()
        
        # Direct imports
        for match in re.finditer(r'import\s+(flopy(?:\.[\\w.]+)?)', source_code):
            patterns.add(match.group(1))
        
        # From imports
        for match in re.finditer(r'from\s+(flopy(?:\.[\\w.]+)?)\s+import', source_code):
            patterns.add(match.group(1))
        
        # Usage patterns
        for match in re.finditer(r'(flopy\.[\\w.]+)\(', source_code):
            patterns.add(match.group(1))
        
        return sorted(list(patterns))
    
    def _count_workflow_steps(self, source_code: str) -> int:
        """Count major workflow steps in the code."""
        step_indicators = [
            r'# Step \d+',
            r'## Step \d+',
            r'# \d+\.',
            r'def \w+\(',
            r'sim\s*=',
            r'gwf\s*=',
            r'\.write_simulation\(',
            r'\.run_simulation\('
        ]
        
        total_steps = 0
        for pattern in step_indicators:
            total_steps += len(re.findall(pattern, source_code, re.IGNORECASE))
        
        return max(1, total_steps // 2)  # Normalize and ensure minimum 1
    
    def _detect_model_type(self, source_code: str) -> str:
        """Detect the primary model type from imports and usage."""
        if 'ModflowGwf' in source_code or 'gwf' in source_code.lower():
            if 'ModflowGwt' in source_code or 'gwt' in source_code.lower():
                return 'mf6-coupled'
            return 'mf6-gwf'
        elif 'ModflowGwt' in source_code or 'gwt' in source_code.lower():
            return 'mf6-gwt'
        elif 'ModflowGwe' in source_code or 'gwe' in source_code.lower():
            return 'mf6-gwe'
        elif 'flopy.mf6' in source_code:
            return 'mf6'
        elif 'flopy.modflow' in source_code:
            return 'mf2005'
        else:
            return 'unknown'
    
    def _assess_code_complexity(self, source_code: str) -> float:
        """Assess code complexity on a scale of 0-1."""
        complexity_factors = {
            'functions': len(re.findall(r'def \w+\(', source_code)) * 0.1,
            'classes': len(re.findall(r'class \w+', source_code)) * 0.2,
            'imports': len(re.findall(r'^import|^from', source_code, re.MULTILINE)) * 0.05,
            'equations': len(re.findall(r'np\.|math\.', source_code)) * 0.1,
            'loops': len(re.findall(r'for |while ', source_code)) * 0.1,
            'conditions': len(re.findall(r'if |elif ', source_code)) * 0.05
        }
        
        total_complexity = sum(complexity_factors.values())
        return min(1.0, total_complexity / 10.0)  # Normalize to 0-1
    
    def claude_comprehensive_analysis(self, doc_data: Dict, code_data: Dict, example_name: str) -> Dict:
        """Generate comprehensive analysis using Claude Code SDK."""
        logger.debug(f"Generating Claude analysis for {example_name}")
        
        if self.claude_analyzer:
            try:
                # Use Claude Code SDK for comprehensive analysis
                analysis = self.claude_analyzer.generate_comprehensive_analysis(
                    doc_data, code_data, example_name
                )
                logger.debug(f"Claude analysis successful for {example_name}")
                return analysis
                
            except Exception as e:
                logger.warning(f"Claude analysis failed for {example_name}: {e}. Using fallback.")
        
        # Fallback to heuristic analysis if Claude fails or is unavailable
        logger.debug(f"Using fallback heuristic analysis for {example_name}")
        analysis = {
            'workflow_purpose': self._generate_purpose(doc_data, code_data),
            'best_use_cases': self._generate_use_cases(doc_data, code_data),
            'prerequisites': self._generate_prerequisites(doc_data, code_data),
            'common_modifications': self._generate_modifications(doc_data, code_data),
            'complexity': self._determine_complexity(doc_data, code_data),
            'tags': self._generate_tags(doc_data, code_data, example_name),
            'embedding_text': self._create_embedding_text(doc_data, code_data, example_name)
        }
        
        return analysis
    
    def _generate_purpose(self, doc_data: Dict, code_data: Dict) -> str:
        """Generate workflow purpose from documentation and code."""
        description = doc_data.get('description', '')
        model_type = code_data.get('model_type', 'unknown')
        packages = code_data.get('packages_used', [])
        
        purpose = f"Demonstrates {model_type.upper()} modeling"
        if description and len(description) > 20:
            purpose += f": {description[:200]}"
        if packages:
            purpose += f". Uses packages: {', '.join(packages[:5])}"
        
        return purpose
    
    def _generate_use_cases(self, doc_data: Dict, code_data: Dict) -> List[str]:
        """Generate use cases based on analysis."""
        use_cases = []
        
        model_type = code_data.get('model_type', 'unknown')
        packages = code_data.get('packages_used', [])
        scenarios = doc_data.get('scenarios', [])
        
        # Add model-type specific use cases
        if 'gwf' in model_type:
            use_cases.append("Groundwater flow modeling and analysis")
        if 'gwt' in model_type:
            use_cases.append("Contaminant transport simulation")
        if 'gwe' in model_type:
            use_cases.append("Heat transport and geothermal modeling")
        
        # Add package-specific use cases
        package_uses = {
            'WEL': "Well injection/extraction scenarios",
            'RIV': "Surface water interaction modeling",
            'MAW': "Multi-aquifer well simulation",
            'SFR': "Stream-aquifer interaction",
            'LAK': "Lake-groundwater interaction",
            'UZF': "Unsaturated zone flow modeling"
        }
        
        for pkg in packages:
            if pkg in package_uses:
                use_cases.append(package_uses[pkg])
        
        # Ensure we have at least 2 use cases
        if len(use_cases) < 2:
            use_cases.extend([
                "Educational groundwater modeling",
                "Benchmark testing and validation"
            ])
        
        return use_cases[:5]  # Limit to 5 use cases
    
    def _generate_prerequisites(self, doc_data: Dict, code_data: Dict) -> List[str]:
        """Generate prerequisites based on complexity."""
        prereqs = ["Basic Python programming", "MODFLOW 6 fundamentals"]
        
        complexity = code_data.get('complexity_score', 0.5)
        equations = doc_data.get('equations', [])
        citations = doc_data.get('citations', [])
        
        if complexity > 0.7:
            prereqs.append("Advanced numerical methods")
        if len(equations) > 0:
            prereqs.append("Mathematical modeling concepts")
        if len(citations) > 2:
            prereqs.append("Hydrogeology theory background")
        
        return prereqs
    
    def _generate_modifications(self, doc_data: Dict, code_data: Dict) -> List[str]:
        """Generate common modifications users might make."""
        modifications = []
        
        packages = code_data.get('packages_used', [])
        
        # Common modifications based on packages
        if 'WEL' in packages:
            modifications.append("Adjust well pumping rates and locations")
        if 'RCH' in packages:
            modifications.append("Modify recharge rates for different scenarios")
        if 'CHD' in packages:
            modifications.append("Change boundary head values")
        
        # General modifications
        modifications.extend([
            "Adjust spatial and temporal discretization",
            "Modify hydraulic conductivity values",
            "Change model domain size and boundaries"
        ])
        
        return modifications[:5]
    
    def _determine_complexity(self, doc_data: Dict, code_data: Dict) -> str:
        """Determine complexity level based on multiple factors."""
        complexity_score = code_data.get('complexity_score', 0.5)
        equations = len(doc_data.get('equations', []))
        citations = len(doc_data.get('citations', []))
        packages = len(code_data.get('packages_used', []))
        
        total_score = complexity_score + (equations * 0.1) + (citations * 0.05) + (packages * 0.05)
        
        if total_score > 0.8:
            return "advanced"
        elif total_score > 0.5:
            return "intermediate"
        else:
            return "beginner"
    
    def _generate_tags(self, doc_data: Dict, code_data: Dict, example_name: str) -> List[str]:
        """Generate relevant tags."""
        tags = set()
        
        # Model type tags
        model_type = code_data.get('model_type', '')
        if 'gwf' in model_type:
            tags.update(['groundwater-flow', 'hydraulics'])
        if 'gwt' in model_type:
            tags.update(['transport', 'contamination'])
        if 'gwe' in model_type:
            tags.update(['heat-transport', 'geothermal'])
        
        # Package tags
        packages = code_data.get('packages_used', [])
        package_tags = {
            'WEL': 'wells', 'RIV': 'rivers', 'MAW': 'multi-aquifer-wells',
            'SFR': 'streams', 'LAK': 'lakes', 'UZF': 'unsaturated-zone',
            'NPF': 'node-property-flow', 'STO': 'storage', 'IC': 'initial-conditions'
        }
        
        for pkg in packages:
            if pkg in package_tags:
                tags.add(package_tags[pkg])
        
        # Example name tags
        name_lower = example_name.lower()
        if 'toth' in name_lower:
            tags.add('toth-problem')
        if 'henry' in name_lower:
            tags.add('henry-problem')
        if 'bump' in name_lower:
            tags.add('flow-diversion')
        
        return sorted(list(tags))[:10]  # Limit to 10 tags
    
    def _create_embedding_text(self, doc_data: Dict, code_data: Dict, example_name: str) -> str:
        """Create comprehensive text for embedding generation."""
        components = [
            f"MODFLOW 6 Example: {doc_data.get('title', example_name)}",
            f"Description: {doc_data.get('description', 'No description available')}",
            f"Model Type: {code_data.get('model_type', 'unknown')}",
            f"Packages Used: {', '.join(code_data.get('packages_used', []))}",
            f"Complexity: {self._determine_complexity(doc_data, code_data)}"
        ]
        
        # Add scenarios if available
        scenarios = doc_data.get('scenarios', [])
        if scenarios:
            components.append(f"Scenarios: {', '.join(scenarios)}")
        
        # Add citations if available
        citations = doc_data.get('citations', [])
        if citations:
            components.append(f"References: {', '.join(citations[:3])}")
        
        return ". ".join(components)
    
    def insert_workflow_record(self, record: Dict) -> bool:
        """Insert workflow record into database."""
        try:
            with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
                with conn.cursor() as cur:
                    # Check if record already exists
                    cur.execute(
                        "SELECT id FROM flopy_workflows WHERE tutorial_file = %s AND source_repository = %s",
                        (record['tutorial_file'], record['source_repository'])
                    )
                    
                    if cur.fetchone():
                        logger.info(f"Record already exists: {record['tutorial_file']}")
                        return False
                    
                    # Create dummy embedding vector (1536 dimensions of zeros)
                    dummy_embedding = [0.0] * 1536
                    
                    # Insert new record
                    insert_sql = """
                        INSERT INTO flopy_workflows (
                            tutorial_file, source_repository, github_url, title, description,
                            source_code, file_hash, total_lines, packages_used, modules_used,
                            num_steps, model_type, workflow_purpose, best_use_cases,
                            prerequisites, common_modifications, complexity, tags,
                            embedding_text, embedding, processed_at, extracted_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """
                    
                    cur.execute(insert_sql, (
                        record['tutorial_file'],
                        record['source_repository'],
                        record['github_url'],
                        record['title'],
                        record['description'],
                        record['source_code'],
                        record['file_hash'],
                        record['total_lines'],
                        record['packages_used'],
                        record['modules_used'],
                        record['num_steps'],
                        record['model_type'],
                        record['workflow_purpose'],
                        record['best_use_cases'],
                        record['prerequisites'],
                        record['common_modifications'],
                        record['complexity'],
                        record['tags'],
                        record['embedding_text'],
                        dummy_embedding,
                        record['processed_at'],
                        record['extracted_at']
                    ))
                    
                    conn.commit()
                    logger.info(f"Successfully inserted: {record['tutorial_file']}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to insert record {record['tutorial_file']}: {e}")
            return False
    
    def process_all_examples(self):
        """Process all MODFLOW 6 examples."""
        logger.info("Starting MODFLOW 6 examples processing...")
        
        # Phase 1: Discovery
        mappings = self.discover_and_map_files()
        if not mappings:
            logger.error("No valid mappings found!")
            return
        
        # Phase 2-4: Process each example
        processed_count = 0
        failed_count = 0
        
        for mapping in mappings:
            try:
                logger.info(f"Processing: {mapping['example_name']}")
                
                # Extract documentation
                doc_data = self.parse_latex_doc(mapping['doc_path'])
                
                # Analyze code
                code_data = self.analyze_python_script(mapping['script_path'])
                
                # Claude synthesis (placeholder for now)
                claude_analysis = self.claude_comprehensive_analysis(
                    doc_data, code_data, mapping['example_name']
                )
                
                # Create database record
                record = {
                    'tutorial_file': mapping['relative_script_path'],
                    'source_repository': 'modflow6-examples',
                    'github_url': mapping['github_url'],
                    'title': doc_data.get('title', mapping['example_name']),
                    'description': doc_data.get('description', ''),
                    'source_code': code_data.get('source_code', ''),
                    'file_hash': code_data.get('file_hash', ''),
                    'total_lines': code_data.get('total_lines', 0),
                    'packages_used': code_data.get('packages_used', []),
                    'modules_used': code_data.get('modules_used', []),
                    'num_steps': code_data.get('num_steps', 1),
                    'model_type': code_data.get('model_type', 'unknown'),
                    'workflow_purpose': claude_analysis['workflow_purpose'],
                    'best_use_cases': claude_analysis['best_use_cases'],
                    'prerequisites': claude_analysis['prerequisites'],
                    'common_modifications': claude_analysis['common_modifications'],
                    'complexity': claude_analysis['complexity'],
                    'tags': claude_analysis['tags'],
                    'embedding_text': claude_analysis['embedding_text'],
                    'processed_at': datetime.now(),
                    'extracted_at': datetime.now()
                }
                
                # Insert to database
                if self.insert_workflow_record(record):
                    processed_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to process {mapping['example_name']}: {e}")
                failed_count += 1
                continue
        
        logger.info(f"Processing complete! Processed: {processed_count}, Failed: {failed_count}")


def main():
    processor = MODFLOW6ExamplesProcessor()
    processor.process_all_examples()


if __name__ == "__main__":
    main()