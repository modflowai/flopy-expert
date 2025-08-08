#!/usr/bin/env python3
"""
Batch process FloPy tests to generate examples
Can be run directly by Claude Code
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.review_tests import TestReviewCLI
import argparse

def main():
    parser = argparse.ArgumentParser(description='Batch process FloPy tests')
    parser.add_argument('--start', type=int, help='Starting test index (0-based)')
    parser.add_argument('--count', type=int, default=5, help='Number of tests to process')
    parser.add_argument('--validate-only', action='store_true', help='Only validate existing models')
    parser.add_argument('--list', action='store_true', help='List all tests')
    parser.add_argument('--status', action='store_true', help='Show processing status')
    
    args = parser.parse_args()
    
    cli = TestReviewCLI()
    
    if args.list:
        print("\nAvailable tests:")
        for i, test in enumerate(cli.test_files):
            status = "✓" if test.name in cli.status['completed'] else " "
            print(f"[{status}] {i:3d}. {test.name}")
        print(f"\nTotal: {len(cli.status['completed'])}/{len(cli.test_files)} completed")
        
    elif args.status:
        print(f"\nProcessing Status:")
        print(f"  Total tests: {len(cli.test_files)}")
        print(f"  Completed: {len(cli.status['completed'])}")
        print(f"  Skipped: {len(cli.status['skipped'])}")
        print(f"  Models created: {len(cli.status['models_created'])}")
        print(f"  Current index: {cli.status['current_index']}")
        
        if cli.status['models_created']:
            print(f"\nModels created:")
            for test, variants in cli.status['models_created'].items():
                print(f"  - {test}: {', '.join(variants) if variants else 'basic'}")
                
    elif args.validate_only:
        print("\nValidating all models...")
        results = cli.validate_all_models()
        
    else:
        # Batch process
        start_idx = args.start if args.start is not None else cli.status['current_index']
        cli.batch_process(start_idx, args.count)

if __name__ == "__main__":
    main()