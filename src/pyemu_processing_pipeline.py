#!/usr/bin/env python3
"""
Processing Pipeline for pyEMU Semantic Database

Adapted from FloPy pipeline but focused on uncertainty analysis and PEST concepts
"""
import asyncio
import hashlib
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import ast
import re

import psycopg2
from psycopg2.extras import RealDictCursor
import google.genai as genai
from openai import AsyncOpenAI
import subprocess

from .pyemu_docs_parser import PyEMUDocsParser, PyEMUModule


@dataclass
class PyEMUProcessingCheckpoint:
    """Represents a processing checkpoint for pyEMU"""
    batch_id: int
    completed_files: List[str]
    failed_files: List[str]
    timestamp: datetime
    total_processed: int
    category: str


@dataclass
class PyEMUModuleInfo:
    """Information extracted from a pyEMU module"""
    file_path: str
    relative_path: str
    category: str              # core, utils, pst, mat, plot
    module_name: str          # e.g., "sc" for Schur, "en" for Ensemble
    module_docstring: Optional[str]
    class_docstrings: List[str]
    function_docstrings: List[str]
    imports: List[str]
    classes: List[str]
    functions: List[str]
    file_hash: str
    last_modified: datetime
    # Git information
    git_commit_hash: Optional[str] = None
    git_branch: Optional[str] = None
    git_commit_date: Optional[datetime] = None


@dataclass
class PyEMUSemanticAnalysis:
    """Semantic analysis for uncertainty/PEST concepts"""
    semantic_purpose: str
    use_cases: List[str]          # When to use this method
    pest_integration: List[str]   # How it works with PEST/PEST++
    statistical_concepts: List[str]  # Key statistical concepts
    common_pitfalls: List[str]    # Common mistakes in usage


