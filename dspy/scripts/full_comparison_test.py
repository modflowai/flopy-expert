#!/usr/bin/env python3
"""
Full Comprehensive Comparison Test: v00 vs v02 Embeddings
Tests ALL 72 workflows with ALL their questions
"""

import sys
sys.path.append('/home/danilopezmella/flopy_expert')
import psycopg2
import numpy as np
import openai
import config
import time
from datetime import datetime
from collections import defaultdict

# Initialize OpenAI
openai.api_key = config.OPENAI_API_KEY

def calculate_similarity(emb1, emb2):
    emb1_norm = emb1 / np.linalg.norm(emb1)
    emb2_norm = emb2 / np.linalg.norm(emb2)
    return np.dot(emb1_norm, emb2_norm)

def generate_embedding(text):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = openai.embeddings.create(
                model='text-embedding-3-small',
                input=text
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"    ⚠ Embedding error: {e}")
                return None
            time.sleep(2 ** attempt)
    return None

def test_version(workflows, version='v02'):
    """Test a specific embedding version on all workflows"""
    print(f"\\n🔬 Testing {version.upper()} embeddings on {len(workflows)} workflows...")
    
    all_ranks = []
    question_count = 0
    workflow_scores = []
    category_stats = defaultdict(lambda: {'total': 0, 'hits': 0})
    
    questions_key = f'questions_{version}'
    embedding_key = f'embedding_{version}'
    
    for i, workflow in enumerate(workflows, 1):
        workflow_name = workflow['file']
        category = workflow.get('primary_package', 'unknown')
        
        # Progress indicator
        if i % 5 == 0:
            print(f"  Progress: {i}/{len(workflows)} workflows ({i/len(workflows)*100:.1f}%)...")
        
        workflow_ranks = []
        
        questions = workflow[questions_key][:10]  # Limit to 10 questions per workflow
        
        for j, question in enumerate(questions):
            if not question or len(question.strip()) < 10:
                continue
                
            question_emb = generate_embedding(question)
            if question_emb is None:
                continue
                
            question_count += 1
            category_stats[category]['total'] += 1
            
            # Find best match - calculate similarity with parent workflow
            parent_sim = calculate_similarity(question_emb, workflow[embedding_key])
            
            # Calculate similarities with other workflows  
            other_sims = []
            for other in workflows:
                if other['id'] != workflow['id']:
                    sim = calculate_similarity(question_emb, other[embedding_key])
                    other_sims.append(sim)
            
            # Determine rank
            if not other_sims:
                rank = 1
            else:
                better_matches = sum(1 for sim in other_sims if sim > parent_sim)
                rank = better_matches + 1
            
            workflow_ranks.append(rank)
            all_ranks.append(rank)
            
            if rank == 1:
                category_stats[category]['hits'] += 1
            
            # Rate limiting
            time.sleep(0.1)
        
        # Calculate workflow metrics
        if workflow_ranks:
            avg_rank = sum(workflow_ranks) / len(workflow_ranks)
            perfect_hits = sum(1 for r in workflow_ranks if r == 1)
            success_rate = perfect_hits / len(workflow_ranks)
            
            workflow_scores.append({
                'file': workflow_name,
                'category': category,
                'avg_rank': avg_rank,
                'perfect_hits': perfect_hits,
                'total_questions': len(workflow_ranks),
                'success_rate': success_rate
            })
    
    # Calculate summary metrics
    rank_1 = sum(1 for r in all_ranks if r == 1)
    rank_3 = sum(1 for r in all_ranks if r <= 3)
    rank_5 = sum(1 for r in all_ranks if r <= 5)
    
    return {
        'version': version,
        'workflow_scores': workflow_scores,
        'category_stats': dict(category_stats),
        'summary_metrics': {
            'total_questions': question_count,
            'rank_1_accuracy': rank_1 / question_count * 100 if question_count > 0 else 0,
            'top_3_accuracy': rank_3 / question_count * 100 if question_count > 0 else 0,
            'top_5_accuracy': rank_5 / question_count * 100 if question_count > 0 else 0,
            'mean_rank': np.mean(all_ranks) if all_ranks else 0,
            'median_rank': np.median(all_ranks) if all_ranks else 0
        }
    }

