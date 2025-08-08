#!/usr/bin/env python3
"""
FloPy Workflows Analysis v02 Generator
Ultra-Discriminative Prompt Version

Uses Perplexity Pro recommendations to create highly discriminative embeddings
that prevent confusion between similar workflows (MT3D vs MF6, SEAWAT, etc.)
"""

import asyncio
import json
import re
import time
from pathlib import Path
import sys
from typing import Dict, List, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import google.genai as genai
from openai import AsyncOpenAI

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
import config

class WorkflowAnalysisGenerator:
    def __init__(self):
        # Initialize AI clients (same as v00)
        self.gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        
        self.neon_conn = config.NEON_CONNECTION_STRING
        self.max_retries = 3
        
    def fetch_workflows_for_v02(self, limit: int = 100, source_repo: str = 'flopy') -> List[Dict]:
        """Fetch workflows that need analysis_v02"""
        with psycopg2.connect(self.neon_conn) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        id, tutorial_file, source_code
                    FROM flopy_workflows
                    WHERE analysis_v02 IS NULL
                        AND source_code IS NOT NULL
                        AND source_repository = %s
                    ORDER BY tutorial_file
                    LIMIT %s
                """, (source_repo, limit))
                return cur.fetchall()
    
    async def generate_analysis(self, workflow: Dict, source_repo: str = 'flopy') -> Dict[str, Any]:
        """Generate ultra-discriminative analysis"""
        
        # Extract filename for context
        filename = workflow['tutorial_file'].split('/')[-1] if '/' in workflow['tutorial_file'] else workflow['tutorial_file']
        
        # Adapt prompt based on source repository
        if source_repo == 'modflow6-examples':
            prompt = f"""
Analyze this MODFLOW 6 example code to create highly specific embeddings that distinguish it from other groundwater modeling examples.

SOURCE CODE:
```python
{workflow['source_code']}
```

FILENAME: {filename}

Please generate a JSON response with detailed differentiation:

{{
    "title": "A very specific title that someone would use only for this exact type of MODFLOW 6 example (avoid generic terms)",
    
    "model_type_and_physics": "Please specify clearly: Is this GROUNDWATER FLOW (GWF), TRANSPORT (GWT), ENERGY (GWE), PARTICLE (PRT), or COUPLED? What governing equations and physical processes are involved?",
    
    "boundary_packages_detailed": "List each MODFLOW 6 package used with: (1) Package code (WEL/CHD/DRN/etc), (2) Physical meaning (pumping well/constant head/etc), (3) How it's configured in this specific example",
    
    "workflow_complexity": "Please classify as: BASIC (demonstrates single concept), INTERMEDIATE (multiple interacting features), or ADVANCED (complex physics or coupling). What prior knowledge is required? What specific techniques are demonstrated?",
    
    "unique_distinguishing_features": "What makes this MODFLOW 6 example different from other examples? Compare to: different physics types, boundary conditions, advanced features, coupling approaches. Be as specific as possible.",
    
    "technical_concepts_specific": [
        "5-8 concepts that are specific to this MODFLOW 6 example type",
        "Please avoid generic terms like 'groundwater modeling', 'finite difference', 'Python'", 
        "Include: specific physics, unique methods, package-specific features, MODFLOW 6 capabilities",
        "Examples: 'aquifer thermal energy storage', 'variable density flow', 'advanced package options', 'model coupling'"
    ],
    
    "discriminative_questions": [
        "10 questions that would specifically apply to this type of MODFLOW 6 example:",
        "- 2 about the specific model physics: 'what is [unique concept] in [GWF/GWT/GWE]'",
        "- 3 about specific packages: 'how to configure [exact package] for [specific use case]'",
        "- 2 about specific features: '[advanced feature] setup', '[coupling method] implementation'", 
        "- 2 about specific applications: 'when to use [this approach] for [specific scenario]'",
        "- 1 about this example's unique demonstration that no other example shows",
        "Make questions very specific - users searching for this exact MODFLOW 6 capability"
    ],
    
    "ultra_specific_keywords": [
        "10-15 terms that would specifically be used for this MODFLOW 6 example type",
        "Please avoid generic terms: 'modflow', 'groundwater', 'model', 'example'",
        "Include specific terms: package codes, physics types, method names, feature names, coupling terms",
        "Focus on: what makes this searchable only for this specific MODFLOW 6 capability?"
    ]
}}

Goal: Make this MODFLOW 6 example clearly distinguishable from any other example through specific, targeted descriptions.
"""
        else:  # FloPy workflows
            prompt = f"""
Analyze this FloPy workflow code to create highly specific embeddings that distinguish it from similar MODFLOW workflows.

SOURCE CODE:
```python
{workflow['source_code']}
```

FILENAME: {filename}

Please generate a JSON response with detailed differentiation:

