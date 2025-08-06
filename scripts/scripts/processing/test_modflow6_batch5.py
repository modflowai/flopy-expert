#!/usr/bin/env python3
"""
Test MODFLOW 6 Examples Processor - Process 5 Examples
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.process_modflow6_examples import MODFLOW6ExamplesProcessor
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_batch_5():
    """Test processing 5 MODFLOW 6 examples."""
    processor = MODFLOW6ExamplesProcessor()
    
    # Get mappings
    mappings = processor.discover_and_map_files()
    
    # Select 5 diverse examples for testing
    test_examples = ['toth', 'henry', 'radial', 'maw-p01', 'bump']  # bump already exists, will skip
    test_mappings = []
    
    for example_name in test_examples:
        for mapping in mappings:
            if example_name in mapping['example_name']:
                test_mappings.append(mapping)
                break
    
    # If we don't have enough, just take first 5
    if len(test_mappings) < 5:
        test_mappings = mappings[:5]
    
    logger.info(f"Processing {len(test_mappings)} examples:")
    for mapping in test_mappings:
        logger.info(f"  - {mapping['example_name']}")
    
    # Process each example
    processed_count = 0
    failed_count = 0
    
    for mapping in test_mappings:
        try:
            logger.info(f"Processing: {mapping['example_name']}")
            
            # Extract documentation
            doc_data = processor.parse_latex_doc(mapping['doc_path'])
            
            # Analyze code  
            code_data = processor.analyze_python_script(mapping['script_path'])
            
            # Claude synthesis
            claude_analysis = processor.claude_comprehensive_analysis(
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
            if processor.insert_workflow_record(record):
                processed_count += 1
                logger.info(f"✅ Successfully processed: {mapping['example_name']}")
            else:
                logger.info(f"⏭️  Skipped (already exists): {mapping['example_name']}")
                processed_count += 1  # Count as success since it exists
                
        except Exception as e:
            logger.error(f"❌ Failed to process {mapping['example_name']}: {e}")
            failed_count += 1
            continue
    
    logger.info(f"Batch processing complete! Processed: {processed_count}, Failed: {failed_count}")
    
    # Show what we have in the database now
    import psycopg2
    import config
    
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tutorial_file, title, model_type, complexity 
                FROM flopy_workflows 
                WHERE source_repository = 'modflow6-examples'
                ORDER BY tutorial_file
            """)
            
            results = cur.fetchall()
            logger.info(f"\nMODFLOW 6 examples in database ({len(results)}):")
            for row in results:
                logger.info(f"  {row[0]} - {row[1]} ({row[2]}, {row[3]})")

if __name__ == "__main__":
    test_batch_5()