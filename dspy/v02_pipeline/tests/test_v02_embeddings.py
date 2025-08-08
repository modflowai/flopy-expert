#!/usr/bin/env python3
"""
Unified Testing Framework for V02 Embeddings
Tests the quality and performance of v02 embeddings vs baselines
"""

import sys
sys.path.append('/home/danilopezmella/flopy_expert')
sys.path.append('/home/danilopezmella/flopy_expert/dspy')

import psycopg2
import numpy as np
import openai
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
import logging

import config as main_config
from v02_pipeline.config import pipeline_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class V02EmbeddingTester:
    """Test framework for v02 embeddings"""
    
    def __init__(self, repository: str = "flopy"):
        """
        Initialize tester
        
        Args:
            repository: Which repository to test ('flopy', 'modflow6-examples', 'pyemu')
        """
        self.repository = repository
        self.repo_config = pipeline_config.get_table_config(repository)
        self.conn = psycopg2.connect(main_config.NEON_CONNECTION_STRING)
        self.cur = self.conn.cursor()
        
        # Initialize OpenAI for query embeddings
        openai.api_key = main_config.OPENAI_API_KEY
        self.embedding_model = pipeline_config.EMBEDDING_MODEL
        
        # Results storage
        self.test_results = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_dir = Path("v02_pipeline/test_results")
        self.results_dir.mkdir(exist_ok=True, parents=True)
    
    def load_workflows_with_embeddings(self) -> Tuple[List[Dict], List[Dict]]:
        """Load workflows with both baseline and v02 embeddings"""
        
        # Determine columns based on repository
        if self.repository == "pyemu":
            baseline_col = "embedding"
            analysis_col = "workflow_purpose"
            id_col = "notebook_file"
            title_col = "title"
        else:
            baseline_col = pipeline_config.get_column_name('baseline_embedding')
            analysis_col = f"{pipeline_config.get_column_name('analysis')}->>'discriminative_questions'"
            id_col = "tutorial_file"
            title_col = "title"
        
        v02_emb_col = pipeline_config.get_column_name('embedding')
        
        # Build query
        filter_clause = f"WHERE {self.repo_config['filter']}" if self.repo_config.get('filter') else ""
        
        query = f"""
            SELECT 
                id,
                {id_col} as file,
                {title_col} as title,
                {baseline_col}::text as baseline_emb,
                {v02_emb_col}::text as v02_emb,
                {analysis_col} as questions
            FROM {self.repo_config['table']}
            {filter_clause}
            {"AND" if filter_clause else "WHERE"} {baseline_col} IS NOT NULL 
            AND {v02_emb_col} IS NOT NULL
            ORDER BY {id_col}
        """
        
        self.cur.execute(query)
        workflows = []
        
        for row in self.cur.fetchall():
            # Parse embeddings
            baseline_emb = self._parse_embedding(row[3])
            v02_emb = self._parse_embedding(row[4])
            
            # Parse questions
            questions = []
            if row[5]:
                if isinstance(row[5], str):
                    try:
                        questions = json.loads(row[5])
                    except:
                        questions = []
                elif isinstance(row[5], list):
                    questions = row[5]
            
            workflows.append({
                'id': row[0],
                'file': row[1],
                'title': row[2],
                'baseline_embedding': baseline_emb,
                'v02_embedding': v02_emb,
                'questions': questions[:10]  # Limit to 10
            })
        
        logger.info(f"Loaded {len(workflows)} workflows with both embeddings")
        return workflows
    
    def _parse_embedding(self, emb_str: str) -> np.ndarray:
        """Parse embedding string to numpy array"""
        if emb_str.startswith('['):
            values = [float(x) for x in emb_str.strip('[]').split(',')]
        else:
            values = [float(x) for x in emb_str.split(',')]
        return np.array(values)
    
    def generate_query_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a query"""
        try:
            response = openai.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def calculate_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate cosine similarity"""
        emb1_norm = emb1 / np.linalg.norm(emb1)
        emb2_norm = emb2 / np.linalg.norm(emb2)
        return float(np.dot(emb1_norm, emb2_norm))
    
    def test_workflow_questions(self, workflows: List[Dict]) -> Dict[str, Any]:
        """Test workflows using their generated questions"""
        
        baseline_ranks = []
        v02_ranks = []
        improvements = []
        
        total_questions = 0
        baseline_correct = 0
        v02_correct = 0
        
        for i, workflow in enumerate(workflows, 1):
            if not workflow['questions']:
                continue
            
            logger.info(f"[{i}/{len(workflows)}] Testing {workflow['file']}")
            
            for question in workflow['questions'][:5]:  # Test first 5 questions
                if not question or len(question) < 10:
                    continue
                
                # Generate query embedding
                query_emb = self.generate_query_embedding(question)
                if query_emb is None:
                    continue
                
                total_questions += 1
                
                # Calculate similarities for all workflows
                baseline_sims = []
                v02_sims = []
                
                for other in workflows:
                    baseline_sim = self.calculate_similarity(query_emb, other['baseline_embedding'])
                    v02_sim = self.calculate_similarity(query_emb, other['v02_embedding'])
                    
                    baseline_sims.append((other['file'], baseline_sim))
                    v02_sims.append((other['file'], v02_sim))
                
                # Sort by similarity
                baseline_sims.sort(key=lambda x: x[1], reverse=True)
                v02_sims.sort(key=lambda x: x[1], reverse=True)
                
                # Find ranks
                baseline_rank = next(i for i, (f, _) in enumerate(baseline_sims, 1) 
                                   if f == workflow['file'])
                v02_rank = next(i for i, (f, _) in enumerate(v02_sims, 1) 
                               if f == workflow['file'])
                
                baseline_ranks.append(baseline_rank)
                v02_ranks.append(v02_rank)
                improvements.append(baseline_rank - v02_rank)
                
                if baseline_rank == 1:
                    baseline_correct += 1
                if v02_rank == 1:
                    v02_correct += 1
                
                # Store detailed result
                self.test_results.append({
                    'workflow': workflow['file'],
                    'question': question[:100],
                    'baseline_rank': baseline_rank,
                    'v02_rank': v02_rank,
                    'improvement': baseline_rank - v02_rank,
                    'baseline_top_match': baseline_sims[0][0],
                    'v02_top_match': v02_sims[0][0]
                })
        
        # Calculate metrics
        results = {
            'repository': self.repository,
            'total_workflows': len(workflows),
            'total_questions': total_questions,
            'baseline': {
                'rank_1_accuracy': baseline_correct / total_questions * 100 if total_questions > 0 else 0,
                'mean_rank': np.mean(baseline_ranks) if baseline_ranks else 0,
                'median_rank': np.median(baseline_ranks) if baseline_ranks else 0,
                'top_3_accuracy': sum(1 for r in baseline_ranks if r <= 3) / len(baseline_ranks) * 100 if baseline_ranks else 0
            },
            'v02': {
                'rank_1_accuracy': v02_correct / total_questions * 100 if total_questions > 0 else 0,
                'mean_rank': np.mean(v02_ranks) if v02_ranks else 0,
                'median_rank': np.median(v02_ranks) if v02_ranks else 0,
                'top_3_accuracy': sum(1 for r in v02_ranks if r <= 3) / len(v02_ranks) * 100 if v02_ranks else 0
            },
            'improvement': {
                'rank_1_accuracy_gain': (v02_correct - baseline_correct) / total_questions * 100 if total_questions > 0 else 0,
                'mean_rank_improvement': np.mean(baseline_ranks) - np.mean(v02_ranks) if baseline_ranks else 0,
                'improved_queries': sum(1 for imp in improvements if imp > 0),
                'degraded_queries': sum(1 for imp in improvements if imp < 0)
            }
        }
        
        return results
    
    def save_results(self, results: Dict[str, Any]):
        """Save test results to files"""
        
        # Save summary JSON
        json_file = self.results_dir / f"{self.repository}_v02_test_{self.timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump({
                'summary': results,
                'detailed_results': self.test_results
            }, f, indent=2, default=str)
        
        # Save detailed CSV
        csv_file = self.results_dir / f"{self.repository}_v02_test_{self.timestamp}.csv"
        with open(csv_file, 'w', newline='') as f:
            if self.test_results:
                fieldnames = list(self.test_results[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.test_results)
        
        logger.info(f"Results saved to:")
        logger.info(f"  JSON: {json_file}")
        logger.info(f"  CSV: {csv_file}")
    
    def print_summary(self, results: Dict[str, Any]):
        """Print results summary"""
        
        print("\n" + "=" * 80)
        print(f"V02 EMBEDDING TEST RESULTS - {self.repository.upper()}")
        print("=" * 80)
        
        print(f"\nDataset: {results['total_workflows']} workflows, {results['total_questions']} questions")
        
        print("\nBASELINE PERFORMANCE:")
        baseline = results['baseline']
        print(f"  Rank #1 Accuracy: {baseline['rank_1_accuracy']:.1f}%")
        print(f"  Top 3 Accuracy: {baseline['top_3_accuracy']:.1f}%")
        print(f"  Mean Rank: {baseline['mean_rank']:.2f}")
        print(f"  Median Rank: {baseline['median_rank']:.1f}")
        
        print("\nV02 PERFORMANCE:")
        v02 = results['v02']
        print(f"  Rank #1 Accuracy: {v02['rank_1_accuracy']:.1f}%")
        print(f"  Top 3 Accuracy: {v02['top_3_accuracy']:.1f}%")
        print(f"  Mean Rank: {v02['mean_rank']:.2f}")
        print(f"  Median Rank: {v02['median_rank']:.1f}")
        
        print("\nIMPROVEMENT:")
        imp = results['improvement']
        print(f"  Rank #1 Accuracy Gain: {imp['rank_1_accuracy_gain']:+.1f} percentage points")
        print(f"  Mean Rank Improvement: {imp['mean_rank_improvement']:+.2f}")
        print(f"  Improved Queries: {imp['improved_queries']}")
        print(f"  Degraded Queries: {imp['degraded_queries']}")
        
        # Assessment
        if imp['rank_1_accuracy_gain'] > 10:
            print("\n🚀 EXCELLENT improvement achieved!")
        elif imp['rank_1_accuracy_gain'] > 5:
            print("\n✅ Good improvement achieved!")
        elif imp['rank_1_accuracy_gain'] > 0:
            print("\n📈 Modest improvement achieved.")
        else:
            print("\n⚠️ No improvement or regression detected.")
    
    def run_test(self):
        """Run the complete test"""
        try:
            # Load workflows
            workflows = self.load_workflows_with_embeddings()
            
            if not workflows:
                logger.error(f"No workflows found with both embeddings for {self.repository}")
                return
            
            # Run tests
            results = self.test_workflow_questions(workflows)
            
            # Save results
            self.save_results(results)
            
            # Print summary
            self.print_summary(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Test failed: {e}", exc_info=True)
            raise
        finally:
            self.cur.close()
            self.conn.close()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test V02 Embeddings")
    parser.add_argument(
        "--repository",
        choices=["flopy", "modflow6-examples", "pyemu"],
        default="flopy",
        help="Which repository to test"
    )
    
    args = parser.parse_args()
    
    tester = V02EmbeddingTester(repository=args.repository)
    tester.run_test()

if __name__ == "__main__":
    main()