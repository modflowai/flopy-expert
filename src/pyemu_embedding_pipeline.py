#!/usr/bin/env python3
"""
PyEMU Ultra-Discriminative Embedding Pipeline

Professional production pipeline for generating ultra-discriminative embeddings for PyEMU workflows.
Follows established codebase patterns and integrates with existing database schema.

NOTE: This pipeline uses "v02" naming internally (database columns, variables) for consistency 
with experimental work in dspy/ that achieved improvements in semantic search accuracy. The v02 
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
class PyEMUEmbeddingCheckpoint:
    """Checkpoint for PyEMU embedding generation progress"""
    batch_id: int
    completed_workflows: List[str]
    failed_workflows: List[str]
    timestamp: datetime
    total_processed: int


@dataclass
class PyEMUWorkflowAnalysis:
    """Ultra-discriminative analysis for PyEMU workflow"""
    workflow_purpose: str
    discriminative_questions: List[str]
    key_differentiators: List[str]
    pest_tool_specifics: List[str]
    statistical_implementation: List[str]
    unique_pyemu_features: List[str]


class PyEMUEmbeddingPipelineV02:
    """Professional v02 embedding pipeline for PyEMU workflows"""
    
    def __init__(self,
                 neon_conn_string: str,
                 gemini_api_key: str,
                 openai_api_key: str,
                 batch_size: int = 5,
                 gemini_model: str = "gemini-2.0-flash-exp",
                 openai_model: str = "text-embedding-3-small"):
        """
        Initialize the PyEMU v02 embedding pipeline
        
        Args:
            neon_conn_string: PostgreSQL connection string
            gemini_api_key: Gemini API key for analysis generation
            openai_api_key: OpenAI API key for embeddings
            batch_size: Number of workflows to process per batch
            gemini_model: Gemini model for analysis
            openai_model: OpenAI model for embeddings
        """
        self.neon_conn = neon_conn_string
        self.batch_size = batch_size
        
        # Initialize AI clients
        self.gemini_client = genai.Client(api_key=gemini_api_key)
        self.gemini_model = gemini_model
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.openai_model = openai_model
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Create checkpoints directory
        self.checkpoints_dir = Path("/home/danilopezmella/flopy_expert/archive/pyemu_checkpoints")
        self.checkpoints_dir.mkdir(exist_ok=True)
        
        # Ensure v02 columns exist
        self._ensure_v02_columns()
        
        self.logger.info("Initialized PyEMU V02 Embedding Pipeline")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging following established patterns"""
        logger = logging.getLogger("pyemu_embedding_v02")
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
        log_file = Path("/home/danilopezmella/flopy_expert/logs") / f"pyemu_embedding_v02_{datetime.now():%Y%m%d_%H%M%S}.log"
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
                        ALTER TABLE pyemu_workflows 
                        ADD COLUMN IF NOT EXISTS analysis_v02 JSONB,
                        ADD COLUMN IF NOT EXISTS emb_string_02 TEXT,
                        ADD COLUMN IF NOT EXISTS dspy_emb_02 vector(1536)
                    """)
                    conn.commit()
                    self.logger.info("Ensured v02 columns exist in pyemu_workflows table")
        except Exception as e:
            self.logger.error(f"Error ensuring v02 columns: {e}")
            raise
    
    def load_workflows_needing_processing(self) -> List[Dict[str, Any]]:
        """Load PyEMU workflows that need v02 processing"""
        try:
            with psycopg2.connect(self.neon_conn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get workflows without v02 analysis or embeddings
                    query = """
                        SELECT 
                            id, notebook_file, title, workflow_type,
                            pest_concepts, uncertainty_methods, pyemu_modules,
                            workflow_purpose, tags,
                            analysis_v02, dspy_emb_02
                        FROM pyemu_workflows
                        WHERE (analysis_v02 IS NULL OR dspy_emb_02 IS NULL)
                        ORDER BY notebook_file
                    """
                    
                    cur.execute(query)
                    workflows = []
                    
                    for row in cur.fetchall():
                        workflows.append({
                            'id': row['id'],
                            'notebook_file': row['notebook_file'],
                            'title': row['title'],
                            'workflow_type': row['workflow_type'],
                            'pest_concepts': row['pest_concepts'] or [],
                            'uncertainty_methods': row['uncertainty_methods'] or [],
                            'pyemu_modules': row['pyemu_modules'] or [],
                            'workflow_purpose': row['workflow_purpose'],
                            'tags': row['tags'] or [],
                            'needs_analysis': row['analysis_v02'] is None,
                            'needs_embedding': row['dspy_emb_02'] is None
                        })
                    
                    self.logger.info(f"Found {len(workflows)} PyEMU workflows needing v02 processing")
                    return workflows
                    
        except Exception as e:
            self.logger.error(f"Error loading workflows: {e}")
            raise
    
    def get_ultra_discriminative_prompt(self) -> str:
        """Get the PyEMU ultra-discriminative prompt template"""
        return """You are an expert in uncertainty quantification and PEST++ inverse modeling analyzing PyEMU workflows.

