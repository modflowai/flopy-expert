#!/usr/bin/env python3
"""
Comprehensive LangExtract processor for FloPy GitHub issues

Extracts all relevant information in a single pass:
- Problems and errors
- Module references and relationships
- Code snippets and solutions
- Environment details
- Resolution patterns
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from collections import defaultdict
import time

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))
from utils.logging_config import setup_logging

# Import LangExtract
try:
    import langextract
    from langextract import data
except ImportError:
    print("Error: LangExtract not installed. Install with: pip install langextract")
    sys.exit(1)

from extraction_schema import (
    PROBLEM_EXAMPLES,
    MODULE_EXAMPLES,
    CODE_SNIPPET_EXAMPLES,
    RESOLUTION_EXAMPLES,
    ENVIRONMENT_EXAMPLES,
    COMMENT_INSIGHT_EXAMPLES,
    ExtractionPrompts
)


class ComprehensiveIssueExtractor:
    """Extracts comprehensive structured data from FloPy GitHub issues"""
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize with Gemini model"""
        self.logger = setup_logging("langextract_processor")
        
        # Initialize Gemini client
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")
            
        self.client = genai.Client(api_key=api_key)
        self.model = model_name
        self.logger.info(f"Initialized with model: {model_name}")
        
        # Initialize extractors for each type
        self.extractors = self._initialize_extractors()
        
    def _initialize_extractors(self) -> Dict[str, LangExtract]:
        """Initialize LangExtract instances for each extraction type"""
        extractors = {}
        
        # Problem extractor
        extractors['problem'] = LangExtract(
            client=self.client,
            model=self.model,
            instruction=ExtractionPrompts.PROBLEM_EXTRACTION,
            examples=PROBLEM_EXAMPLES
        )
        
        # Module extractor
        extractors['module'] = LangExtract(
            client=self.client,
            model=self.model,
            instruction=ExtractionPrompts.MODULE_EXTRACTION,
            examples=MODULE_EXAMPLES
        )
        
        # Code extractor
        extractors['code'] = LangExtract(
            client=self.client,
            model=self.model,
            instruction=ExtractionPrompts.CODE_EXTRACTION,
            examples=CODE_SNIPPET_EXAMPLES
        )
        
        # Resolution extractor
        extractors['resolution'] = LangExtract(
            client=self.client,
            model=self.model,
            instruction=ExtractionPrompts.RESOLUTION_EXTRACTION,
            examples=RESOLUTION_EXAMPLES
        )
        
        # Environment extractor
        extractors['environment'] = LangExtract(
            client=self.client,
            model=self.model,
            instruction=ExtractionPrompts.ENVIRONMENT_EXTRACTION,
            examples=ENVIRONMENT_EXAMPLES
        )
        
        # Comment insights extractor
        extractors['comments'] = LangExtract(
            client=self.client,
            model=self.model,
            instruction="Extract insights from comments",
            examples=COMMENT_INSIGHT_EXAMPLES
        )
        
        return extractors
    
    def _prepare_issue_text(self, issue: Dict) -> str:
        """Prepare complete issue text for extraction"""
        parts = []
        
        # Title and body
        parts.append(f"TITLE: {issue.get('title', '')}")
        parts.append(f"BODY:\n{issue.get('body', '')}")
        
        # Labels
        if issue.get('labels'):
            parts.append(f"LABELS: {', '.join(issue['labels'])}")
        
        # Comments
        comments = issue.get('comments', [])
        if comments:
            parts.append("\nCOMMENTS:")
            for i, comment in enumerate(comments, 1):
                author = comment.get('author', 'unknown')
                body = comment.get('body', '')
                parts.append(f"\nComment {i} by {author}:")
                parts.append(body)
        
        # Metadata
        parts.append(f"\nCREATED: {issue.get('created_at', '')}")
        parts.append(f"CLOSED: {issue.get('closed_at', '')}")
        parts.append(f"STATE: {issue.get('state', '')}")
        
        return "\n\n".join(parts)
    
    def extract_comprehensive(self, issue: Dict) -> Dict[str, Any]:
        """Extract all information from an issue"""
        issue_text = self._prepare_issue_text(issue)
        
        extraction_result = {
            'issue_number': issue.get('number'),
            'title': issue.get('title'),
            'extractions': {},
            'metadata': {
                'extraction_timestamp': datetime.now().isoformat(),
                'model': self.model
            }
        }
        
        # Run all extractors
        for extractor_name, extractor in self.extractors.items():
            try:
                self.logger.debug(f"Running {extractor_name} extractor on issue #{issue.get('number')}")
                
                # Extract with LangExtract
                result = extractor.extract(issue_text)
                
                # Process and store results
                extraction_result['extractions'][extractor_name] = self._process_extraction(result)
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error in {extractor_name} extraction: {e}")
                extraction_result['extractions'][extractor_name] = {'error': str(e)}
        
        # Add module relationships
        extraction_result['extractions']['relationships'] = self._extract_relationships(
            issue_text, 
            extraction_result['extractions']
        )
        
        return extraction_result
    
    def _process_extraction(self, result: Any) -> Dict:
        """Process LangExtract result into structured format"""
        if hasattr(result, 'extractions'):
            # Convert extractions to dict format
            extractions = []
            for extraction in result.extractions:
                ext_dict = {
                    'text': extraction.text,
                    'attributes': extraction.attributes if hasattr(extraction, 'attributes') else {}
                }
                extractions.append(ext_dict)
            return {'extractions': extractions}
        else:
            return {'raw_result': str(result)}
    
    def _extract_relationships(self, issue_text: str, extractions: Dict) -> List[Dict]:
        """Extract relationships between modules based on context"""
        relationships = []
        
        # Look for common patterns
        patterns = [
            (r'(\w+)\s+(?:doesn\'t|does not)\s+work\s+with\s+(\w+)', 'incompatible_with'),
            (r'(\w+)\s+conflicts?\s+with\s+(\w+)', 'conflicts_with'),
            (r'(\w+)\s+requires?\s+(\w+)', 'requires'),
            (r'(\w+)\s+depends?\s+on\s+(\w+)', 'depends_on'),
            (r'error\s+in\s+(\w+)\s+affects?\s+(\w+)', 'affects'),
        ]
        
        for pattern, rel_type in patterns:
            for match in re.finditer(pattern, issue_text, re.IGNORECASE):
                relationships.append({
                    'type': rel_type,
                    'source': match.group(1),
                    'target': match.group(2),
                    'evidence': match.group(0)
                })
        
        return relationships
    
    def process_issues(self, issues: List[Dict]) -> List[Dict]:
        """Process multiple issues"""
        results = []
        
        for i, issue in enumerate(issues):
            self.logger.info(f"Processing issue {i+1}/{len(issues)}: #{issue.get('issue_number', 'unknown')}")
            
            try:
                result = self.extract_comprehensive(issue.get('original_issue', issue))
                results.append(result)
                
                # Save intermediate results every 10 issues
                if (i + 1) % 10 == 0:
                    self.logger.info(f"Processed {i+1} issues, saving intermediate results...")
                    
            except Exception as e:
                self.logger.error(f"Failed to process issue #{issue.get('issue_number')}: {e}")
                results.append({
                    'issue_number': issue.get('issue_number'),
                    'error': str(e)
                })
        
        return results
    
    def analyze_extraction_quality(self, results: List[Dict]) -> Dict:
        """Analyze the quality of extractions"""
        stats = {
            'total_issues': len(results),
            'successful_extractions': 0,
            'extraction_coverage': defaultdict(int),
            'modules_found': defaultdict(int),
            'resolution_types': defaultdict(int),
            'problem_categories': defaultdict(int)
        }
        
        for result in results:
            if 'error' not in result:
                stats['successful_extractions'] += 1
                
                # Check coverage
                for extractor_name in self.extractors.keys():
                    if extractor_name in result.get('extractions', {}):
                        stats['extraction_coverage'][extractor_name] += 1
                
                # Analyze specific extractions
                if 'module' in result.get('extractions', {}):
                    modules = result['extractions']['module'].get('extractions', [])
                    for mod in modules:
                        if 'module_name' in mod.get('attributes', {}):
                            stats['modules_found'][mod['attributes']['module_name']] += 1
                
                if 'resolution' in result.get('extractions', {}):
                    resolutions = result['extractions']['resolution'].get('extractions', [])
                    for res in resolutions:
                        if 'resolution_type' in res.get('attributes', {}):
                            stats['resolution_types'][res['attributes']['resolution_type']] += 1
        
        return dict(stats)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Extract comprehensive data from FloPy issues")
    parser.add_argument("--input", required=True, help="Input enriched JSON file")
    parser.add_argument("--output", default="../data/extracted/", help="Output directory")
    parser.add_argument("--limit", type=int, help="Limit number of issues to process")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gemini model to use")
    
    args = parser.parse_args()
    
    # Load environment
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent.parent / '.env'
    load_dotenv(env_path)
    
    # Set up output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize extractor
    extractor = ComprehensiveIssueExtractor(model_name=args.model)
    
    # Load input data
    input_file = Path(args.input)
    print(f"Loading issues from: {input_file}")
    
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    issues = data.get('enriched_issues', [])
    if args.limit:
        issues = issues[:args.limit]
    
    print(f"Processing {len(issues)} issues...")
    
    # Process issues
    results = extractor.process_issues(issues)
    
    # Analyze quality
    stats = extractor.analyze_extraction_quality(results)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"comprehensive_extraction_{timestamp}.json"
    
    output_data = {
        'metadata': {
            'source_file': str(input_file),
            'extraction_date': datetime.now().isoformat(),
            'model': args.model,
            'statistics': stats
        },
        'extracted_issues': results
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nExtraction complete!")
    print(f"Results saved to: {output_file}")
    print(f"\nStatistics:")
    print(f"  Successful: {stats['successful_extractions']}/{stats['total_issues']}")
    print(f"  Coverage by extractor:")
    for extractor, count in stats['extraction_coverage'].items():
        print(f"    {extractor}: {count}")
    print(f"  Top modules found:")
    for module, count in sorted(stats['modules_found'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"    {module}: {count}")


if __name__ == "__main__":
    main()