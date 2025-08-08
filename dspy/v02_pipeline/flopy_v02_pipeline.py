#!/usr/bin/env python3
"""
FloPy V02 Ultra-Discriminative Pipeline
Production pipeline for generating v02 embeddings for FloPy workflows
"""

import sys
sys.path.append('/home/danilopezmella/flopy_expert')

import psycopg2
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

import config as main_config
from v02_pipeline.config import pipeline_config
from v02_pipeline.processors.checkpoint_manager import CheckpointManager
from v02_pipeline.processors.ultra_discriminative_analyzer import UltraDiscriminativeAnalyzer
from v02_pipeline.processors.embedding_generator import EmbeddingGenerator
from v02_pipeline.prompts import flopy_prompts

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(pipeline_config.LOG_DIR / f"flopy_v02_{datetime.now():%Y%m%d_%H%M%S}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FloPyV02Pipeline:
    """Main pipeline for FloPy v02 embedding generation"""
    
    def __init__(self, repository: str = "flopy"):
        """
        Initialize the pipeline
        
        Args:
            repository: Which repository to process ('flopy' or 'modflow6-examples')
        """
        self.repository = repository
        self.repo_config = pipeline_config.get_table_config(repository)
        self.conn = psycopg2.connect(main_config.NEON_CONNECTION_STRING)
        self.cur = self.conn.cursor()
        
        # Initialize processors
        self.analyzer = UltraDiscriminativeAnalyzer(
            api_key=main_config.GEMINI_API_KEY,
            model_name=pipeline_config.ANALYSIS_MODEL
        )
        
        self.embedder = EmbeddingGenerator(
            api_key=main_config.OPENAI_API_KEY,
            model=pipeline_config.EMBEDDING_MODEL
        )
        
        # Setup checkpoint managers for each stage
        self.checkpoint_dir = pipeline_config.CHECKPOINT_DIR
        self.analysis_checkpoint = CheckpointManager(
            self.checkpoint_dir, 
            f"flopy_{repository}", 
            "analysis_generation"
        )
        self.embedding_checkpoint = CheckpointManager(
            self.checkpoint_dir,
            f"flopy_{repository}",
            "embedding_creation"
        )
        
        logger.info(f"Initialized FloPy V02 Pipeline for repository: {repository}")
    
    def load_workflows(self) -> List[Dict[str, Any]]:
        """Load workflows from database"""
        logger.info(f"Loading workflows from {self.repo_config['table']}")
        
        filter_clause = f"WHERE {self.repo_config['filter']}" if self.repo_config['filter'] else ""
        
        query = f"""
            SELECT 
                id, tutorial_file, title, model_type, 
                packages_used, workflow_purpose, tags,
                analysis_v02
            FROM {self.repo_config['table']}
            {filter_clause}
            ORDER BY tutorial_file
        """
        
        self.cur.execute(query)
        workflows = []
        
        for row in self.cur.fetchall():
            workflows.append({
                'id': row[0],
                'tutorial_file': row[1],
                'title': row[2],
                'model_type': row[3],
                'packages_used': row[4] or [],
                'workflow_purpose': row[5],
                'tags': row[6] or [],
                'analysis_v02': row[7]
            })
        
        logger.info(f"Loaded {len(workflows)} workflows")
        return workflows
    
    def stage1_generate_analysis(self, workflows: List[Dict[str, Any]]) -> Dict[str, Dict]:
        """
        Stage 1: Generate ultra-discriminative analysis
        """
        logger.info("=" * 60)
        logger.info("STAGE 1: Generating Ultra-Discriminative Analysis")
        logger.info("=" * 60)
        
        # Filter to workflows needing analysis
        workflows_needing_analysis = [
            w for w in workflows 
            if not w['analysis_v02'] and self.analysis_checkpoint.should_process(w['id'])
        ]
        
        if not workflows_needing_analysis:
            logger.info("All workflows already have v02 analysis")
            return {}
        
        logger.info(f"Generating analysis for {len(workflows_needing_analysis)} workflows")
        
        # Get appropriate prompt template
        prompt_template = flopy_prompts.get_prompt_for_repository(self.repository)
        required_fields = flopy_prompts.FLOPY_REQUIRED_FIELDS
        
        # Format workflows for prompt
        formatted_workflows = []
        for w in workflows_needing_analysis:
            formatted = flopy_prompts.format_workflow_for_prompt(w, self.repository)
            formatted['id'] = w['id']
            formatted_workflows.append(formatted)
        
        # Generate analysis with checkpoint support
        results = self.analyzer.batch_generate(
            formatted_workflows,
            prompt_template,
            required_fields,
            self.analysis_checkpoint
        )
        
        # Save to database
        for workflow_id, analysis in results.items():
            self.cur.execute(f"""
                UPDATE {self.repo_config['table']}
                SET {pipeline_config.get_column_name('analysis')} = %s
                WHERE id = %s
            """, (json.dumps(analysis), workflow_id))
            self.conn.commit()
        
        # Save checkpoint
        self.analysis_checkpoint.save_checkpoint()
        
        logger.info(f"Generated analysis for {len(results)} workflows")
        logger.info(self.analysis_checkpoint.get_summary())
        
        return results
    
    def stage2_generate_embeddings(self, workflows: List[Dict[str, Any]]) -> Dict[str, Dict]:
        """
        Stage 2: Generate embeddings from analysis
        """
        logger.info("=" * 60)
        logger.info("STAGE 2: Generating Embeddings")
        logger.info("=" * 60)
        
        # Reload workflows to get updated analysis
        workflows = self.load_workflows()
        
        # Filter to workflows with analysis but no embeddings
        workflows_needing_embeddings = []
        for w in workflows:
            if w['analysis_v02'] and self.embedding_checkpoint.should_process(w['id']):
                # Check if already has v02 embedding
                self.cur.execute(f"""
                    SELECT {pipeline_config.get_column_name('embedding')} IS NOT NULL
                    FROM {self.repo_config['table']}
                    WHERE id = %s
                """, (w['id'],))
                has_embedding = self.cur.fetchone()[0]
                
                if not has_embedding:
                    workflows_needing_embeddings.append({
                        'workflow': w,
                        'analysis': w['analysis_v02']
                    })
        
        if not workflows_needing_embeddings:
            logger.info("All workflows already have v02 embeddings")
            return {}
        
        logger.info(f"Generating embeddings for {len(workflows_needing_embeddings)} workflows")
        
        # Generate embeddings with checkpoint support
        results = self.embedder.batch_generate(
            workflows_needing_embeddings,
            self.embedding_checkpoint
        )
        
        # Save to database
        for workflow_id, embedding_data in results.items():
            embedding_str = EmbeddingGenerator.format_embedding_for_postgres(
                embedding_data['embedding']
            )
            
            self.cur.execute(f"""
                UPDATE {self.repo_config['table']}
                SET {pipeline_config.get_column_name('embedding')} = %s::vector,
                    {pipeline_config.get_column_name('embedding_text')} = %s
                WHERE id = %s
            """, (embedding_str, embedding_data['embedding_text'], workflow_id))
            self.conn.commit()
        
        # Save checkpoint
        self.embedding_checkpoint.save_checkpoint()
        
        logger.info(f"Generated embeddings for {len(results)} workflows")
        logger.info(self.embedding_checkpoint.get_summary())
        
        return results
    
    def stage3_validate_quality(self) -> Dict[str, Any]:
        """
        Stage 3: Validate quality of generated content
        """
        logger.info("=" * 60)
        logger.info("STAGE 3: Quality Validation")
        logger.info("=" * 60)
        
        # Check completeness
        self.cur.execute(f"""
            SELECT 
                COUNT(*) as total,
                COUNT({pipeline_config.get_column_name('analysis')}) as with_analysis,
                COUNT({pipeline_config.get_column_name('embedding')}) as with_embedding
            FROM {self.repo_config['table']}
            {f"WHERE {self.repo_config['filter']}" if self.repo_config['filter'] else ""}
        """)
        
        total, with_analysis, with_embedding = self.cur.fetchone()
        
        # Check quality metrics
        self.cur.execute(f"""
            SELECT 
                id, tutorial_file,
                {pipeline_config.get_column_name('analysis')},
                LENGTH({pipeline_config.get_column_name('embedding_text')}) as text_length
            FROM {self.repo_config['table']}
            WHERE {pipeline_config.get_column_name('analysis')} IS NOT NULL
            {f"AND {self.repo_config['filter']}" if self.repo_config['filter'] else ""}
        """)
        
        quality_issues = []
        for row in self.cur.fetchall():
            workflow_id, file, analysis, text_length = row
            
            # Check number of questions
            if analysis:
                questions = analysis.get('discriminative_questions', [])
                if len(questions) < pipeline_config.MIN_QUESTIONS_PER_WORKFLOW:
                    quality_issues.append(f"{file}: Only {len(questions)} questions")
            
            # Check embedding text length
            if text_length and text_length < pipeline_config.MIN_EMBEDDING_TEXT_LENGTH:
                quality_issues.append(f"{file}: Short embedding text ({text_length} chars)")
        
        validation_results = {
            'total_workflows': total,
            'with_analysis': with_analysis,
            'with_embedding': with_embedding,
            'completeness_pct': (with_embedding / total * 100) if total > 0 else 0,
            'quality_issues': quality_issues,
            'expected_count': self.repo_config['expected_count'],
            'meets_expectations': with_embedding >= self.repo_config['expected_count']
        }
        
        logger.info(f"Validation Results:")
        logger.info(f"  Total: {total}")
        logger.info(f"  With Analysis: {with_analysis} ({with_analysis/total*100:.1f}%)")
        logger.info(f"  With Embeddings: {with_embedding} ({with_embedding/total*100:.1f}%)")
        logger.info(f"  Quality Issues: {len(quality_issues)}")
        
        if quality_issues:
            logger.warning("Quality issues found:")
            for issue in quality_issues[:5]:  # Show first 5
                logger.warning(f"  - {issue}")
        
        return validation_results
    
    def run_full_pipeline(self):
        """Run the complete pipeline"""
        logger.info("=" * 80)
        logger.info(f"FloPy V02 Pipeline - Repository: {self.repository}")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        try:
            # Load workflows
            workflows = self.load_workflows()
            
            # Stage 1: Generate Analysis
            analysis_results = self.stage1_generate_analysis(workflows)
            
            # Stage 2: Generate Embeddings
            embedding_results = self.stage2_generate_embeddings(workflows)
            
            # Stage 3: Validate Quality
            validation_results = self.stage3_validate_quality()
            
            # Summary
            elapsed = datetime.now() - start_time
            logger.info("=" * 80)
            logger.info("PIPELINE COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Repository: {self.repository}")
            logger.info(f"Time Elapsed: {elapsed}")
            logger.info(f"Workflows Processed: {validation_results['with_embedding']}/{validation_results['total']}")
            logger.info(f"Success Rate: {validation_results['completeness_pct']:.1f}%")
            
            if validation_results['meets_expectations']:
                logger.info("✅ Pipeline completed successfully!")
            else:
                logger.warning(f"⚠️ Expected {self.repo_config['expected_count']} workflows, got {validation_results['with_embedding']}")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise
        finally:
            self.close()
    
    def close(self):
        """Clean up resources"""
        self.cur.close()
        self.conn.close()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FloPy V02 Ultra-Discriminative Pipeline")
    parser.add_argument(
        "--repository", 
        choices=["flopy", "modflow6-examples"],
        default="flopy",
        help="Which repository to process"
    )
    parser.add_argument(
        "--reset-checkpoints",
        action="store_true",
        help="Reset checkpoints and start fresh"
    )
    
    args = parser.parse_args()
    
    # Create and run pipeline
    pipeline = FloPyV02Pipeline(repository=args.repository)
    
    if args.reset_checkpoints:
        logger.warning("Resetting checkpoints...")
        pipeline.analysis_checkpoint.reset()
        pipeline.embedding_checkpoint.reset()
    
    pipeline.run_full_pipeline()

if __name__ == "__main__":
    main()