class PyEMUProcessor:
    """Processing pipeline for pyEMU semantic database"""
    
    def __init__(self, 
                 repo_path: str,
                 neon_conn_string: str, 
                 gemini_api_key: str, 
                 openai_api_key: str,
                 batch_size: int = 10,
                 gemini_model: str = "gemini-2.5-flash",
                 openai_model: str = "text-embedding-3-small"):
        self.repo_path = Path(repo_path)
        self.neon_conn = neon_conn_string
        self.batch_size = batch_size
        
        # Initialize AI clients
        self.gemini_client = genai.Client(api_key=gemini_api_key)
        self.gemini_model = "gemini-2.5-pro"  # Always use pro for better quality
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.openai_model = openai_model
        
        # Initialize docs parser
        self.docs_parser = PyEMUDocsParser(repo_path)
        
        # Create checkpoints directory
        self.checkpoints_dir = Path("/home/danilopezmella/flopy_expert/pyemu_checkpoints")
        self.checkpoints_dir.mkdir(exist_ok=True)
        
        # Ensure database tables exist
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Create pyEMU-specific database tables if they don't exist"""
        
        table_schemas = [
            # pyEMU modules table - separate from FloPy
            """
            CREATE TABLE IF NOT EXISTS pyemu_modules (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                file_path TEXT UNIQUE NOT NULL,
                relative_path TEXT NOT NULL,
                
                -- pyEMU-specific categorization
                category TEXT,              -- core, utils, pst, mat, plot
                module_name TEXT,          -- sc, en, ev, etc.
                
                -- Content
                module_docstring TEXT,
                source_code TEXT,
                
                -- AI-generated semantic analysis for uncertainty/PEST
                semantic_purpose TEXT NOT NULL,
                use_cases TEXT[],          -- When to use this method
                pest_integration TEXT[],   -- PEST/PEST++ workflow integration
                statistical_concepts TEXT[], -- Key stats concepts
                common_pitfalls TEXT[],    -- Common usage mistakes
                
                -- For debugging what was embedded
                embedding_text TEXT NOT NULL,
                
                -- Single embedding combining code + semantic understanding
                embedding vector(1536) NOT NULL,
                
                -- Full-text search
                search_vector tsvector GENERATED ALWAYS AS (
                    to_tsvector('english', 
                        COALESCE(module_name, '') || ' ' ||
                        COALESCE(category, '') || ' ' ||
                        COALESCE(semantic_purpose, '') || ' ' ||
                        COALESCE(module_docstring, '')
                    )
                ) STORED,
                
                -- Metadata
                file_hash TEXT NOT NULL,
                last_modified TIMESTAMP,
                processed_at TIMESTAMP DEFAULT NOW(),
                
                -- Git tracking
                git_commit_hash TEXT,
                git_branch TEXT,
                git_commit_date TIMESTAMP
            );
            """,
            
            # pyEMU processing log
            """
            CREATE TABLE IF NOT EXISTS pyemu_processing_log (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                batch_id INTEGER,
                category TEXT,
                total_files INTEGER,
                successful_files INTEGER,
                failed_files INTEGER,
                processing_time_seconds INTEGER,
                error_details JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """
        ]
        
        # Index creation statements
        index_schemas = [
            "CREATE INDEX IF NOT EXISTS idx_pyemu_modules_category ON pyemu_modules(category);",
            "CREATE INDEX IF NOT EXISTS idx_pyemu_modules_name ON pyemu_modules(module_name);", 
            "CREATE INDEX IF NOT EXISTS idx_pyemu_modules_embedding ON pyemu_modules USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);",
            "CREATE INDEX IF NOT EXISTS idx_pyemu_modules_search_vector ON pyemu_modules USING gin(search_vector);",
        ]
        
        try:
            with psycopg2.connect(self.neon_conn) as conn:
                with conn.cursor() as cur:
                    # Create tables
                    for schema in table_schemas:
                        cur.execute(schema)
                    
                    # Create indexes
                    for index in index_schemas:
                        cur.execute(index)
                    
                    conn.commit()
                    print("✅ pyEMU database tables and indexes ready")
                    
        except Exception as e:
            print(f"❌ Error creating pyEMU database tables: {e}")
            raise
    
    def get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file content"""
        return hashlib.sha256(file_path.read_bytes()).hexdigest()
    
    def get_git_info(self) -> Dict[str, Any]:
        """Get current git information from repository"""
        try:
            # Get current commit hash
            commit_hash = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], 
                cwd=self.repo_path
            ).decode().strip()
            
            # Get current branch
            branch = subprocess.check_output(
                ['git', 'branch', '--show-current'], 
                cwd=self.repo_path
            ).decode().strip()
            
            # Get commit date
            commit_date_str = subprocess.check_output(
                ['git', 'show', '-s', '--format=%ci', 'HEAD'], 
                cwd=self.repo_path
            ).decode().strip()
            
            # Parse the date string
            commit_date = datetime.strptime(commit_date_str.split()[0] + ' ' + commit_date_str.split()[1], 
                                          '%Y-%m-%d %H:%M:%S')
            
            return {
                'commit_hash': commit_hash,
                'branch': branch or 'detached',
                'commit_date': commit_date
            }
        except Exception as e:
            print(f"Warning: Could not get git info: {e}")
            return {
                'commit_hash': None,
                'branch': None,
                'commit_date': None
            }
    
    def extract_module_info(self, file_path: Path, module: PyEMUModule) -> PyEMUModuleInfo:
        """Extract information from a pyEMU module"""
        content = file_path.read_text(encoding='utf-8')
        relative_path = file_path.relative_to(self.repo_path)
        
        # Extract module name from path
        module_name = file_path.stem
        
        # Get git information
        git_info = self.get_git_info()
        
        # Parse AST to extract docstring, imports, classes, functions
        try:
            tree = ast.parse(content)
            module_docstring = ast.get_docstring(tree)
            
            imports = []
            classes = []
            functions = []
            class_docstrings = []
            function_docstrings = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                    class_doc = ast.get_docstring(node)
                    if class_doc:
                        class_docstrings.append(class_doc)
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                    func_doc = ast.get_docstring(node)
                    if func_doc:
                        function_docstrings.append(func_doc)
                    
        except Exception as e:
            print(f"Warning: Could not parse AST for {file_path}: {e}")
            module_docstring = None
            imports = []
            classes = []
            functions = []
            class_docstrings = []
            function_docstrings = []
        
        return PyEMUModuleInfo(
            file_path=str(file_path),
            relative_path=str(relative_path),
            category=module.category,
            module_name=module_name,
            module_docstring=module_docstring,
            class_docstrings=class_docstrings,
            function_docstrings=function_docstrings,
            imports=imports,
            classes=classes,
            functions=functions,
            file_hash=self.get_file_hash(file_path),
            last_modified=datetime.fromtimestamp(file_path.stat().st_mtime),
            git_commit_hash=git_info['commit_hash'],
            git_branch=git_info['branch'],
            git_commit_date=git_info['commit_date']
        )
    
    async def analyze_with_gemini(self, module_info: PyEMUModuleInfo, enable_gemini: bool = True) -> PyEMUSemanticAnalysis:
        """Analyze module with Gemini for uncertainty/PEST understanding"""
        
        # Check if Gemini is disabled
        if not enable_gemini:
            return self._create_fallback_analysis(module_info)
        
        prompt = f"""
