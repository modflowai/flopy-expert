#!/usr/bin/env python3
"""
Reverse-Engineering Test for FloPy Workflow Embeddings

Tests if questions generated FROM workflows can find their parent workflow through semantic search.
This validates that our embeddings actually capture the semantic meaning properly.
"""

import json
import psycopg2
import numpy as np
from typing import List, Dict, Tuple
import openai
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
import config

# Initialize OpenAI
openai.api_key = config.OPENAI_API_KEY

def get_workflows_with_embeddings(limit: int = 10) -> List[Dict]:
    """Fetch workflows that have both analysis and embeddings"""
    conn = psycopg2.connect(config.NEON_CONNECTION_STRING)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            id,
            tutorial_file,
            analysis_v00,
            dspy_emb_00::text
        FROM flopy_workflows 
        WHERE analysis_v00 IS NOT NULL 
        AND dspy_emb_00 IS NOT NULL
        ORDER BY analysis_generated_at DESC
        LIMIT %s
    """, (limit,))
    
    workflows = []
    for row in cur.fetchall():
        # Parse the vector string into array
        emb_str = row[3].strip('[]')
        embedding = np.array([float(x) for x in emb_str.split(',')])
        
        workflows.append({
            'id': row[0],
            'tutorial_file': row[1],
            'analysis': row[2],
            'embedding': embedding,
            'questions': row[2].get('potential_questions', [])
        })
    
    cur.close()
    conn.close()
    return workflows

def generate_question_embedding(question: str) -> np.ndarray:
    """Generate embedding for a single question"""
    try:
        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=question
        )
        return np.array(response.data[0].embedding)
    except Exception as e:
        print(f"Error embedding question: {e}")
        return None

def calculate_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """Calculate cosine similarity between two embeddings"""
    # Normalize vectors
    emb1_norm = emb1 / np.linalg.norm(emb1)
    emb2_norm = emb2 / np.linalg.norm(emb2)
    # Cosine similarity
    return np.dot(emb1_norm, emb2_norm)

def find_parent_rank(question_emb: np.ndarray, 
                     parent_id: str,
                     all_workflows: List[Dict]) -> Tuple[int, float, List[Tuple[str, float]]]:
    """
    Find where the parent workflow ranks for this question
    Returns: (rank, similarity_score, all_similarities)
    """
    similarities = []
    
    for workflow in all_workflows:
        sim = calculate_similarity(question_emb, workflow['embedding'])
        similarities.append((workflow['id'], sim, workflow['tutorial_file']))
    
    # Sort by similarity (highest first)
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    # Find parent rank (1-indexed)
    parent_rank = None
    parent_sim = None
    for i, (wf_id, sim, _) in enumerate(similarities):
        if wf_id == parent_id:
            parent_rank = i + 1
            parent_sim = sim
            break
    
    return parent_rank, parent_sim, similarities[:5]  # Return top 5 for analysis

def run_reverse_engineering_test():
    """Main test function"""
    print("=" * 80)
    print("Reverse-Engineering Test for FloPy Workflow Embeddings")
    print("=" * 80)
    
    # Fetch workflows
    print("\n1. Fetching workflows with embeddings...")
    workflows = get_workflows_with_embeddings(limit=10)
    print(f"   Found {len(workflows)} workflows")
    
    # Track results
    total_questions = 0
    rank_1_hits = 0
    rank_3_hits = 0
    rank_5_hits = 0
    all_ranks = []
    failed_questions = []
    
    print("\n2. Testing each question against all embeddings...")
    print("-" * 80)
    
    for i, workflow in enumerate(workflows):
        workflow_name = Path(workflow['tutorial_file']).name
        print(f"\n[{i+1}/{len(workflows)}] {workflow_name}")
        print(f"   Testing {len(workflow['questions'])} questions...")
        
        workflow_ranks = []
        
        for j, question in enumerate(workflow['questions']):
            # Generate embedding for question
            question_emb = generate_question_embedding(question)
            if question_emb is None:
                continue
            
            # Find where parent ranks
            rank, similarity, top_5 = find_parent_rank(
                question_emb, 
                workflow['id'], 
                workflows
            )
            
            total_questions += 1
            workflow_ranks.append(rank)
            all_ranks.append(rank)
            
            if rank == 1:
                rank_1_hits += 1
                print(f"   ✓ Q{j+1}: Rank #{rank} (sim={similarity:.3f})")
            elif rank <= 3:
                rank_3_hits += 1
                print(f"   ⚠ Q{j+1}: Rank #{rank} (sim={similarity:.3f})")
            elif rank <= 5:
                rank_5_hits += 1
                print(f"   ⚠ Q{j+1}: Rank #{rank} (sim={similarity:.3f})")
            else:
                print(f"   ✗ Q{j+1}: Rank #{rank} (sim={similarity:.3f})")
                failed_questions.append({
                    'workflow': workflow_name,
                    'question': question[:60] + '...',
                    'rank': rank,
                    'similarity': similarity,
                    'top_match': Path(top_5[0][2]).name if top_5 else 'N/A'
                })
        
        # Workflow summary
        if workflow_ranks:
            avg_rank = sum(workflow_ranks) / len(workflow_ranks)
            print(f"   Workflow average rank: {avg_rank:.1f}")
    
    # Calculate final metrics
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    
    if total_questions > 0:
        print(f"\nTotal questions tested: {total_questions}")
        print(f"Rank #1 hits: {rank_1_hits} ({rank_1_hits/total_questions*100:.1f}%)")
        print(f"Top 3 hits: {rank_3_hits + rank_1_hits} ({(rank_3_hits + rank_1_hits)/total_questions*100:.1f}%)")
        print(f"Top 5 hits: {rank_5_hits + rank_3_hits + rank_1_hits} ({(rank_5_hits + rank_3_hits + rank_1_hits)/total_questions*100:.1f}%)")
        
        avg_rank = sum(all_ranks) / len(all_ranks)
        print(f"\nAverage rank: {avg_rank:.2f}")
        print(f"Median rank: {np.median(all_ranks):.0f}")
        
        # Quality assessment
        print("\n" + "=" * 80)
        print("QUALITY ASSESSMENT")
        print("=" * 80)
        
        rank_1_pct = rank_1_hits / total_questions * 100
        if rank_1_pct >= 80:
            print("✅ EXCELLENT: Embeddings are highly effective!")
        elif rank_1_pct >= 60:
            print("✓ GOOD: Embeddings work well but could be improved")
        elif rank_1_pct >= 40:
            print("⚠ FAIR: Embeddings need significant improvement")
        else:
            print("❌ POOR: Embeddings are not capturing semantic meaning properly")
        
        # Show worst performers
        if failed_questions:
            print("\n" + "=" * 80)
            print("WORST PERFORMING QUESTIONS (Rank > 5)")
            print("=" * 80)
            for fq in failed_questions[:5]:
                print(f"\nWorkflow: {fq['workflow']}")
                print(f"Question: {fq['question']}")
                print(f"Rank: #{fq['rank']} (Expected #1)")
                print(f"Top match was: {fq['top_match']}")
    else:
        print("No questions were tested!")

if __name__ == "__main__":
    run_reverse_engineering_test()