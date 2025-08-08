#!/usr/bin/env python3
"""
FloPy test analyzer using claude-code-sdk
Uses your logged Claude session - no API key needed!
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Optional
import sys

from claude_code_sdk import query, ClaudeCodeOptions, Message

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from scripts.review_tests import TestReviewCLI

async def analyze_test_async(test_file: Path, prompt_template: str) -> Optional[Dict]:
    """
    Analyze a test file using claude-code-sdk
    """
    print(f"\nAnalyzing: {test_file.name}")
    print("="*60)
    
    # Read test file
    with open(test_file) as f:
        test_code = f.read()
    
    # Truncate if too long
    if len(test_code) > 10000:
        test_code = test_code[:10000] + "\n... [truncated]"
    
    # Add test code to prompt
    full_prompt = prompt_template.replace(
        "```python\n{test_code[:3000]}...  # Truncated for brevity\n```",
        f"```python\n{test_code}\n```"
    )
    
    # Add instruction to return only JSON
    full_prompt += "\n\nIMPORTANT: Return ONLY the JSON object, no markdown formatting or other text."
    
    # Configure Claude Code options
    options = ClaudeCodeOptions(
        max_turns=1,  # We only need one response
        system_prompt="You are an expert at analyzing FloPy tests and generating standalone models.",
        cwd=Path("/home/danilopezmella/flopy_expert"),
        allowed_tools=[],  # No tools needed for analysis
        permission_mode="default"  # Use default permission mode
    )
    
    print("Calling Claude Code SDK...")
    messages = []
    
    try:
        async for message in query(prompt=full_prompt, options=options):
            messages.append(message)
        
        if messages:
            # Get the last message content
            last_message = messages[-1]
            
            # Extract the result from ResultMessage
            if hasattr(last_message, 'result'):
                response_text = last_message.result
            else:
                response_text = str(last_message)
            
            # Parse JSON from response
            try:
                # Remove markdown if present
                if "```json" in response_text:
                    import re
                    json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
                    if json_match:
                        response_text = json_match.group(1)
                
                result = json.loads(response_text)
                print("✓ Successfully parsed Claude's response")
                return result
                
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON: {e}")
                
                # Save raw response for debugging
                debug_dir = Path("test_review/debug")
                debug_dir.mkdir(exist_ok=True)
                debug_file = debug_dir / f"{test_file.stem}_raw.txt"
                debug_file.write_text(response_text)
                print(f"Raw response saved to {debug_file}")
                
                # Try to extract JSON
                import re
                json_pattern = r'\{[\s\S]*\}'
                matches = re.findall(json_pattern, response_text)
                if matches:
                    for match in sorted(matches, key=len, reverse=True):
                        try:
                            result = json.loads(match)
                            print("✓ Extracted JSON from response")
                            return result
                        except:
                            continue
                
                return None
        else:
            print("No response from Claude")
            return None
            
    except Exception as e:
        print(f"Error calling Claude Code SDK: {e}")
        return None

def analyze_test(test_file: Path, prompt_template: str) -> Optional[Dict]:
    """
    Synchronous wrapper for async analyze function
    """
    return asyncio.run(analyze_test_async(test_file, prompt_template))

def process_next_test() -> bool:
    """
    Process the next unprocessed test file
    """
    cli = TestReviewCLI()
    
    # Find next unprocessed test
    test_file = None
    for tf in cli.test_files:
        if tf.name not in cli.status['completed'] and tf.name not in cli.status['skipped']:
            test_file = tf
            break
    
    if not test_file:
        print("No unprocessed tests found!")
        return False
    
    print(f"\n{'='*70}")
    print(f"Processing: {test_file.name}")
    print(f"{'='*70}")
    
    # Create prompt
    prompt = cli.create_prompt_template(test_file)
    
    # Analyze with Claude Code SDK
    result = analyze_test(test_file, prompt)
    
    if result:
        print("\n✅ Successfully got response from Claude!")
        
        # Check structure
        if "metadata" in result and "models" in result:
            print("✅ Response has correct structure")
            
            # Save result
            result_file = cli.results_dir / f"{test_file.stem}.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"✅ Saved to {result_file}")
            
            # Generate model files
            cli.generate_model_files(test_file, result)
            
            # Update status
            cli.status['completed'].append(test_file.name)
            if 'models' in result:
                variants = [m.get('variant', 'basic') for m in result['models']]
                cli.status['models_created'][test_file.name] = variants
            cli.status['current_index'] += 1
            cli.save_status()
            
            print(f"\n✅ Successfully processed {test_file.name}")
            print(f"   - Metadata saved to: test_review/results/{test_file.stem}.json")
            print(f"   - Model saved to: test_review/models/{test_file.stem}/")
            
            # Show what was created
            model_dir = Path("test_review/models") / test_file.stem
            if model_dir.exists():
                for variant_dir in model_dir.iterdir():
                    if variant_dir.is_dir():
                        print(f"   - Variant: {variant_dir.name}")
                        model_file = variant_dir / "model.py"
                        if model_file.exists():
                            print(f"     ✓ model.py created")
                            
                            # Test the model
                            print(f"     Testing model...")
                            test_result = cli.test_model(model_file, variant_dir)
                            if test_result["runs"] and test_result["converges"]:
                                print(f"     ✅ Model runs successfully!")
                            elif test_result["runs"]:
                                print(f"     ⚠️  Model runs but doesn't converge")
                            else:
                                print(f"     ❌ Model failed to run")
            
            return True
        else:
            print("❌ Response missing required fields")
            print(f"Keys in response: {list(result.keys())}")
    else:
        print("❌ Failed to get response from Claude")
    
    return False

def review_last_test():
    """Review the last processed test"""
    cli = TestReviewCLI()
    
    if not cli.status['completed']:
        print("No tests have been processed yet")
        return
    
    last_test = cli.status['completed'][-1]
    test_stem = Path(last_test).stem
    
    print(f"\n{'='*70}")
    print(f"Review: {last_test}")
    print(f"{'='*70}")
    
    # Check if files exist
    result_file = cli.results_dir / f"{test_stem}.json"
    model_dir = cli.models_dir / test_stem
    
    if result_file.exists():
        print(f"✓ Metadata: {result_file}")
        with open(result_file) as f:
            data = json.load(f)
            if "metadata" in data:
                # Handle both old and new metadata formats
                purpose = (data['metadata'].get('documentation', {}).get('purpose') or 
                          data['metadata'].get('purpose', 'N/A'))
                phase = (data['metadata'].get('classification', {}).get('phase_name') or 
                        data['metadata'].get('primary_phase', 'N/A'))
                print(f"  Purpose: {purpose}")
                print(f"  Primary Phase: {phase}")
    
    if model_dir.exists():
        print(f"✓ Models in: {model_dir}")
        for variant_dir in model_dir.iterdir():
            if variant_dir.is_dir():
                print(f"  - Variant: {variant_dir.name}")
                test_results = variant_dir / "test_results.json"
                if test_results.exists():
                    with open(test_results) as f:
                        results = json.load(f)
                        if results['runs'] and results['converges']:
                            print(f"    ✅ Passes tests")
                        elif results['runs']:
                            print(f"    ⚠️  Runs but doesn't converge")
                        else:
                            print(f"    ❌ Fails to run")
                            if results.get('error'):
                                # Show more of the error, especially the actual error line
                                error_text = results['error']
                                # Try to find the actual error message (last line of traceback)
                                error_lines = error_text.split('\n')
                                for line in reversed(error_lines):
                                    if line.strip() and not line.strip().startswith('File'):
                                        print(f"    Error: {line.strip()}")
                                        break
                                else:
                                    # Fallback to showing first part
                                    print(f"    Error: {error_text[:200]}...")
    
    print("\nOptions:")
    print("  1. Approve - Keep and move on")
    print("  2. Redo - Regenerate this test")
    print("  3. Skip - Mark as not useful")
    print("  4. View - See the generated model code")
    print("  5. Show full error details")
    
    return last_test

def redo_test(test_name: str):
    """Redo a specific test with error feedback"""
    cli = TestReviewCLI()
    
    # Find test file
    test_file = None
    for tf in cli.test_files:
        if tf.name == test_name or tf.stem == Path(test_name).stem:
            test_file = tf
            break
    
    if not test_file:
        print(f"Test not found: {test_name}")
        return False
    
    print(f"\nRedoing: {test_file.name}")
    
    # Collect error information before removing files
    test_stem = test_file.stem
    model_dir = cli.models_dir / test_stem
    error_info = ""
    
    if model_dir.exists():
        print("  Collecting error information...")
        for variant_dir in model_dir.iterdir():
            if variant_dir.is_dir():
                test_results = variant_dir / "test_results.json"
                if test_results.exists():
                    with open(test_results) as f:
                        results = json.load(f)
                        if results.get('error'):
                            error_info += f"\nPrevious error in variant '{variant_dir.name}':\n"
                            error_info += results['error']
                            # Extract the key error message
                            error_lines = results['error'].split('\n')
                            for line in reversed(error_lines):
                                if line.strip() and not line.strip().startswith('File') and 'Error:' not in line.strip():
                                    error_info += f"\nKey error: {line.strip()}"
                                    break
    
    # Remove from completed list
    if test_file.name in cli.status['completed']:
        cli.status['completed'].remove(test_file.name)
    
    # Remove existing files
    result_file = cli.results_dir / f"{test_stem}.json"
    
    if result_file.exists():
        result_file.unlink()
        print(f"  Removed: {result_file}")
    
    if model_dir.exists():
        import shutil
        shutil.rmtree(model_dir)
        print(f"  Removed: {model_dir}")
    
    # Update status
    if test_file.name in cli.status.get('models_created', {}):
        del cli.status['models_created'][test_file.name]
    
    cli.save_status()
    
    # Reprocess with error feedback
    print("\nReprocessing with error feedback...")
    base_prompt = cli.create_prompt_template(test_file)
    
    # Add error information to prompt if we have it
    if error_info:
        enhanced_prompt = base_prompt + f"\n\nIMPORTANT: The previous attempt failed with the following error(s):{error_info}\n\nPlease fix these specific issues in your generated code. Pay special attention to Python syntax and executable paths. Note: We have MODFLOW 6 available at /home/danilopezmella/flopy_expert/bin/mf6 but no MODFLOW-2005."
        print("  ✓ Added error feedback to prompt")
    else:
        enhanced_prompt = base_prompt + f"\n\nNote: We have MODFLOW 6 available at /home/danilopezmella/flopy_expert/bin/mf6 for running simulations. Choose the appropriate MODFLOW version based on what the test is demonstrating."
        print("  Added available executable info to prompt")
    
    result = analyze_test(test_file, enhanced_prompt)
    
    if result and "metadata" in result and "models" in result:
        # Save and generate
        result_file = cli.results_dir / f"{test_stem}.json"
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        cli.generate_model_files(test_file, result)
        
        # Update status
        cli.status['completed'].append(test_file.name)
        if 'models' in result:
            variants = [m.get('variant', 'basic') for m in result['models']]
            cli.status['models_created'][test_file.name] = variants
        cli.save_status()
        
        print(f"✅ Successfully regenerated {test_file.name}")
        return True
    else:
        print(f"❌ Failed to regenerate {test_file.name}")
        return False

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process FloPy tests with Claude Code SDK")
    parser.add_argument('--next', action='store_true', help='Process next unprocessed test')
    parser.add_argument('--test', help='Process specific test file')
    parser.add_argument('--count', type=int, default=1, help='Number of tests to process')
    parser.add_argument('--review', action='store_true', help='Review last processed test')
    parser.add_argument('--redo', help='Redo a specific test')
    parser.add_argument('--skip', help='Skip a test (mark as not useful)')
    parser.add_argument('--error', help='Show full error details for a test')
    
    args = parser.parse_args()
    
    if args.review:
        # Review last processed test
        last_test = review_last_test()
        if last_test:
            print(f"\nTo redo: python3 {__file__} --redo {last_test}")
            print(f"To skip: python3 {__file__} --skip {last_test}")
    
    elif args.redo:
        # Redo a specific test
        success = redo_test(args.redo)
        if success:
            # Review after redo
            review_last_test()
    
    elif args.skip:
        # Skip a test
        cli = TestReviewCLI()
        if args.skip in cli.status['completed']:
            cli.status['completed'].remove(args.skip)
        if args.skip not in cli.status['skipped']:
            cli.status['skipped'].append(args.skip)
        cli.save_status()
        print(f"✓ Skipped: {args.skip}")
    
    elif args.error:
        # Show full error details
        test_stem = Path(args.error).stem
        model_dir = Path("test_review/models") / test_stem
        
        print(f"\n{'='*70}")
        print(f"ERROR DETAILS: {args.error}")
        print(f"{'='*70}")
        
        if model_dir.exists():
            for variant_dir in model_dir.iterdir():
                if variant_dir.is_dir():
                    test_results = variant_dir / "test_results.json"
                    if test_results.exists():
                        with open(test_results) as f:
                            results = json.load(f)
                            if results.get('error'):
                                print(f"\nVariant: {variant_dir.name}")
                                print("-" * 40)
                                print(results['error'])
                            else:
                                print(f"\nVariant: {variant_dir.name} - No error recorded")
        else:
            print(f"No model directory found for {args.error}")
    
    elif args.test:
        # Process specific test
        cli = TestReviewCLI()
        test_file = None
        for tf in cli.test_files:
            if tf.name == args.test or tf.stem == args.test:
                test_file = tf
                break
        
        if test_file:
            prompt = cli.create_prompt_template(test_file)
            result = analyze_test(test_file, prompt)
            if result:
                print(f"✅ Successfully analyzed {test_file.name}")
            else:
                print(f"❌ Failed to analyze {test_file.name}")
        else:
            print(f"Test not found: {args.test}")
    
    else:
        # Process next test(s)
        success_count = 0
        for i in range(args.count):
            if process_next_test():
                success_count += 1
            else:
                break
        
        print(f"\n{'='*70}")
        print(f"Processed {success_count}/{args.count} tests successfully")
        print(f"{'='*70}")

if __name__ == "__main__":
    main()