#!/usr/bin/env python3
"""
Generate Enhanced Analysis v00 for FloPy Workflows
Following the successful repository_files pattern - simple and effective
"""
import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import Json, RealDictCursor
import google.genai as genai
from openai import AsyncOpenAI
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
import config


class WorkflowAnalysisGenerator:
    """Generate simple, effective analysis for FloPy workflows"""
    
    def __init__(self):
        # Initialize connections
        self.neon_conn = config.NEON_CONNECTION_STRING
        
        # Initialize AI clients
        self.gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        
        # Processing settings
        self.batch_size = 5
        self.rate_limit_delay = 1.0
        self.max_retries = 3
        
    def fetch_workflows_for_processing(self, limit: int = 5) -> List[Dict]:
        """Fetch workflows that need analysis_v00"""
        with psycopg2.connect(self.neon_conn) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        id, tutorial_file, source_code
                    FROM flopy_workflows
                    WHERE analysis_v00 IS NULL
                        AND source_code IS NOT NULL
                    ORDER BY tutorial_file
                    LIMIT %s
                """, (limit,))
                return cur.fetchall()
    
    async def generate_analysis(self, workflow: Dict) -> Dict[str, Any]:
        """Generate simple analysis following repository_files pattern"""
        
        # Extract filename for context
        filename = workflow['tutorial_file'].split('/')[-1] if '/' in workflow['tutorial_file'] else workflow['tutorial_file']
        
        prompt = f"""
Analyze this FloPy workflow code as if you're a frustrated user trying to find this exact tutorial through search.

SOURCE CODE:
```python
{workflow['source_code']}
```

FILENAME: {filename}

Generate a JSON response optimized for semantic search:

{{
    "title": "Specific, technical title describing the exact problem solved (avoid generic terms like 'FloPy Tutorial')",
    
    "summary": "2-3 sentences MAX. First sentence: what specific groundwater modeling problem this solves. Second sentence: the key packages/methods used. Third sentence (optional): what makes this approach unique or when to use it.",
    
    "key_concepts": [
        "5-8 TECHNICAL concepts - focus on hydrogeological terms and MODFLOW-specific features",
        "Examples: 'transient stress periods', 'hydraulic conductivity tensor', 'ghost node correction'",
        "AVOID: generic programming terms like 'array', 'loop', 'function'"
    ],
    
    "potential_questions": [
        "Generate exactly 10 questions following this distribution:",
        "- 2 beginner questions: 'what is [concept] in MODFLOW'",
        "- 3 implementation questions: 'how to [specific task] in FloPy'", 
        "- 2 error/troubleshooting: '[package] error', '[method] not working'",
        "- 2 comparison/choice: '[package1] vs [package2]', 'when to use [method]'",
        "- 1 specific to this workflow's unique aspect",
        "Write as users actually type - lowercase, informal, sometimes incomplete"
    ],
    
    "keywords": [
        "10-15 SEARCH TERMS different from concepts",
        "Include: package codes (WEL, CHD), method names, file extensions, error keywords",
        "Think: what would autocomplete suggest? what's in the error message?"
    ]
}}

