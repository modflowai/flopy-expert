import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from create_flopy_knowledge_base import FloPyKnowledgeBuilder
import asyncpg

load_dotenv()

async def quick_process():
    REPO_PATH = 'flopy'
    NEON_CONN = os.getenv('NEON_CONNECTION_STRING')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Find a specific unprocessed file
    target_files = [
        'flopy/flopy/modflow/mfbas.py',  # BAS package
        'flopy/flopy/modflow/mfoc.py',   # OC package
        'flopy/flopy/modflow/mfrch.py',  # RCH package
        'flopy/flopy/modflow/mfuzf.py'   # UZF package - the one confused with SMS!
    ]
    
    builder = FloPyKnowledgeBuilder(REPO_PATH, NEON_CONN, GEMINI_API_KEY, OPENAI_API_KEY)
    
    for file_path in target_files:
        path = Path(file_path)
        if not path.exists():
            print(f"File not found: {file_path}")
            continue
            
        print(f"\nProcessing: {path.name}")
        
        try:
            # Check if already processed
            conn = await asyncpg.connect(NEON_CONN)
            exists = await conn.fetchval("SELECT COUNT(*) FROM modules WHERE file_path = $1", str(path))
            await conn.close()
            
            if exists:
                print("  → Already in database")
                continue
            
            # Extract and process
            module_info = builder.extract_module_info(path)
            print(f"  Package code: {module_info.package_code}")
            
            # Quick analysis
            gemini_results = await builder.analyze_modules_with_gemini([module_info])
            print(f"  Purpose: {gemini_results[0].get('semantic_purpose', 'N/A')[:100]}...")
            
            # Store
            await builder.store_in_database([module_info], gemini_results)
            print("  ✓ Stored successfully")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")

if __name__ == "__main__":
    asyncio.run(quick_process())