WORKFLOW: {notebook_file}
TITLE: {title}
TYPE: {workflow_type}
PEST CONCEPTS: {pest_concepts}
UNCERTAINTY METHODS: {uncertainty_methods}
PYEMU MODULES: {pyemu_modules}

CRITICAL REQUIREMENT: Generate ULTRA-DISCRIMINATIVE technical questions that are IMPOSSIBLE to answer correctly 
without understanding THIS SPECIFIC workflow's implementation details.

Your questions must differentiate between:
1. PEST++ TOOLS: PESTPP-IES vs PESTPP-GLM vs PESTPP-SEN vs PESTPP-SWP vs PESTPP-DA
2. UNCERTAINTY APPROACHES: Monte Carlo vs FOSM vs GLUE vs Null Space Monte Carlo
3. CALIBRATION METHODS: Regularization types (Tikhonov vs SVD-Assist vs Subspace)
4. SENSITIVITY ANALYSES: Morris vs Sobol vs PEST++ DSS vs Method of Morris
5. IMPLEMENTATION STAGES: Prior vs Posterior, Linear vs Nonlinear, First-order vs Second-order

FORCE DIFFERENTIATION by including:
- Specific PyEMU class names and methods (Pst, Schur, EnsembleSmoother, etc.)
- Exact statistical calculations and matrix operations
- PEST control file parameters and settings
- Computational complexity and scaling
- Specific error handling in uncertainty propagation

Generate a JSON with:
{{
    "workflow_purpose": "Ultra-specific purpose focusing on exact statistical method",
    "discriminative_questions": [10 ultra-specific technical questions],
    "key_differentiators": ["What makes this unique from similar workflows"],
    "pest_tool_specifics": ["Exact PEST++ tool configurations used"],
    "statistical_implementation": ["Precise mathematical operations performed"],
    "unique_pyemu_features": ["PyEMU-specific classes and methods used"]
}}

EXAMPLES OF ULTRA-DISCRIMINATIVE QUESTIONS BASED ON KEY DIFFERENTIATORS:

For PESTPP-IES workflows:
- "Which pyemu.ParameterEnsemble method updates realizations using the Kalman gain in this workflow?"
- "How does this workflow's ensemble localization strategy differ from standard EnKF?"
- "What ensemble size vs parameter dimension ratio does this PESTPP-IES implementation use?"

For PESTPP-GLM workflows:
- "How does pyemu.Jco handle the Jacobian matrix scaling before SVD decomposition here?"
- "What regularization weight adjustment does PESTPP-GLM apply after each lambda iteration?"
- "Which pyemu.Schur method calculates the posterior parameter covariance in this workflow?"

For Monte Carlo workflows:
- "How does ParameterEnsemble.from_gaussian_draw() enforce parameter bounds in this prior MC?"
- "What correlation structure does pyemu.Cov.from_parameter_data() impose on the ensemble?"
- "How many realizations are needed for this workflow's Sobol sensitivity convergence?"

For FOSM workflows:
- "What singular value truncation does pyemu.ErrVar apply to the Jacobian before uncertainty propagation?"
- "How does this workflow's Schur complement handle forecast sensitivity calculation?"
- "Which linear assumption violations does this FOSM implementation check for?"

For Schur complement examples:
- "How does pyemu.Schur.get_forecast_summary() handle parameter-to-forecast covariance?"
- "What specific prior information weight does this workflow apply to observations?"
- "How are forecast variances adjusted for nonlinearity in this implementation?"

