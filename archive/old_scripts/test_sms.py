import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from create_flopy_knowledge_base import FloPyKnowledgeBuilder

# Load environment variables
load_dotenv()

async def main():
    # Get configuration from environment
    REPO_PATH = os.getenv('REPO_PATH', 'flopy')
    NEON_CONN = os.getenv('NEON_CONNECTION_STRING')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    print("Processing SMS package file...")
    
    # Build knowledge base
    builder = FloPyKnowledgeBuilder(REPO_PATH, NEON_CONN, GEMINI_API_KEY, OPENAI_API_KEY)
    
    # Get the SMS file
    sms_file = Path(REPO_PATH) / 'flopy' / 'mfusg' / 'mfusgsms.py'
    
    if not sms_file.exists():
        print(f"SMS file {sms_file} does not exist")
        return
    
    print(f"Processing: {sms_file}")
    
    # Extract module information
    try:
        module_info = builder.extract_module_info(sms_file)
        print(f"✓ Extracted: {module_info.relative_path} - {module_info.model_family} - {module_info.package_code}")
    except Exception as e:
        print(f"✗ Error processing {sms_file}: {e}")
        return
    
    # Analyze with Gemini
    print("Analyzing SMS with Gemini...")
    gemini_results = await builder.analyze_modules_with_gemini([module_info])
    
    print(f"✓ Gemini analysis complete")
    print(f"Purpose: {gemini_results[0].get('semantic_purpose', 'N/A')}")
    
    # Store in database
    print("Storing SMS in database...")
    await builder.store_in_database([module_info], gemini_results)
    
    print("✓ SMS package processed successfully!")

if __name__ == "__main__":
    asyncio.run(main())