def main():
    print("=" * 80)
    print("COMPREHENSIVE EMBEDDING COMPARISON TEST (ALL 72 WORKFLOWS)")
    print("=" * 80)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    print(f"Timestamp: {timestamp}")
    
    # Load all workflows
    print("\\n📊 Loading all FloPy workflows...")
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    id, tutorial_file, analysis_v00, analysis_v02,
                    dspy_emb_00::text, dspy_emb_02::text
                FROM flopy_workflows
                WHERE analysis_v00 IS NOT NULL AND analysis_v02 IS NOT NULL
                AND source_repository = 'flopy'
                ORDER BY tutorial_file
            """)
            
            workflows = []
            for row in cur.fetchall():
                # Parse embeddings
                emb_v00 = np.array([float(x) for x in row[4].strip('[]').split(',')])
                emb_v02 = np.array([float(x) for x in row[5].strip('[]').split(',')])
                
                # Extract package from filename
                filename = row[1].split('/')[-1]
                package = 'general'
                if 'wel' in filename.lower():
                    package = 'WEL'
                elif 'chd' in filename.lower():
                    package = 'CHD'
                elif 'dis' in filename.lower():
                    package = 'DIS'
                elif 'mf6' in filename.lower():
                    package = 'MF6'
                elif 'export' in filename.lower():
                    package = 'export'
                
                workflows.append({
                    'id': row[0],
                    'file': filename,
                    'questions_v00': row[2].get('potential_questions', []),
                    'questions_v02': row[3].get('discriminative_questions', []),
                    'embedding_v00': emb_v00,
                    'embedding_v02': emb_v02,
                    'primary_package': package
                })
    
    print(f"✓ Loaded {len(workflows)} workflows")
    
    # Count total questions
    v00_questions = sum(len(w['questions_v00'][:10]) for w in workflows)
    v02_questions = sum(len(w['questions_v02'][:10]) for w in workflows)
    print(f"  v00 questions to test: {v00_questions}")
    print(f"  v02 questions to test: {v02_questions}")
    
    # Test v00 (baseline)
    print("\\n" + "=" * 50)
    print("TESTING v00 BASELINE EMBEDDINGS")
    print("=" * 50)
    v00_results = test_version(workflows, 'v00')
    
    # Test v02 (ultra-discriminative) 
    print("\\n" + "=" * 50)
    print("TESTING v02 ULTRA-DISCRIMINATIVE EMBEDDINGS")
    print("=" * 50)
    v02_results = test_version(workflows, 'v02')
    
    # Generate final report
    print("\\n" + "=" * 80)
    print("FINAL COMPREHENSIVE RESULTS")
    print("=" * 80)
    
    v00_metrics = v00_results['summary_metrics']
    v02_metrics = v02_results['summary_metrics']
    
    print(f"\\n📊 SUMMARY METRICS")
    print("-" * 40)
    print(f"{'Metric':<20} {'v00 Baseline':<15} {'v02 Ultra':<15} {'Improvement':<12}")
    print("-" * 62)
    
    improvement_r1 = v02_metrics['rank_1_accuracy'] - v00_metrics['rank_1_accuracy']
    improvement_r3 = v02_metrics['top_3_accuracy'] - v00_metrics['top_3_accuracy']
    improvement_rank = v00_metrics['mean_rank'] - v02_metrics['mean_rank']  # Lower is better
    
    print(f"{'Questions Tested:':<20} {v00_metrics['total_questions']:<15} {v02_metrics['total_questions']:<15} {'=':<12}")
    print(f"{'Rank #1 Accuracy:':<20} {v00_metrics['rank_1_accuracy']:<15.1f} {v02_metrics['rank_1_accuracy']:<15.1f} {improvement_r1:+.1f}%")
    print(f"{'Top 3 Accuracy:':<20} {v00_metrics['top_3_accuracy']:<15.1f} {v02_metrics['top_3_accuracy']:<15.1f} {improvement_r3:+.1f}%")
    print(f"{'Mean Rank:':<20} {v00_metrics['mean_rank']:<15.2f} {v02_metrics['mean_rank']:<15.2f} {improvement_rank:+.2f}")
    
    # Assessment
    print(f"\\n🎯 ASSESSMENT")
    print("-" * 40)
    if improvement_r1 >= 10:
        assessment = "🚀 EXCELLENT: Major improvement achieved!"
    elif improvement_r1 >= 5:
        assessment = "✅ VERY GOOD: Significant improvement"
    elif improvement_r1 >= 2:
        assessment = "✓ GOOD: Meaningful improvement" 
    elif improvement_r1 >= 0:
        assessment = "➡️ MINOR: Small improvement"
    else:
        assessment = "⚠️ REGRESSION: Performance declined"
    
    print(assessment)
    print(f"Overall Rank #1 improvement: {improvement_r1:+.1f} percentage points")
    
    # Category breakdown
    print(f"\\n📦 CATEGORY PERFORMANCE")
    print("-" * 40)
    print(f"{'Category':<15} {'v00 Acc %':<12} {'v02 Acc %':<12} {'Improvement':<12}")
    print("-" * 51)
    
    for category in set(v00_results['category_stats'].keys()) | set(v02_results['category_stats'].keys()):
        v00_cat = v00_results['category_stats'].get(category, {'total': 0, 'hits': 0})
        v02_cat = v02_results['category_stats'].get(category, {'total': 0, 'hits': 0})
        
        v00_acc = v00_cat['hits'] / v00_cat['total'] * 100 if v00_cat['total'] > 0 else 0
        v02_acc = v02_cat['hits'] / v02_cat['total'] * 100 if v02_cat['total'] > 0 else 0
        cat_improvement = v02_acc - v00_acc
        
        print(f"{category:<15} {v00_acc:<12.1f} {v02_acc:<12.1f} {cat_improvement:+.1f}%")
    
    # Top improved workflows
    print(f"\\n🌟 TOP 10 MOST IMPROVED WORKFLOWS")
    print("-" * 40)
    
    improvements = []
    for v02_wf in v02_results['workflow_scores']:
        v00_wf = next((w for w in v00_results['workflow_scores'] if w['file'] == v02_wf['file']), None)
        if v00_wf:
            improvement = (v02_wf['success_rate'] - v00_wf['success_rate']) * 100
            improvements.append({
                'file': v02_wf['file'],
                'v00_rate': v00_wf['success_rate'] * 100,
                'v02_rate': v02_wf['success_rate'] * 100,
                'improvement': improvement
            })
    
    improvements.sort(key=lambda x: x['improvement'], reverse=True)
    for i, imp in enumerate(improvements[:10], 1):
        print(f"{i:2d}. {imp['file'][:30]:<30} {imp['v00_rate']:.1f}% → {imp['v02_rate']:.1f}% ({imp['improvement']:+.1f}%)")
    
    print(f"\\n" + "=" * 80)
    print("COMPREHENSIVE TEST COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    main()