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
    
    # Validate environment variables
    if not NEON_CONN:
        print("Error: NEON_CONNECTION_STRING not found in environment")
        return
    
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not found in environment")
        return
    
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not found in environment")
        return
    
    if not Path(REPO_PATH).exists():
        print(f"Error: Repository path '{REPO_PATH}' does not exist")
        return
    
    print(f"Configuration:")
    print(f"  Repository: {REPO_PATH}")
    print(f"  Neon Database: Connected to mfai_db")
    print(f"  Gemini API: Configured")
    print(f"  OpenAI API: Configured")
    print()
    
    # Build knowledge base with a small subset
    builder = FloPyKnowledgeBuilder(REPO_PATH, NEON_CONN, GEMINI_API_KEY, OPENAI_API_KEY)
    
    print("Processing just the first 10 FloPy files...")
    
    # Get just the first 10 Python files from key directories
    py_files = []
    
    # Get some key package files
    key_dirs = ['modflow', 'mf6', 'mfusg', 'utils']
    for key_dir in key_dirs:
        dir_path = Path(REPO_PATH) / 'flopy' / key_dir
        if dir_path.exists():
            dir_files = list(dir_path.glob('*.py'))[:3]  # First 3 from each dir
            py_files.extend(dir_files)
            if len(py_files) >= 10:
                break
    
    py_files = py_files[:10]  # Limit to 10 files
    
    print(f"Processing {len(py_files)} files:")
    for f in py_files:
        print(f"  - {f.relative_to(Path(REPO_PATH))}")
    
    # Extract module information
    modules = []
    for py_file in py_files:
        try:
            module_info = builder.extract_module_info(py_file)
            modules.append(module_info)
            print(f"Extracted: {module_info.relative_path} - {module_info.model_family} - {module_info.package_code}")
        except Exception as e:
            print(f"Error processing {py_file}: {e}")
    
    print(f"\\nExtracted information from {len(modules)} modules")
    
    # Analyze with Gemini
    print("Analyzing modules with Gemini 2.5 Flash...")
    gemini_results = await builder.analyze_modules_with_gemini(modules, batch_size=5)
    
    print(f"Gemini analysis complete: {len(gemini_results)} results")
    
    # Store in database
    print("Storing in Neon database...")
    await builder.store_in_database(modules, gemini_results)
    
    print("Small test complete! Check the database for results.")


if __name__ == "__main__":
    asyncio.run(main())