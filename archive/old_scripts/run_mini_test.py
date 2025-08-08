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
    
    print("Processing just 3 FloPy files...")
    
    # Build knowledge base with a small subset
    builder = FloPyKnowledgeBuilder(REPO_PATH, NEON_CONN, GEMINI_API_KEY, OPENAI_API_KEY)
    
    # Get 3 specific files
    py_files = [
        Path(REPO_PATH) / 'flopy' / 'version.py',
        Path(REPO_PATH) / 'flopy' / 'modflow' / 'mfwel.py',
        Path(REPO_PATH) / 'flopy' / 'mf6' / 'mfbase.py'
    ]
    
    # Filter existing files
    py_files = [f for f in py_files if f.exists()]
    
    print(f"Processing {len(py_files)} files:")
    for f in py_files:
        print(f"  - {f.relative_to(Path(REPO_PATH))}")
    
    # Extract module information
    modules = []
    for py_file in py_files:
        try:
            module_info = builder.extract_module_info(py_file)
            modules.append(module_info)
            print(f"✓ Extracted: {module_info.relative_path} - {module_info.model_family} - {module_info.package_code}")
        except Exception as e:
            print(f"✗ Error processing {py_file}: {e}")
    
    print(f"\nExtracted information from {len(modules)} modules")
    
    # Analyze with Gemini
    print("Analyzing modules with Gemini...")
    gemini_results = await builder.analyze_modules_with_gemini(modules, batch_size=3)
    
    print(f"✓ Gemini analysis complete: {len(gemini_results)} results")
    
    # Store in database
    print("Storing in Neon database...")
    await builder.store_in_database(modules, gemini_results)
    
    print("✓ Mini test complete! Check the database for results.")

if __name__ == "__main__":
    asyncio.run(main())