{{
    "title": "A very specific title that someone would use only for this exact workflow type (avoid generic terms)",
    
    "model_type_and_physics": "Please specify clearly: Is this FLOW-ONLY (MODFLOW/MF6), TRANSPORT-ONLY (MT3D), COUPLED (SEAWAT), or OTHER? What governing equations and physical processes are involved?",
    
    "boundary_packages_detailed": "List each boundary package with: (1) Package code (WEL/CHD/DRN/etc), (2) Physical meaning (pumping well/constant head/etc), (3) How it affects this specific model",
    
    "workflow_complexity": "Please classify as: BASIC (first-time users), INTERMEDIATE (some experience), or ADVANCED (expert level). What prior knowledge is required? What specific skills are taught?",
    
    "unique_distinguishing_features": "What makes this workflow different from similar ones? Please compare to: flow vs transport, different boundary types, basic vs advanced tutorials. Be as specific as possible.",
    
    "technical_concepts_specific": [
        "5-8 concepts that are specific to this workflow type",
        "Please avoid generic terms like 'groundwater modeling', 'finite difference', 'Python'", 
        "Include: specific physics, unique methods, package-specific features",
        "Examples: 'multi-species reactive transport', 'variable density flow', 'stress period multipliers'"
    ],
    
    "discriminative_questions": [
        "10 questions that would specifically apply to this type of workflow:",
        "- 2 about the specific model type: 'what is [unique concept] in [MT3D/MF6/SEAWAT]'",
        "- 3 about specific packages: 'how to set up [exact package] for [specific use case]'",
        "- 2 about specific errors: '[package-specific error]', '[workflow-type] not converging'", 
        "- 2 about specific comparisons: 'when to use [this package] vs [that package] for [specific case]'",
        "- 1 about this workflow's unique feature that no other workflow has",
        "Make questions very specific - users searching for this exact thing"
    ],
    
    "ultra_specific_keywords": [
        "10-15 terms that would specifically be used for this workflow type",
        "Please avoid generic terms: 'flopy', 'modflow', 'tutorial', 'example'",
        "Include specific terms: package codes, error messages, method names, file formats",
        "Focus on: what makes this searchable only for this specific use case?"
    ]
}}

Goal: Make this workflow clearly distinguishable from any other workflow through specific, targeted descriptions.
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
                
                if not response or not response.text:
                    raise Exception("Empty response from Gemini")
                
                # Extract JSON from response (same pattern as v00)
                text = response.text
                json_match = re.search(r'\{[\s\S]*\}', text)
                
                if json_match:
                    json_str = json_match.group(0)
                    analysis = json.loads(json_str)
                    
                    # Validate required fields
                    required_fields = ['title', 'model_type_and_physics', 'discriminative_questions', 'ultra_specific_keywords']
                    for field in required_fields:
                        if field not in analysis or not analysis[field]:
                            raise ValueError(f"Missing required field: {field}")
                    
                    return analysis
                    
                else:
                    raise ValueError("No JSON found in response")
                
            except Exception as e:
                print(f"    ⚠ Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5
                else:
                    raise Exception(f"All {max_retries} attempts failed: {e}")

    def create_embedding_string(self, analysis: Dict) -> str:
        """Create embedding string from v02 analysis"""
        
        # Build embedding string with ultra-specific structure
        parts = [
            f"Title: {analysis.get('title', '')}",
            f"Model Type: {analysis.get('model_type_and_physics', '')}",
            f"Boundary Packages: {analysis.get('boundary_packages_detailed', '')}",
            f"Complexity: {analysis.get('workflow_complexity', '')}",
            f"Distinguishing Features: {analysis.get('unique_distinguishing_features', '')}",
            f"Technical Concepts: {', '.join(analysis.get('technical_concepts_specific', []))}",
            f"Questions: {' | '.join(analysis.get('discriminative_questions', []))}",
            f"Keywords: {', '.join(analysis.get('ultra_specific_keywords', []))}"
        ]
        
        return "\n\n".join(parts)

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate OpenAI embedding for text"""
        max_retries = self.max_retries
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = await self.openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                print(f"    ⚠ Embedding attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5
                else:
                    raise Exception(f"All {max_retries} embedding attempts failed: {e}")

    def save_to_database(self, workflow_id: str, analysis: Dict, embedding_string: str, embedding: List[float]):
        """Save analysis, embedding string, and vector to v02 columns"""
        with psycopg2.connect(self.neon_conn) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE flopy_workflows
                    SET 
                        analysis_v02 = %s,
                        emb_string_02 = %s,
                        dspy_emb_02 = %s,
                        analysis_generated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (
                    json.dumps(analysis),
                    embedding_string,
                    embedding,  # pgvector handles the conversion
                    workflow_id
                ))

    async def process_workflow(self, workflow: Dict, source_repo: str = 'flopy') -> bool:
        """Process a single workflow"""
        try:
            filename = Path(workflow['tutorial_file']).name
            print(f"Processing: {filename}")
            
            # Generate analysis
            analysis = await self.generate_analysis(workflow, source_repo)
            print(f"✓ Generated analysis for: {filename}")
            
            # Create embedding string
            embedding_string = self.create_embedding_string(analysis)
            
            # Generate embedding
            embedding = await self.generate_embedding(embedding_string)
            print(f"✓ Generated embedding for: {filename}")
            
            # Save to database
            self.save_to_database(workflow['id'], analysis, embedding_string, embedding)
            print(f"✓ Success: {filename}")
            
            # Validate counts
            questions = analysis.get('discriminative_questions', [])
            concepts = analysis.get('technical_concepts_specific', [])
            keywords = analysis.get('ultra_specific_keywords', [])
            
            print(f"  - Questions: {len(questions)}")
            print(f"  - Concepts: {len(concepts)}")
            print(f"  - Keywords: {len(keywords)}")
            
            return True
            
        except Exception as e:
            print(f"✗ Failed: {filename} - {e}")
            return False

    async def process_batch(self, workflows: List[Dict], source_repo: str = 'flopy'):
        """Process workflows in batch with rate limiting"""
        successful = 0
        failed = 0
        
        for i, workflow in enumerate(workflows, 1):
            print(f"\n[{i}/{len(workflows)}]")
            
            success = await self.process_workflow(workflow, source_repo)
            
            if success:
                successful += 1
            else:
                failed += 1
            
            # Rate limiting
            if i < len(workflows):  # Don't sleep after last item
                await asyncio.sleep(1.0)  # 1 second between requests
        
        return successful, failed

    def get_database_stats(self) -> Dict:
        """Get current database statistics"""
        with psycopg2.connect(self.neon_conn) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(analysis_v00) as with_v00,
                        COUNT(analysis_v02) as with_v02,
                        COUNT(emb_string_00) as with_emb_00,
                        COUNT(emb_string_02) as with_emb_02,
                        COUNT(dspy_emb_00) as with_vec_00,
                        COUNT(dspy_emb_02) as with_vec_02
                    FROM flopy_workflows
                    WHERE source_repository = 'flopy'
                """)
                
                result = cur.fetchone()
                return {
                    'total': result[0],
                    'with_v00': result[1], 
                    'with_v02': result[2],
                    'with_emb_00': result[3],
                    'with_emb_02': result[4],
                    'with_vec_00': result[5],
                    'with_vec_02': result[6]
                }

