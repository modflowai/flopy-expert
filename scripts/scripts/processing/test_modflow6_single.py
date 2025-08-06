#!/usr/bin/env python3
"""
Test MODFLOW 6 Examples Processor with Single Example
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.process_modflow6_examples import MODFLOW6ExamplesProcessor
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_single_example():
    """Test with a single example to debug issues."""
    processor = MODFLOW6ExamplesProcessor()
    
    # Get mappings but only process the first one
    mappings = processor.discover_and_map_files()
    
    if not mappings:
        logger.error("No mappings found!")
        return
    
    # Pick a simple example for testing
    test_mapping = None
    for mapping in mappings:
        if 'bump' in mapping['example_name']:  # Simple flow diversion example
            test_mapping = mapping
            break
    
    if not test_mapping:
        test_mapping = mappings[0]  # Just use first one
    
    logger.info(f"Testing with: {test_mapping['example_name']}")
    
    try:
        # Test each phase separately
        logger.info("Phase 1: Parsing LaTeX documentation...")
        doc_data = processor.parse_latex_doc(test_mapping['doc_path'])
        logger.info(f"Doc title: {doc_data.get('title', 'N/A')}")
        logger.info(f"Doc description length: {len(doc_data.get('description', ''))}")
        
        logger.info("Phase 2: Analyzing Python script...")
        code_data = processor.analyze_python_script(test_mapping['script_path'])
        logger.info(f"Code lines: {code_data.get('total_lines', 0)}")
        logger.info(f"Packages found: {code_data.get('packages_used', [])}")
        logger.info(f"Model type: {code_data.get('model_type', 'unknown')}")
        
        logger.info("Phase 3: Claude analysis...")
        claude_analysis = processor.claude_comprehensive_analysis(
            doc_data, code_data, test_mapping['example_name']
        )
        logger.info(f"Generated purpose: {claude_analysis['workflow_purpose'][:100]}...")
        logger.info(f"Complexity: {claude_analysis['complexity']}")
        logger.info(f"Tags: {claude_analysis['tags'][:5]}")
        
        # Create record but don't insert yet
        record = {
            'tutorial_file': test_mapping['relative_script_path'],
            'source_repository': 'modflow6-examples',
            'github_url': test_mapping['github_url'],
            'title': doc_data.get('title', test_mapping['example_name']),
            'description': doc_data.get('description', ''),
            'workflow_purpose': claude_analysis['workflow_purpose'],
            'best_use_cases': claude_analysis['best_use_cases'],
            'prerequisites': claude_analysis['prerequisites'],
            'common_modifications': claude_analysis['common_modifications'],
            'complexity': claude_analysis['complexity'],
            'tags': claude_analysis['tags'],
            'embedding_text': claude_analysis['embedding_text']
        }
        
        logger.info("✅ Successfully processed single example!")
        logger.info("Record preview:")
        for key, value in record.items():
            if isinstance(value, str) and len(value) > 100:
                logger.info(f"  {key}: {value[:100]}...")
            else:
                logger.info(f"  {key}: {value}")
                
    except Exception as e:
        logger.error(f"Failed to process example: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_example()