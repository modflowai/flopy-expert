#!/usr/bin/env python3
"""
Test MODFLOW 6 Examples Processor - Insert One Example
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.process_modflow6_examples import MODFLOW6ExamplesProcessor
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_insert_one():
    """Test inserting one MODFLOW 6 example."""
    processor = MODFLOW6ExamplesProcessor()
    
    # Get mappings
    mappings = processor.discover_and_map_files()
    
    # Find the bump example (simple)
    test_mapping = None
    for mapping in mappings:
        if 'bump' in mapping['example_name']:
            test_mapping = mapping
            break
    
    if not test_mapping:
        logger.error("Could not find bump example!")
        return
    
    logger.info(f"Processing and inserting: {test_mapping['example_name']}")
    
    try:
        # Extract documentation
        doc_data = processor.parse_latex_doc(test_mapping['doc_path'])
        
        # Analyze code
        code_data = processor.analyze_python_script(test_mapping['script_path'])
        
        # Claude synthesis
        claude_analysis = processor.claude_comprehensive_analysis(
            doc_data, code_data, test_mapping['example_name']
        )
        
        # Create database record
        record = {
            'tutorial_file': test_mapping['relative_script_path'],
            'source_repository': 'modflow6-examples',
            'github_url': test_mapping['github_url'],
            'title': doc_data.get('title', test_mapping['example_name']),
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
        success = processor.insert_workflow_record(record)
        
        if success:
            logger.info("✅ Successfully inserted single MODFLOW 6 example!")
        else:
            logger.error("❌ Failed to insert example")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_insert_one()