CRITICAL: Make questions sound like frustrated Stack Overflow searches, not textbook queries.
"""
        
        max_retries = self.max_retries
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self.gemini_client.models.generate_content,
                    model=config.GEMINI_MODEL,
                    contents=prompt
                )
                
                # Extract JSON from response
                text = response.text
                json_match = re.search(r'\{[\s\S]*\}', text)
                
                if json_match:
                    json_str = json_match.group(0)
                    analysis = json.loads(json_str)
                    
                    # Validate required fields
                    required_fields = ['title', 'summary', 'key_concepts', 'potential_questions', 'keywords']
                    for field in required_fields:
                        if field not in analysis or not analysis[field]:
                            raise ValueError(f"Missing required field: {field}")
                    
                    print(f"✓ Generated analysis for: {filename}")
                    return analysis
                    
                else:
                    raise ValueError("No JSON found in response")
                    
            except Exception as e:
                print(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise Exception("All retries exhausted - Gemini analysis failed")
    
    
    def format_embedding_string(self, workflow: Dict, analysis: Dict) -> str:
        """Create clean embedding string following repository_files pattern"""
        
        filename = workflow['tutorial_file'].split('/')[-1] if '/' in workflow['tutorial_file'] else workflow['tutorial_file']
        filepath = workflow['tutorial_file']
        
        embedding_string = f"""
            Filename: {filename}
            Filepath: {filepath}
            Repository: flopy
            
            Title: {analysis['title']}
            
            Summary: {analysis['summary']}
            
            Key Concepts: {', '.join(analysis['key_concepts'])}
            
            Potential Questions: {' | '.join(analysis['potential_questions'])}
            
            Keywords: {', '.join(analysis['keywords'])}
            """
        
        # Clean up extra whitespace while preserving structure
        lines = [line.strip() for line in embedding_string.strip().split('\n')]
        return '\n'.join(lines)
    
    async def create_embedding(self, text: str) -> List[float]:
        """Create OpenAI embedding from text"""
        try:
            response = await self.openai_client.embeddings.create(
                input=text,
                model=config.OPENAI_EMBEDDING_MODEL
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding creation failed: {e}")
            return [0.0] * 1536
    
    async def process_workflow(self, workflow: Dict) -> bool:
        """Process a single workflow"""
        try:
            filename = workflow['tutorial_file'].split('/')[-1]
            print(f"\nProcessing: {filename}")
            
            # Step 1: Generate analysis
            analysis = await self.generate_analysis(workflow)
            
            # Step 2: Create embedding string
            embedding_string = self.format_embedding_string(workflow, analysis)
            
            # Step 3: Create embedding vector
            embedding_vector = await self.create_embedding(embedding_string)
            
            # Step 4: Store in database
            with psycopg2.connect(self.neon_conn) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE flopy_workflows
                        SET 
                            analysis_v00 = %s,
                            analysis_generated_at = %s,
                            emb_string_00 = %s,
                            dspy_emb_00 = %s
                        WHERE id = %s
                    """, (
                        Json(analysis),
                        datetime.now(),
                        embedding_string,
                        embedding_vector,
                        workflow['id']
                    ))
                    conn.commit()
            
            print(f"✓ Success: {filename}")
            print(f"  - Questions: {len(analysis.get('potential_questions', []))}")
            print(f"  - Concepts: {len(analysis.get('key_concepts', []))}")
            print(f"  - Keywords: {len(analysis.get('keywords', []))}")
            
            return True
            
        except Exception as e:
            print(f"✗ Failed: {e}")
            return False
    
    async def run(self, limit: int = 5):
        """Main processing loop"""
        print("=" * 80)
        print("FloPy Workflows Analysis v00 Generator")
        print("Simple & Effective (Repository Files Pattern)")
        print("=" * 80)
        print(f"AI Models:")
        print(f"  Analysis: {config.GEMINI_MODEL}")
        print(f"  Embeddings: {config.OPENAI_EMBEDDING_MODEL}")
        print(f"  Max retries: {self.max_retries}")
        print(f"  Rate limit: {self.rate_limit_delay}s between calls")
        
        # Fetch workflows
        workflows = self.fetch_workflows_for_processing(limit)
        print(f"\nFound {len(workflows)} workflows to process")
        
        if not workflows:
            print("No workflows need processing.")
            return
        
        # Process workflows
        successful = 0
        failed = 0
        
        for i, workflow in enumerate(workflows, 1):
            print(f"\n[{i}/{len(workflows)}]", end="")
            
            success = await self.process_workflow(workflow)
            if success:
                successful += 1
            else:
                failed += 1
            
            # Rate limiting
            if i < len(workflows):
                await asyncio.sleep(self.rate_limit_delay)
        
        # Summary
        print("\n" + "=" * 80)
        print("Processing Complete!")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        print("=" * 80)
        
        # Show statistics
        self.show_statistics()
    
    def show_statistics(self):
        """Display processing statistics"""
        with psycopg2.connect(self.neon_conn) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get sample result
                cur.execute("""
                    SELECT 
                        tutorial_file,
                        analysis_v00->>'title' as title,
                        LENGTH(emb_string_00) as emb_length,
                        array_length(
                            string_to_array(
                                analysis_v00->>'potential_questions'::text, ','
                            ), 1
                        ) as num_questions
                    FROM flopy_workflows
                    WHERE analysis_v00 IS NOT NULL
                    LIMIT 1
                """)
                
                result = cur.fetchone()
                if result:
                    print("\nSample Result:")
                    print(f"  File: {result['tutorial_file']}")
                    print(f"  Title: {result['title']}")
                    print(f"  Embedding Length: {result['emb_length']} chars")
                
                # Overall statistics
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(analysis_v00) as with_analysis,
                        COUNT(emb_string_00) as with_embedding,
                        COUNT(dspy_emb_00) as with_vector
                    FROM flopy_workflows
                """)
                
                stats = cur.fetchone()
                print(f"\nDatabase Statistics:")
                print(f"  Total workflows: {stats['total']}")
                print(f"  With analysis_v00: {stats['with_analysis']}")
                print(f"  With emb_string_00: {stats['with_embedding']}")
                print(f"  With dspy_emb_00: {stats['with_vector']}")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate analysis for FloPy workflows')
    parser.add_argument('--limit', type=int, default=5, help='Number of workflows to process')
    parser.add_argument('--test', action='store_true', help='Test mode - process 1 workflow')
    
    args = parser.parse_args()
    
    if args.test:
        args.limit = 1
        print("🧪 TEST MODE - Processing 1 workflow")
    
    generator = WorkflowAnalysisGenerator()
    await generator.run(limit=args.limit)


if __name__ == "__main__":
    asyncio.run(main())