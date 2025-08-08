#!/usr/bin/env python3
"""
Compare Test Versions - Track Embedding Improvements Over Time

This script compares multiple test results to show improvements in embedding quality.
"""

import json
from pathlib import Path
from datetime import datetime
import argparse

def load_test_results(results_dir="test_results"):
    """Load all test results from JSON files"""
    results = []
    results_path = Path(results_dir)
    
    if not results_path.exists():
        print(f"Results directory {results_dir} not found")
        return results
    
    for json_file in results_path.glob("embedding_test_*.json"):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                results.append({
                    'file': json_file.name,
                    'data': data
                })
        except Exception as e:
            print(f"Error loading {json_file}: {e}")
    
    return results

def compare_versions(results):
    """Compare different test versions"""
    if not results:
        print("No test results found to compare")
        return
    
    print("=" * 80)
    print("EMBEDDING TEST VERSION COMPARISON")
    print("=" * 80)
    
    # Sort by timestamp
    results.sort(key=lambda x: x['data']['metadata']['timestamp'])
    
    print(f"\nFound {len(results)} test versions:")
    print("-" * 80)
    
    for i, result in enumerate(results, 1):
        meta = result['data']['metadata']
        metrics = result['data']['summary_metrics']
        
        print(f"\n{i}. {meta.get('test_version', 'Unknown')}")
        print(f"   Prompt: {meta.get('prompt_version', 'Unknown')}")
        print(f"   Date: {meta.get('timestamp', 'Unknown')}")
        print(f"   Workflows: {meta.get('total_workflows', 'Unknown')}")
        print(f"   Rank #1: {metrics.get('rank_1_accuracy', 0):.1f}%")
        print(f"   Top 3: {metrics.get('top_3_accuracy', 0):.1f}%")
        print(f"   Mean Rank: {metrics.get('mean_rank', 0):.2f}")
        print(f"   Description: {meta.get('test_description', 'No description')}")
    
    if len(results) >= 2:
        print("\n" + "=" * 80)
        print("IMPROVEMENT ANALYSIS")
        print("=" * 80)
        
        baseline = results[0]['data']['summary_metrics']
        latest = results[-1]['data']['summary_metrics']
        
        rank1_change = latest['rank_1_accuracy'] - baseline['rank_1_accuracy']
        top3_change = latest['top_3_accuracy'] - baseline['top_3_accuracy']
        rank_change = latest['mean_rank'] - baseline['mean_rank']
        
        print(f"\nBaseline → Latest:")
        print(f"Rank #1: {baseline['rank_1_accuracy']:.1f}% → {latest['rank_1_accuracy']:.1f}% " +
              f"({rank1_change:+.1f}%)")
        print(f"Top 3: {baseline['top_3_accuracy']:.1f}% → {latest['top_3_accuracy']:.1f}% " +
              f"({top3_change:+.1f}%)")
        print(f"Mean Rank: {baseline['mean_rank']:.2f} → {latest['mean_rank']:.2f} " +
              f"({rank_change:+.2f})")
        
        # Assessment
        if rank1_change > 5:
            assessment = "🚀 SIGNIFICANT IMPROVEMENT"
        elif rank1_change > 1:
            assessment = "✅ GOOD IMPROVEMENT"
        elif rank1_change > -1:
            assessment = "➡️ MINOR CHANGE"
        else:
            assessment = "⚠️ PERFORMANCE DECLINE"
        
        print(f"\nOverall: {assessment}")

def generate_comparison_report(results):
    """Generate detailed comparison report"""
    if len(results) < 2:
        return
    
    print("\n" + "=" * 80)
    print("DETAILED CATEGORY COMPARISON")
    print("=" * 80)
    
    # Compare category performance
    baseline_cats = results[0]['data'].get('category_analysis', {})
    latest_cats = results[-1]['data'].get('category_analysis', {})
    
    all_categories = set(baseline_cats.keys()) | set(latest_cats.keys())
    
    print(f"\n{'Category':<15} {'Baseline':<12} {'Latest':<12} {'Change':<10}")
    print("-" * 55)
    
    for category in sorted(all_categories):
        baseline_acc = baseline_cats.get(category, {}).get('rank_1_accuracy', 0)
        latest_acc = latest_cats.get(category, {}).get('rank_1_accuracy', 0)
        change = latest_acc - baseline_acc
        
        if change > 0:
            change_str = f"+{change:.1f}%"
        else:
            change_str = f"{change:.1f}%"
        
        print(f"{category:<15} {baseline_acc:<12.1f} {latest_acc:<12.1f} {change_str:<10}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Compare embedding test versions')
    parser.add_argument('--results-dir', default='test_results', 
                       help='Directory containing test results')
    args = parser.parse_args()
    
    results = load_test_results(args.results_dir)
    
    if not results:
        print("No test results found. Run comprehensive_embedding_test.py first.")
        return
    
    compare_versions(results)
    generate_comparison_report(results)
    
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    
    if len(results) >= 2:
        latest_acc = results[-1]['data']['summary_metrics']['rank_1_accuracy']
        if latest_acc < 60:
            print("1. Consider implementing ultra-discriminative prompt")
            print("2. Focus on confused categories (MT3D vs MF6, SEAWAT)")
            print("3. Add explicit model type labeling")
        elif latest_acc < 70:
            print("1. Fine-tune prompts for worst-performing categories")
            print("2. Add package-specific differentiation")
            print("3. Test with more workflows")
        else:
            print("1. System is production-ready!")
            print("2. Scale to full workflow collection")
            print("3. Deploy for user testing")

if __name__ == "__main__":
    main()