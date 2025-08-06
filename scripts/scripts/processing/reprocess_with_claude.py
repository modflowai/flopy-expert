#!/usr/bin/env python3
"""
Reprocess MODFLOW 6 Examples with Enhanced Claude Analysis
Updates existing records with rich Claude-powered analysis.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.process_modflow6_examples import MODFLOW6ExamplesProcessor
import psycopg2
import config
from datetime import datetime
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def reprocess_all_with_claude():
    """Reprocess all MODFLOW 6 examples with enhanced Claude analysis."""
    
    processor = MODFLOW6ExamplesProcessor()
    
    # Get all existing MODFLOW 6 records
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tutorial_file, source_code, file_hash 
                FROM flopy_workflows 
                WHERE source_repository = 'modflow6-examples'
                ORDER BY tutorial_file
            """)
            
            existing_records = cur.fetchall()
            logger.info(f"Found {len(existing_records)} existing MODFLOW 6 records to enhance")
    
    # Get all mappings for processing
    mappings = processor.discover_and_map_files()
    mapping_dict = {m['relative_script_path']: m for m in mappings}
    
    updated_count = 0
    failed_count = 0
    
    for tutorial_file, stored_source, stored_hash in existing_records:
        if tutorial_file not in mapping_dict:
            logger.warning(f"No mapping found for {tutorial_file}")
            continue
            
        mapping = mapping_dict[tutorial_file]
        example_name = mapping['example_name']
        
        try:
            logger.info(f"Reprocessing: {example_name}")
            start_time = time.time()
            
            # Parse documentation
            doc_data = processor.parse_latex_doc(mapping['doc_path'])
            
            # Analyze code (should be same as stored)
            code_data = processor.analyze_python_script(mapping['script_path'])
            
            # Generate enhanced Claude analysis
            claude_analysis = processor.claude_comprehensive_analysis(
                doc_data, code_data, example_name
            )
            
            # Update the record with enhanced analysis
            with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
                with conn.cursor() as cur:
                    update_sql = """
                        UPDATE flopy_workflows SET
                            workflow_purpose = %s,
                            best_use_cases = %s,
                            prerequisites = %s,
                            common_modifications = %s,
                            complexity = %s,
                            tags = %s,
                            embedding_text = %s,
                            processed_at = %s
                        WHERE tutorial_file = %s AND source_repository = 'modflow6-examples'
                    """
                    
                    cur.execute(update_sql, (
                        claude_analysis['workflow_purpose'],
                        claude_analysis['best_use_cases'],
                        claude_analysis['prerequisites'],
                        claude_analysis['common_modifications'],
                        claude_analysis['complexity'],
                        claude_analysis['tags'],
                        claude_analysis['embedding_text'],
                        datetime.now(),
                        tutorial_file
                    ))
                    
                    conn.commit()
            
            updated_count += 1
            processing_time = time.time() - start_time
            logger.info(f"  ✅ Enhanced ({processing_time:.1f}s): {example_name}")
            
            # Brief pause to avoid overwhelming
            time.sleep(0.2)
            
        except Exception as e:
            failed_count += 1
            logger.error(f"  ❌ Failed to enhance {example_name}: {e}")
            continue
    
    logger.info(f"Reprocessing complete! Enhanced: {updated_count}, Failed: {failed_count}")
    
    # Show sample of enhanced records
    logger.info("Sample of enhanced records:")
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tutorial_file, complexity, array_length(tags, 1) as tag_count,
                       length(embedding_text) as embedding_length
                FROM flopy_workflows 
                WHERE source_repository = 'modflow6-examples'
                ORDER BY tutorial_file
                LIMIT 10
            """)
            
            for row in cur.fetchall():
                logger.info(f"  {row[0]}: {row[1]}, {row[2]} tags, {row[3]} chars embedding")


if __name__ == "__main__":
    reprocess_all_with_claude()