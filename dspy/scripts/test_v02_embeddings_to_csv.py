#!/usr/bin/env python3
"""
Test v02 embeddings using the SAME questions we generated for each workflow
Tests all 72 FloPy workflows with their 10 questions each (720 total)
Saves results to CSV for analysis - INCREMENTAL AND INTERACTIVE
"""

import sys
sys.path.append('/home/danilopezmella/flopy_expert')
import psycopg2
import numpy as np
import openai
import config
import csv
from datetime import datetime
import json
import os
from pathlib import Path

# Initialize OpenAI
openai.api_key = config.OPENAI_API_KEY

def calculate_similarity(emb1, emb2):
    """Calculate cosine similarity between two embeddings"""
    emb1_norm = emb1 / np.linalg.norm(emb1)
    emb2_norm = emb2 / np.linalg.norm(emb2)
    return np.dot(emb1_norm, emb2_norm)

def generate_embedding(text):
    """Generate embedding for a text using OpenAI"""
    try:
        response = openai.embeddings.create(
            model='text-embedding-3-small',
            input=text
        )
        return np.array(response.data[0].embedding)
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def load_checkpoint(checkpoint_file):
    """Load checkpoint to resume from previous run"""
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r') as f:
            checkpoint = json.load(f)
            print(f"📥 Loaded checkpoint: {checkpoint['workflows_completed']} workflows completed")
            return checkpoint
    return {'workflows_completed': [], 'results': []}

def save_checkpoint(checkpoint_file, checkpoint_data):
    """Save checkpoint for resuming"""
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)

