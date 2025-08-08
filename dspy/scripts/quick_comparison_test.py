#!/usr/bin/env python3
"""
Quick comparison test between v00 and v02 embeddings
Tests a few workflows to get initial results quickly
"""

import sys
sys.path.append('/home/danilopezmella/flopy_expert')
import psycopg2
import numpy as np
import openai
import config
import time

# Initialize OpenAI
openai.api_key = config.OPENAI_API_KEY

def calculate_similarity(emb1, emb2):
    emb1_norm = emb1 / np.linalg.norm(emb1)
    emb2_norm = emb2 / np.linalg.norm(emb2)
    return np.dot(emb1_norm, emb2_norm)

def generate_embedding(text):
    try:
        response = openai.embeddings.create(
            model='text-embedding-3-small',
            input=text
        )
        return np.array(response.data[0].embedding)
    except Exception as e:
        print(f"  ⚠ Embedding error: {e}")
        return None

def main():
    print('🧪 Quick v00 vs v02 comparison test...')
    
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            # Get 5 workflows with their embeddings and questions
            cur.execute("""
                SELECT 
                    id, tutorial_file, analysis_v00, analysis_v02,
                    dspy_emb_00::text, dspy_emb_02::text
                FROM flopy_workflows
                WHERE analysis_v00 IS NOT NULL AND analysis_v02 IS NOT NULL
                AND source_repository = 'flopy'
                ORDER BY tutorial_file
                LIMIT 5
            """)
            
            workflows = []
            for row in cur.fetchall():
                # Parse embeddings
                emb_v00 = np.array([float(x) for x in row[4].strip('[]').split(',')])
                emb_v02 = np.array([float(x) for x in row[5].strip('[]').split(',')])
                
                workflows.append({
                    'id': row[0],
                    'file': row[1].split('/')[-1],
                    'questions_v00': row[2].get('potential_questions', [])[:2],  # First 2 questions
                    'questions_v02': row[3].get('discriminative_questions', [])[:2],
                    'embedding_v00': emb_v00,
                    'embedding_v02': emb_v02
                })

    print(f'Testing {len(workflows)} workflows...')

    v00_hits = 0
    v02_hits = 0
    total_questions = 0

    for i, workflow in enumerate(workflows):
        filename = workflow['file']
        print(f'\\n📁 {filename}')
        
        # Test both v00 and v02 questions
        for version in ['v00', 'v02']:
            questions_key = f'questions_{version}'
            embedding_key = f'embedding_{version}'
            
            for q in workflow[questions_key]:
                q_emb = generate_embedding(q)
                if q_emb is None:
                    continue
                    
                total_questions += 1
                
                # Find best match - calculate similarity with parent workflow
                parent_sim = calculate_similarity(q_emb, workflow[embedding_key])
                
                # Calculate similarities with other workflows  
                other_sims = []
                for other in workflows:
                    if other['id'] != workflow['id']:
                        sim = calculate_similarity(q_emb, other[embedding_key])
                        other_sims.append(sim)
                
                # Check if parent is #1
                is_parent_best = not other_sims or parent_sim > max(other_sims)
                
                if version == 'v00':
                    if is_parent_best:
                        v00_hits += 1
                else:  # v02
                    if is_parent_best:
                        v02_hits += 1
                
                rank_str = '#1' if is_parent_best else 'not #1'
                print(f'  {version}: {q[:40]}... → {rank_str}')
                
                time.sleep(0.3)  # Rate limit

    print(f'\\n📊 QUICK RESULTS (sample of {len(workflows)} workflows):')
    v00_accuracy = v00_hits / (total_questions/2) * 100 if total_questions > 0 else 0
    v02_accuracy = v02_hits / (total_questions/2) * 100 if total_questions > 0 else 0
    improvement = v02_accuracy - v00_accuracy
    
    print(f'  v00 accuracy: {v00_hits}/{total_questions//2} ({v00_accuracy:.1f}%)')
    print(f'  v02 accuracy: {v02_hits}/{total_questions//2} ({v02_accuracy:.1f}%)')
    print(f'  Improvement: {improvement:+.1f} percentage points')
    
    if improvement >= 10:
        assessment = "🚀 EXCELLENT improvement!"
    elif improvement >= 5:
        assessment = "✅ VERY GOOD improvement!"
    elif improvement >= 2:
        assessment = "✓ Good improvement"
    elif improvement >= 0:
        assessment = "➡️ Minor improvement"
    else:
        assessment = "⚠️ Regression"
        
    print(f'  Assessment: {assessment}')

if __name__ == "__main__":
    main()