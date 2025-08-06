#!/usr/bin/env python3
"""
Workflow Processing Pipeline for FloPy Tutorials

Processes tutorial files to extract modeling workflows and patterns,
then stores them in a searchable database with semantic embeddings.
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
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from flopy_workflow_extractor import JupytextWorkflowExtractor, JupytextWorkflow


class WorkflowProcessor:
    """Process and store FloPy workflows with semantic analysis"""
    
    def __init__(self,
                 tutorials_path: str,
                 neon_conn_string: str,
                 gemini_api_key: str,
                 openai_api_key: str):
        self.tutorials_path = Path(tutorials_path)
        self.neon_conn = neon_conn_string
        
        # Initialize AI clients
        self.gemini_client = genai.Client(api_key=gemini_api_key)
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        
        # Initialize extractor
        self.extractor = JupytextWorkflowExtractor(tutorials_path)
        
        # Ensure database tables exist
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Create workflow tables if they don't exist"""
        
        table_schemas = [
            # Workflows table
            """
            CREATE TABLE IF NOT EXISTS flopy_workflows (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                tutorial_file TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                model_type TEXT,
                
                -- Workflow structure
                packages_used TEXT[],
                num_steps INTEGER,
                complexity TEXT,
                tags TEXT[],
                
                -- AI-generated analysis
                workflow_purpose TEXT,
                best_use_cases TEXT[],
                prerequisites TEXT[],
                common_modifications TEXT[],
                
                -- Search capabilities
                embedding_text TEXT NOT NULL,
                embedding vector(1536) NOT NULL,
                search_vector tsvector,
                
                -- Metadata
                file_hash TEXT NOT NULL,
                total_lines INTEGER,
                extracted_at TIMESTAMP,
                processed_at TIMESTAMP DEFAULT NOW()
            );
            """,
            
            # Workflow steps table
            """
            CREATE TABLE IF NOT EXISTS flopy_workflow_steps (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                workflow_id UUID REFERENCES flopy_workflows(id) ON DELETE CASCADE,
                step_number INTEGER NOT NULL,
                description TEXT NOT NULL,
                code_snippet TEXT,
                
                -- Extracted elements
                imports TEXT[],
                flopy_classes TEXT[],
                key_functions TEXT[],
                parameters JSONB,
                
                -- AI analysis
                step_explanation TEXT,
                
                created_at TIMESTAMP DEFAULT NOW()
            );
            """,
            
            # Workflow relationships table (for finding similar workflows)
            """
            CREATE TABLE IF NOT EXISTS flopy_workflow_relationships (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                source_workflow_id UUID REFERENCES flopy_workflows(id),
                target_workflow_id UUID REFERENCES flopy_workflows(id),
                relationship_type TEXT, -- 'similar', 'extends', 'simplifies'
                similarity_score FLOAT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """
        ]
        
        # Index creation
        index_schemas = [
            "CREATE INDEX IF NOT EXISTS idx_flopy_workflows_model_type ON flopy_workflows(model_type);",
            "CREATE INDEX IF NOT EXISTS idx_flopy_workflows_complexity ON flopy_workflows(complexity);",
            "CREATE INDEX IF NOT EXISTS idx_flopy_workflows_tags ON flopy_workflows USING gin(tags);",
            "CREATE INDEX IF NOT EXISTS idx_flopy_workflows_packages ON flopy_workflows USING gin(packages_used);",
            "CREATE INDEX IF NOT EXISTS idx_flopy_workflows_embedding ON flopy_workflows USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);",
            "CREATE INDEX IF NOT EXISTS idx_flopy_workflows_search_vector ON flopy_workflows USING gin(search_vector);",
            "CREATE INDEX IF NOT EXISTS idx_flopy_workflow_steps_workflow ON flopy_workflow_steps(workflow_id);",
        ]
        
        # Trigger to update search vector
        trigger_sql = """
            CREATE OR REPLACE FUNCTION update_workflow_search_vector() RETURNS trigger AS $$
            BEGIN
                NEW.search_vector := to_tsvector('english',
                    COALESCE(NEW.title, '') || ' ' ||
                    COALESCE(NEW.description, '') || ' ' ||
                    COALESCE(NEW.workflow_purpose, '') || ' ' ||
                    COALESCE(array_to_string(NEW.tags, ' '), '')
                );
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            
            DROP TRIGGER IF EXISTS workflow_search_vector_update ON flopy_workflows;
            
            CREATE TRIGGER workflow_search_vector_update
            BEFORE INSERT OR UPDATE ON flopy_workflows
            FOR EACH ROW EXECUTE FUNCTION update_workflow_search_vector();
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
                    print("✅ Workflow database tables and indexes ready")
                    
        except Exception as e:
            print(f"❌ Error creating workflow tables: {e}")
            raise
    
    async def analyze_workflow_with_gemini(self, workflow: JupytextWorkflow) -> Dict[str, Any]:
        """Analyze workflow pattern with Gemini for deeper understanding with retry logic"""
        
        prompt = f"""
