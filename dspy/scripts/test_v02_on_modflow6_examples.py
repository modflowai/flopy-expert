#!/usr/bin/env python3
"""
Test Ultra-Discriminative v02 Prompt on MODFLOW 6 Examples
See if the approach generalizes beyond FloPy tutorial workflows
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

class ModFlow6TestGenerator:
    def __init__(self):
        # Initialize AI clients (same as working v02)
        self.gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        
        self.neon_conn = config.NEON_CONNECTION_STRING
        self.max_retries = 3
        
    def fetch_modflow6_workflows(self, limit: int = 10) -> List[Dict]:
        """Fetch MODFLOW 6 examples for testing"""
        with psycopg2.connect(self.neon_conn) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        id, tutorial_file, source_code
                    FROM flopy_workflows
                    WHERE source_repository = 'modflow6-examples'
                        AND source_code IS NOT NULL
                        AND analysis_v02 IS NULL
                    ORDER BY tutorial_file
                    LIMIT %s
                """, (limit,))
                return cur.fetchall()
    
    async def generate_analysis(self, workflow: Dict) -> Dict[str, Any]:
        """Generate ultra-discriminative analysis for MODFLOW 6 examples"""
        
        # Extract filename for context
        filename = workflow['tutorial_file'].split('/')[-1] if '/' in workflow['tutorial_file'] else workflow['tutorial_file']
        
        # Adapt prompt for MODFLOW 6 examples (not FloPy tutorials)
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
    
    "packages_and_features": "List each MODFLOW 6 package used with: (1) Package code (WEL/CHD/DRN/etc), (2) Physical meaning (pumping well/constant head/etc), (3) How it's configured in this specific example",
    
    "example_complexity": "Please classify as: BASIC (demonstrates single concept), INTERMEDIATE (multiple interacting features), or ADVANCED (complex physics or coupling). What prior knowledge is required? What specific techniques are demonstrated?",
    
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
                
                # Extract JSON from response (same pattern as v00/v02)
                text = response.text
                json_match = re.search(r'\\{[\\s\\S]*\\}', text)
                
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
                    retry_delay *= 2
                else:
                    raise Exception(f"All {max_retries} attempts failed: {e}")

    def create_embedding_string(self, analysis: Dict) -> str:
        """Create embedding string from analysis"""
        parts = [
            f"Title: {analysis.get('title', '')}",
            f"Model Type: {analysis.get('model_type_and_physics', '')}",
            f"Packages: {analysis.get('packages_and_features', '')}",
            f"Complexity: {analysis.get('example_complexity', '')}",
            f"Distinguishing Features: {analysis.get('unique_distinguishing_features', '')}",
            f"Technical Concepts: {', '.join(analysis.get('technical_concepts_specific', []))}",
            f"Questions: {' | '.join(analysis.get('discriminative_questions', []))}",
            f"Keywords: {', '.join(analysis.get('ultra_specific_keywords', []))}"
        ]
        
        return "\\n\\n".join(parts)

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

    async def process_workflow(self, workflow: Dict) -> bool:
        """Process a single MODFLOW 6 workflow"""
        try:
            filename = Path(workflow['tutorial_file']).name
            print(f"Processing: {filename}")
            
            # Generate analysis
            analysis = await self.generate_analysis(workflow)
            print(f"✓ Generated analysis for: {filename}")
            
            # Create embedding string
            embedding_string = self.create_embedding_string(analysis)
            
            # Generate embedding
            embedding = await self.generate_embedding(embedding_string)
            print(f"✓ Generated embedding for: {filename}")
            
            # Store results (just print for now, don't save to avoid conflicts)
            print(f"✓ Success: {filename}")
            
            # Show analysis quality
            questions = analysis.get('discriminative_questions', [])
            concepts = analysis.get('technical_concepts_specific', [])
            keywords = analysis.get('ultra_specific_keywords', [])
            
            print(f"  📊 Analysis Quality:")
            print(f"    - Title: {analysis.get('title', 'N/A')[:60]}...")
            print(f"    - Model Type: {analysis.get('model_type_and_physics', 'N/A')[:50]}...")
            print(f"    - Questions: {len(questions)}")
            print(f"    - Concepts: {len(concepts)}")
            print(f"    - Keywords: {len(keywords)}")
            
            # Show sample questions
            print(f"  🔍 Sample Questions:")
            for i, q in enumerate(questions[:3], 1):
                print(f"    {i}. {q[:80]}...")
            
            return True
            
        except Exception as e:
            print(f"✗ Failed: {filename} - {e}")
            return False

    async def run_test(self, limit: int = 10):
        """Test the v02 approach on MODFLOW 6 examples"""
        print("=" * 80)
        print("TESTING ULTRA-DISCRIMINATIVE PROMPT ON MODFLOW 6 EXAMPLES")
        print("=" * 80)
        print(f"Testing approach generalization beyond FloPy tutorials")
        print()
        
        # Fetch workflows
        workflows = self.fetch_modflow6_workflows(limit)
        print(f"Found {len(workflows)} MODFLOW 6 examples to test\\n")
        
        if not workflows:
            print("No MODFLOW 6 examples available for testing!")
            return
        
        # Process workflows
        successful = 0
        failed = 0
        
        for i, workflow in enumerate(workflows, 1):
            print(f"\\n[{i}/{len(workflows)}]")
            
            success = await self.process_workflow(workflow)
            
            if success:
                successful += 1
            else:
                failed += 1
            
            # Rate limiting
            if i < len(workflows):
                await asyncio.sleep(1.0)
        
        # Final summary
        print("\\n" + "=" * 80)
        print("MODFLOW 6 EXAMPLES TEST COMPLETE!")
        print("=" * 80)
        print(f"  Successful: {successful}/{len(workflows)} ({successful/len(workflows)*100:.1f}%)")
        print(f"  Failed: {failed}")
        
        if successful > 0:
            print(f"\\n🎯 ASSESSMENT:")
            if successful == len(workflows):
                print("✅ EXCELLENT: Ultra-discriminative approach works perfectly on MODFLOW 6 examples!")
            elif successful >= len(workflows) * 0.8:
                print("✓ GOOD: Approach generalizes well to MODFLOW 6 examples") 
            else:
                print("⚠️ MIXED: Some challenges adapting to MODFLOW 6 examples")
        
        print("=" * 80)

async def main():
    """Main test function"""
    generator = ModFlow6TestGenerator()
    await generator.run_test(limit=10)

if __name__ == "__main__":
    asyncio.run(main())