#!/usr/bin/env python3
"""
Quick analysis of how ultra-discriminative prompts work on MODFLOW 6 examples
"""

import asyncio
import sys
sys.path.append('/home/danilopezmella/flopy_expert')
import psycopg2
import config
import google.genai as genai
import json
import re

# Initialize Gemini
gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)

async def analyze_modflow6_example(filename, source_code):
    """Test ultra-discriminative prompt on a MODFLOW 6 example"""
    
    prompt = f"""
Analyze this MODFLOW 6 example to create highly specific technical analysis.

FILENAME: {filename}
SOURCE CODE (first 1000 chars):
```python
{source_code[:1000]}...
```

Generate analysis focusing on:
1. What specific MODFLOW 6 physics/capability does this demonstrate?
2. What makes this example unique compared to other MODFLOW 6 examples?
3. What technical questions would someone ask when looking for THIS specific example?

Provide 3 ultra-specific questions that would ONLY apply to this example type.
"""
    
    try:
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model=config.GEMINI_MODEL,
            contents=prompt
        )
        return response.text if response else "No response"
    except Exception as e:
        return f"Error: {e}"

async def main():
    print("🧪 QUICK MODFLOW 6 ULTRA-DISCRIMINATIVE TEST")
    print("=" * 60)
    
    # Get 3 different types of MODFLOW 6 examples
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tutorial_file, source_code
                FROM flopy_workflows
                WHERE source_repository = 'modflow6-examples'
                AND source_code IS NOT NULL
                ORDER BY tutorial_file
                LIMIT 3
            """)
            
            workflows = cur.fetchall()
    
    for i, (tutorial_file, source_code) in enumerate(workflows, 1):
        filename = tutorial_file.split('/')[-1]
        print(f"\\n[{i}/3] Testing: {filename}")
        print("-" * 50)
        
        analysis = await analyze_modflow6_example(filename, source_code)
        
        # Extract key insights
        lines = analysis.split('\\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['physics', 'unique', 'specific', 'question']):
                print(f"  {line.strip()}")
        
        await asyncio.sleep(1)  # Rate limit
    
    print("\\n" + "=" * 60)
    print("🎯 ASSESSMENT:")
    print("This shows whether ultra-discriminative prompts can adapt")
    print("to different types of technical workflows beyond FloPy tutorials.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())