async def main():
    """Main processing function"""
    import argparse
    parser = argparse.ArgumentParser(description='Generate v02 workflow analysis')
    parser.add_argument('--limit', type=int, default=72, help='Max workflows to process')
    parser.add_argument('--source', type=str, default='flopy', choices=['flopy', 'modflow6-examples'], 
                        help='Source repository to process')
    parser.add_argument('--test', action='store_true', help='Process only 1 workflow for testing')
    args = parser.parse_args()
    
    if args.test:
        limit = 1
        print("🧪 TEST MODE - Processing 1 workflow")
    else:
        limit = args.limit
    
    source_repo = args.source
    
    generator = WorkflowAnalysisGenerator()
    
    print("=" * 80)
    if source_repo == 'modflow6-examples':
        print("MODFLOW 6 Examples Analysis v02 Generator")
        print("Ultra-Discriminative Prompt for Research Examples")
    else:
        print("FloPy Workflows Analysis v02 Generator")
        print("Ultra-Discriminative Prompt (Perplexity Pro Recommendations)")
    print("=" * 80)
    print("AI Models:")
    print("  Analysis: gemini-2.5-pro")
    print("  Embeddings: text-embedding-3-small")
    print(f"  Max retries: {generator.max_retries}")
    print("  Rate limit: 1.0s between calls")
    print(f"  Source repository: {source_repo}")
    print()
    
    # Fetch workflows
    workflows = generator.fetch_workflows_for_v02(limit, source_repo)
    print(f"Found {len(workflows)} {source_repo} workflows to process\n")
    
    if not workflows:
        print(f"No {source_repo} workflows need v02 processing!")
        return
    
    # Process workflows
    successful, failed = await generator.process_batch(workflows, source_repo)
    
    # Final summary
    print("\n" + "=" * 80)
    print("Processing Complete!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print("=" * 80)
    
    # Show sample result
    if successful > 0:
        stats = generator.get_database_stats()
        sample_file = workflows[0]['tutorial_file'].split('/')[-1]
        print(f"\nSample Result:")
        print(f"  File: {sample_file}")
        print(f"  Ultra-Discriminative Analysis: v02")
    
    # Database statistics
    stats = generator.get_database_stats()
    print(f"\nDatabase Statistics:")
    print(f"  Total FloPy workflows: {stats['total']}")
    print(f"  With analysis_v00: {stats['with_v00']}")
    print(f"  With analysis_v02: {stats['with_v02']}")
    print(f"  With emb_string_00: {stats['with_emb_00']}")
    print(f"  With emb_string_02: {stats['with_emb_02']}")
    print(f"  With dspy_emb_00: {stats['with_vec_00']}")
    print(f"  With dspy_emb_02: {stats['with_vec_02']}")

if __name__ == "__main__":
    asyncio.run(main())