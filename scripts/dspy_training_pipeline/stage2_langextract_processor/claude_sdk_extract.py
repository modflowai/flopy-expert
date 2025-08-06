#!/usr/bin/env python3
"""
Use Claude Code SDK to extract structured information from issue #2150
"""

import json
import asyncio
from pathlib import Path
from claude_code_sdk import query, ClaudeCodeOptions, Message


async def extract_with_claude(issue_data):
    """Use Claude Code SDK to extract structured information"""
    
    # Prepare the issue context
    issue_num = issue_data['issue_number']
    title = issue_data['title']
    body = issue_data['original_issue']['body']
    comments = issue_data['original_issue'].get('comments', [])
    
    # Build the prompt
    prompt = f"""
I need you to analyze GitHub issue #{issue_num} from the FloPy repository and extract structured information.

ISSUE TITLE: {title}

ISSUE BODY:
{body}

COMMENTS:
{chr(10).join([f"{c['author']}: {c['body']}" for c in comments[:3]])}

Please extract:
1. The SPECIFIC FloPy modules/functions that have the bug (e.g., flopy.utils.cvfd_utils.shapefile_to_xcyc)
2. The actual problem described (what's broken)
3. The root cause if mentioned
4. Any resolution or fix mentioned

Focus ONLY on FloPy modules, not external packages like geopandas or AlgoMesh.
Be specific - if the bug is in shapefile_to_xcyc function, say "flopy.utils.cvfd_utils.shapefile_to_xcyc" not just "cvfd_utils".

Provide your response in this exact JSON format:
```json
{{
  "issue_number": {issue_num},
  "flopy_modules": [
    {{
      "full_path": "flopy.package.module.function",
      "type": "function|class|module",
      "role": "affected|mentioned|compared"
    }}
  ],
  "problem": {{
    "summary": "Brief description",
    "details": "Detailed explanation",
    "error_type": "incorrect_output|crash|performance|etc"
  }},
  "resolution": {{
    "status": "open|fixed|workaround",
    "description": "What was done or suggested"
  }}
}}
```
"""
    
    messages = []
    
    # Query Claude Code SDK
    async for message in query(
        prompt=prompt,
        options=ClaudeCodeOptions(
            max_turns=1,
            output_format="json",
            system_prompt="You are analyzing FloPy GitHub issues to extract structured information about bugs and affected modules. Be precise and focus only on FloPy-specific code."
        )
    ):
        messages.append(message)
    
    return messages


async def main():
    """Process issue #2150 with Claude Code SDK"""
    
    # Load issue data
    with open('issue_2150.json', 'r') as f:
        issue_data = json.load(f)
    
    print(f"Processing issue #{issue_data['issue_number']}: {issue_data['title']}")
    print("Using Claude Code SDK for extraction...")
    
    try:
        messages = await extract_with_claude(issue_data)
        
        # Save raw messages
        with open('claude_sdk_messages.json', 'w') as f:
            # Convert messages to serializable format
            serializable_messages = []
            for msg in messages:
                if hasattr(msg, '__dict__'):
                    serializable_messages.append(msg.__dict__)
                else:
                    serializable_messages.append(str(msg))
            json.dump(serializable_messages, f, indent=2)
        
        print(f"\nReceived {len(messages)} messages")
        
        # Extract the result
        for msg in messages:
            if hasattr(msg, 'type') and msg.type == 'result':
                print("\nExtraction Result:")
                print(msg.result if hasattr(msg, 'result') else str(msg))
                
                # Try to parse the JSON result
                try:
                    if hasattr(msg, 'result'):
                        # Find JSON in the result
                        result_text = msg.result
                        start = result_text.find('{')
                        end = result_text.rfind('}') + 1
                        if start >= 0 and end > start:
                            json_text = result_text[start:end]
                            extracted_data = json.loads(json_text)
                            
                            # Save cleaned extraction
                            with open('issue_2150_claude_extracted.json', 'w') as f:
                                json.dump(extracted_data, f, indent=2)
                            
                            print("\nExtracted FloPy modules:")
                            for mod in extracted_data.get('flopy_modules', []):
                                print(f"  - {mod['full_path']} ({mod['type']}, {mod['role']})")
                            
                            print(f"\nProblem: {extracted_data.get('problem', {}).get('summary', 'N/A')}")
                except Exception as e:
                    print(f"Error parsing JSON: {e}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())