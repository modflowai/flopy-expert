#!/usr/bin/env python3
"""
Generate ultra-discriminative v02 analysis for PyEMU workflows
Adapted from FloPy strategy but focused on uncertainty/PEST concepts
"""

import sys
sys.path.append('/home/danilopezmella/flopy_expert')
import psycopg2
import config
import json
import google.genai as genai
import asyncio
from datetime import datetime
import time

class PyEMUUltraDiscriminativeGenerator:
    def __init__(self):
        # Use google.genai (same as working v00) to avoid safety filters
        self.gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.conn = psycopg2.connect(config.NEON_CONNECTION_STRING)
        self.cur = self.conn.cursor()
        
    def generate_ultra_discriminative_prompt(self, workflow):
        """Create PyEMU-specific ultra-discriminative prompt"""
        
        prompt = f"""You are an expert in uncertainty quantification and PEST++ inverse modeling analyzing PyEMU workflows.

WORKFLOW: {workflow['notebook_file']}
TITLE: {workflow['title']}
TYPE: {workflow['workflow_type']}
PEST CONCEPTS: {', '.join(workflow['pest_concepts']) if workflow['pest_concepts'] else 'general'}
UNCERTAINTY METHODS: {', '.join(workflow['uncertainty_methods']) if workflow['uncertainty_methods'] else 'general'}
PYEMU MODULES: {', '.join(workflow['pyemu_modules']) if workflow['pyemu_modules'] else 'various'}

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

Make questions so specific that ONLY someone who understands THIS EXACT workflow could answer correctly."""

        return prompt
    
    def generate_analysis(self, workflow):
        """Generate ultra-discriminative analysis using Gemini"""
        prompt = self.generate_ultra_discriminative_prompt(workflow)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use the same API pattern as working v00
                response = asyncio.run(self._generate_async(prompt))
                
                # Parse JSON from response
                text = response.text
                # Find JSON in response
                start = text.find('{')
                end = text.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = text[start:end]
                    analysis = json.loads(json_str)
                    
                    # Validate required fields
                    required = ['workflow_purpose', 'discriminative_questions']
                    if all(field in analysis for field in required):
                        return analysis
                    else:
                        print(f"  ⚠️ Missing required fields, retrying...")
                
            except json.JSONDecodeError as e:
                print(f"  ⚠️ JSON parse error: {e}")
            except Exception as e:
                print(f"  ⚠️ Generation error: {e}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
        
        return None
    
    async def _generate_async(self, prompt):
        """Async wrapper for Gemini generation"""
        response = await asyncio.to_thread(
            self.gemini_client.models.generate_content,
            model=config.GEMINI_MODEL,
            contents=prompt
        )
        return response
    
    def process_all_workflows(self):
        """Process all PyEMU workflows"""
        print("📚 Loading PyEMU workflows...")
        
        self.cur.execute("""
            SELECT 
                id, notebook_file, title, workflow_type,
                pest_concepts, uncertainty_methods, pyemu_modules,
                description
            FROM pyemu_workflows
            ORDER BY notebook_file
        """)
        
        workflows = []
        for row in self.cur.fetchall():
            workflows.append({
                'id': row[0],
                'notebook_file': row[1],
                'title': row[2],
                'workflow_type': row[3],
                'pest_concepts': row[4] or [],
                'uncertainty_methods': row[5] or [],
                'pyemu_modules': row[6] or [],
                'description': row[7]
            })
        
        print(f"Found {len(workflows)} PyEMU workflows")
        
        # Process each workflow
        success_count = 0
        for i, workflow in enumerate(workflows, 1):
            print(f"\n[{i}/{len(workflows)}] Processing: {workflow['notebook_file']}")
            print(f"  Type: {workflow['workflow_type']}")
            
            # Check if already has v02
            self.cur.execute("""
                SELECT analysis_v02 IS NOT NULL 
                FROM pyemu_workflows 
                WHERE id = %s
            """, (workflow['id'],))
            
            has_v02 = self.cur.fetchone()[0]
            if has_v02:
                print("  ✓ Already has v02 analysis, skipping...")
                success_count += 1
                continue
            
            # Generate ultra-discriminative analysis
            print("  🧬 Generating ultra-discriminative analysis...")
            analysis = self.generate_analysis(workflow)
            
            if analysis:
                # Update database
                self.cur.execute("""
                    UPDATE pyemu_workflows
                    SET analysis_v02 = %s
                    WHERE id = %s
                """, (json.dumps(analysis), workflow['id']))
                self.conn.commit()
                
                print(f"  ✅ Generated {len(analysis.get('discriminative_questions', []))} questions")
                if analysis.get('discriminative_questions'):
                    sample_q = str(analysis['discriminative_questions'][0])
                    print(f"     Sample: {sample_q[:80]}...")
                success_count += 1
            else:
                print("  ❌ Failed to generate analysis")
            
            # Rate limiting
            time.sleep(1)
        
        print(f"\n{'='*60}")
        print(f"✅ Successfully generated v02 analysis for {success_count}/{len(workflows)} workflows")
        
        # Summary
        self.cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(analysis_v02) as with_v02
            FROM pyemu_workflows
        """)
        result = self.cur.fetchone()
        print(f"\nDatabase Status:")
        print(f"  Total workflows: {result[0]}")
        print(f"  With v02 analysis: {result[1]}")
        
        if result[1] == result[0]:
            print("\n🎉 All PyEMU workflows now have ultra-discriminative analysis!")
            print("Next step: Generate v02 embeddings using these discriminative questions")
        
    def close(self):
        self.cur.close()
        self.conn.close()

def main():
    print("=" * 80)
    print("PyEMU Ultra-Discriminative Analysis Generator v02")
    print("=" * 80)
    print()
    print("Strategy: Force differentiation between similar uncertainty workflows")
    print("Focus: PEST++ tools, statistical methods, implementation details")
    print()
    
    generator = PyEMUUltraDiscriminativeGenerator()
    try:
        generator.process_all_workflows()
    finally:
        generator.close()

if __name__ == "__main__":
    main()