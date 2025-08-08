import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from create_flopy_knowledge_base import FloPyKnowledgeBuilder

load_dotenv()

async def process_uzf():
    REPO_PATH = 'flopy'
    NEON_CONN = os.getenv('NEON_CONNECTION_STRING')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # UZF files
    uzf_files = [
        'flopy/modflow/mfuzf1.py',      # MODFLOW-2005 UZF
        'flopy/mf6/modflow/mfgwfuzf.py' # MODFLOW 6 UZF
    ]
    
    builder = FloPyKnowledgeBuilder(REPO_PATH, NEON_CONN, GEMINI_API_KEY, OPENAI_API_KEY)
    
    for file_path in uzf_files:
        path = Path(REPO_PATH) / file_path
        if not path.exists():
            print(f"File not found: {file_path}")
            continue
            
        print(f"\nProcessing UZF: {path.name}")
        
        try:
            # Extract
            module_info = builder.extract_module_info(path)
            print(f"  Model family: {module_info.model_family}")
            print(f"  Package code: {module_info.package_code}")
            
            # Analyze
            gemini_results = await builder.analyze_modules_with_gemini([module_info])
            purpose = gemini_results[0].get('semantic_purpose', 'N/A')
            print(f"  Purpose: {purpose[:150]}...")
            
            # Store
            await builder.store_in_database([module_info], gemini_results)
            print("  ✓ Stored successfully")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")

if __name__ == "__main__":
    asyncio.run(process_uzf())