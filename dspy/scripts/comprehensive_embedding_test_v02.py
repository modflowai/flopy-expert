#!/usr/bin/env python3
"""
Comprehensive FloPy Workflow Embeddings Test Suite v02
Tests the v02 ultra-discriminative embeddings and compares with v00 baseline
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

class EmbeddingTestSuiteV02:
    """Test suite for v02 embeddings with comparison to v00 baseline"""
    
    def __init__(self):
        self.conn = psycopg2.connect(config.NEON_CONNECTION_STRING)
        self.results = {
            'metadata': {},
            'workflow_results': [],
            'question_results': [],
            'category_analysis': {},
            'confusion_matrix': defaultdict(list),
            'summary_metrics': {},
            'version_comparison': {}
        }
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def fetch_workflows_v02(self, limit: Optional[int] = None) -> List[Dict]:
        """Fetch all FloPy workflows with v02 embeddings"""
        cur = self.conn.cursor()
        
        query = """
            SELECT 
                id,
                tutorial_file,
                analysis_v02,
                dspy_emb_02::text,
                analysis_v00,
                dspy_emb_00::text,
                source_repository
            FROM flopy_workflows 
            WHERE analysis_v02 IS NOT NULL 
            AND dspy_emb_02 IS NOT NULL
            AND analysis_v00 IS NOT NULL
            AND dspy_emb_00 IS NOT NULL
            AND source_repository = 'flopy'
            ORDER BY tutorial_file
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        cur.execute(query)
        
        workflows = []
        for row in cur.fetchall():
            # Parse the v02 vector string into array
            emb_str_v02 = row[3].strip('[]')
            embedding_v02 = np.array([float(x) for x in emb_str_v02.split(',')])
            
            # Parse the v00 vector string into array  
            emb_str_v00 = row[5].strip('[]')
            embedding_v00 = np.array([float(x) for x in emb_str_v00.split(',')])
            
            # Try to extract package from filename or title
            filename = Path(row[1]).name
            title_v02 = row[2].get('title', '')
            title_v00 = row[4].get('title', '')
            
            # Simple package detection from common patterns
            package = 'general'
            if 'wel' in filename.lower() or 'well' in title_v02.lower():
                package = 'WEL'
            elif 'chd' in filename.lower() or 'constant head' in title_v02.lower():
                package = 'CHD'
            elif 'dis' in filename.lower() or 'discretization' in title_v02.lower():
                package = 'DIS'
            elif 'npf' in filename.lower() or 'node property' in title_v02.lower():
                package = 'NPF'
            elif 'rch' in filename.lower() or 'recharge' in title_v02.lower():
                package = 'RCH'
            elif 'drn' in filename.lower() or 'drain' in title_v02.lower():
                package = 'DRN'
            elif 'sfr' in filename.lower() or 'stream' in title_v02.lower():
                package = 'SFR'
            elif 'lak' in filename.lower() or 'lake' in title_v02.lower():
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
                'analysis_v02': row[2],
                'embedding_v02': embedding_v02,
                'analysis_v00': row[4], 
                'embedding_v00': embedding_v00,
                'source_repository': row[6],
                'primary_package': package,
                'questions_v02': row[2].get('discriminative_questions', []),
                'questions_v00': row[4].get('potential_questions', []),
                'title_v02': title_v02,
                'title_v00': title_v00,
                'concepts_v02': row[2].get('technical_concepts_specific', []),
                'concepts_v00': row[4].get('key_concepts', [])
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
    
    def find_top_matches(self, query_emb: np.ndarray, workflows: List[Dict], embedding_version: str = 'v02', k: int = 10) -> List[Tuple]:
        """Find top k most similar workflows"""
        similarities = []
        embedding_key = f'embedding_{embedding_version}'
        
        for workflow in workflows:
            sim = self.calculate_similarity(query_emb, workflow[embedding_key])
            similarities.append({
                'workflow': workflow,
                'similarity': sim,
                'file': Path(workflow['tutorial_file']).name
            })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:k]
    
    def test_version(self, workflows: List[Dict], version: str = 'v02') -> Dict:
        """Test a specific embedding version"""
        print(f"\\n🔬 Testing {version.upper()} embeddings...")
        
        all_ranks = []
        question_count = 0
        workflow_scores = []
        
        questions_key = f'questions_{version}'
        embedding_key = f'embedding_{version}'
        
        for i, workflow in enumerate(workflows, 1):
            workflow_name = Path(workflow['tutorial_file']).name
            category = workflow.get('primary_package', 'unknown')
            
            # Progress indicator
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(workflows)} workflows tested...")
            
            workflow_ranks = []
            question_details = []
            
            for j, question in enumerate(workflow[questions_key]):
                question_emb = self.generate_embedding(question)
                if question_emb is None:
                    continue
                
                # Find top matches using the specified version
                top_matches = self.find_top_matches(question_emb, workflows, version, k=10)
                
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
        
        # Calculate summary metrics
        rank_1 = sum(1 for r in all_ranks if r == 1)
        rank_3 = sum(1 for r in all_ranks if r <= 3)
        rank_5 = sum(1 for r in all_ranks if r <= 5)
        rank_10 = sum(1 for r in all_ranks if r <= 10)
        
        return {
            'version': version,
            'workflow_scores': workflow_scores,
            'summary_metrics': {
                'total_questions_tested': question_count,
                'rank_1_accuracy': rank_1 / question_count * 100 if question_count > 0 else 0,
                'top_3_accuracy': rank_3 / question_count * 100 if question_count > 0 else 0,
                'top_5_accuracy': rank_5 / question_count * 100 if question_count > 0 else 0,
                'top_10_accuracy': rank_10 / question_count * 100 if question_count > 0 else 0,
                'mean_rank': np.mean(all_ranks) if all_ranks else 0,
                'median_rank': np.median(all_ranks) if all_ranks else 0,
                'std_rank': np.std(all_ranks) if all_ranks else 0
            }
        }
    
    def run_comprehensive_test(self):
        """Run the complete test suite comparing v00 and v02"""
        print("=" * 80)
        print("COMPREHENSIVE EMBEDDING COMPARISON TEST (v00 vs v02)")
        print("=" * 80)
        print(f"Timestamp: {self.timestamp}")
        
        # Phase 1: Setup
        print("\\n📊 Phase 1: Data Collection")
        print("-" * 40)
        workflows = self.fetch_workflows_v02()
        print(f"✓ Loaded {len(workflows)} FloPy workflows with both v00 and v02 embeddings")
        
        # Metadata
        self.results['metadata'] = {
            'test_version': 'v02_vs_v00_comparison',
            'timestamp': self.timestamp,
            'total_workflows': len(workflows),
            'v00_questions': sum(len(w['questions_v00']) for w in workflows),
            'v02_questions': sum(len(w['questions_v02']) for w in workflows),
            'test_description': 'Comparing ultra-discriminative v02 embeddings against v00 baseline'
        }
        
        # Phase 2: Test both versions
        print("\\n🔬 Phase 2: Testing Both Embedding Versions")
        print("-" * 40)
        
        # Test v00 (baseline)
        v00_results = self.test_version(workflows, 'v00')
        
        # Test v02 (ultra-discriminative)
        v02_results = self.test_version(workflows, 'v02')
        
        # Phase 3: Comparison Analysis
        print("\\n📈 Phase 3: Comparative Analysis")
        print("-" * 40)
        
        self.results['v00_results'] = v00_results
        self.results['v02_results'] = v02_results
        
        # Compare metrics
        v00_metrics = v00_results['summary_metrics']
        v02_metrics = v02_results['summary_metrics']
        
        self.results['version_comparison'] = {
            'rank_1_improvement': v02_metrics['rank_1_accuracy'] - v00_metrics['rank_1_accuracy'],
            'top_3_improvement': v02_metrics['top_3_accuracy'] - v00_metrics['top_3_accuracy'],
            'mean_rank_improvement': v00_metrics['mean_rank'] - v02_metrics['mean_rank'],  # Lower is better
            'v00_rank_1': v00_metrics['rank_1_accuracy'],
            'v02_rank_1': v02_metrics['rank_1_accuracy']
        }
        
        print("✓ Analysis complete")
        
    def generate_report(self):
        """Generate comprehensive comparison report"""
        print("\\n" + "=" * 80)
        print("EMBEDDING VERSION COMPARISON REPORT")
        print("=" * 80)
        
        v00_metrics = self.results['v00_results']['summary_metrics']
        v02_metrics = self.results['v02_results']['summary_metrics']
        comparison = self.results['version_comparison']
        
        # Executive Summary
        print("\\n📋 EXECUTIVE SUMMARY")
        print("-" * 40)
        print(f"Test Date: {self.results['metadata']['timestamp']}")
        print(f"Workflows Tested: {self.results['metadata']['total_workflows']}")
        print(f"v00 Questions Tested: {v00_metrics['total_questions_tested']}")
        print(f"v02 Questions Tested: {v02_metrics['total_questions_tested']}")
        
        # Performance Comparison
        print("\\n🏆 PERFORMANCE COMPARISON")
        print("-" * 40)
        print(f"{'Metric':<20} {'v00 Baseline':<15} {'v02 Ultra':<15} {'Improvement':<12}")
        print("-" * 62)
        print(f"{'Rank #1 Accuracy:':<20} {v00_metrics['rank_1_accuracy']:<15.1f} {v02_metrics['rank_1_accuracy']:<15.1f} {comparison['rank_1_improvement']:+.1f}%")
        print(f"{'Top 3 Accuracy:':<20} {v00_metrics['top_3_accuracy']:<15.1f} {v02_metrics['top_3_accuracy']:<15.1f} {comparison['top_3_improvement']:+.1f}%")
        print(f"{'Mean Rank:':<20} {v00_metrics['mean_rank']:<15.2f} {v02_metrics['mean_rank']:<15.2f} {comparison['mean_rank_improvement']:+.2f}")
        
        # Quality Assessment
        print("\\n🎯 IMPROVEMENT ASSESSMENT")
        print("-" * 40)
        improvement = comparison['rank_1_improvement']
        if improvement >= 10:
            assessment = "🚀 EXCELLENT: Major improvement achieved!"
        elif improvement >= 5:
            assessment = "✅ VERY GOOD: Significant improvement"
        elif improvement >= 2:
            assessment = "✓ GOOD: Meaningful improvement"
        elif improvement >= 0:
            assessment = "➡️ MINOR: Small improvement"
        else:
            assessment = "⚠️ REGRESSION: Performance declined"
        
        print(assessment)
        print(f"Overall improvement: {improvement:+.1f} percentage points")
        
        # Best Performers Comparison
        print("\\n🌟 TOP 5 MOST IMPROVED WORKFLOWS")
        print("-" * 40)
        
        v00_scores = {wf['file']: wf['success_rate'] for wf in self.results['v00_results']['workflow_scores']}
        v02_scores = {wf['file']: wf['success_rate'] for wf in self.results['v02_results']['workflow_scores']}
        
        improvements = []
        for file in v00_scores:
            if file in v02_scores:
                improvement = (v02_scores[file] - v00_scores[file]) * 100
                improvements.append({
                    'file': file,
                    'v00_rate': v00_scores[file] * 100,
                    'v02_rate': v02_scores[file] * 100,
                    'improvement': improvement
                })
        
        improvements.sort(key=lambda x: x['improvement'], reverse=True)
        for i, imp in enumerate(improvements[:5], 1):
            print(f"{i}. {imp['file'][:35]:<35} {imp['v00_rate']:.1f}% → {imp['v02_rate']:.1f}% ({imp['improvement']:+.1f}%)")
        
        # Recommendations
        print("\\n💡 RECOMMENDATIONS")
        print("-" * 40)
        if improvement >= 5:
            print("1. ✅ Ultra-discriminative prompting is highly effective!")
            print("2. 🚀 Deploy v02 embeddings to production")
            print("3. 📈 Consider applying similar techniques to other datasets")
        elif improvement >= 2:
            print("1. ✓ Good improvement achieved with v02 prompts")
            print("2. 🔍 Analyze top improved workflows for pattern insights")
            print("3. 🎯 Fine-tune prompts for remaining challenging workflows")
        else:
            print("1. ⚠️ Ultra-discriminative approach needs refinement")
            print("2. 🔍 Investigate why certain workflows didn't improve")
            print("3. 🎯 Consider hybrid approach or different prompt strategies")
    
    def export_results(self):
        """Export detailed results to files"""
        output_dir = Path("test_results")
        output_dir.mkdir(exist_ok=True)
        
        # Export complete results JSON
        json_file = output_dir / f"embedding_comparison_{self.timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\\n📁 Complete comparison results exported to: {json_file}")
    
    def close(self):
        """Clean up database connection"""
        self.conn.close()

def main():
    """Run the comprehensive comparison test suite"""
    tester = EmbeddingTestSuiteV02()
    
    try:
        tester.run_comprehensive_test()
        tester.generate_report()
        tester.export_results()
    finally:
        tester.close()
    
    print("\\n" + "=" * 80)
    print("COMPARISON TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()