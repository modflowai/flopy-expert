#!/usr/bin/env python3
"""
Test Claude SDK integration for a single test
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.claude_analyzer import analyze_test_with_claude, save_claude_result
from scripts.review_tests import TestReviewCLI

def test_single_test():
    """Test processing a single test with Claude SDK"""
    
    # Initialize CLI to get test files
    cli = TestReviewCLI()
    
    # Get the next unprocessed test
    test_file = None
    for tf in cli.test_files:
        if tf.name not in cli.status['completed'] and tf.name not in cli.status['skipped']:
            test_file = tf
            break
    
    if not test_file:
        print("No unprocessed tests found!")
        return False
    
    print(f"\n{'='*70}")
    print(f"Testing Claude SDK integration with: {test_file.name}")
    print(f"{'='*70}")
    
    # Create prompt
    prompt = cli.create_prompt_template(test_file)
    
    # Analyze with Claude SDK
    result = analyze_test_with_claude(test_file, prompt)
    
    if result:
        print("\n✅ Successfully got response from Claude!")
        
        # Check structure
        if "metadata" in result and "models" in result:
            print("✅ Response has correct structure")
            
            # Save and generate files
            success = save_claude_result(test_file.name, result)
            
            if success:
                print(f"\n✅ Successfully processed {test_file.name}")
                print(f"   - Metadata saved to: test_review/results/{test_file.stem}.json")
                print(f"   - Model saved to: test_review/models/{test_file.stem}/")
                
                # Show what was created
                model_dir = Path("test_review/models") / test_file.stem
                if model_dir.exists():
                    for variant_dir in model_dir.iterdir():
                        if variant_dir.is_dir():
                            print(f"   - Variant: {variant_dir.name}")
                            if (variant_dir / "model.py").exists():
                                print(f"     ✓ model.py created")
                            if (variant_dir / "test_results.json").exists():
                                print(f"     ✓ test passed")
                
                return True
            else:
                print("❌ Failed to save result")
        else:
            print("❌ Response missing required fields")
            print(f"Keys in response: {list(result.keys())}")
    else:
        print("❌ Failed to get response from Claude")
    
    return False

if __name__ == "__main__":
    # Set up API key if needed
    import os
    if not os.getenv("ANTHROPIC_API_KEY"):
        # Try to load from config
        try:
            import config
            os.environ["ANTHROPIC_API_KEY"] = config.ANTHROPIC_API_KEY
            print("✓ API key loaded from config")
        except:
            print("⚠️  No ANTHROPIC_API_KEY found")
            print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
            sys.exit(1)
    
    # Test with a single test
    success = test_single_test()
    
    if success:
        print("\n" + "="*70)
        print("✅ Claude SDK integration is working!")
        print("You can now process tests autonomously")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("❌ Claude SDK integration test failed")
        print("="*70)