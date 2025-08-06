#!/usr/bin/env python3
"""
Robust Processing Pipeline for FloPy Semantic Database

Implements Step 2 of our roadmap: Batch Processing with Checkpoints
- Process 224 documented modules in batches of 10
- Use Gemini for semantic analysis 
- Create OpenAI embeddings
- Save checkpoints after each batch
- Handle errors and retries
- Track file hashes for incremental updates
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
import subprocess

import psycopg2
from psycopg2.extras import RealDictCursor
import google.genai as genai
from openai import AsyncOpenAI

from .flopy_docs_parser import FloPyDocsParser, ModulePattern


@dataclass
class ProcessingCheckpoint:
    """Represents a processing checkpoint"""
    batch_id: int
    completed_files: List[str]
    failed_files: List[str]
    timestamp: datetime
    total_processed: int
    model_family: str


@dataclass
class ModuleInfo:
    """Information extracted from a Python module"""
    file_path: str
    relative_path: str
    model_family: str
    package_code: Optional[str]
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
class SemanticAnalysis:
    """Semantic analysis from Gemini"""
    semantic_purpose: str
    user_scenarios: List[str]
    related_concepts: List[str]
    typical_errors: List[str]


class FloPyProcessor:
    """Main processing pipeline for FloPy semantic database"""
    
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
        self.docs_parser = FloPyDocsParser(repo_path)
        
        # Create checkpoints directory
        self.checkpoints_dir = self.repo_path / "processing_checkpoints"
        self.checkpoints_dir.mkdir(exist_ok=True)
        
        # Ensure database tables exist
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Create database tables if they don't exist"""
        
        table_schemas = [
            # Extensions
            "CREATE EXTENSION IF NOT EXISTS vector;",
            "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";",
            
            # Main flopy_modules table
            """
            CREATE TABLE IF NOT EXISTS flopy_modules (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                file_path TEXT UNIQUE NOT NULL,
                relative_path TEXT NOT NULL,
                
                -- Extracted from path/filename
                model_family TEXT,
                package_code TEXT,
                
                -- Content
                module_docstring TEXT,
                source_code TEXT,
                
                -- Gemini semantic analysis
                semantic_purpose TEXT NOT NULL,
                user_scenarios TEXT[],
                related_concepts TEXT[],
                typical_errors TEXT[],
                
                -- The actual text that was embedded for debugging
                embedding_text TEXT NOT NULL,
                
                -- Single embedding combining code + semantic understanding
                embedding vector(1536) NOT NULL,
                
                -- Full-text search
                search_vector tsvector GENERATED ALWAYS AS (
                    to_tsvector('english', 
                        COALESCE(package_code, '') || ' ' ||
                        COALESCE(model_family, '') || ' ' ||
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
            
            
            # Processing log table
            """
            CREATE TABLE IF NOT EXISTS processing_log (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                batch_id INTEGER,
                model_family TEXT,
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
            "CREATE INDEX IF NOT EXISTS idx_flopy_modules_model_family ON flopy_modules(model_family);",
            "CREATE INDEX IF NOT EXISTS idx_flopy_modules_package_code ON flopy_modules(package_code);", 
            "CREATE INDEX IF NOT EXISTS idx_flopy_modules_embedding ON flopy_modules USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);",
            "CREATE INDEX IF NOT EXISTS idx_flopy_modules_search_vector ON flopy_modules USING gin(search_vector);"
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
                    print("✅ Database tables and indexes ready")
                    
        except Exception as e:
            print(f"❌ Error creating database tables: {e}")
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
    
    def extract_module_info(self, file_path: Path, pattern: ModulePattern) -> ModuleInfo:
        """Extract basic information from a Python module"""
        content = file_path.read_text(encoding='utf-8')
        relative_path = file_path.relative_to(self.repo_path)
        
        # Extract package code from filename
        package_code = self._extract_package_code(file_path)
        
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
        
        return ModuleInfo(
            file_path=str(file_path),
            relative_path=str(relative_path),
            model_family=pattern.model_family,
            package_code=package_code,
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
    
    def _extract_package_code(self, file_path: Path) -> Optional[str]:
        """Extract package code from filename (e.g., mfgwfwel.py -> WEL)"""
        filename = file_path.stem
        
        # Better patterns for package codes - look for 3-4 letter codes at end
        patterns = [
            r'mfgwf([a-z]{3,4})$',     # mfgwfwel -> wel, mfgwfchd -> chd
            r'mfgwt([a-z]{3,4})$',     # mfgwtadv -> adv
            r'mfgwe([a-z]{3,4})$',     # mfgweadv -> adv
            r'mfprt([a-z]{3,4})$',     # mfprtprp -> prp
            r'mfutl([a-z]{3,4})$',     # mfutlobs -> obs
            r'mf([a-z]{3,4})$',        # mfwel -> wel, mfchd -> chd
            r'mt([a-z]{3})$',          # mtadv -> adv
            r'swt([a-z]{3})$',         # swtvdf -> vdf
            r'mp[67]?([a-z]{3})$',     # mp7bas -> bas
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        # Special cases for common packages
        special_cases = {
            'simulation': 'SIM',
            'sms': 'SMS',
            'uzf': 'UZF',
            'dis': 'DIS',
            'disu': 'DISU', 
            'disv': 'DISV',
            'tdis': 'TDIS',
            'gnc': 'GNC',
            'ims': 'IMS',
            'mvr': 'MVR',
            'nam': 'NAM'
        }
        
        for keyword, code in special_cases.items():
            if keyword in filename.lower():
                return code
        
        return None
    
    async def analyze_with_gemini(self, module_info: ModuleInfo, enable_gemini: bool = True) -> SemanticAnalysis:
        """Analyze module with Gemini for semantic understanding"""
        
        # Check if Gemini is disabled in config
        if not enable_gemini:
            return self._create_fallback_analysis(module_info)
        
        prompt = f"""
Analyze this FloPy Python module for groundwater modeling:

File: {module_info.relative_path}
Model Family: {module_info.model_family}
Package Code: {module_info.package_code or 'Unknown'}

Module Docstring:
{module_info.module_docstring or 'No docstring available'}

Classes: {', '.join(module_info.classes[:5])}
Functions: {', '.join(module_info.functions[:5])}

Provide a comprehensive analysis in markdown format with these sections:

## Purpose
What specific groundwater modeling purpose does this module serve? Be precise about MODFLOW packages, solver types, boundary conditions, etc. If this is a solver like SMS, distinguish it clearly from packages like UZF.

## User Scenarios
List 3-4 specific scenarios when a hydrologist would use this module:
- Scenario 1 description
- Scenario 2 description  
- Scenario 3 description

## Related Concepts
List related FloPy concepts, packages, solvers, or modeling approaches:
- Related concept 1
- Related concept 2
- Related concept 3

## Typical Errors
Common mistakes users make with this module:
- Error type 1 and how to avoid it
- Error type 2 and how to avoid it
- Error type 3 and how to avoid it

Focus on practical modeling applications and real-world usage patterns.
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
                
                # Extract user scenarios (list items)
                scenarios_match = re.search(r'## User Scenarios\s*\n(.+?)(?=\n## |$)', text, re.DOTALL)
                scenarios = []
                if scenarios_match:
                    scenarios_text = scenarios_match.group(1)
                    scenarios = [line.strip()[2:].strip() for line in scenarios_text.split('\n') 
                               if line.strip().startswith('- ')]
                
                # Extract related concepts (list items)
                concepts_match = re.search(r'## Related Concepts\s*\n(.+?)(?=\n## |$)', text, re.DOTALL)
                concepts = []
                if concepts_match:
                    concepts_text = concepts_match.group(1)
                    concepts = [line.strip()[2:].strip() for line in concepts_text.split('\n') 
                              if line.strip().startswith('- ')]
                
                # Extract typical errors (list items)
                errors_match = re.search(r'## Typical Errors\s*\n(.+?)(?=\n## |$)', text, re.DOTALL)
                errors = []
                if errors_match:
                    errors_text = errors_match.group(1)
                    errors = [line.strip()[2:].strip() for line in errors_text.split('\n') 
                             if line.strip().startswith('- ')]
                
                # Validate we got meaningful content
                if not purpose or len(purpose) < 50:
                    raise ValueError(f"AI analysis returned minimal purpose ({len(purpose)} chars)")
                
                # Accept even partial results if we have good purpose
                if len(scenarios) == 0:
                    print(f"  Warning: No user scenarios extracted, using defaults")
                    scenarios = ["General module usage", "Integration with other packages"]
                
                return SemanticAnalysis(
                    semantic_purpose=purpose,
                    user_scenarios=scenarios,
                    related_concepts=concepts,
                    typical_errors=errors
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
    
    def _create_fallback_analysis(self, module_info: ModuleInfo) -> SemanticAnalysis:
        """Create fallback semantic analysis when Gemini is unavailable"""
        
        # Enhanced fallback based on package code and module info
        package_code = module_info.package_code or "module"
        model_family = module_info.model_family
        
        # Package-specific analysis
        package_descriptions = {
            'SMS': 'Sparse Matrix Solver for MODFLOW-USG and MODFLOW 6 - handles complex numerical solutions',
            'UZF': 'Unsaturated Zone Flow package for simulating vadose zone processes',
            'WEL': 'Well package for simulating pumping wells and injection wells',
            'CHD': 'Constant Head package for setting fixed head boundary conditions',
            'DRN': 'Drain package for simulating drainage systems',
            'GHB': 'General Head Boundary package for head-dependent flux boundaries',
            'RIV': 'River package for simulating surface water-groundwater interaction',
            'LAK': 'Lake package for simulating lake-groundwater interaction',
            'SFR': 'Streamflow Routing package for simulating stream networks',
            'MAW': 'Multi-Aquifer Well package for complex well configurations',
        }
        
        purpose = package_descriptions.get(package_code, 
            f"FloPy {model_family} module for {package_code.lower()} functionality")
        
        # Model family specific scenarios
        if model_family == 'mf6':
            scenarios = [
                "MODFLOW 6 model setup and configuration",
                "Advanced groundwater flow simulation",
                "Multi-model coupling applications"
            ]
        elif model_family == 'modflow':
            scenarios = [
                "Classic MODFLOW-2005 model development", 
                "Legacy model conversion and analysis",
                "Standard groundwater flow modeling"
            ]
        elif model_family == 'mt3d':
            scenarios = [
                "Contaminant transport modeling",
                "Solute transport simulation",
                "Geochemical reaction modeling"
            ]
        else:
            scenarios = [
                f"{model_family.upper()} model applications",
                "Specialized groundwater modeling",
                "Model post-processing and analysis"
            ]
        
        return SemanticAnalysis(
            semantic_purpose=purpose,
            user_scenarios=scenarios,
            related_concepts=[model_family, package_code, "MODFLOW", "groundwater"],
            typical_errors=["Parameter validation", "Input file formatting", "Boundary condition setup"]
        )
    
    async def create_embedding(self, module_info: ModuleInfo, semantic_analysis: SemanticAnalysis) -> tuple[List[float], str]:
        """Create combined embedding for module and return both embedding and text"""
        
        # Combine all text for embedding
        # Use class docstrings (more detailed) with fallback to module docstring
        primary_docstring = ""
        if module_info.class_docstrings:
            # Use the first (usually main) class docstring, truncated to avoid token limits
            primary_docstring = module_info.class_docstrings[0][:500]
        elif module_info.module_docstring:
            primary_docstring = module_info.module_docstring
        
        text_parts = [
            module_info.package_code or "",
            module_info.model_family,
            primary_docstring,
            semantic_analysis.semantic_purpose,
            " ".join(semantic_analysis.user_scenarios),
            " ".join(semantic_analysis.related_concepts),
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
                        module_info: ModuleInfo, 
                        semantic_analysis: SemanticAnalysis, 
                        embedding: List[float],
                        embedding_text: str) -> bool:
        """Save processed module to database"""
        
        try:
            with psycopg2.connect(self.neon_conn) as conn:
                with conn.cursor() as cur:
                    # Check if module already exists
                    cur.execute(
                        "SELECT id, file_hash FROM flopy_modules WHERE file_path = %s",
                        (module_info.file_path,)
                    )
                    existing = cur.fetchone()
                    
                    if existing and existing[1] == module_info.file_hash:
                        print(f"Skipping {module_info.relative_path} - unchanged")
                        return True
                    
                    # Insert or update module
                    sql = """
                        INSERT INTO flopy_modules (
                            file_path, relative_path, model_family, package_code,
                            module_docstring, source_code, semantic_purpose,
                            user_scenarios, related_concepts, typical_errors,
                            embedding_text, embedding, file_hash, last_modified
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (file_path) DO UPDATE SET
                            relative_path = EXCLUDED.relative_path,
                            model_family = EXCLUDED.model_family,
                            package_code = EXCLUDED.package_code,
                            module_docstring = EXCLUDED.module_docstring,
                            source_code = EXCLUDED.source_code,
                            semantic_purpose = EXCLUDED.semantic_purpose,
                            user_scenarios = EXCLUDED.user_scenarios,
                            related_concepts = EXCLUDED.related_concepts,
                            typical_errors = EXCLUDED.typical_errors,
                            embedding_text = EXCLUDED.embedding_text,
                            embedding = EXCLUDED.embedding,
                            file_hash = EXCLUDED.file_hash,
                            last_modified = EXCLUDED.last_modified,
                            processed_at = NOW()
                    """
                    
                    # Read source code
                    source_code = Path(module_info.file_path).read_text(encoding='utf-8')
                    
                    cur.execute(sql, (
                        module_info.file_path,
                        module_info.relative_path,
                        module_info.model_family,
                        module_info.package_code,
                        module_info.module_docstring,
                        source_code,
                        semantic_analysis.semantic_purpose,
                        semantic_analysis.user_scenarios,
                        semantic_analysis.related_concepts,
                        semantic_analysis.typical_errors,
                        embedding_text,
                        embedding,
                        module_info.file_hash,
                        module_info.last_modified
                    ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            print(f"Database save failed for {module_info.relative_path}: {e}")
            return False
    
    def save_checkpoint(self, checkpoint: ProcessingCheckpoint):
        """Save processing checkpoint to disk"""
        checkpoint_file = self.checkpoints_dir / f"checkpoint_{checkpoint.model_family}_{checkpoint.batch_id}.json"
        
        # Convert dataclass to dict and handle datetime serialization
        checkpoint_data = asdict(checkpoint)
        checkpoint_data['timestamp'] = checkpoint.timestamp.isoformat()
        
        checkpoint_file.write_text(json.dumps(checkpoint_data, indent=2))
        print(f"Checkpoint saved: {checkpoint_file}")
    
    def load_checkpoint(self, model_family: str) -> Optional[ProcessingCheckpoint]:
        """Load the latest checkpoint for a model family"""
        checkpoints = list(self.checkpoints_dir.glob(f"checkpoint_{model_family}_*.json"))
        
        if not checkpoints:
            return None
        
        # Find latest checkpoint
        latest = max(checkpoints, key=lambda p: p.stat().st_mtime)
        
        try:
            data = json.loads(latest.read_text())
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            return ProcessingCheckpoint(**data)
        except Exception as e:
            print(f"Failed to load checkpoint {latest}: {e}")
            return None
    
    async def process_batch(self, 
                           batch: List[Tuple[Path, ModulePattern]], 
                           batch_id: int, 
                           model_family: str) -> Tuple[List[str], List[str]]:
        """Process a batch of files"""
        completed = []
        failed = []
        
        print(f"\nProcessing batch {batch_id} ({model_family}): {len(batch)} files")
        
        for file_path, pattern in batch:
            try:
                print(f"  Processing {file_path.relative_to(self.repo_path)}...")
                
                # Extract module info
                module_info = self.extract_module_info(file_path, pattern)
                
                # Semantic analysis with Gemini (or fallback if disabled)
                enable_gemini = getattr(self, 'enable_gemini', True)
                semantic_analysis = await self.analyze_with_gemini(module_info, enable_gemini=enable_gemini)
                
                # Create embedding
                embedding, embedding_text = await self.create_embedding(module_info, semantic_analysis)
                
                # Save to database
                if self.save_to_database(module_info, semantic_analysis, embedding, embedding_text):
                    completed.append(str(file_path))
                    print(f"    ✓ Saved {module_info.package_code or 'module'}")
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
    
    async def process_model_family(self, model_family: str, files: List[Tuple[Path, ModulePattern]]):
        """Process all files for a model family with checkpointing"""
        
        print(f"\n{'='*60}")
        print(f"Processing {model_family.upper()}: {len(files)} files")
        print(f"{'='*60}")
        
        # Load checkpoint if exists
        checkpoint = self.load_checkpoint(model_family)
        start_batch = 0
        total_processed = 0
        
        if checkpoint:
            print(f"Resuming from checkpoint: batch {checkpoint.batch_id}")
            start_batch = checkpoint.batch_id + 1
            total_processed = checkpoint.total_processed
            
            # Filter out already completed files
            completed_set = set(checkpoint.completed_files)
            files = [(f, p) for f, p in files if str(f) not in completed_set]
        
        # Process in batches
        for i in range(0, len(files), self.batch_size):
            batch_id = start_batch + (i // self.batch_size)
            batch = files[i:i + self.batch_size]
            
            completed, failed = await self.process_batch(batch, batch_id, model_family)
            total_processed += len(completed)
            
            # Save checkpoint
            checkpoint = ProcessingCheckpoint(
                batch_id=batch_id,
                completed_files=completed,
                failed_files=failed,
                timestamp=datetime.now(),
                total_processed=total_processed,
                model_family=model_family
            )
            self.save_checkpoint(checkpoint)
            
            print(f"Batch {batch_id} complete: {len(completed)} success, {len(failed)} failed")
            
            # Longer delay between batches
            await asyncio.sleep(2)
        
        print(f"\n{model_family.upper()} processing complete: {total_processed} modules processed")
    
    async def process_all(self):
        """Process all documented modules following documentation order"""
        
        print("🚀 Starting FloPy Semantic Database Processing")
        print("=" * 80)
        
        # Get processing queue
        queue = self.docs_parser.create_processing_queue()
        
        # Process in priority order (MF6 first, then others)
        priority_order = ['mf6', 'modflow', 'mt3d', 'seawat', 'modpath', 'utils', 'plot', 'export', 'pest', 'discretization']
        
        total_files = sum(len(files) for files in queue.values())
        print(f"Total modules to process: {total_files}")
        print()
        
        start_time = datetime.now()
        
        for family in priority_order:
            if family in queue:
                await self.process_model_family(family, queue[family])
        
        # Process any remaining families
        for family, files in queue.items():
            if family not in priority_order:
                await self.process_model_family(family, files)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "=" * 80)
        print("🎉 FloPy Semantic Database Processing Complete!")
        print(f"⏱️  Total time: {duration}")
        print(f"📊 Total modules: {total_files}")
        print("=" * 80)


async def main():
    """Main entry point"""
    
    # Configuration
    repo_path = "/home/danilopezmella/flopy_expert"
    neon_conn_string = "your_neon_connection_string_here"
    gemini_api_key = "your_gemini_api_key_here"
    openai_api_key = "your_openai_api_key_here"
    
    processor = FloPyProcessor(
        repo_path=repo_path,
        neon_conn_string=neon_conn_string,
        gemini_api_key=gemini_api_key,
        openai_api_key=openai_api_key,
        batch_size=10
    )
    
    await processor.process_all()


if __name__ == "__main__":
    # Test mode - just show what would be processed
    print("FloPy Processing Pipeline - Test Mode")
    print("This would process all 224 documented modules in batches of 10")
    print("With checkpoints, Gemini analysis, and OpenAI embeddings")
    print("\nTo run for real, set up API keys and database connection")
    
    # Show processing queue
    parser = FloPyDocsParser("/home/danilopezmella/flopy_expert")
    parser.print_processing_summary()