Analyze this pyEMU module for parameter estimation and uncertainty analysis:

File: {module_info.relative_path}
Category: {module_info.category}
Module: {module_info.module_name}

Module Docstring:
{module_info.module_docstring or 'No docstring available'}

Classes: {', '.join(module_info.classes[:5])}
Functions: {', '.join(module_info.functions[:5])}

Provide a comprehensive analysis in markdown format with these sections:

## Purpose
What specific uncertainty analysis or PEST-related purpose does this module serve? Focus on statistical methods, parameter estimation, or PEST integration.

## Use Cases
List 3-4 specific scenarios when a modeler would use this module:
- Use case 1 for parameter estimation or uncertainty
- Use case 2 for model calibration workflow
- Use case 3 for sensitivity or worth analysis

## PEST Integration
How does this module work with PEST/PEST++:
- PEST file integration point 1
- Workflow connection 2
- Data flow aspect 3

## Statistical Concepts
Key statistical or mathematical concepts involved:
- Statistical concept 1 (e.g., FOSM, Bayes, Monte Carlo)
- Mathematical foundation 2
- Uncertainty principle 3

## Common Pitfalls
Common mistakes users make with this module:
- Pitfall 1 and how to avoid it
- Pitfall 2 and best practice
- Pitfall 3 and solution

