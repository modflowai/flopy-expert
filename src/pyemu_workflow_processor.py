#!/usr/bin/env python3
"""
PyEmu Workflow Processing Pipeline

Processes PyEmu example notebooks to extract uncertainty analysis patterns
and stores them in a searchable database.
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import Json
import google.genai as genai
from openai import AsyncOpenAI

import sys
sys.path.append(str(Path(__file__).parent))
from pyemu_workflow_extractor import PyEmuWorkflowExtractor, PyEmuWorkflow


class PyEmuWorkflowProcessor:
    """Process and store PyEmu uncertainty analysis workflows"""
    
    def __init__(self,
                 examples_path: str,
                 neon_conn_string: str,
                 gemini_api_key: str,
                 openai_api_key: str):
        self.examples_path = Path(examples_path)
        self.neon_conn = neon_conn_string
        
        # Initialize AI clients
        self.gemini_client = genai.Client(api_key=gemini_api_key)
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        
        # Initialize extractor
        self.extractor = PyEmuWorkflowExtractor(examples_path)
        
        # Ensure database tables exist
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Create PyEmu workflow tables if they don't exist"""
        
        table_schemas = [
            # PyEmu workflows table
            """
            CREATE TABLE IF NOT EXISTS pyemu_workflows (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                notebook_file TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                workflow_type TEXT,
                
                -- PyEmu-specific fields
                pest_concepts TEXT[],
                uncertainty_methods TEXT[],
                pyemu_modules TEXT[],
                prerequisites TEXT[],
                
                -- Workflow metadata
                num_sections INTEGER,
                total_cells INTEGER,
                code_cells INTEGER,
                complexity TEXT,
                tags TEXT[],
                
                -- AI-generated analysis
                workflow_purpose TEXT,
                best_practices TEXT[],
                common_applications TEXT[],
                implementation_tips TEXT[],
                
                -- Search capabilities
                embedding_text TEXT NOT NULL,
                embedding vector(1536) NOT NULL,
                search_vector tsvector,
                
                -- File tracking
                file_hash TEXT NOT NULL,
                extracted_at TIMESTAMP,
                processed_at TIMESTAMP DEFAULT NOW()
            );
            """,
            
            # PyEmu workflow sections table
            """
            CREATE TABLE IF NOT EXISTS pyemu_workflow_sections (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                workflow_id UUID REFERENCES pyemu_workflows(id) ON DELETE CASCADE,
                section_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                
                -- Section content
                pest_concepts TEXT[],
                uncertainty_methods TEXT[],
                pyemu_classes TEXT[],
                key_functions TEXT[],
                code_snippets TEXT[],
                
                -- AI analysis
                section_explanation TEXT,
                
                created_at TIMESTAMP DEFAULT NOW()
            );
            """,
            
            # PyEmu workflow relationships
            """
            CREATE TABLE IF NOT EXISTS pyemu_workflow_relationships (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                source_workflow_id UUID REFERENCES pyemu_workflows(id),
                target_workflow_id UUID REFERENCES pyemu_workflows(id),
                relationship_type TEXT,
                similarity_score FLOAT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """
        ]
        
        # Index creation
        index_schemas = [
            "CREATE INDEX IF NOT EXISTS idx_pyemu_workflows_type ON pyemu_workflows(workflow_type);",
            "CREATE INDEX IF NOT EXISTS idx_pyemu_workflows_complexity ON pyemu_workflows(complexity);",
            "CREATE INDEX IF NOT EXISTS idx_pyemu_workflows_tags ON pyemu_workflows USING gin(tags);",
            "CREATE INDEX IF NOT EXISTS idx_pyemu_workflows_methods ON pyemu_workflows USING gin(uncertainty_methods);",
            "CREATE INDEX IF NOT EXISTS idx_pyemu_workflows_embedding ON pyemu_workflows USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);",
            "CREATE INDEX IF NOT EXISTS idx_pyemu_workflows_search ON pyemu_workflows USING gin(search_vector);"
        ]
        
        # Search vector trigger
        trigger_sql = """
            CREATE OR REPLACE FUNCTION update_pyemu_workflow_search_vector() RETURNS trigger AS $$
            BEGIN
                NEW.search_vector := to_tsvector('english',
                    COALESCE(NEW.title, '') || ' ' ||
                    COALESCE(NEW.description, '') || ' ' ||
                    COALESCE(NEW.workflow_purpose, '') || ' ' ||
                    COALESCE(array_to_string(NEW.tags, ' '), '') || ' ' ||
                    COALESCE(array_to_string(NEW.uncertainty_methods, ' '), '')
                );
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            
            DROP TRIGGER IF EXISTS pyemu_workflow_search_update ON pyemu_workflows;
            
            CREATE TRIGGER pyemu_workflow_search_update
            BEFORE INSERT OR UPDATE ON pyemu_workflows
            FOR EACH ROW EXECUTE FUNCTION update_pyemu_workflow_search_vector();
        """
        
        try:
            with psycopg2.connect(self.neon_conn) as conn:
                with conn.cursor() as cur:
                    # Create tables
                    for schema in table_schemas:
                        cur.execute(schema)
                    
                    # Create indexes
                    for index in index_schemas:
                        cur.execute(index)
                    
                    # Create trigger
                    cur.execute(trigger_sql)
                    
                    conn.commit()
                    print("✅ PyEmu workflow database tables ready")
                    
        except Exception as e:
            print(f"❌ Error creating PyEmu workflow tables: {e}")
            raise
    
    async def analyze_workflow_with_gemini(self, workflow: PyEmuWorkflow) -> Dict[str, Any]:
        """Analyze PyEmu workflow for uncertainty analysis patterns with retry logic"""
        
        prompt = f"""
Analyze this PyEmu uncertainty analysis workflow:

Title: {workflow.title}
Type: {workflow.workflow_type}
PEST Concepts: {', '.join(workflow.pest_concepts)}
Uncertainty Methods: {', '.join(workflow.uncertainty_methods)}
PyEmu Modules: {', '.join(workflow.pyemu_modules)}
Prerequisites: {', '.join(workflow.prerequisites)}

Sections:
{self._format_workflow_sections(workflow.sections[:5])}

Provide analysis focused on uncertainty quantification and PEST:

## Workflow Purpose
What uncertainty analysis objective does this workflow accomplish? Be specific about the statistical methods and PEST integration.

## Best Practices
List 3-4 best practices demonstrated in this workflow:
- Practice 1
- Practice 2  
- Practice 3

## Common Applications
When would you use this workflow pattern:
- Application 1
- Application 2
- Application 3

## Implementation Tips
Key tips for implementing this uncertainty analysis:
- Tip 1
- Tip 2
- Tip 3

Focus on practical uncertainty quantification and parameter estimation applications.
"""
        
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self.gemini_client.models.generate_content,
                    model="gemini-2.5-pro",  # Use the pro model for better quality
                    contents=prompt
                )
                
                # Parse response
                text = response.text
                
                # Extract sections
                import re
                
                purpose_match = re.search(r'## Workflow Purpose\s*\n(.+?)(?=\n## |$)', text, re.DOTALL)
                purpose = purpose_match.group(1).strip() if purpose_match else ""
                
                practices = self._extract_list_items(text, "Best Practices")
                applications = self._extract_list_items(text, "Common Applications")
                tips = self._extract_list_items(text, "Implementation Tips")
                
                # Log what we got for debugging
                print(f"  Purpose length: {len(purpose) if purpose else 0}")
                print(f"  Best practices count: {len(practices)}")
                print(f"  First 100 chars of purpose: {purpose[:100] if purpose else 'EMPTY'}")
                
                # Validate that we got meaningful content
                if not purpose or len(purpose) < 50:
                    raise ValueError(f"AI analysis returned empty or minimal content (purpose: {len(purpose) if purpose else 0} chars)")
                
                # For practices, be more lenient - even 1 good practice is better than fallback
                if not practices:
                    raise ValueError(f"AI analysis returned no best practices")
                
                print(f"  ✓ Analysis successful!")
                
                return {
                    'workflow_purpose': purpose,
                    'best_practices': practices,
                    'common_applications': applications,
                    'implementation_tips': tips
                }
                
            except Exception as e:
                print(f"Gemini analysis attempt {attempt + 1}/{max_retries} failed for {workflow.title}: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print(f"All retries exhausted. Using fallback analysis.")
                    return self._create_fallback_analysis(workflow)
    
    def _format_workflow_sections(self, sections) -> str:
        """Format sections for prompt"""
        formatted = []
        for i, section in enumerate(sections, 1):
            formatted.append(f"{i}. {section.title}")
            if section.description:
                formatted.append(f"   Description: {section.description[:100]}...")
            if section.uncertainty_methods:
                formatted.append(f"   Methods: {', '.join(section.uncertainty_methods[:3])}")
            if section.pest_concepts:
                formatted.append(f"   PEST: {', '.join(section.pest_concepts[:3])}")
        return '\n'.join(formatted)
    
    def _extract_list_items(self, text: str, section: str) -> List[str]:
        """Extract bullet points from markdown section"""
        import re
        section_match = re.search(rf'## {section}\s*\n(.+?)(?=\n## |$)', text, re.DOTALL)
        items = []
        if section_match:
            section_text = section_match.group(1)
            # Debug: print what we found
            if len(items) == 0 and "Best Practices" in section:
                print(f"\n  DEBUG: Found section text for {section}:")
                print(f"  {section_text[:200]}...")
            
            lines = section_text.split('\n')
            for line in lines:
                # Try different bullet formats
                line_stripped = line.strip()
                if line_stripped.startswith('-'):
                    item = line_stripped[1:].strip()
                    if item:
                        items.append(item)
                elif line_stripped.startswith('*'):
                    item = line_stripped[1:].strip()
                    if item:
                        items.append(item)
                elif line_stripped.startswith('•'):
                    item = line_stripped[1:].strip()
                    if item:
                        items.append(item)
                # Also try numbered lists
                elif re.match(r'^\d+\.\s+', line_stripped):
                    item = re.sub(r'^\d+\.\s+', '', line_stripped)
                    if item:
                        items.append(item)
        else:
            if "Best Practices" in section:
                print(f"\n  DEBUG: No section match found for '{section}'")
                print(f"  First 300 chars of full text: {text[:300]}...")
        
        return items[:10]
    
    def _create_fallback_analysis(self, workflow: PyEmuWorkflow) -> Dict[str, Any]:
        """Create fallback analysis when AI unavailable"""
        purpose = f"Demonstrates {workflow.workflow_type} using {', '.join(workflow.uncertainty_methods[:3])}"
        
        practices = [
            f"Using {workflow.workflow_type} for uncertainty analysis",
            "PEST integration patterns",
            "Proper uncertainty quantification workflow"
        ]
        
        return {
            'workflow_purpose': purpose,
            'best_practices': practices,
            'common_applications': ["Uncertainty analysis", "Parameter estimation", "Model calibration"],
            'implementation_tips': ["Follow PyEmu conventions", "Check PEST file setup", "Validate results"]
        }
    
    async def create_workflow_embedding(self, workflow: PyEmuWorkflow, analysis: Dict[str, Any]) -> tuple[List[float], str]:
        """Create embedding for PyEmu workflow searchability"""
        
        # Combine text for embedding
        text_parts = [
            workflow.title,
            workflow.description,
            workflow.workflow_type,
            ' '.join(workflow.pest_concepts),
            ' '.join(workflow.uncertainty_methods),
            ' '.join(workflow.pyemu_modules),
            ' '.join(workflow.tags),
            analysis['workflow_purpose'],
            ' '.join(analysis['best_practices']),
        ]
        
        combined_text = ' '.join(filter(None, text_parts))
        
        try:
            response = await self.openai_client.embeddings.create(
                input=combined_text,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding, combined_text
            
        except Exception as e:
            print(f"Embedding creation failed for {workflow.title}: {e}")
            return [0.0] * 1536, combined_text
    
    async def process_workflow(self, workflow: PyEmuWorkflow) -> bool:
        """Process a single PyEmu workflow"""
        
        try:
            # Check if already processed
            with psycopg2.connect(self.neon_conn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, file_hash FROM pyemu_workflows WHERE notebook_file = %s",
                        (workflow.notebook_file,)
                    )
                    existing = cur.fetchone()
                    
                    if existing and existing[1] == workflow.file_hash:
                        print(f"Skipping {workflow.notebook_file} - unchanged")
                        return True
            
            # Analyze with Gemini
            analysis = await self.analyze_workflow_with_gemini(workflow)
            
            # Create embedding
            embedding, embedding_text = await self.create_workflow_embedding(workflow, analysis)
            
            # Store in database
            with psycopg2.connect(self.neon_conn) as conn:
                with conn.cursor() as cur:
                    # Insert or update workflow
                    workflow_sql = """
                        INSERT INTO pyemu_workflows (
                            notebook_file, title, description, workflow_type,
                            pest_concepts, uncertainty_methods, pyemu_modules, prerequisites,
                            num_sections, total_cells, code_cells, complexity, tags,
                            workflow_purpose, best_practices, common_applications, implementation_tips,
                            embedding_text, embedding, file_hash, extracted_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (notebook_file) DO UPDATE SET
                            title = EXCLUDED.title,
                            description = EXCLUDED.description,
                            workflow_type = EXCLUDED.workflow_type,
                            pest_concepts = EXCLUDED.pest_concepts,
                            uncertainty_methods = EXCLUDED.uncertainty_methods,
                            pyemu_modules = EXCLUDED.pyemu_modules,
                            prerequisites = EXCLUDED.prerequisites,
                            num_sections = EXCLUDED.num_sections,
                            total_cells = EXCLUDED.total_cells,
                            code_cells = EXCLUDED.code_cells,
                            complexity = EXCLUDED.complexity,
                            tags = EXCLUDED.tags,
                            workflow_purpose = EXCLUDED.workflow_purpose,
                            best_practices = EXCLUDED.best_practices,
                            common_applications = EXCLUDED.common_applications,
                            implementation_tips = EXCLUDED.implementation_tips,
                            embedding_text = EXCLUDED.embedding_text,
                            embedding = EXCLUDED.embedding,
                            file_hash = EXCLUDED.file_hash,
                            extracted_at = EXCLUDED.extracted_at,
                            processed_at = NOW()
                        RETURNING id
                    """
                    
                    cur.execute(workflow_sql, (
                        workflow.notebook_file,
                        workflow.title,
                        workflow.description,
                        workflow.workflow_type,
                        workflow.pest_concepts,
                        workflow.uncertainty_methods,
                        workflow.pyemu_modules,
                        workflow.prerequisites,
                        len(workflow.sections),
                        workflow.total_cells,
                        workflow.code_cells,
                        workflow.complexity,
                        workflow.tags,
                        analysis['workflow_purpose'],
                        analysis['best_practices'],
                        analysis['common_applications'],
                        analysis['implementation_tips'],
                        embedding_text,
                        embedding,
                        workflow.file_hash,
                        workflow.extracted_at
                    ))
                    
                    workflow_id = cur.fetchone()[0]
                    
                    # Delete existing sections
                    cur.execute("DELETE FROM pyemu_workflow_sections WHERE workflow_id = %s", (workflow_id,))
                    
                    # Insert sections
                    for i, section in enumerate(workflow.sections, 1):
                        section_sql = """
                            INSERT INTO pyemu_workflow_sections (
                                workflow_id, section_number, title, description,
                                pest_concepts, uncertainty_methods, pyemu_classes,
                                key_functions, code_snippets
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        cur.execute(section_sql, (
                            workflow_id,
                            i,
                            section.title,
                            section.description,
                            section.pest_concepts[:10],
                            section.uncertainty_methods[:10],
                            section.pyemu_classes[:10],
                            section.key_functions[:20],
                            section.code_snippets[:3]
                        ))
                    
                    conn.commit()
                    print(f"✓ Saved PyEmu workflow: {workflow.title}")
                    return True
                    
        except Exception as e:
            print(f"Failed to process {workflow.notebook_file}: {e}")
            return False
    
    async def process_all_workflows(self):
        """Process all PyEmu example workflows"""
        
        print("🚀 Starting PyEmu Workflow Extraction")
        print("=" * 60)
        
        # Extract all workflows
        workflows = self.extractor.extract_all_workflows()
        print(f"\nExtracted {len(workflows)} PyEmu workflows")
        
        # Process each workflow
        successful = 0
        for i, workflow in enumerate(workflows):
            print(f"\nProcessing {i+1}/{len(workflows)}: {workflow.title}")
            if await self.process_workflow(workflow):
                successful += 1
            
            # Small delay to respect rate limits
            await asyncio.sleep(1)
        
        print(f"\n✅ PyEmu workflow processing complete: {successful}/{len(workflows)} successful")
        
        # Find similar workflows
        print("\n🔍 Finding similar PyEmu workflows...")
        await self.find_similar_workflows()
    
    async def find_similar_workflows(self, threshold: float = 0.75):
        """Find relationships between similar PyEmu workflows"""
        
        try:
            with psycopg2.connect(self.neon_conn) as conn:
                with conn.cursor() as cur:
                    # Get all workflow embeddings
                    cur.execute("""
                        SELECT id, title, embedding 
                        FROM pyemu_workflows
                    """)
                    
                    workflows = cur.fetchall()
                    
                    # Compare each pair
                    relationships = []
                    for i, (id1, title1, emb1) in enumerate(workflows):
                        for j, (id2, title2, emb2) in enumerate(workflows[i+1:], i+1):
                            # Calculate cosine similarity
                            cur.execute("""
                                SELECT 1 - (%s::vector <=> %s::vector) as similarity
                            """, (emb1, emb2))
                            similarity = cur.fetchone()[0]
                            
                            if similarity >= threshold:
                                relationships.append({
                                    'source': id1,
                                    'target': id2,
                                    'type': 'similar',
                                    'score': similarity
                                })
                    
                    # Store relationships
                    for rel in relationships:
                        cur.execute("""
                            INSERT INTO pyemu_workflow_relationships 
                            (source_workflow_id, target_workflow_id, relationship_type, similarity_score)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (rel['source'], rel['target'], rel['type'], rel['score']))
                    
                    conn.commit()
                    print(f"✓ Found {len(relationships)} similar PyEmu workflow pairs")
                    
        except Exception as e:
            print(f"Error finding similar workflows: {e}")


# Main execution
if __name__ == "__main__":
    import asyncio
    import sys
    sys.path.append('/home/danilopezmella/flopy_expert')
    import config
    
    processor = PyEmuWorkflowProcessor(
        examples_path="/home/danilopezmella/flopy_expert/pyemu/examples",
        neon_conn_string=config.NEON_CONNECTION_STRING,
        gemini_api_key=config.GEMINI_API_KEY,
        openai_api_key=config.OPENAI_API_KEY
    )
    
    asyncio.run(processor.process_all_workflows())