def main():
    print("=" * 80)
    print("V02 EMBEDDINGS TEST - Interactive & Incremental")
    print("=" * 80)
    print()
    
    # Setup checkpoint
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    checkpoint_file = f"scripts/test_results/v02_checkpoint_{timestamp}.json"
    
    # Check for existing checkpoint
    existing_checkpoints = list(Path("scripts/test_results").glob("v02_checkpoint_*.json"))
    if existing_checkpoints:
        print("Found existing checkpoints:")
        for i, cp in enumerate(existing_checkpoints[-5:], 1):  # Show last 5
            print(f"  {i}. {cp.name}")
        
        choice = input("\nResume from checkpoint? (enter number or 'n' for new): ")
        if choice != 'n' and choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(existing_checkpoints[-5:]):
                checkpoint_file = str(existing_checkpoints[-5:][idx])
                timestamp = checkpoint_file.split('_')[-1].replace('.json', '')
    
    checkpoint = load_checkpoint(checkpoint_file)
    
    # Connect to database
    conn = psycopg2.connect(config.NEON_CONNECTION_STRING)
    cur = conn.cursor()
    
    # Get all 72 FloPy workflows with v02 embeddings and questions
    cur.execute("""
        SELECT 
            id,
            tutorial_file,
            analysis_v02,
            dspy_emb_02::text
        FROM flopy_workflows 
        WHERE source_repository = 'flopy'
        AND dspy_emb_02 IS NOT NULL
        AND analysis_v02 IS NOT NULL
        ORDER BY tutorial_file
    """)
    
    workflows = []
    for row in cur.fetchall():
        # Parse the embedding from string
        emb_str = row[3]
        emb_values = [float(x) for x in emb_str.strip('[]').split(',')]
        
        # Extract filename from path
        filename = row[1].split('/')[-1]
        
        # Extract questions from analysis JSON
        analysis = row[2]
        questions = analysis.get('discriminative_questions', [])
        
        workflows.append({
            'id': row[0],
            'file': filename,
            'full_path': row[1],
            'embedding': np.array(emb_values),
            'questions': questions
        })
    
    print(f"Loaded {len(workflows)} workflows")
    
    # Filter out already completed workflows
    completed_workflows = set(checkpoint.get('workflows_completed', []))
    workflows_to_process = [w for w in workflows if w['file'] not in completed_workflows]
    
    print(f"  Already completed: {len(completed_workflows)}")
    print(f"  To process: {len(workflows_to_process)}")
    
    if not workflows_to_process:
        print("\n✅ All workflows already processed!")
        return
    
    # Prepare CSV output
    csv_filename = f"scripts/test_results/v02_test_{timestamp}.csv"
    
    # Load existing results from checkpoint
    results = checkpoint.get('results', [])
    total_questions = len(results)
    correct_predictions = sum(1 for r in results if r['correct'])
    top3_correct = sum(1 for r in results if r['rank'] <= 3)
    top5_correct = sum(1 for r in results if r['rank'] <= 5)
    
    print(f"\n📊 Starting test (interactive mode)...")
    print("Press Ctrl+C to pause and save checkpoint")
    print("-" * 40)
    
    try:
        for i, workflow in enumerate(workflows_to_process, 1):
            workflow_name = workflow['file']
            questions = workflow['questions'][:10]  # Use the 10 questions we generated
            
            print(f"\n🔍 Workflow {i}/{len(workflows_to_process)}: {workflow_name}")
            print(f"   Questions: {len(questions)}")
            
            workflow_results = []
            
            for q_idx, question in enumerate(questions):
                if not question or len(question.strip()) < 10:
                    continue
                
                # Generate embedding for the question
                print(f"   Q{q_idx+1}: {question[:60]}...")
                question_emb = generate_embedding(question)
                if question_emb is None:
                    continue
                
                total_questions += 1
                
                # Calculate similarity with ALL workflows
                similarities = []
                for other_wf in workflows:
                    sim = calculate_similarity(question_emb, other_wf['embedding'])
                    similarities.append({
                        'workflow': other_wf['file'],
                        'similarity': sim
                    })
                
                # Sort by similarity
                similarities.sort(key=lambda x: x['similarity'], reverse=True)
                
                # Find rank of correct workflow
                rank = next(i for i, s in enumerate(similarities, 1) 
                           if s['workflow'] == workflow_name)
                
                # Get similarity with correct workflow
                correct_similarity = next(s['similarity'] for s in similarities 
                                         if s['workflow'] == workflow_name)
                
                # Interactive display
                symbol = "✅" if rank == 1 else "❌"
                print(f"      {symbol} Rank: #{rank:2d} | Similarity: {correct_similarity:.3f} | Top match: {similarities[0]['workflow'][:30]}")
                if rank > 1:
                    print(f"         Top similarity: {similarities[0]['similarity']:.3f} (diff: {similarities[0]['similarity'] - correct_similarity:.3f})")
                
                # Track accuracy
                if rank == 1:
                    correct_predictions += 1
                if rank <= 3:
                    top3_correct += 1
                if rank <= 5:
                    top5_correct += 1
                
                # Save result
                result = {
                    'workflow': workflow_name,
                    'question_idx': q_idx + 1,
                    'question': question[:100],  # Truncate for CSV
                    'rank': rank,
                    'similarity_with_correct': correct_similarity,
                    'similarity_with_top': similarities[0]['similarity'],
                    'top_match': similarities[0]['workflow'],
                    'correct': rank == 1
                }
                results.append(result)
                workflow_results.append(result)
            
            # Workflow summary
            wf_correct = sum(1 for r in workflow_results if r['correct'])
            print(f"   📊 Workflow accuracy: {wf_correct}/{len(workflow_results)} ({wf_correct/len(workflow_results)*100:.1f}%)")
            
            # Mark workflow as completed
            completed_workflows.add(workflow_name)
            
            # Save checkpoint after each workflow
            checkpoint_data = {
                'workflows_completed': list(completed_workflows),
                'results': results
            }
            save_checkpoint(checkpoint_file, checkpoint_data)
            
            # Running total display
            if total_questions > 0:
                current_accuracy = correct_predictions / total_questions * 100
                print(f"\n   🎯 Running Total: {current_accuracy:.1f}% accuracy ({correct_predictions}/{total_questions})")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted! Checkpoint saved.")
        print(f"   Completed: {len(completed_workflows)} workflows")
        print(f"   Checkpoint: {checkpoint_file}")
        print(f"   Resume with: python3 {__file__}")
        return
    
    # Calculate final metrics
    accuracy = correct_predictions / total_questions * 100
    top3_accuracy = top3_correct / total_questions * 100
    top5_accuracy = top5_correct / total_questions * 100
    mean_rank = sum(r['rank'] for r in results) / len(results)
    
    # Save to CSV
    with open(csv_filename, 'w', newline='') as f:
        fieldnames = ['workflow', 'question_idx', 'question', 
                     'rank', 'similarity_with_correct', 'similarity_with_top', 
                     'top_match', 'correct']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    print(f"Total workflows tested: {len(workflows)}")
    print(f"Total questions tested: {total_questions}")
    print(f"Questions per workflow: ~{total_questions/len(workflows):.1f}")
    print()
    print("ACCURACY METRICS:")
    print(f"  Rank #1 Accuracy: {accuracy:.1f}%")
    print(f"  Top 3 Accuracy:   {top3_accuracy:.1f}%")
    print(f"  Top 5 Accuracy:   {top5_accuracy:.1f}%")
    print(f"  Mean Rank:        {mean_rank:.2f}")
    print()
    print(f"Results saved to: {csv_filename}")
    
    # Also save summary as JSON
    summary = {
        'timestamp': timestamp,
        'total_workflows': len(workflows),
        'total_questions': total_questions,
        'rank_1_accuracy': accuracy,
        'top_3_accuracy': top3_accuracy,
        'top_5_accuracy': top5_accuracy,
        'mean_rank': mean_rank
    }
    
    json_filename = csv_filename.replace('.csv', '_summary.json')
    with open(json_filename, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Summary saved to: {json_filename}")
    
    conn.close()

if __name__ == "__main__":
    main()