Focus on practical calibration and uncertainty quantification applications.
"""
        
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self.gemini_client.models.generate_content,
                    model=self.gemini_model,
                    contents=prompt
                )
                
                # Parse markdown response
                text = response.text
                
                # Extract sections using regex
                purpose_match = re.search(r'## Purpose\s*\n(.+?)(?=\n## |$)', text, re.DOTALL)
                purpose = purpose_match.group(1).strip() if purpose_match else ""
                
                # Extract use cases
                use_cases_match = re.search(r'## Use Cases\s*\n(.+?)(?=\n## |$)', text, re.DOTALL)
                use_cases = []
                if use_cases_match:
                    use_cases_text = use_cases_match.group(1)
                    use_cases = [line.strip()[2:].strip() for line in use_cases_text.split('\n') 
                               if line.strip().startswith('- ')]
                
                # Extract PEST integration
                pest_match = re.search(r'## PEST Integration\s*\n(.+?)(?=\n## |$)', text, re.DOTALL)
                pest_integration = []
                if pest_match:
                    pest_text = pest_match.group(1)
                    pest_integration = [line.strip()[2:].strip() for line in pest_text.split('\n') 
                                      if line.strip().startswith('- ')]
                
                # Extract statistical concepts
                stats_match = re.search(r'## Statistical Concepts\s*\n(.+?)(?=\n## |$)', text, re.DOTALL)
                stats_concepts = []
                if stats_match:
                    stats_text = stats_match.group(1)
                    stats_concepts = [line.strip()[2:].strip() for line in stats_text.split('\n') 
                                    if line.strip().startswith('- ')]
                
                # Extract common pitfalls
                pitfalls_match = re.search(r'## Common Pitfalls\s*\n(.+?)(?=\n## |$)', text, re.DOTALL)
                pitfalls = []
                if pitfalls_match:
                    pitfalls_text = pitfalls_match.group(1)
                    pitfalls = [line.strip()[2:].strip() for line in pitfalls_text.split('\n') 
                              if line.strip().startswith('- ')]
                
                # Validate we got meaningful content
                if not purpose or len(purpose) < 50:
                    raise ValueError(f"AI analysis returned minimal purpose ({len(purpose)} chars)")
                
                # Accept even partial results if we have good purpose
                if len(use_cases) == 0:
                    print(f"  Warning: No use cases extracted, using defaults")
                    use_cases = ["General uncertainty analysis", "PEST integration"]
                
                return PyEMUSemanticAnalysis(
                    semantic_purpose=purpose,
                    use_cases=use_cases,
                    pest_integration=pest_integration,
                    statistical_concepts=stats_concepts,
                    common_pitfalls=pitfalls
                )
                
            except Exception as e:
                print(f"Gemini attempt {attempt + 1}/{max_retries} failed for {module_info.relative_path}: {e}")
                if attempt < max_retries - 1:
                    print(f"  Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print(f"  All retries exhausted. Using fallback analysis.")
                    return self._create_fallback_analysis(module_info)
    
    def _create_fallback_analysis(self, module_info: PyEMUModuleInfo) -> PyEMUSemanticAnalysis:
        """Create fallback semantic analysis for pyEMU modules"""
        
        # Module-specific analysis based on name and category
        module_analyses = {
            'sc': 'Schur complement for conditional uncertainty propagation (PREDUNC foundation)',
            'ev': 'Error variance analysis for prediction uncertainty (PREDVAR foundation)',
            'en': 'Ensemble management for Monte Carlo and PEST++ IES analyses',
            'la': 'Linear analysis base class for FOSM uncertainty quantification',
            'mc': 'Monte Carlo utilities for non-linear uncertainty analysis',
            'geostats': 'Geostatistical tools for spatial correlation and kriging',
            'pst_handler': 'PEST control file manipulation and management',
            'helpers': 'Utility functions for common PEST workflows',
            'mat_handler': 'Matrix operations for Jacobian and covariance matrices',
        }
        
        purpose = module_analyses.get(module_info.module_name, 
            f"pyEMU {module_info.category} module for {module_info.module_name} functionality")
        
        # Category-specific scenarios
        if module_info.category == 'core':
            use_cases = [
                "Linear uncertainty analysis for forecast predictions",
                "Parameter estimation workflow with PEST++",
                "Sensitivity analysis for model parameters"
            ]
        elif module_info.category == 'utils':
            use_cases = [
                "PEST interface setup and configuration",
                "Geostatistical parameter field generation",
                "Model file preprocessing and postprocessing"
            ]
        else:
            use_cases = [
                f"{module_info.category.upper()} operations",
                "PEST workflow automation",
                "Model analysis and visualization"
            ]
        
        return PyEMUSemanticAnalysis(
            semantic_purpose=purpose,
            use_cases=use_cases,
            pest_integration=["PEST control file integration", "PEST++ compatibility"],
            statistical_concepts=["FOSM", "Linear analysis", "Uncertainty propagation"],
            common_pitfalls=["Incorrect uncertainty assumptions", "Non-linear model limitations"]
        )
    
    async def create_embedding(self, module_info: PyEMUModuleInfo, semantic_analysis: PyEMUSemanticAnalysis) -> tuple[List[float], str]:
        """Create combined embedding for pyEMU module"""
        
        # Combine all text for embedding
        primary_docstring = ""
        if module_info.class_docstrings:
            primary_docstring = module_info.class_docstrings[0][:500]
        elif module_info.module_docstring:
            primary_docstring = module_info.module_docstring
        
        text_parts = [
            module_info.module_name,
            module_info.category,
            primary_docstring,
            semantic_analysis.semantic_purpose,
            " ".join(semantic_analysis.use_cases),
            " ".join(semantic_analysis.pest_integration),
            " ".join(semantic_analysis.statistical_concepts),
        ]
        
        combined_text = " ".join(filter(None, text_parts))
        
        try:
            response = await self.openai_client.embeddings.create(
                input=combined_text,
                model=self.openai_model
            )
            return response.data[0].embedding, combined_text
            
        except Exception as e:
            print(f"Embedding creation failed for {module_info.relative_path}: {e}")
            # Return zero vector as fallback
            return [0.0] * 1536, combined_text
    
    def save_to_database(self, 
                        module_info: PyEMUModuleInfo, 
                        semantic_analysis: PyEMUSemanticAnalysis, 
                        embedding: List[float],
                        embedding_text: str) -> bool:
        """Save processed pyEMU module to database"""
        
        try:
            with psycopg2.connect(self.neon_conn) as conn:
                with conn.cursor() as cur:
                    # Check if module already exists
                    cur.execute(
                        "SELECT id, file_hash FROM pyemu_modules WHERE file_path = %s",
                        (module_info.file_path,)
                    )
                    existing = cur.fetchone()
                    
                    if existing and existing[1] == module_info.file_hash:
                        print(f"Skipping {module_info.relative_path} - unchanged")
                        return True
                    
                    # Insert or update module
                    sql = """
                        INSERT INTO pyemu_modules (
                            file_path, relative_path, category, module_name,
                            module_docstring, source_code, semantic_purpose,
                            use_cases, pest_integration, statistical_concepts, common_pitfalls,
                            embedding_text, embedding, file_hash, last_modified,
                            git_commit_hash, git_branch, git_commit_date
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (file_path) DO UPDATE SET
                            relative_path = EXCLUDED.relative_path,
                            category = EXCLUDED.category,
                            module_name = EXCLUDED.module_name,
                            module_docstring = EXCLUDED.module_docstring,
                            source_code = EXCLUDED.source_code,
                            semantic_purpose = EXCLUDED.semantic_purpose,
                            use_cases = EXCLUDED.use_cases,
                            pest_integration = EXCLUDED.pest_integration,
                            statistical_concepts = EXCLUDED.statistical_concepts,
                            common_pitfalls = EXCLUDED.common_pitfalls,
                            embedding_text = EXCLUDED.embedding_text,
                            embedding = EXCLUDED.embedding,
                            file_hash = EXCLUDED.file_hash,
                            last_modified = EXCLUDED.last_modified,
                            git_commit_hash = EXCLUDED.git_commit_hash,
                            git_branch = EXCLUDED.git_branch,
                            git_commit_date = EXCLUDED.git_commit_date,
                            processed_at = NOW()
                    """
                    
                    # Read source code
                    source_code = Path(module_info.file_path).read_text(encoding='utf-8')
                    
                    cur.execute(sql, (
                        module_info.file_path,
                        module_info.relative_path,
                        module_info.category,
                        module_info.module_name,
                        module_info.module_docstring,
                        source_code,
                        semantic_analysis.semantic_purpose,
                        semantic_analysis.use_cases,
                        semantic_analysis.pest_integration,
                        semantic_analysis.statistical_concepts,
                        semantic_analysis.common_pitfalls,
                        embedding_text,
                        embedding,
                        module_info.file_hash,
                        module_info.last_modified,
                        module_info.git_commit_hash,
                        module_info.git_branch,
                        module_info.git_commit_date
                    ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            print(f"Database save failed for {module_info.relative_path}: {e}")
            return False
    
    def save_checkpoint(self, checkpoint: PyEMUProcessingCheckpoint):
        """Save processing checkpoint to disk"""
        checkpoint_file = self.checkpoints_dir / f"checkpoint_{checkpoint.category}_{checkpoint.batch_id}.json"
        
        # Convert dataclass to dict and handle datetime serialization
        checkpoint_data = asdict(checkpoint)
        checkpoint_data['timestamp'] = checkpoint.timestamp.isoformat()
        
        checkpoint_file.write_text(json.dumps(checkpoint_data, indent=2))
        print(f"Checkpoint saved: {checkpoint_file}")
    
    def load_checkpoint(self, category: str) -> Optional[PyEMUProcessingCheckpoint]:
        """Load the latest checkpoint for a category"""
        checkpoints = list(self.checkpoints_dir.glob(f"checkpoint_{category}_*.json"))
        
        if not checkpoints:
            return None
        
        # Find latest checkpoint
        latest = max(checkpoints, key=lambda p: p.stat().st_mtime)
        
        try:
            data = json.loads(latest.read_text())
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            return PyEMUProcessingCheckpoint(**data)
        except Exception as e:
            print(f"Failed to load checkpoint {latest}: {e}")
            return None
    
    async def process_batch(self, 
                           batch: List[Tuple[Path, PyEMUModule]], 
                           batch_id: int, 
                           category: str) -> Tuple[List[str], List[str]]:
        """Process a batch of pyEMU files"""
        completed = []
        failed = []
        
        print(f"\nProcessing batch {batch_id} ({category}): {len(batch)} files")
        
        for file_path, module in batch:
            try:
                print(f"  Processing {file_path.relative_to(self.repo_path)}...")
                
                # Extract module info
                module_info = self.extract_module_info(file_path, module)
                
                # Semantic analysis with Gemini
                semantic_analysis = await self.analyze_with_gemini(module_info)
                
                # Create embedding
                embedding, embedding_text = await self.create_embedding(module_info, semantic_analysis)
                
                # Save to database
                if self.save_to_database(module_info, semantic_analysis, embedding, embedding_text):
                    completed.append(str(file_path))
                    print(f"    ✓ Saved {module_info.module_name}")
                else:
                    failed.append(str(file_path))
                    print(f"    ✗ Failed to save")
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                failed.append(str(file_path))
                print(f"    ✗ Error processing {file_path.name}: {e}")
                traceback.print_exc()
        
        return completed, failed
    
    async def process_category(self, category: str, files: List[Tuple[Path, PyEMUModule]]):
        """Process all files for a category with checkpointing"""
        
        print(f"\n{'='*60}")
        print(f"Processing {category.upper()}: {len(files)} files")
        print(f"{'='*60}")
        
        # Load checkpoint if exists
        checkpoint = self.load_checkpoint(category)
        start_batch = 0
        total_processed = 0
        
        if checkpoint:
            print(f"Resuming from checkpoint: batch {checkpoint.batch_id}")
            start_batch = checkpoint.batch_id + 1
            total_processed = checkpoint.total_processed
            
            # Filter out already completed files
            completed_set = set(checkpoint.completed_files)
            files = [(f, m) for f, m in files if str(f) not in completed_set]
        
        # Process in batches
        for i in range(0, len(files), self.batch_size):
            batch_id = start_batch + (i // self.batch_size)
            batch = files[i:i + self.batch_size]
            
            completed, failed = await self.process_batch(batch, batch_id, category)
            total_processed += len(completed)
            
            # Save checkpoint
            checkpoint = PyEMUProcessingCheckpoint(
                batch_id=batch_id,
                completed_files=completed,
                failed_files=failed,
                timestamp=datetime.now(),
                total_processed=total_processed,
                category=category
            )
            self.save_checkpoint(checkpoint)
            
            print(f"Batch {batch_id} complete: {len(completed)} success, {len(failed)} failed")
            
            # Longer delay between batches
            await asyncio.sleep(2)
        
        print(f"\n{category.upper()} processing complete: {total_processed} modules processed")
    
    async def process_all(self):
        """Process all documented pyEMU modules"""
        
        print("🚀 Starting pyEMU Semantic Database Processing")
        print("=" * 80)
        
        # Get processing queue
        queue = self.docs_parser.create_processing_queue()
        
        # Process in priority order (core first)
        priority_order = ['core', 'utils', 'pst', 'mat', 'plot']
        
        total_files = sum(len(files) for files in queue.values())
        print(f"Total modules to process: {total_files}")
        print()
        
        start_time = datetime.now()
        
        for category in priority_order:
            if category in queue:
                await self.process_category(category, queue[category])
        
        # Process any remaining categories
        for category, files in queue.items():
            if category not in priority_order:
                await self.process_category(category, files)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "=" * 80)
        print("🎉 pyEMU Semantic Database Processing Complete!")
        print(f"⏱️  Total time: {duration}")
        print(f"📊 Total modules: {total_files}")
        print("=" * 80)


# Main execution
if __name__ == "__main__":
    import asyncio
    import sys
    sys.path.append('/home/danilopezmella/flopy_expert')
    import config
    
    processor = PyEMUProcessor(
        repo_path="/home/danilopezmella/flopy_expert/pyemu",
        neon_conn_string=config.NEON_CONNECTION_STRING,
        gemini_api_key=config.GEMINI_API_KEY,
        openai_api_key=config.OPENAI_API_KEY,
        batch_size=config.BATCH_SIZE,
        gemini_model=config.GEMINI_MODEL
    )
    
    asyncio.run(processor.process_all())