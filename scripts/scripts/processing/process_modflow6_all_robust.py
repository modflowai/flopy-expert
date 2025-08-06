#!/usr/bin/env python3
"""
Robust MODFLOW 6 Examples Processor - All 73 Examples
Features checkpoint saving, resume capability, and error recovery.
"""

import os
import json
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.process_modflow6_examples import MODFLOW6ExamplesProcessor
from datetime import datetime
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RobustMODFLOW6Processor(MODFLOW6ExamplesProcessor):
    """Enhanced processor with checkpoint saving and resume capability."""
    
    def __init__(self, base_path: str = "/home/danilopezmella/flopy_expert/modflow6-examples"):
        super().__init__(base_path)
        self.checkpoint_dir = "/home/danilopezmella/flopy_expert/processing_checkpoints"
        self.checkpoint_file = os.path.join(self.checkpoint_dir, "modflow6_processing.json")
        
        # Ensure checkpoint directory exists
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        
    def load_checkpoint(self) -> dict:
        """Load processing checkpoint if it exists."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                    logger.info(f"Loaded checkpoint: {len(checkpoint.get('processed', []))} examples already processed")
                    return checkpoint
            except Exception as e:
                logger.warning(f"Could not load checkpoint: {e}")
        
        return {
            'processed': [],
            'failed': [],
            'started_at': datetime.now().isoformat(),
            'last_updated': None
        }
    
    def save_checkpoint(self, checkpoint: dict):
        """Save processing checkpoint."""
        checkpoint['last_updated'] = datetime.now().isoformat()
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)
            logger.debug(f"Checkpoint saved: {len(checkpoint['processed'])} processed")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def is_already_processed(self, example_name: str, checkpoint: dict) -> bool:
        """Check if example is already processed."""
        return example_name in checkpoint.get('processed', [])
    
    def process_all_examples_robust(self):
        """Process all MODFLOW 6 examples with checkpoint recovery."""
        logger.info("🚀 Starting robust MODFLOW 6 examples processing...")
        
        # Load checkpoint
        checkpoint = self.load_checkpoint()
        
        # Get all mappings
        mappings = self.discover_and_map_files()
        if not mappings:
            logger.error("No valid mappings found!")
            return
        
        # Filter out already processed examples
        remaining_mappings = [
            m for m in mappings 
            if not self.is_already_processed(m['example_name'], checkpoint)
        ]
        
        total_examples = len(mappings)
        already_processed = len(checkpoint.get('processed', []))
        remaining = len(remaining_mappings)
        
        logger.info(f"📊 Processing Status:")
        logger.info(f"   Total examples: {total_examples}")
        logger.info(f"   Already processed: {already_processed}")
        logger.info(f"   Remaining: {remaining}")
        logger.info(f"   Previously failed: {len(checkpoint.get('failed', []))}")
        
        if remaining == 0:
            logger.info("🎉 All examples already processed!")
            self.print_final_summary()
            return
        
        # Process remaining examples
        processed_count = already_processed
        failed_count = len(checkpoint.get('failed', []))
        
        for idx, mapping in enumerate(remaining_mappings, 1):
            example_name = mapping['example_name']
            
            try:
                logger.info(f"📝 Processing [{idx}/{remaining}]: {example_name}")
                start_time = time.time()
                
                # Extract documentation
                logger.debug("  🔍 Parsing LaTeX documentation...")
                doc_data = self.parse_latex_doc(mapping['doc_path'])
                
                # Analyze code
                logger.debug("  ⚙️  Analyzing Python script...")
                code_data = self.analyze_python_script(mapping['script_path'])
                
                # Claude synthesis
                logger.debug("  🧠 Generating comprehensive analysis...")
                claude_analysis = self.claude_comprehensive_analysis(
                    doc_data, code_data, example_name
                )
                
                # Create database record
                record = {
                    'tutorial_file': mapping['relative_script_path'],
                    'source_repository': 'modflow6-examples',
                    'github_url': mapping['github_url'],
                    'title': doc_data.get('title', example_name),
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
                logger.debug("  💾 Inserting to database...")
                if self.insert_workflow_record(record):
                    processed_count += 1
                    checkpoint['processed'].append(example_name)
                    
                    processing_time = time.time() - start_time
                    logger.info(f"  ✅ Success ({processing_time:.1f}s): {example_name}")
                else:
                    # Already exists - still count as success
                    processed_count += 1
                    checkpoint['processed'].append(example_name)
                    logger.info(f"  ⏭️  Already exists: {example_name}")
                
                # Save checkpoint every 5 examples
                if len(checkpoint['processed']) % 5 == 0:
                    self.save_checkpoint(checkpoint)
                    logger.info(f"  💾 Checkpoint saved ({len(checkpoint['processed'])} processed)")
                
                # Brief pause to avoid overwhelming the system
                time.sleep(0.5)
                
            except Exception as e:
                failed_count += 1
                checkpoint['failed'].append({
                    'example_name': example_name,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                
                logger.error(f"  ❌ Failed: {example_name} - {str(e)}")
                
                # Save checkpoint on failures too
                self.save_checkpoint(checkpoint)
                continue
        
        # Final checkpoint save
        checkpoint['completed_at'] = datetime.now().isoformat()
        self.save_checkpoint(checkpoint)
        
        # Print final summary
        logger.info("🏁 Processing Complete!")
        logger.info(f"   Total processed: {processed_count}/{total_examples}")
        logger.info(f"   Failed: {failed_count}")
        
        self.print_final_summary()
    
    def print_final_summary(self):
        """Print comprehensive summary of all workflows."""
        logger.info("📊 Final Database Summary:")
        
        try:
            import psycopg2
            import config
            
            with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
                with conn.cursor() as cur:
                    # Count by source repository
                    cur.execute("""
                        SELECT source_repository, COUNT(*) 
                        FROM flopy_workflows 
                        GROUP BY source_repository
                        ORDER BY source_repository
                    """)
                    
                    results = cur.fetchall()
                    total_workflows = sum(count for _, count in results)
                    
                    logger.info(f"   Total workflows in database: {total_workflows}")
                    for repo, count in results:
                        logger.info(f"   - {repo}: {count}")
                    
                    # Count MODFLOW 6 examples by type
                    cur.execute("""
                        SELECT model_type, complexity, COUNT(*) 
                        FROM flopy_workflows 
                        WHERE source_repository = 'modflow6-examples'
                        GROUP BY model_type, complexity
                        ORDER BY model_type, complexity
                    """)
                    
                    mf6_results = cur.fetchall()
                    if mf6_results:
                        logger.info("   MODFLOW 6 examples breakdown:")
                        for model_type, complexity, count in mf6_results:
                            logger.info(f"     - {model_type} ({complexity}): {count}")
        
        except Exception as e:
            logger.error(f"Could not generate summary: {e}")
    
    def print_failed_examples(self):
        """Print details of failed examples from checkpoint."""
        checkpoint = self.load_checkpoint()
        failed = checkpoint.get('failed', [])
        
        if failed:
            logger.info(f"❌ Failed Examples ({len(failed)}):")
            for failure in failed:
                logger.info(f"   - {failure['example_name']}: {failure['error']}")
        else:
            logger.info("✅ No failed examples!")
    
    def retry_failed_examples(self):
        """Retry processing failed examples."""
        checkpoint = self.load_checkpoint()
        failed = checkpoint.get('failed', [])
        
        if not failed:
            logger.info("No failed examples to retry!")
            return
        
        logger.info(f"🔄 Retrying {len(failed)} failed examples...")
        
        # Get all mappings
        mappings = self.discover_and_map_files()
        mapping_dict = {m['example_name']: m for m in mappings}
        
        # Retry each failed example
        retry_success = 0
        retry_failed = []
        
        for failure in failed:
            example_name = failure['example_name']
            
            if example_name not in mapping_dict:
                logger.warning(f"Could not find mapping for: {example_name}")
                continue
            
            mapping = mapping_dict[example_name]
            
            try:
                logger.info(f"🔄 Retrying: {example_name}")
                
                # Same processing logic as main function
                doc_data = self.parse_latex_doc(mapping['doc_path'])
                code_data = self.analyze_python_script(mapping['script_path'])
                claude_analysis = self.claude_comprehensive_analysis(
                    doc_data, code_data, example_name
                )
                
                record = {
                    'tutorial_file': mapping['relative_script_path'],
                    'source_repository': 'modflow6-examples',
                    'github_url': mapping['github_url'],
                    'title': doc_data.get('title', example_name),
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
                
                if self.insert_workflow_record(record):
                    retry_success += 1
                    checkpoint['processed'].append(example_name)
                    logger.info(f"  ✅ Retry successful: {example_name}")
                else:
                    logger.info(f"  ⏭️  Already exists: {example_name}")
                    retry_success += 1
                    checkpoint['processed'].append(example_name)
                
            except Exception as e:
                logger.error(f"  ❌ Retry failed: {example_name} - {str(e)}")
                retry_failed.append({
                    'example_name': example_name,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        # Update checkpoint
        checkpoint['failed'] = retry_failed
        self.save_checkpoint(checkpoint)
        
        logger.info(f"🔄 Retry complete: {retry_success} successful, {len(retry_failed)} still failed")


def main():
    """Main processing function with command-line options."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Process MODFLOW 6 examples robustly')
    parser.add_argument('--retry-failed', action='store_true', 
                       help='Retry only failed examples from checkpoint')
    parser.add_argument('--show-failed', action='store_true',
                       help='Show failed examples from checkpoint')
    parser.add_argument('--summary', action='store_true',
                       help='Show summary without processing')
    
    args = parser.parse_args()
    
    processor = RobustMODFLOW6Processor()
    
    if args.show_failed:
        processor.print_failed_examples()
    elif args.summary:
        processor.print_final_summary()
    elif args.retry_failed:
        processor.retry_failed_examples()
    else:
        processor.process_all_examples_robust()


if __name__ == "__main__":
    main()