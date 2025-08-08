#!/usr/bin/env python3
"""
Generate v02 embeddings for PyEMU workflows from ultra-discriminative analysis
Similar to FloPy but for uncertainty/PEST domain
"""

import sys
sys.path.append('/home/danilopezmella/flopy_expert')
import psycopg2
import openai
import config
import json
import numpy as np
from datetime import datetime
import time

# Initialize OpenAI
openai.api_key = config.OPENAI_API_KEY

class PyEMUEmbeddingGenerator:
    def __init__(self):
        self.conn = psycopg2.connect(config.NEON_CONNECTION_STRING)
        self.cur = self.conn.cursor()
        self.embedding_model = 'text-embedding-3-small'
        
    def create_embedding_text(self, workflow, analysis):
        """Create comprehensive text for embedding from ultra-discriminative analysis"""
        
        # Extract key components
        questions = analysis.get('discriminative_questions', [])
        purpose = analysis.get('workflow_purpose', '')
        differentiators = analysis.get('key_differentiators', [])
        pest_specifics = analysis.get('pest_tool_specifics', [])
        statistical_impl = analysis.get('statistical_implementation', [])
        pyemu_features = analysis.get('unique_pyemu_features', [])
        
        # Build comprehensive embedding text
        embedding_parts = [
            f"Notebook: {workflow['notebook_file']}",
            f"Title: {workflow['title']}",
            f"Type: {workflow['workflow_type']}",
            f"Purpose: {purpose}",
            "",
            "ULTRA-DISCRIMINATIVE QUESTIONS:"
        ]
        
        # Add all questions (these are the key differentiators)
        for i, q in enumerate(questions[:10], 1):
            embedding_parts.append(f"{i}. {q}")
        
        # Add technical differentiators
        if differentiators:
            embedding_parts.append("")
            embedding_parts.append("KEY DIFFERENTIATORS:")
            for diff in differentiators:
                embedding_parts.append(f"- {diff}")
        
        # Add PEST++ specifics
        if pest_specifics:
            embedding_parts.append("")
            embedding_parts.append("PEST++ TOOL SPECIFICS:")
            for spec in pest_specifics:
                embedding_parts.append(f"- {spec}")
        
        # Add statistical implementation details
        if statistical_impl:
            embedding_parts.append("")
            embedding_parts.append("STATISTICAL IMPLEMENTATION:")
            for impl in statistical_impl:
                embedding_parts.append(f"- {impl}")
        
        # Add PyEMU-specific features
        if pyemu_features:
            embedding_parts.append("")
            embedding_parts.append("PYEMU CLASSES/METHODS:")
            for feature in pyemu_features:
                embedding_parts.append(f"- {feature}")
        
        # Add original metadata for context
        if workflow.get('pest_concepts'):
            embedding_parts.append("")
            embedding_parts.append(f"PEST Concepts: {', '.join(workflow['pest_concepts'])}")
        
        if workflow.get('uncertainty_methods'):
            embedding_parts.append(f"Uncertainty Methods: {', '.join(workflow['uncertainty_methods'])}")
        
        if workflow.get('pyemu_modules'):
            embedding_parts.append(f"PyEMU Modules: {', '.join(workflow['pyemu_modules'])}")
        
        return "\n".join(embedding_parts)
    
    def generate_embedding(self, text):
        """Generate embedding using OpenAI"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = openai.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                print(f"    ⚠️ Embedding error (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        return None
    
    def process_all_workflows(self):
        """Process all PyEMU workflows with v02 analysis"""
        
        print("📚 Loading PyEMU workflows with v02 analysis...")
        
        # Get workflows that have v02 analysis but no v02 embeddings
        self.cur.execute("""
            SELECT 
                id, notebook_file, title, workflow_type,
                pest_concepts, uncertainty_methods, pyemu_modules,
                analysis_v02
            FROM pyemu_workflows
            WHERE analysis_v02 IS NOT NULL
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
                'analysis_v02': row[7]
            })
        
        print(f"Found {len(workflows)} workflows with v02 analysis")
        
        # Check how many already have embeddings
        self.cur.execute("""
            SELECT COUNT(*) FROM pyemu_workflows 
            WHERE dspy_emb_02 IS NOT NULL
        """)
        already_embedded = self.cur.fetchone()[0]
        print(f"  Already have v02 embeddings: {already_embedded}")
        print(f"  Need to generate: {len(workflows) - already_embedded}")
        print()
        
        success_count = 0
        skip_count = 0
        
        for i, workflow in enumerate(workflows, 1):
            print(f"[{i}/{len(workflows)}] Processing: {workflow['notebook_file']}")
            
            # Check if already has v02 embedding
            self.cur.execute("""
                SELECT dspy_emb_02 IS NOT NULL 
                FROM pyemu_workflows 
                WHERE id = %s
            """, (workflow['id'],))
            
            has_embedding = self.cur.fetchone()[0]
            if has_embedding:
                print("  ✓ Already has v02 embedding, skipping...")
                skip_count += 1
                continue
            
            # Create embedding text from ultra-discriminative analysis
            print("  📝 Creating embedding text from v02 analysis...")
            embedding_text = self.create_embedding_text(workflow, workflow['analysis_v02'])
            
            # Show sample of embedding text
            print(f"  📄 Text length: {len(embedding_text)} chars")
            sample = embedding_text.split('\n')[6] if len(embedding_text.split('\n')) > 6 else embedding_text[:100]
            print(f"     Sample question: {sample[:80]}...")
            
            # Generate embedding
            print("  🧬 Generating OpenAI embedding...")
            embedding = self.generate_embedding(embedding_text)
            
            if embedding:
                # Convert to PostgreSQL vector format
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                
                # Update database
                self.cur.execute("""
                    UPDATE pyemu_workflows
                    SET dspy_emb_02 = %s::vector,
                        emb_string_02 = %s
                    WHERE id = %s
                """, (embedding_str, embedding_text, workflow['id']))
                self.conn.commit()
                
                print(f"  ✅ Embedding generated and saved")
                success_count += 1
            else:
                print("  ❌ Failed to generate embedding")
            
            # Rate limiting
            time.sleep(0.5)
        
        print(f"\n{'='*60}")
        print(f"✅ Successfully generated {success_count} new v02 embeddings")
        print(f"⏭️ Skipped {skip_count} (already had embeddings)")
        
        # Final status
        self.cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(analysis_v02) as with_v02_analysis,
                COUNT(dspy_emb_02) as with_v02_embeddings
            FROM pyemu_workflows
        """)
        result = self.cur.fetchone()
        
        print(f"\n📊 Final Status:")
        print(f"  Total workflows: {result[0]}")
        print(f"  With v02 analysis: {result[1]}")
        print(f"  With v02 embeddings: {result[2]}")
        
        if result[2] == result[0]:
            print("\n🎉 All PyEMU workflows now have ultra-discriminative v02 embeddings!")
            print("Next step: Test v02 vs baseline embeddings for search improvement")
    
    def close(self):
        self.cur.close()
        self.conn.close()

def main():
    print("=" * 80)
    print("PyEMU v02 Embedding Generator")
    print("=" * 80)
    print()
    print("Creating embeddings from ultra-discriminative questions")
    print(f"Model: text-embedding-3-small")
    print(f"Dimensions: 1536")
    print()
    
    generator = PyEMUEmbeddingGenerator()
    try:
        generator.process_all_workflows()
    finally:
        generator.close()

if __name__ == "__main__":
    main()