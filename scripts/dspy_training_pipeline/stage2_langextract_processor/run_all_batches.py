#!/usr/bin/env python3
"""
Run all batches and combine results
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime
import time


def run_batch(batch_num, batch_size=10):
    """Run a single batch"""
    print(f"\n{'='*60}")
    print(f"Starting batch {batch_num}")
    print(f"{'='*60}")
    
    cmd = ["python3", "process_batch.py", "--batch", str(batch_num), "--size", str(batch_size)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error in batch {batch_num}:")
        print(result.stderr)
        return False
    else:
        print(result.stdout)
        return True


def combine_batches():
    """Combine all batch results into a single file"""
    batch_dir = Path("../data/extracted/batches")
    batch_files = sorted(batch_dir.glob("batch_*.json"))
    
    print(f"\nFound {len(batch_files)} batch files")
    
    all_results = []
    total_successful = 0
    total_failed = 0
    total_extractions = 0
    total_modules = 0
    
    for batch_file in batch_files:
        with open(batch_file, 'r') as f:
            batch_data = json.load(f)
        
        results = batch_data['results']
        all_results.extend(results)
        
        metadata = batch_data['metadata']
        total_successful += metadata['successful']
        total_failed += metadata['failed']
        
        # Calculate statistics
        for result in results:
            if 'error' not in result:
                metrics = result.get('quality_metrics', {})
                total_extractions += metrics.get('total_extractions', 0)
                total_modules += metrics.get('module_count', 0)
    
    # Save combined results
    output_file = Path("../data/extracted") / f"all_issues_combined_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    successful_results = [r for r in all_results if 'error' not in r]
    with_problems = sum(1 for r in successful_results if r['quality_metrics']['has_problem'])
    with_resolutions = sum(1 for r in successful_results if r['quality_metrics']['has_resolution'])
    
    combined_data = {
        'metadata': {
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'model': 'gemini-2.5-flash',
            'extraction_method': 'focused_comprehensive',
            'issues_processed': len(all_results),
            'successful': total_successful,
            'failed': total_failed,
            'batch_files_combined': len(batch_files)
        },
        'statistics': {
            'total_extractions': total_extractions,
            'total_modules_extracted': total_modules,
            'average_extractions_per_issue': round(total_extractions / total_successful, 2) if total_successful else 0,
            'average_modules_per_issue': round(total_modules / total_successful, 2) if total_successful else 0,
            'issues_with_problems': with_problems,
            'issues_with_resolutions': with_resolutions,
            'extraction_rate': f"{total_successful}/{len(all_results)} ({total_successful/len(all_results)*100:.1f}%)"
        },
        'results': all_results
    }
    
    with open(output_file, 'w') as f:
        json.dump(combined_data, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"ALL BATCHES COMBINED!")
    print(f"{'='*60}")
    print(f"Combined results saved to: {output_file}")
    print(f"\nFinal Summary:")
    print(f"  - Total issues: {len(all_results)}")
    print(f"  - Successful: {total_successful}")
    print(f"  - Failed: {total_failed}")
    print(f"  - Total extractions: {total_extractions}")
    print(f"  - Total modules: {total_modules}")
    print(f"  - Average per issue: {total_extractions/total_successful:.1f} extractions")
    print(f"\nQuality metrics:")
    print(f"  - With problems: {with_problems} ({with_problems/total_successful*100:.1f}%)")
    print(f"  - With resolutions: {with_resolutions} ({with_resolutions/total_successful*100:.1f}%)")


def main():
    # Calculate number of batches needed
    total_issues = 88
    batch_size = 10
    num_batches = (total_issues + batch_size - 1) // batch_size
    
    print(f"Processing {total_issues} issues in {num_batches} batches of {batch_size}")
    
    # Run each batch
    for batch_num in range(num_batches):
        success = run_batch(batch_num, batch_size)
        if not success:
            print(f"Failed at batch {batch_num}. Stopping.")
            return
        
        # Small delay between batches
        if batch_num < num_batches - 1:
            print(f"\nWaiting 5 seconds before next batch...")
            time.sleep(5)
    
    print("\n" + "="*60)
    print("All batches complete! Combining results...")
    print("="*60)
    
    # Combine all batch results
    combine_batches()


if __name__ == "__main__":
    main()