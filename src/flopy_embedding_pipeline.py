#!/usr/bin/env python3
"""
FloPy Ultra-Discriminative Embedding Pipeline

Professional production pipeline for generating ultra-discriminative embeddings for FloPy workflows.
Follows established codebase patterns and integrates with existing database schema.

NOTE: This pipeline uses "v02" naming internally (database columns, variables) for consistency 
with experimental work in dspy/ that achieved 54.4% → 70.7% accuracy improvement. The v02 
designation refers to the ultra-discriminative approach (vs baseline v00 embeddings), but 
filenames are kept clean without version numbers.
"""

import asyncio
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import psycopg2
from psycopg2.extras import RealDictCursor
import google.genai as genai
from openai import AsyncOpenAI


@dataclass
class EmbeddingCheckpoint:
    """Checkpoint for embedding generation progress"""
    batch_id: int
    completed_workflows: List[str]
    failed_workflows: List[str]
    timestamp: datetime
    total_processed: int
    repository: str


@dataclass
class WorkflowAnalysis:
    """Ultra-discriminative analysis for workflow"""
    workflow_purpose: str
    discriminative_questions: List[str]
    key_differentiators: List[str]
    modflow_version_specifics: List[str]
    package_implementations: List[str]
    flopy_methods_used: List[str]


