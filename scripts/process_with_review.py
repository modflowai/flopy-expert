#!/usr/bin/env python3
"""
Process FloPy tests with automatic review and quality checks
"""

import sys
import subprocess
from pathlib import Path

def run_command(cmd):
    """Run a command and return success status"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode == 0

def process_one_with_review():
    """Process one test with review"""
    
    print("\n" + "="*70)
    print("PROCESSING NEXT TEST WITH REVIEW")
    print("="*70)
    
    # Process next test
    print("\n1. Processing next test...")
    if not run_command("python3 scripts/claude_code_integration.py --next"):
        print("❌ Failed to process test")
        return False
    
    # Review the result
    print("\n2. Reviewing result...")
    run_command("python3 scripts/claude_code_integration.py --review")
    
    # Ask user what to do
    print("\n3. What would you like to do?")
    print("   [a] Approve and continue")
    print("   [r] Redo this test")
    print("   [s] Skip this test")
    print("   [q] Quit")
    
    choice = input("\nChoice: ").lower().strip()
    
    if choice == 'r':
        # Get last test name from status
        import json
        with open("test_review/status.json") as f:
            status = json.load(f)
        last_test = status['completed'][-1] if status['completed'] else None
        
        if last_test:
            print(f"\nRedoing {last_test}...")
            run_command(f"python3 scripts/claude_code_integration.py --redo {last_test}")
            print("\nReview after redo:")
            run_command("python3 scripts/claude_code_integration.py --review")
    
    elif choice == 's':
        # Skip last test
        import json
        with open("test_review/status.json") as f:
            status = json.load(f)
        last_test = status['completed'][-1] if status['completed'] else None
        
        if last_test:
            print(f"\nSkipping {last_test}...")
            run_command(f"python3 scripts/claude_code_integration.py --skip {last_test}")
    
    elif choice == 'q':
        print("\nQuitting...")
        return False
    
    # Default is approve (or 'a')
    return True

def main():
    """Main processing loop with review"""
    
    print("FloPy Test Processing with Review")
    print("="*70)
    
    while True:
        if not process_one_with_review():
            break
        
        print("\n" + "-"*70)
        cont = input("\nContinue with next test? [y/n]: ").lower().strip()
        if cont != 'y':
            break
    
    # Show final status
    import json
    with open("test_review/status.json") as f:
        status = json.load(f)
    
    print("\n" + "="*70)
    print("FINAL STATUS")
    print("="*70)
    print(f"Completed: {len(status['completed'])}/{status['total_tests']}")
    print(f"Skipped: {len(status['skipped'])}")
    print(f"Models created: {len(status['models_created'])}")

if __name__ == "__main__":
    main()