Make questions so specific that ONLY someone who understands THIS EXACT workflow could answer."""
    
    def format_workflow_for_prompt(self, workflow: Dict[str, Any]) -> Dict[str, str]:
        """Format workflow data for prompt template"""
        # Format arrays as comma-separated strings
        pest_concepts = ', '.join(workflow['pest_concepts']) if workflow['pest_concepts'] else 'general PEST concepts'
        uncertainty_methods = ', '.join(workflow['uncertainty_methods']) if workflow['uncertainty_methods'] else 'various methods'
        pyemu_modules = ', '.join(workflow['pyemu_modules']) if workflow['pyemu_modules'] else 'various modules'
        
        return {
            'notebook_file': workflow['notebook_file'],
            'title': workflow['title'] or 'Unknown Title',
            'workflow_type': workflow['workflow_type'] or 'uncertainty_analysis',
            'pest_concepts': pest_concepts,
            'uncertainty_methods': uncertainty_methods,
            'pyemu_modules': pyemu_modules
        }
    
    async def generate_analysis(self, workflow: Dict[str, Any]) -> Optional[PyEMUWorkflowAnalysis]:
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
            
            # Create PyEMUWorkflowAnalysis object
            analysis = PyEMUWorkflowAnalysis(
                workflow_purpose=analysis_data.get('workflow_purpose', ''),
                discriminative_questions=analysis_data.get('discriminative_questions', []),
                key_differentiators=analysis_data.get('key_differentiators', []),
                pest_tool_specifics=analysis_data.get('pest_tool_specifics', []),
                statistical_implementation=analysis_data.get('statistical_implementation', []),
                unique_pyemu_features=analysis_data.get('unique_pyemu_features', [])
            )
            
            self.logger.info(f"Generated analysis for {workflow['notebook_file']}")
            return analysis
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error for {workflow['notebook_file']}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error generating analysis for {workflow['notebook_file']}: {e}")
            return None
    
    def create_embedding_text(self, workflow: Dict[str, Any], analysis: PyEMUWorkflowAnalysis) -> str:
        """Create text for embedding generation"""
        parts = []
        
        # Add workflow metadata
        parts.append(f"PyEMU Workflow: {workflow['notebook_file']}")
        parts.append(f"Title: {workflow['title']}")
        parts.append(f"Type: {workflow['workflow_type']}")
        parts.append(f"Purpose: {analysis.workflow_purpose}")
        
        # Add discriminative questions
        if analysis.discriminative_questions:
            parts.append("Ultra-specific PyEMU questions:")
            for i, question in enumerate(analysis.discriminative_questions[:15], 1):
                if isinstance(question, dict):
                    question_text = question.get('question_text', str(question))
                else:
                    question_text = str(question)
                parts.append(f"{i}. {question_text}")
        
        # Add key differentiators
        if analysis.key_differentiators:
            parts.append("PyEMU workflow differentiators:")
            for diff in analysis.key_differentiators[:5]:
                parts.append(f"- {diff}")
        
        # Add PEST++ specifics
        if analysis.pest_tool_specifics:
            parts.append("PEST++ tool specifics:")
            for spec in analysis.pest_tool_specifics[:3]:
                parts.append(f"- {spec}")
        
        # Add statistical implementation details
        if analysis.statistical_implementation:
            parts.append("Statistical implementation:")
            for impl in analysis.statistical_implementation[:3]:
                parts.append(f"- {impl}")
        
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
    
    def save_to_database(self, workflow_id: str, analysis: PyEMUWorkflowAnalysis, 
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
                        'pest_tool_specifics': analysis.pest_tool_specifics,
                        'statistical_implementation': analysis.statistical_implementation,
                        'unique_pyemu_features': analysis.unique_pyemu_features
                    })
                    
                    embedding_str = self.format_embedding_for_postgres(embedding)
                    
                    cur.execute("""
                        UPDATE pyemu_workflows
                        SET analysis_v02 = %s,
                            emb_string_02 = %s,
                            dspy_emb_02 = %s::vector
                        WHERE id = %s
                    """, (analysis_json, embedding_text, embedding_str, workflow_id))
                    
                    conn.commit()
                    
        except Exception as e:
            self.logger.error(f"Error saving to database: {e}")
            raise
    
    def load_checkpoint(self) -> Optional[PyEMUEmbeddingCheckpoint]:
        """Load processing checkpoint"""
        checkpoint_file = self.checkpoints_dir / "embedding_v02_pyemu_checkpoint.json"
        
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)
                    return PyEMUEmbeddingCheckpoint(
                        batch_id=data['batch_id'],
                        completed_workflows=data['completed_workflows'],
                        failed_workflows=data['failed_workflows'],
                        timestamp=datetime.fromisoformat(data['timestamp']),
                        total_processed=data['total_processed']
                    )
            except Exception as e:
                self.logger.warning(f"Error loading checkpoint: {e}")
        
        return None
    
    def save_checkpoint(self, checkpoint: PyEMUEmbeddingCheckpoint):
        """Save processing checkpoint"""
        checkpoint_file = self.checkpoints_dir / "embedding_v02_pyemu_checkpoint.json"
        
        try:
            with open(checkpoint_file, 'w') as f:
                json.dump({
                    'batch_id': checkpoint.batch_id,
                    'completed_workflows': checkpoint.completed_workflows,
                    'failed_workflows': checkpoint.failed_workflows,
                    'timestamp': checkpoint.timestamp.isoformat(),
                    'total_processed': checkpoint.total_processed
                }, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving checkpoint: {e}")
    
    async def process_workflow(self, workflow: Dict[str, Any]) -> bool:
        """Process a single PyEMU workflow"""
        try:
            workflow_file = workflow['notebook_file']
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
                        cur.execute("SELECT analysis_v02 FROM pyemu_workflows WHERE id = %s", 
                                   (workflow['id'],))
                        analysis_data = cur.fetchone()[0]
                        
                        analysis = PyEMUWorkflowAnalysis(
                            workflow_purpose=analysis_data.get('workflow_purpose', ''),
                            discriminative_questions=analysis_data.get('discriminative_questions', []),
                            key_differentiators=analysis_data.get('key_differentiators', []),
                            pest_tool_specifics=analysis_data.get('pest_tool_specifics', []),
                            statistical_implementation=analysis_data.get('statistical_implementation', []),
                            unique_pyemu_features=analysis_data.get('unique_pyemu_features', [])
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
            self.logger.error(f"Error processing workflow {workflow['notebook_file']}: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    async def run_pipeline(self):
        """Run the complete PyEMU v02 embedding pipeline"""
        start_time = datetime.now()
        
        self.logger.info("=" * 80)
        self.logger.info("PYEMU V02 EMBEDDING PIPELINE")
        self.logger.info("=" * 80)
        
        try:
            # Load workflows needing processing
            workflows = self.load_workflows_needing_processing()
            
            if not workflows:
                self.logger.info("No PyEMU workflows need v02 processing")
                return
            
            # Load checkpoint
            checkpoint = self.load_checkpoint()
            if checkpoint:
                self.logger.info(f"Resuming from checkpoint: {checkpoint.total_processed} completed")
                completed_files = set(checkpoint.completed_workflows)
                workflows = [w for w in workflows if w['notebook_file'] not in completed_files]
            else:
                checkpoint = PyEMUEmbeddingCheckpoint(
                    batch_id=0,
                    completed_workflows=[],
                    failed_workflows=[],
                    timestamp=start_time,
                    total_processed=0
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
                        checkpoint.completed_workflows.append(workflow['notebook_file'])
                        checkpoint.total_processed += 1
                    else:
                        checkpoint.failed_workflows.append(workflow['notebook_file'])
                
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
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(analysis_v02) as with_analysis,
                            COUNT(dspy_emb_02) as with_embedding
                        FROM pyemu_workflows
                    """)
                    
                    total, with_analysis, with_embedding = cur.fetchone()
                    
                    self.logger.info(f"Validation Results:")
                    self.logger.info(f"  Total workflows: {total}")
                    self.logger.info(f"  With v02 analysis: {with_analysis} ({with_analysis/total*100:.1f}%)")
                    self.logger.info(f"  With v02 embeddings: {with_embedding} ({with_embedding/total*100:.1f}%)")
                    
                    if with_embedding == total:
                        self.logger.info("✅ All PyEMU workflows have v02 embeddings!")
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
    
    parser = argparse.ArgumentParser(description="PyEMU V02 Embedding Pipeline")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Batch size for processing"
    )
    
    args = parser.parse_args()
    
    # Create and run pipeline
    pipeline = PyEMUEmbeddingPipelineV02(
        neon_conn_string=config.NEON_CONNECTION_STRING,
        gemini_api_key=config.GEMINI_API_KEY,
        openai_api_key=config.OPENAI_API_KEY,
        batch_size=args.batch_size
    )
    
    await pipeline.run_pipeline()


if __name__ == "__main__":
    asyncio.run(main())