Analyze this FloPy modeling workflow tutorial:

Title: {workflow.title}
Description: {workflow.description}
Model Type: {workflow.model_type}
Packages Used: {', '.join(workflow.packages_used)}
Number of Sections: {len(workflow.sections)}
Tags: {', '.join(workflow.tags)}

Workflow Sections:
{self._format_workflow_sections(workflow.sections[:5])}  # First 5 sections

Provide a comprehensive analysis in markdown format:

## Workflow Purpose
What is the main modeling objective this workflow accomplishes? Be specific about the hydrogeological problem being solved.

## Best Use Cases
List 3-4 specific scenarios where this workflow pattern would be most applicable:
- Use case 1
- Use case 2
- Use case 3

## Prerequisites
What knowledge or data does a user need before using this workflow:
- Prerequisite 1
- Prerequisite 2
- Prerequisite 3

## Common Modifications
How might users typically modify this workflow for their needs:
- Modification 1
- Modification 2
- Modification 3

Focus on practical applications and real-world usage patterns.
"""
        
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self.gemini_client.models.generate_content,
                    model="gemini-2.5-pro",  # Use the pro model from config
                    contents=prompt
                )
                
                # Parse markdown response
                text = response.text
                
                # Extract sections
                import re
                
                purpose_match = re.search(r'## Workflow Purpose\s*\n(.+?)(?=\n## |$)', text, re.DOTALL)
                purpose = purpose_match.group(1).strip() if purpose_match else ""
                
                use_cases = self._extract_list_items(text, "Best Use Cases")
                prerequisites = self._extract_list_items(text, "Prerequisites")
                modifications = self._extract_list_items(text, "Common Modifications")
                
                # Validate that we got meaningful content
                if not purpose or len(purpose) < 50:
                    raise ValueError(f"AI analysis returned minimal purpose ({len(purpose)} chars)")
                
                # Be more lenient with lists - even 1 use case is better than fallback
                if not use_cases:
                    raise ValueError("AI analysis returned no use cases")
                
                return {
                    'workflow_purpose': purpose,
                    'best_use_cases': use_cases,
                    'prerequisites': prerequisites,
                    'common_modifications': modifications
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
        """Format workflow sections for prompt"""
        formatted = []
        for i, section in enumerate(sections, 1):
            formatted.append(f"{i}. {section.title}")
            if section.description:
                formatted.append(f"   Description: {section.description[:100]}...")
            if section.packages_used:
                formatted.append(f"   Packages: {', '.join(section.packages_used[:3])}")
            if section.key_functions:
                formatted.append(f"   Functions: {', '.join(section.key_functions[:3])}")
        return '\n'.join(formatted)
    
    def _extract_list_items(self, text: str, section: str) -> List[str]:
        """Extract list items from a markdown section"""
        import re
        section_match = re.search(rf'## {section}\s*\n(.+?)(?=\n## |$)', text, re.DOTALL)
        items = []
        if section_match:
            section_text = section_match.group(1)
            lines = section_text.split('\n')
            for line in lines:
                # Match both "- item" and "1. item" list formats
                if line.strip().startswith('-'):
                    item = line.strip()[1:].strip()
                    if item:
                        items.append(item)
                elif re.match(r'^\d+\.\s+', line.strip()):
                    item = re.sub(r'^\d+\.\s+', '', line.strip())
                    if item:
                        items.append(item)
        return items[:10]  # Limit to 10 items
    
    def _create_fallback_analysis(self, workflow: JupytextWorkflow) -> Dict[str, Any]:
        """Create fallback analysis when AI is unavailable"""
        purpose = f"Demonstrates {workflow.model_type.upper()} modeling with {', '.join(workflow.packages_used[:3])} packages"
        
        use_cases = [
            f"{workflow.model_type.upper()} model setup and configuration",
            f"Learning {'steady-state' if 'steady-state' in workflow.tags else 'transient'} flow modeling",
            "Educational example for FloPy usage"
        ]
        
        return {
            'workflow_purpose': purpose,
            'best_use_cases': use_cases,
            'prerequisites': ["Basic FloPy knowledge", "Understanding of MODFLOW concepts"],
            'common_modifications': ["Adjust grid resolution", "Change boundary conditions", "Modify parameters"]
        }
    
    async def create_workflow_embedding(self, workflow: JupytextWorkflow, analysis: Dict[str, Any]) -> tuple[List[float], str]:
        """Create embedding for workflow searchability"""
        
        # Combine text for embedding
        text_parts = [
            workflow.title,
            workflow.description,
            workflow.model_type,
            ' '.join(workflow.packages_used),
            ' '.join(workflow.tags),
            analysis['workflow_purpose'],
            ' '.join(analysis['best_use_cases']),
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
    
    async def process_workflow(self, workflow: JupytextWorkflow) -> bool:
        """Process a single workflow and store in database"""
        
        try:
            # Check if already processed
            with psycopg2.connect(self.neon_conn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, file_hash FROM flopy_workflows WHERE tutorial_file = %s",
                        (workflow.tutorial_file,)
                    )
                    existing = cur.fetchone()
                    
                    if existing and existing[1] == workflow.file_hash:
                        print(f"Skipping {workflow.tutorial_file} - unchanged")
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
                        INSERT INTO flopy_workflows (
                            tutorial_file, title, description, model_type,
                            packages_used, num_steps, complexity, tags,
                            workflow_purpose, best_use_cases, prerequisites, common_modifications,
                            embedding_text, embedding, file_hash, total_lines, extracted_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (tutorial_file) DO UPDATE SET
                            title = EXCLUDED.title,
                            description = EXCLUDED.description,
                            model_type = EXCLUDED.model_type,
                            packages_used = EXCLUDED.packages_used,
                            num_steps = EXCLUDED.num_steps,
                            complexity = EXCLUDED.complexity,
                            tags = EXCLUDED.tags,
                            workflow_purpose = EXCLUDED.workflow_purpose,
                            best_use_cases = EXCLUDED.best_use_cases,
                            prerequisites = EXCLUDED.prerequisites,
                            common_modifications = EXCLUDED.common_modifications,
                            embedding_text = EXCLUDED.embedding_text,
                            embedding = EXCLUDED.embedding,
                            file_hash = EXCLUDED.file_hash,
                            total_lines = EXCLUDED.total_lines,
                            extracted_at = EXCLUDED.extracted_at,
                            processed_at = NOW()
                        RETURNING id
                    """
                    
                    cur.execute(workflow_sql, (
                        workflow.tutorial_file,
                        workflow.title,
                        workflow.description,
                        workflow.model_type,
                        workflow.packages_used,
                        len(workflow.sections),
                        workflow.complexity,
                        workflow.tags,
                        analysis['workflow_purpose'],
                        analysis['best_use_cases'],
                        analysis['prerequisites'],
                        analysis['common_modifications'],
                        embedding_text,
                        embedding,
                        workflow.file_hash,
                        workflow.total_lines,
                        workflow.extracted_at
                    ))
                    
                    workflow_id = cur.fetchone()[0]
                    
                    # Delete existing steps
                    cur.execute("DELETE FROM flopy_workflow_steps WHERE workflow_id = %s", (workflow_id,))
                    
                    # Insert workflow sections as steps
                    for i, section in enumerate(workflow.sections, 1):
                        # Combine code snippets into one
                        code_snippet = '\n\n'.join(section.code_snippets[:3]) if section.code_snippets else ''
                        
                        # Get imports from cells
                        imports = []
                        for cell in section.cells:
                            if cell.cell_type == 'code':
                                for line in cell.content.splitlines():
                                    if line.strip().startswith(('import ', 'from ')):
                                        imports.append(line.strip())
                        
                        step_sql = """
                            INSERT INTO flopy_workflow_steps (
                                workflow_id, step_number, description, code_snippet,
                                imports, flopy_classes, key_functions, parameters
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        cur.execute(step_sql, (
                            workflow_id,
                            i,
                            section.title,
                            code_snippet,
                            imports[:10],  # Limit imports
                            section.packages_used,
                            section.key_functions[:20],  # Limit functions
                            Json({})  # No parameters in sections
                        ))
                    
                    conn.commit()
                    print(f"✓ Saved workflow: {workflow.title}")
                    return True
                    
        except Exception as e:
            print(f"Failed to process {workflow.tutorial_file}: {e}")
            return False
    
    async def process_all_workflows(self):
        """Process all tutorial workflows"""
        
        print("🚀 Starting FloPy Workflow Extraction")
        print("=" * 60)
        
        # Extract all workflows
        workflows = self.extractor.extract_all_workflows()
        print(f"\nExtracted {len(workflows)} workflows")
        
        # Process each workflow
        successful = 0
        for i, workflow in enumerate(workflows):
            print(f"\nProcessing {i+1}/{len(workflows)}: {workflow.title}")
            if await self.process_workflow(workflow):
                successful += 1
            
            # Small delay to respect rate limits
            await asyncio.sleep(1)
        
        print(f"\n✅ Workflow processing complete: {successful}/{len(workflows)} successful")
        
        # Find similar workflows
        print("\n🔍 Finding similar workflows...")
        await self.find_similar_workflows()
    
    async def find_similar_workflows(self, threshold: float = 0.8):
        """Find and store relationships between similar workflows"""
        
        try:
            with psycopg2.connect(self.neon_conn) as conn:
                with conn.cursor() as cur:
                    # Get all workflow embeddings
                    cur.execute("""
                        SELECT id, title, embedding 
                        FROM flopy_workflows
                    """)
                    
                    workflows = cur.fetchall()
                    
                    # Compare each pair
                    relationships = []
                    for i, (id1, title1, emb1) in enumerate(workflows):
                        for j, (id2, title2, emb2) in enumerate(workflows[i+1:], i+1):
                            # Calculate cosine similarity using SQL
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
                            INSERT INTO flopy_workflow_relationships 
                            (source_workflow_id, target_workflow_id, relationship_type, similarity_score)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (rel['source'], rel['target'], rel['type'], rel['score']))
                    
                    conn.commit()
                    print(f"✓ Found {len(relationships)} similar workflow pairs")
                    
        except Exception as e:
            print(f"Error finding similar workflows: {e}")


async def main():
    """Run workflow processing"""
    import sys
    sys.path.append('/home/danilopezmella/flopy_expert')
    import config
    
    processor = WorkflowProcessor(
        tutorials_path="/home/danilopezmella/flopy_expert/flopy/.docs/Notebooks",
        neon_conn_string=config.NEON_CONNECTION_STRING,
        gemini_api_key=config.GEMINI_API_KEY,
        openai_api_key=config.OPENAI_API_KEY
    )
    
    await processor.process_all_workflows()


if __name__ == "__main__":
    asyncio.run(main())