class FloPyEmbeddingPipelineV02:
    """Professional v02 embedding pipeline for FloPy workflows"""
    
    def __init__(self,
                 neon_conn_string: str,
                 gemini_api_key: str,
                 openai_api_key: str,
                 repository: str = "flopy",
                 batch_size: int = 10,
                 gemini_model: str = "gemini-2.0-flash-exp",
                 openai_model: str = "text-embedding-3-small"):
        """
        Initialize the FloPy v02 embedding pipeline
        
        Args:
            neon_conn_string: PostgreSQL connection string
            gemini_api_key: Gemini API key for analysis generation
            openai_api_key: OpenAI API key for embeddings
            repository: Repository to process ('flopy' or 'modflow6-examples')
            batch_size: Number of workflows to process per batch
            gemini_model: Gemini model for analysis
            openai_model: OpenAI model for embeddings
        """
        self.neon_conn = neon_conn_string
        self.repository = repository
        self.batch_size = batch_size
        
        # Initialize AI clients
        self.gemini_client = genai.Client(api_key=gemini_api_key)
        self.gemini_model = gemini_model
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.openai_model = openai_model
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Create checkpoints directory
        self.checkpoints_dir = Path("/home/danilopezmella/flopy_expert/archive/processing_checkpoints")
        self.checkpoints_dir.mkdir(exist_ok=True)
        
        # Ensure v02 columns exist
        self._ensure_v02_columns()
        
        self.logger.info(f"Initialized FloPy V02 Embedding Pipeline for repository: {repository}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging following established patterns"""
        logger = logging.getLogger(f"flopy_embedding_v02_{self.repository}")
        logger.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        log_file = Path("/home/danilopezmella/flopy_expert/logs") / f"flopy_embedding_v02_{self.repository}_{datetime.now():%Y%m%d_%H%M%S}.log"
        log_file.parent.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def _ensure_v02_columns(self):
        """Ensure v02 columns exist in database"""
        try:
            with psycopg2.connect(self.neon_conn) as conn:
                with conn.cursor() as cur:
                    # Add v02 columns if they don't exist
                    cur.execute("""
                        ALTER TABLE flopy_workflows 
                        ADD COLUMN IF NOT EXISTS analysis_v02 JSONB,
                        ADD COLUMN IF NOT EXISTS emb_string_02 TEXT,
                        ADD COLUMN IF NOT EXISTS dspy_emb_02 vector(1536)
                    """)
                    conn.commit()
                    self.logger.info("Ensured v02 columns exist in flopy_workflows table")
        except Exception as e:
            self.logger.error(f"Error ensuring v02 columns: {e}")
            raise
    
    def get_filter_clause(self) -> str:
        """Get repository-specific filter clause"""
        if self.repository == "modflow6-examples":
            return "WHERE tutorial_file LIKE '%.py' AND tutorial_file LIKE 'ex-%'"
        else:
            return "WHERE tutorial_file LIKE '%.py' AND tutorial_file NOT LIKE 'ex-%'"
    
    def load_workflows_needing_processing(self) -> List[Dict[str, Any]]:
        """Load workflows that need v02 processing"""
        try:
            with psycopg2.connect(self.neon_conn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    filter_clause = self.get_filter_clause()
                    
                    # Get workflows without v02 analysis or embeddings
                    query = f"""
                        SELECT 
                            id, tutorial_file, title, model_type,
                            packages_used, workflow_purpose, tags,
                            analysis_v02, dspy_emb_02
                        FROM flopy_workflows
                        {filter_clause}
                        AND (analysis_v02 IS NULL OR dspy_emb_02 IS NULL)
                        ORDER BY tutorial_file
                    """
                    
                    cur.execute(query)
                    workflows = []
                    
                    for row in cur.fetchall():
                        workflows.append({
                            'id': row['id'],
                            'tutorial_file': row['tutorial_file'],
                            'title': row['title'],
                            'model_type': row['model_type'],
                            'packages_used': row['packages_used'] or [],
                            'workflow_purpose': row['workflow_purpose'],
                            'tags': row['tags'] or [],
                            'needs_analysis': row['analysis_v02'] is None,
                            'needs_embedding': row['dspy_emb_02'] is None
                        })
                    
                    self.logger.info(f"Found {len(workflows)} workflows needing v02 processing")
                    return workflows
                    
        except Exception as e:
            self.logger.error(f"Error loading workflows: {e}")
            raise
    
    def get_ultra_discriminative_prompt(self) -> str:
        """Get the ultra-discriminative prompt template"""
        if self.repository == "modflow6-examples":
            return """You are an expert analyzing official MODFLOW 6 example problems.

EXAMPLE: {tutorial_file}
TITLE: {title}
PURPOSE: {workflow_purpose}

These are OFFICIAL MODFLOW 6 examples, not tutorials. They demonstrate specific features and capabilities.

CRITICAL: Generate questions that distinguish THIS example from other MODFLOW 6 examples.

Focus on:
1. UNIQUE FEATURES demonstrated (not found in other examples)
2. SPECIFIC PROBLEM SETUP (boundary conditions, domain, parameters)
3. ADVANCED PACKAGES used (not common ones)
4. NUMERICAL METHODS specific to this problem
5. VALIDATION/COMPARISON aspects if present

Generate a JSON with:
{{
    "workflow_purpose": "What specific MODFLOW 6 feature this example demonstrates",
    "discriminative_questions": [10 ultra-specific questions about THIS example],
    "key_differentiators": ["Unique aspects not found in other examples"],
    "advanced_features": ["Advanced MODFLOW 6 features used"],
    "problem_specifics": ["Specific problem setup details"],
    "validation_aspects": ["How results are validated or compared"]
}}"""
        else:
            return """You are an expert MODFLOW modeler analyzing FloPy tutorial workflows.

WORKFLOW: {tutorial_file}
TITLE: {title}
PACKAGES: {packages_used}
MODEL TYPE: {model_type}

CRITICAL REQUIREMENT: Generate ULTRA-DISCRIMINATIVE technical questions that are IMPOSSIBLE to answer correctly 
without understanding THIS SPECIFIC workflow's implementation details.

Your questions must differentiate between:
1. MODFLOW VERSIONS: MODFLOW-2005 vs MODFLOW-6 vs MODFLOW-NWT vs MODFLOW-USG
2. PACKAGE IMPLEMENTATIONS: Same package code but different implementations (e.g., WEL in MF2005 vs MF6)
3. SOLVER CONFIGURATIONS: PCG vs GMG vs SMS/IMS with specific settings
4. GRID TYPES: Regular DIS vs vertex DISV vs unstructured DISU
5. FLOPY METHODS: High-level convenience methods vs low-level array manipulation

FORCE DIFFERENTIATION by including:
- Specific FloPy class names and method signatures
- Exact array dimensions and shapes used
- Package-specific parameter names and units
- Version-specific keyword arguments
- Grid discretization details unique to this example

Generate a JSON with:
{{
    "workflow_purpose": "Ultra-specific purpose mentioning exact packages and methods",
    "discriminative_questions": [10 ultra-specific technical questions],
    "key_differentiators": ["What makes this unique from similar workflows"],
    "modflow_version_specifics": ["Version-specific implementation details"],
    "package_implementations": ["How packages are specifically configured"],
    "flopy_methods_used": ["Specific FloPy methods and their parameters"]
}}

EXAMPLES OF ULTRA-DISCRIMINATIVE QUESTIONS:
- "In this MF6 workflow, how does ModflowGwfdis handle cell2d array construction for DISV?"
- "What specific IMS outer_maximum value does this tutorial use for PCG convergence?"
- "How does this workflow's flopy.mf6.ModflowGwfnpf rewetting differ from UPW?"
- "What is the exact shape of the stress_period_data recarray for the WEL package here?"
- "Which flopy.utils.binaryfile method reads the CBC file in this specific example?"

Make questions so specific that ONLY someone who has studied THIS EXACT workflow could answer."""
    
    def format_workflow_for_prompt(self, workflow: Dict[str, Any]) -> Dict[str, str]:
        """Format workflow data for prompt template"""
        packages = workflow['packages_used']
        if packages:
            packages_str = ', '.join(packages[:10])  # Limit to 10
        else:
            packages_str = 'Various packages'
        
        return {
            'tutorial_file': workflow['tutorial_file'],
            'title': workflow['title'] or 'Unknown Title',
            'model_type': workflow['model_type'] or 'Unknown',
            'packages_used': packages_str,
            'workflow_purpose': workflow['workflow_purpose'] or 'General workflow'
        }
    
    async def generate_analysis(self, workflow: Dict[str, Any]) -> Optional[WorkflowAnalysis]:
        """Generate ultra-discriminative analysis using Gemini"""
        try:
            # Format prompt
            prompt_template = self.get_ultra_discriminative_prompt()
            formatted_data = self.format_workflow_for_prompt(workflow)
            prompt = prompt_template.format(**formatted_data)
            
            # Generate with Gemini
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=[prompt]
            )
            
            # Parse JSON response
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            analysis_data = json.loads(response_text)
            
            # Create WorkflowAnalysis object
            analysis = WorkflowAnalysis(
                workflow_purpose=analysis_data.get('workflow_purpose', ''),
                discriminative_questions=analysis_data.get('discriminative_questions', []),
                key_differentiators=analysis_data.get('key_differentiators', []),
                modflow_version_specifics=analysis_data.get('modflow_version_specifics', analysis_data.get('advanced_features', [])),
                package_implementations=analysis_data.get('package_implementations', analysis_data.get('problem_specifics', [])),
                flopy_methods_used=analysis_data.get('flopy_methods_used', analysis_data.get('validation_aspects', []))
            )
            
            self.logger.info(f"Generated analysis for {workflow['tutorial_file']}")
            return analysis
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error for {workflow['tutorial_file']}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error generating analysis for {workflow['tutorial_file']}: {e}")
            return None
    
    def create_embedding_text(self, workflow: Dict[str, Any], analysis: WorkflowAnalysis) -> str:
        """Create text for embedding generation"""
        parts = []
        
        # Add workflow metadata
        parts.append(f"Workflow: {workflow['tutorial_file']}")
        parts.append(f"Title: {workflow['title']}")
        parts.append(f"Purpose: {analysis.workflow_purpose}")
        
        # Add discriminative questions
        if analysis.discriminative_questions:
            parts.append("Ultra-specific questions:")
            for i, question in enumerate(analysis.discriminative_questions[:15], 1):
                if isinstance(question, dict):
                    question_text = question.get('question_text', str(question))
                else:
                    question_text = str(question)
                parts.append(f"{i}. {question_text}")
        
        # Add key differentiators
        if analysis.key_differentiators:
            parts.append("Key differentiators:")
            for diff in analysis.key_differentiators[:5]:
                parts.append(f"- {diff}")
        
        # Add technical specifics
        if analysis.modflow_version_specifics:
            parts.append("Technical specifics:")
            for spec in analysis.modflow_version_specifics[:3]:
                parts.append(f"- {spec}")
        
        return "\n".join(parts)
    
    async def generate_embedding(self, embedding_text: str) -> Optional[List[float]]:
        """Generate embedding using OpenAI"""
        try:
            response = await self.openai_client.embeddings.create(
                model=self.openai_model,
                input=embedding_text
            )
            return response.data[0].embedding
        except Exception as e:
            self.logger.error(f"Error generating embedding: {e}")
            return None
    
    def format_embedding_for_postgres(self, embedding: List[float]) -> str:
        """Format embedding for PostgreSQL vector column"""
        return '[' + ','.join(map(str, embedding)) + ']'
    
    def save_to_database(self, workflow_id: str, analysis: WorkflowAnalysis, 
                        embedding_text: str, embedding: List[float]):
        """Save analysis and embedding to database"""
        try:
            with psycopg2.connect(self.neon_conn) as conn:
                with conn.cursor() as cur:
                    # Convert analysis to JSON
                    analysis_json = json.dumps({
                        'workflow_purpose': analysis.workflow_purpose,
                        'discriminative_questions': analysis.discriminative_questions,
                        'key_differentiators': analysis.key_differentiators,
                        'modflow_version_specifics': analysis.modflow_version_specifics,
                        'package_implementations': analysis.package_implementations,
                        'flopy_methods_used': analysis.flopy_methods_used
                    })
                    
                    embedding_str = self.format_embedding_for_postgres(embedding)
                    
                    cur.execute("""
                        UPDATE flopy_workflows
                        SET analysis_v02 = %s,
                            emb_string_02 = %s,
                            dspy_emb_02 = %s::vector
                        WHERE id = %s
                    """, (analysis_json, embedding_text, embedding_str, workflow_id))
                    
                    conn.commit()
                    
        except Exception as e:
            self.logger.error(f"Error saving to database: {e}")
            raise
    
    def load_checkpoint(self) -> Optional[EmbeddingCheckpoint]:
        """Load processing checkpoint"""
        checkpoint_file = self.checkpoints_dir / f"embedding_v02_{self.repository}_checkpoint.json"
        
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)
                    return EmbeddingCheckpoint(
                        batch_id=data['batch_id'],
                        completed_workflows=data['completed_workflows'],
                        failed_workflows=data['failed_workflows'],
                        timestamp=datetime.fromisoformat(data['timestamp']),
                        total_processed=data['total_processed'],
                        repository=data['repository']
                    )
            except Exception as e:
                self.logger.warning(f"Error loading checkpoint: {e}")
        
        return None
    
    def save_checkpoint(self, checkpoint: EmbeddingCheckpoint):
        """Save processing checkpoint"""
        checkpoint_file = self.checkpoints_dir / f"embedding_v02_{self.repository}_checkpoint.json"
        
        try:
            with open(checkpoint_file, 'w') as f:
                json.dump({
                    'batch_id': checkpoint.batch_id,
                    'completed_workflows': checkpoint.completed_workflows,
                    'failed_workflows': checkpoint.failed_workflows,
                    'timestamp': checkpoint.timestamp.isoformat(),
                    'total_processed': checkpoint.total_processed,
                    'repository': checkpoint.repository
                }, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving checkpoint: {e}")
    
    async def process_workflow(self, workflow: Dict[str, Any]) -> bool:
        """Process a single workflow"""
        try:
            workflow_file = workflow['tutorial_file']
            self.logger.info(f"Processing workflow: {workflow_file}")
            
            # Generate analysis if needed
            if workflow['needs_analysis']:
                analysis = await self.generate_analysis(workflow)
                if not analysis:
                    self.logger.error(f"Failed to generate analysis for {workflow_file}")
                    return False
            else:
                # Load existing analysis
                with psycopg2.connect(self.neon_conn) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT analysis_v02 FROM flopy_workflows WHERE id = %s", 
                                   (workflow['id'],))
                        analysis_data = cur.fetchone()[0]
                        
                        analysis = WorkflowAnalysis(
                            workflow_purpose=analysis_data.get('workflow_purpose', ''),
                            discriminative_questions=analysis_data.get('discriminative_questions', []),
                            key_differentiators=analysis_data.get('key_differentiators', []),
                            modflow_version_specifics=analysis_data.get('modflow_version_specifics', []),
                            package_implementations=analysis_data.get('package_implementations', []),
                            flopy_methods_used=analysis_data.get('flopy_methods_used', [])
                        )
            
            # Generate embedding if needed
            if workflow['needs_embedding']:
                embedding_text = self.create_embedding_text(workflow, analysis)
                embedding = await self.generate_embedding(embedding_text)
                
                if not embedding:
                    self.logger.error(f"Failed to generate embedding for {workflow_file}")
                    return False
            else:
                # Already has embedding
                embedding_text = ""
                embedding = []
            
            # Save to database
            if workflow['needs_analysis'] or workflow['needs_embedding']:
                self.save_to_database(workflow['id'], analysis, embedding_text, embedding)
            
            self.logger.info(f"Successfully processed {workflow_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing workflow {workflow['tutorial_file']}: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    async def run_pipeline(self):
        """Run the complete v02 embedding pipeline"""
        start_time = datetime.now()
        
        self.logger.info("=" * 80)
        self.logger.info(f"FLOPY V02 EMBEDDING PIPELINE - Repository: {self.repository}")
        self.logger.info("=" * 80)
        
        try:
            # Load workflows needing processing
            workflows = self.load_workflows_needing_processing()
            
            if not workflows:
                self.logger.info("No workflows need v02 processing")
                return
            
            # Load checkpoint
            checkpoint = self.load_checkpoint()
            if checkpoint:
                self.logger.info(f"Resuming from checkpoint: {checkpoint.total_processed} completed")
                completed_files = set(checkpoint.completed_workflows)
                workflows = [w for w in workflows if w['tutorial_file'] not in completed_files]
            else:
                checkpoint = EmbeddingCheckpoint(
                    batch_id=0,
                    completed_workflows=[],
                    failed_workflows=[],
                    timestamp=start_time,
                    total_processed=0,
                    repository=self.repository
                )
            
            # Process workflows in batches
            total_workflows = len(workflows)
            batch_num = checkpoint.batch_id
            
            for i in range(0, len(workflows), self.batch_size):
                batch = workflows[i:i + self.batch_size]
                batch_num += 1
                
                self.logger.info(f"Processing batch {batch_num}: {i + 1}-{min(i + len(batch), total_workflows)} of {total_workflows}")
                
                # Process batch
                for workflow in batch:
                    success = await self.process_workflow(workflow)
                    
                    if success:
                        checkpoint.completed_workflows.append(workflow['tutorial_file'])
                        checkpoint.total_processed += 1
                    else:
                        checkpoint.failed_workflows.append(workflow['tutorial_file'])
                
                # Update checkpoint
                checkpoint.batch_id = batch_num
                checkpoint.timestamp = datetime.now()
                self.save_checkpoint(checkpoint)
                
                self.logger.info(f"Batch {batch_num} complete. Processed: {checkpoint.total_processed}, Failed: {len(checkpoint.failed_workflows)}")
            
            # Final summary
            elapsed = datetime.now() - start_time
            
            self.logger.info("=" * 80)
            self.logger.info("PIPELINE COMPLETE")
            self.logger.info("=" * 80)
            self.logger.info(f"Repository: {self.repository}")
            self.logger.info(f"Time Elapsed: {elapsed}")
            self.logger.info(f"Total Processed: {checkpoint.total_processed}")
            self.logger.info(f"Failed: {len(checkpoint.failed_workflows)}")
            self.logger.info(f"Success Rate: {(checkpoint.total_processed / (checkpoint.total_processed + len(checkpoint.failed_workflows))) * 100:.1f}%")
            
            if checkpoint.failed_workflows:
                self.logger.warning("Failed workflows:")
                for failed in checkpoint.failed_workflows:
                    self.logger.warning(f"  - {failed}")
            
            # Validation
            self.validate_results()
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            self.logger.error(traceback.format_exc())
            raise
    
    def validate_results(self):
        """Validate pipeline results"""
        try:
            with psycopg2.connect(self.neon_conn) as conn:
                with conn.cursor() as cur:
                    filter_clause = self.get_filter_clause()
                    
                    cur.execute(f"""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(analysis_v02) as with_analysis,
                            COUNT(dspy_emb_02) as with_embedding
                        FROM flopy_workflows
                        {filter_clause}
                    """)
                    
                    total, with_analysis, with_embedding = cur.fetchone()
                    
                    self.logger.info(f"Validation Results:")
                    self.logger.info(f"  Total workflows: {total}")
                    self.logger.info(f"  With v02 analysis: {with_analysis} ({with_analysis/total*100:.1f}%)")
                    self.logger.info(f"  With v02 embeddings: {with_embedding} ({with_embedding/total*100:.1f}%)")
                    
                    if with_embedding == total:
                        self.logger.info("✅ All workflows have v02 embeddings!")
                    else:
                        self.logger.warning(f"⚠️ Missing embeddings: {total - with_embedding}")
                        
        except Exception as e:
            self.logger.error(f"Validation error: {e}")


async def main():
    """Main entry point for the pipeline"""
    import argparse
    import sys
    sys.path.append('/home/danilopezmella/flopy_expert')
    import config
    
    parser = argparse.ArgumentParser(description="FloPy V02 Embedding Pipeline")
    parser.add_argument(
        "--repository",
        choices=["flopy", "modflow6-examples"],
        default="flopy",
        help="Repository to process"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for processing"
    )
    
    args = parser.parse_args()
    
    # Create and run pipeline
    pipeline = FloPyEmbeddingPipelineV02(
        neon_conn_string=config.NEON_CONNECTION_STRING,
        gemini_api_key=config.GEMINI_API_KEY,
        openai_api_key=config.OPENAI_API_KEY,
        repository=args.repository,
        batch_size=args.batch_size
    )
    
    await pipeline.run_pipeline()


if __name__ == "__main__":
    asyncio.run(main())