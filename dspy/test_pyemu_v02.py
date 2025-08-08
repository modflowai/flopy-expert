#!/usr/bin/env python3
"""
Quick test of PyEMU v02 embeddings
"""

import sys
sys.path.append('/home/danilopezmella/flopy_expert')

import psycopg2
import numpy as np
import openai
import json
from typing import List, Dict
import config

# Initialize OpenAI
openai.api_key = config.OPENAI_API_KEY

def get_embedding(text: str) -> np.ndarray:
    """Generate embedding for text"""
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return np.array(response.data[0].embedding)

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity"""
    a_norm = a / np.linalg.norm(a)
    b_norm = b / np.linalg.norm(b)
    return float(np.dot(a_norm, b_norm))

def parse_embedding(emb_str: str) -> np.ndarray:
    """Parse embedding string to numpy array"""
    if emb_str.startswith('['):
        values = [float(x) for x in emb_str.strip('[]').split(',')]
    else:
        values = [float(x) for x in emb_str.split(',')]
    return np.array(values)

def main():
    conn = psycopg2.connect(config.NEON_CONNECTION_STRING)
    cur = conn.cursor()
    
    # Load PyEMU workflows with both embeddings
    cur.execute("""
        SELECT 
            notebook_file,
            title,
            embedding::text as baseline_emb,
            dspy_emb_02::text as v02_emb,
            analysis_v02
        FROM pyemu_workflows
        WHERE embedding IS NOT NULL 
        AND dspy_emb_02 IS NOT NULL
        ORDER BY notebook_file
    """)
    
    workflows = []
    for row in cur.fetchall():
        analysis = row[4]
        questions = []
        
        # Extract questions from analysis
        if analysis and 'discriminative_questions' in analysis:
            for q in analysis['discriminative_questions']:
                if isinstance(q, dict) and 'question_text' in q:
                    questions.append(q['question_text'])
                elif isinstance(q, str):
                    questions.append(q)
        
        workflows.append({
            'file': row[0],
            'title': row[1],
            'baseline_emb': parse_embedding(row[2]),
            'v02_emb': parse_embedding(row[3]),
            'questions': questions[:5]  # Use first 5 questions
        })
    
    print(f"Loaded {len(workflows)} PyEMU workflows")
    
    # Test each workflow's questions
    baseline_correct = 0
    v02_correct = 0
    total_questions = 0
    
    for i, workflow in enumerate(workflows, 1):
        if not workflow['questions']:
            continue
            
        print(f"\n[{i}/{len(workflows)}] Testing {workflow['file']}")
        print(f"  Questions: {len(workflow['questions'])}")
        
        for question in workflow['questions']:
            if len(question) < 10:
                continue
                
            # Generate query embedding
            try:
                query_emb = get_embedding(question)
            except Exception as e:
                print(f"  Error generating embedding: {e}")
                continue
            
            total_questions += 1
            
            # Calculate similarities for all workflows
            baseline_sims = []
            v02_sims = []
            
            for other in workflows:
                baseline_sim = cosine_similarity(query_emb, other['baseline_emb'])
                v02_sim = cosine_similarity(query_emb, other['v02_emb'])
                
                baseline_sims.append((other['file'], baseline_sim))
                v02_sims.append((other['file'], v02_sim))
            
            # Sort by similarity
            baseline_sims.sort(key=lambda x: x[1], reverse=True)
            v02_sims.sort(key=lambda x: x[1], reverse=True)
            
            # Check if correct workflow is top match
            if baseline_sims[0][0] == workflow['file']:
                baseline_correct += 1
                print(f"  ✓ Baseline correct")
            else:
                print(f"  ✗ Baseline: {baseline_sims[0][0]}")
                
            if v02_sims[0][0] == workflow['file']:
                v02_correct += 1
                print(f"  ✓ V02 correct")
            else:
                print(f"  ✗ V02: {v02_sims[0][0]}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("PYEMU V02 EMBEDDING TEST RESULTS")
    print("=" * 60)
    print(f"Total questions tested: {total_questions}")
    print(f"\nBaseline Performance:")
    print(f"  Correct: {baseline_correct}/{total_questions}")
    print(f"  Accuracy: {baseline_correct/total_questions*100:.1f}%" if total_questions > 0 else "N/A")
    print(f"\nV02 Performance:")
    print(f"  Correct: {v02_correct}/{total_questions}")
    print(f"  Accuracy: {v02_correct/total_questions*100:.1f}%" if total_questions > 0 else "N/A")
    print(f"\nImprovement:")
    print(f"  +{v02_correct - baseline_correct} correct answers")
    print(f"  +{(v02_correct - baseline_correct)/total_questions*100:.1f} percentage points" if total_questions > 0 else "N/A")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()