#!/usr/bin/env python3
"""
Comprehensive FloPy Workflow Embeddings Test Suite

A production-ready test that validates semantic search quality across all FloPy workflows.
Generates detailed reports showing strengths, weaknesses, and patterns in the embeddings.
"""

import json
import psycopg2
import numpy as np
from typing import List, Dict, Tuple, Optional
import openai
from pathlib import Path
import sys
import os
from datetime import datetime
import csv
from collections import defaultdict
import time

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
import config

# Initialize OpenAI
openai.api_key = config.OPENAI_API_KEY

class EmbeddingTestSuite:
    """Comprehensive test suite for FloPy workflow embeddings"""
    
    def __init__(self):
        self.conn = psycopg2.connect(config.NEON_CONNECTION_STRING)
        self.results = {
            'metadata': {},
            'workflow_results': [],
            'question_results': [],
            'category_analysis': {},
            'confusion_matrix': defaultdict(list),
            'summary_metrics': {}
        }
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def fetch_workflows(self, limit: Optional[int] = None) -> List[Dict]:
        """Fetch all FloPy workflows with embeddings"""
        cur = self.conn.cursor()
        
        query = """
            SELECT 
                id,
                tutorial_file,
                analysis_v00,
                dspy_emb_00::text,
                source_repository
            FROM flopy_workflows 
            WHERE analysis_v00 IS NOT NULL 
            AND dspy_emb_00 IS NOT NULL
            AND source_repository = 'flopy'
            ORDER BY tutorial_file
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        cur.execute(query)
        
        workflows = []
        for row in cur.fetchall():
            # Parse the vector string into array
            emb_str = row[3].strip('[]')
            embedding = np.array([float(x) for x in emb_str.split(',')])
            
            # Try to extract package from filename or title
            filename = Path(row[1]).name
            title = row[2].get('title', '')
            
            # Simple package detection from common patterns
            package = 'general'
            if 'wel' in filename.lower() or 'well' in title.lower():
                package = 'WEL'
            elif 'chd' in filename.lower() or 'constant head' in title.lower():
                package = 'CHD'
            elif 'dis' in filename.lower() or 'discretization' in title.lower():
                package = 'DIS'
            elif 'npf' in filename.lower() or 'node property' in title.lower():
                package = 'NPF'
            elif 'rch' in filename.lower() or 'recharge' in title.lower():
                package = 'RCH'
            elif 'drn' in filename.lower() or 'drain' in title.lower():
                package = 'DRN'
            elif 'sfr' in filename.lower() or 'stream' in title.lower():
                package = 'SFR'
            elif 'lak' in filename.lower() or 'lake' in title.lower():
                package = 'LAK'
            elif 'mf6' in filename.lower():
                package = 'MF6'
            elif 'export' in filename.lower():
                package = 'export'
            elif 'grid' in filename.lower():
                package = 'grid'
            
            workflows.append({
                'id': row[0],
                'tutorial_file': row[1],
                'analysis': row[2],
                'embedding': embedding,
                'source_repository': row[4],
                'primary_package': package,
                'questions': row[2].get('potential_questions', []),
                'title': row[2].get('title', ''),
                'concepts': row[2].get('key_concepts', [])
            })
        
        cur.close()
        return workflows
    
    def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for text with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = openai.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )
                return np.array(response.data[0].embedding)
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"    ⚠ Error embedding: {e}")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
        return None
    
    def calculate_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate cosine similarity between embeddings"""
        emb1_norm = emb1 / np.linalg.norm(emb1)
        emb2_norm = emb2 / np.linalg.norm(emb2)
        return np.dot(emb1_norm, emb2_norm)
    
    def find_top_matches(self, query_emb: np.ndarray, workflows: List[Dict], k: int = 10) -> List[Tuple]:
        """Find top k most similar workflows"""
        similarities = []
        
        for workflow in workflows:
            sim = self.calculate_similarity(query_emb, workflow['embedding'])
            similarities.append({
                'workflow': workflow,
                'similarity': sim,
                'file': Path(workflow['tutorial_file']).name
            })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:k]
    
    def analyze_category_patterns(self, workflows: List[Dict]) -> Dict:
        """Analyze performance patterns by workflow category"""
        category_stats = defaultdict(lambda: {
            'total_questions': 0,
            'rank_1_hits': 0,
            'rank_3_hits': 0,
            'rank_5_hits': 0,
            'avg_similarity': [],
            'workflows': set()
        })
        
        for workflow in workflows:
            category = workflow.get('primary_package', 'unknown')
            if category:
                category_stats[category]['workflows'].add(
                    Path(workflow['tutorial_file']).name
                )
        
        return category_stats
    
    def run_comprehensive_test(self):
        """Run the complete test suite"""
        print("=" * 80)
        print("COMPREHENSIVE FLOPY WORKFLOW EMBEDDINGS TEST")
        print("=" * 80)
        print(f"Timestamp: {self.timestamp}")
        
        # Phase 1: Setup
        print("\n📊 Phase 1: Data Collection")
        print("-" * 40)
        workflows = self.fetch_workflows()
        print(f"✓ Loaded {len(workflows)} FloPy workflows")
        
        # Metadata
        self.results['metadata'] = {
            'timestamp': self.timestamp,
            'total_workflows': len(workflows),
            'total_questions': sum(len(w['questions']) for w in workflows),
            'unique_packages': len(set(w['primary_package'] for w in workflows))
        }
        
        # Category analysis setup
        category_stats = self.analyze_category_patterns(workflows)
        
        # Phase 2: Testing
        print("\n🔬 Phase 2: Embedding Quality Testing")
        print("-" * 40)
        
        all_ranks = []
        question_count = 0
        workflow_scores = []
        
        print(f"Testing {len(workflows)} workflows...")
        
        for i, workflow in enumerate(workflows, 1):
            workflow_name = Path(workflow['tutorial_file']).name
            category = workflow.get('primary_package', 'unknown')
            
            # Progress indicator (less verbose)
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(workflows)} workflows tested...")
            
            workflow_ranks = []
            question_details = []
            
            for j, question in enumerate(workflow['questions']):
                question_emb = self.generate_embedding(question)
                if question_emb is None:
                    continue
                
                # Find top matches
                top_matches = self.find_top_matches(question_emb, workflows, k=10)
                
                # Find parent rank
                parent_rank = None
                parent_sim = None
                for rank, match in enumerate(top_matches, 1):
                    if match['workflow']['id'] == workflow['id']:
                        parent_rank = rank
                        parent_sim = match['similarity']
                        break
                
                if parent_rank is None:
                    parent_rank = 999  # Not in top 10
                    parent_sim = 0.0
                
                # Record results
                question_count += 1
                workflow_ranks.append(parent_rank)
                all_ranks.append(parent_rank)
                
                # Update category stats
                if category:
                    category_stats[category]['total_questions'] += 1
                    if parent_rank == 1:
                        category_stats[category]['rank_1_hits'] += 1
                    if parent_rank <= 3:
                        category_stats[category]['rank_3_hits'] += 1
                    if parent_rank <= 5:
                        category_stats[category]['rank_5_hits'] += 1
                    category_stats[category]['avg_similarity'].append(parent_sim)
                
                # Track confusion matrix (what got confused with what)
                if parent_rank > 1 and len(top_matches) > 0:
                    self.results['confusion_matrix'][workflow_name].append({
                        'question': question[:50],
                        'confused_with': top_matches[0]['file'],
                        'similarity_diff': top_matches[0]['similarity'] - parent_sim
                    })
                
                # Store detailed results
                question_details.append({
                    'question': question,
                    'rank': parent_rank,
                    'similarity': parent_sim,
                    'top_match': top_matches[0]['file'] if top_matches else 'N/A',
                    'top_match_sim': top_matches[0]['similarity'] if top_matches else 0
                })
            
            # Calculate workflow metrics
            if workflow_ranks:
                avg_rank = sum(workflow_ranks) / len(workflow_ranks)
                workflow_scores.append({
                    'file': workflow_name,
                    'category': category,
                    'avg_rank': avg_rank,
                    'perfect_hits': sum(1 for r in workflow_ranks if r == 1),
                    'total_questions': len(workflow_ranks),
                    'success_rate': sum(1 for r in workflow_ranks if r == 1) / len(workflow_ranks),
                    'questions': question_details
                })
        
        print(f"✓ Tested {question_count} questions across {len(workflows)} workflows")
        
        # Phase 3: Analysis
        print("\n📈 Phase 3: Statistical Analysis")
        print("-" * 40)
        
        # Calculate summary metrics
        rank_1 = sum(1 for r in all_ranks if r == 1)
        rank_3 = sum(1 for r in all_ranks if r <= 3)
        rank_5 = sum(1 for r in all_ranks if r <= 5)
        rank_10 = sum(1 for r in all_ranks if r <= 10)
        
        self.results['summary_metrics'] = {
            'total_questions_tested': question_count,
            'rank_1_accuracy': rank_1 / question_count * 100 if question_count > 0 else 0,
            'top_3_accuracy': rank_3 / question_count * 100 if question_count > 0 else 0,
            'top_5_accuracy': rank_5 / question_count * 100 if question_count > 0 else 0,
            'top_10_accuracy': rank_10 / question_count * 100 if question_count > 0 else 0,
            'mean_rank': np.mean(all_ranks) if all_ranks else 0,
            'median_rank': np.median(all_ranks) if all_ranks else 0,
            'std_rank': np.std(all_ranks) if all_ranks else 0
        }
        
        # Store results
        self.results['workflow_results'] = workflow_scores
        self.results['category_analysis'] = {
            cat: {
                'workflows': len(stats['workflows']),
                'questions': stats['total_questions'],
                'rank_1_accuracy': stats['rank_1_hits'] / stats['total_questions'] * 100 
                    if stats['total_questions'] > 0 else 0,
                'avg_similarity': np.mean(stats['avg_similarity']) 
                    if stats['avg_similarity'] else 0
            }
            for cat, stats in category_stats.items()
        }
        
        print("✓ Analysis complete")
        
    def generate_report(self):
        """Generate comprehensive report"""
        print("\n" + "=" * 80)
        print("FINAL REPORT")
        print("=" * 80)
        
        metrics = self.results['summary_metrics']
        
        # Executive Summary
        print("\n📋 EXECUTIVE SUMMARY")
        print("-" * 40)
        print(f"Total Workflows Tested: {self.results['metadata']['total_workflows']}")
        print(f"Total Questions Tested: {metrics['total_questions_tested']}")
        print(f"Unique Package Categories: {self.results['metadata']['unique_packages']}")
        
        # Performance Metrics
        print("\n🎯 ACCURACY METRICS")
        print("-" * 40)
        print(f"Rank #1 Accuracy: {metrics['rank_1_accuracy']:.1f}%")
        print(f"Top 3 Accuracy: {metrics['top_3_accuracy']:.1f}%")
        print(f"Top 5 Accuracy: {metrics['top_5_accuracy']:.1f}%")
        print(f"Top 10 Accuracy: {metrics['top_10_accuracy']:.1f}%")
        print(f"\nMean Rank: {metrics['mean_rank']:.2f}")
        print(f"Median Rank: {metrics['median_rank']:.1f}")
        print(f"Std Dev: {metrics['std_rank']:.2f}")
        
        # Quality Assessment
        print("\n🏆 QUALITY ASSESSMENT")
        print("-" * 40)
        rank_1_pct = metrics['rank_1_accuracy']
        if rank_1_pct >= 70:
            assessment = "✅ EXCELLENT: Production-ready embeddings!"
        elif rank_1_pct >= 50:
            assessment = "✓ GOOD: Embeddings work well, minor improvements possible"
        elif rank_1_pct >= 30:
            assessment = "⚠ FAIR: Embeddings need optimization"
        else:
            assessment = "❌ POOR: Major improvements required"
        print(assessment)
        
        # Category Performance
        print("\n📦 PERFORMANCE BY CATEGORY")
        print("-" * 40)
        category_analysis = self.results['category_analysis']
        sorted_cats = sorted(category_analysis.items(), 
                           key=lambda x: x[1]['rank_1_accuracy'], 
                           reverse=True)
        
        print(f"{'Category':<20} {'Workflows':<12} {'Questions':<12} {'Rank #1':<10}")
        print("-" * 54)
        for cat, stats in sorted_cats[:10]:  # Top 10 categories
            if stats['questions'] > 0:
                print(f"{cat:<20} {stats['workflows']:<12} {stats['questions']:<12} "
                      f"{stats['rank_1_accuracy']:.1f}%")
        
        # Best and Worst Performers
        print("\n🌟 TOP 5 BEST PERFORMING WORKFLOWS")
        print("-" * 40)
        sorted_workflows = sorted(self.results['workflow_results'], 
                                key=lambda x: x['success_rate'], 
                                reverse=True)
        for i, wf in enumerate(sorted_workflows[:5], 1):
            print(f"{i}. {wf['file'][:40]:<40} {wf['success_rate']*100:.1f}% "
                  f"(avg rank: {wf['avg_rank']:.1f})")
        
        print("\n⚠️  TOP 5 CHALLENGING WORKFLOWS")
        print("-" * 40)
        for i, wf in enumerate(sorted_workflows[-5:], 1):
            print(f"{i}. {wf['file'][:40]:<40} {wf['success_rate']*100:.1f}% "
                  f"(avg rank: {wf['avg_rank']:.1f})")
        
        # Common Confusions
        print("\n🔄 MOST COMMON CONFUSIONS")
        print("-" * 40)
        confusion_counts = defaultdict(int)
        for workflow, confusions in self.results['confusion_matrix'].items():
            for conf in confusions:
                pair = f"{workflow[:20]} ↔ {conf['confused_with'][:20]}"
                confusion_counts[pair] += 1
        
        top_confusions = sorted(confusion_counts.items(), key=lambda x: x[1], reverse=True)
        for pair, count in top_confusions[:5]:
            print(f"{pair}: {count} times")
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS")
        print("-" * 40)
        if rank_1_pct < 50:
            print("1. Review and improve prompts for workflows with < 50% success rate")
            print("2. Add more distinguishing keywords for commonly confused workflows")
            print("3. Consider category-specific embedding strategies")
        elif rank_1_pct < 70:
            print("1. Focus on improving bottom 20% of workflows")
            print("2. Enhance question diversity in prompts")
            print("3. Add package-specific technical terms")
        else:
            print("1. System is production-ready!")
            print("2. Monitor for edge cases in user queries")
            print("3. Consider A/B testing with users")
    
    def export_results(self):
        """Export detailed results to CSV files"""
        output_dir = Path("test_results")
        output_dir.mkdir(exist_ok=True)
        
        # Export workflow results (excluding 'questions' field)
        csv_file = output_dir / f"embedding_test_{self.timestamp}.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'file', 'category', 'avg_rank', 'perfect_hits', 
                'total_questions', 'success_rate'
            ])
            writer.writeheader()
            # Filter out 'questions' field for CSV
            csv_data = [{k: v for k, v in wf.items() if k != 'questions'} 
                       for wf in self.results['workflow_results']]
            writer.writerows(csv_data)
        
        print(f"\n📁 Detailed results exported to: {csv_file}")
        
        # Export summary JSON
        json_file = output_dir / f"embedding_test_{self.timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"📁 Complete results exported to: {json_file}")
    
    def close(self):
        """Clean up database connection"""
        self.conn.close()

def main():
    """Run the comprehensive test suite"""
    tester = EmbeddingTestSuite()
    
    try:
        tester.run_comprehensive_test()
        tester.generate_report()
        tester.export_results()
    finally:
        tester.close()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()