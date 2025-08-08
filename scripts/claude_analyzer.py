#!/usr/bin/env python3
"""
Analyze FloPy tests using Claude SDK Python API
This enables fully autonomous operation
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
import sys

# Import the review CLI
sys.path.append(str(Path(__file__).parent.parent))
from scripts.review_tests import TestReviewCLI

def analyze_test_with_claude(test_file: Path, prompt_template: str) -> Optional[Dict]:
    """
    Analyze a single test file with Claude using Anthropic Python SDK
    """
    
    print(f"\nAnalyzing: {test_file.name}")
    print("="*60)
    
    try:
        from anthropic import Anthropic
        
        # Get API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            # Try config file
            try:
                import config
                api_key = config.ANTHROPIC_API_KEY
            except:
                print("Error: No ANTHROPIC_API_KEY found")
                return None
        
        # Create client
        client = Anthropic(api_key=api_key)
        
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
        
        # Call Claude API
        print("Calling Claude API...")
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8000,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": full_prompt
                }
            ]
        )
        
        # Extract response text
        response_text = response.content[0].text
        
        # Parse JSON
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
            
    except ImportError:
        print("Error: anthropic package not installed")
        print("Install with: pip install anthropic")
        return None
    except Exception as e:
        print(f"Error analyzing test: {e}")
        return None

def process_single_test(test_name: str) -> bool:
    """
    Process a single test by name
    Returns True if successful
    """
    cli = TestReviewCLI()
    
    # Find the test file
    test_file = None
    for tf in cli.test_files:
        if tf.name == test_name or tf.stem == test_name:
            test_file = tf
            break
    
    if not test_file:
        print(f"Test not found: {test_name}")
        return False
    
    # Create prompt
    prompt = cli.create_prompt_template(test_file)
    
    # Analyze with Claude
    result = analyze_test_with_claude(test_file, prompt)
    
    if result:
        # Save result
        result_file = cli.results_dir / f"{test_file.stem}.json"
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Generate model files
        cli.generate_model_files(test_file, result)
        
        # Update status
        cli.status['completed'].append(test_file.name)
        if 'models' in result:
            variants = [m.get('variant', 'basic') for m in result['models']]
            cli.status['models_created'][test_file.name] = variants
        cli.save_status()
        
        print(f"✓ Successfully processed {test_name}")
        return True
    
    return False

def process_next_unprocessed() -> Optional[str]:
    """
    Process the next unprocessed test
    Returns the test name if successful, None otherwise
    """
    cli = TestReviewCLI()
    
    # Find next unprocessed test
    for test_file in cli.test_files:
        if test_file.name not in cli.status['completed'] and \
           test_file.name not in cli.status['skipped']:
            
            if process_single_test(test_file.name):
                return test_file.name
            break
    
    return None

def get_test_prompt(test_name: str) -> Optional[str]:
    """
    Get the prompt for a specific test
    This is useful for Claude Code to get the prompt directly
    """
    cli = TestReviewCLI()
    
    # Find the test file
    test_file = None
    for tf in cli.test_files:
        if tf.name == test_name or tf.stem == test_name:
            test_file = tf
            break
    
    if not test_file:
        return None
    
    return cli.create_prompt_template(test_file)

def save_claude_result(test_name: str, result_json: Dict) -> bool:
    """
    Save Claude's analysis result for a test
    This allows Claude Code to directly provide the JSON result
    """
    cli = TestReviewCLI()
    
    # Find the test file
    test_file = None
    for tf in cli.test_files:
        if tf.name == test_name or tf.stem == test_name:
            test_file = tf
            break
    
    if not test_file:
        print(f"Test not found: {test_name}")
        return False
    
    # Save result
    result_file = cli.results_dir / f"{test_file.stem}.json"
    with open(result_file, 'w') as f:
        json.dump(result_json, f, indent=2)
    
    # Generate model files
    cli.generate_model_files(test_file, result_json)
    
    # Update status
    cli.status['completed'].append(test_file.name)
    if 'models' in result_json:
        variants = [m.get('variant', 'basic') for m in result_json['models']]
        cli.status['models_created'][test_file.name] = variants
    cli.save_status()
    
    print(f"✓ Result saved for {test_name}")
    
    # Test the generated models
    test_dir = cli.models_dir / test_file.stem
    if test_dir.exists():
        for variant_dir in test_dir.iterdir():
            if variant_dir.is_dir():
                model_file = variant_dir / "model.py"
                if model_file.exists():
                    cli.test_model(model_file, variant_dir)
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['next', 'single', 'prompt', 'save'])
    parser.add_argument('--test', help='Test name for single/prompt/save actions')
    parser.add_argument('--json', help='JSON file path for save action')
    
    args = parser.parse_args()
    
    if args.action == 'next':
        # Process next unprocessed test
        result = process_next_unprocessed()
        if result:
            print(f"Processed: {result}")
        else:
            print("No unprocessed tests found")
            
    elif args.action == 'single':
        # Process a single test
        if not args.test:
            print("Error: --test required for single action")
        else:
            process_single_test(args.test)
            
    elif args.action == 'prompt':
        # Get prompt for a test
        if not args.test:
            print("Error: --test required for prompt action")
        else:
            prompt = get_test_prompt(args.test)
            if prompt:
                print(prompt)
            else:
                print(f"Test not found: {args.test}")
                
    elif args.action == 'save':
        # Save Claude's result
        if not args.test or not args.json:
            print("Error: --test and --json required for save action")
        else:
            with open(args.json) as f:
                result = json.load(f)
            save_claude_result(args.test, result)