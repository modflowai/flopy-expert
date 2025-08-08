import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from create_flopy_knowledge_base import FloPyKnowledgeBuilder
from typing import List
import json
import asyncpg

# Load environment variables
load_dotenv()

async def process_full_repository():
    """Process the entire FloPy repository"""
    
    # Configuration
    REPO_PATH = os.getenv('REPO_PATH', 'flopy')
    NEON_CONN = os.getenv('NEON_CONNECTION_STRING')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    print("=== FloPy Full Repository Processing ===")
    print(f"Repository: {REPO_PATH}")
    
    # Build knowledge base
    builder = FloPyKnowledgeBuilder(REPO_PATH, NEON_CONN, GEMINI_API_KEY, OPENAI_API_KEY)
    
    # Collect all Python files
    py_files = list(Path(REPO_PATH).rglob("*.py"))
    
    # Filter out test files and __pycache__
    py_files = [f for f in py_files if 'test' not in str(f).lower() 
                and '__pycache__' not in str(f)
                and 'setup.py' not in str(f.name)]
    
    # Organize by category
    categories = {
        'mf6': [],
        'modflow': [],
        'mfusg': [],
        'mt3d': [],
        'seawat': [],
        'modpath': [],
        'utils': [],
        'plot': [],
        'export': [],
        'discretization': [],
        'core': [],
        'examples': [],
        'other': []
    }
    
    for py_file in py_files:
        rel_path = py_file.relative_to(Path(REPO_PATH))
        parts = rel_path.parts
        
        if 'examples' in parts:
            categories['examples'].append(py_file)
        elif 'mf6' in parts:
            categories['mf6'].append(py_file)
        elif 'mfusg' in parts:
            categories['mfusg'].append(py_file)
        elif 'mt3d' in parts:
            categories['mt3d'].append(py_file)
        elif 'seawat' in parts:
            categories['seawat'].append(py_file)
        elif 'modpath' in parts:
            categories['modpath'].append(py_file)
        elif 'utils' in parts:
            categories['utils'].append(py_file)
        elif 'plot' in parts:
            categories['plot'].append(py_file)
        elif 'export' in parts:
            categories['export'].append(py_file)
        elif 'discretization' in parts:
            categories['discretization'].append(py_file)
        elif 'modflow' in parts:
            categories['modflow'].append(py_file)
        else:
            categories['other'].append(py_file)
    
    # Print summary
    total_files = sum(len(files) for files in categories.values())
    print(f"\nTotal Python files to process: {total_files}")
    for category, files in categories.items():
        if files:
            print(f"  {category}: {len(files)} files")
    
    # Process each category
    for category, files in categories.items():
        if not files:
            continue
        
        print(f"\n=== Processing {category} ({len(files)} files) ===")
        
        # Process in batches to avoid overwhelming APIs
        batch_size = 10
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            
            print(f"\nBatch {i//batch_size + 1} of {(len(files)-1)//batch_size + 1}")
            
            # Extract module information
            modules = []
            for py_file in batch:
                try:
                    module_info = builder.extract_module_info(py_file)
                    modules.append(module_info)
                    print(f"  ✓ {module_info.relative_path} - {module_info.package_code or 'N/A'}")
                except Exception as e:
                    print(f"  ✗ Error with {py_file}: {e}")
            
            if modules:
                # Analyze with Gemini
                print("  Analyzing with Gemini...")
                try:
                    gemini_results = await builder.analyze_modules_with_gemini(modules, batch_size=5)
                    print(f"  ✓ Gemini analysis complete")
                except Exception as e:
                    print(f"  ✗ Gemini error: {e}")
                    # Create empty results if Gemini fails
                    gemini_results = [{'relative_path': m.relative_path} for m in modules]
                
                # Store in database
                print("  Storing in database...")
                try:
                    await builder.store_in_database(modules, gemini_results)
                    print(f"  ✓ Stored {len(modules)} modules")
                except Exception as e:
                    print(f"  ✗ Database error: {e}")
            
            # Rate limiting
            await asyncio.sleep(2)
    
    print("\n=== Repository Processing Complete! ===")
    
    # Get statistics
    conn = await asyncpg.connect(NEON_CONN)
    
    stats = await conn.fetchrow("""
        SELECT 
            COUNT(*) as total_modules,
            COUNT(DISTINCT model_family) as model_families,
            COUNT(DISTINCT package_code) as package_codes,
            COUNT(code_embedding) as modules_with_embeddings
        FROM modules
    """)
    
    print(f"\nDatabase Statistics:")
    print(f"  Total modules: {stats['total_modules']}")
    print(f"  Model families: {stats['model_families']}")
    print(f"  Package codes: {stats['package_codes']}")
    print(f"  Modules with embeddings: {stats['modules_with_embeddings']}")
    
    # Get package distribution
    packages = await conn.fetch("""
        SELECT model_family, COUNT(*) as count
        FROM modules
        WHERE model_family IS NOT NULL
        GROUP BY model_family
        ORDER BY count DESC
    """)
    
    print(f"\nPackage Distribution:")
    for row in packages:
        print(f"  {row['model_family']}: {row['count']} modules")
    
    await conn.close()


async def process_notebooks_and_examples():
    """Process Jupyter notebooks and example scripts"""
    REPO_PATH = os.getenv('REPO_PATH', 'flopy')
    
    print("\n=== Processing Notebooks and Examples ===")
    
    # Find all notebooks
    notebooks = list(Path(REPO_PATH).rglob("*.ipynb"))
    print(f"Found {len(notebooks)} notebooks")
    
    # Find all example scripts
    example_scripts = []
    examples_dir = Path(REPO_PATH) / 'examples'
    if examples_dir.exists():
        example_scripts = list(examples_dir.rglob("*.py"))
    
    tutorials_dir = Path(REPO_PATH) / 'examples' / 'Tutorials'
    if tutorials_dir.exists():
        example_scripts.extend(list(tutorials_dir.rglob("*.py")))
    
    print(f"Found {len(example_scripts)} example scripts")
    
    # TODO: Process these to extract usage patterns
    # This would involve:
    # 1. Parsing notebooks to extract code cells
    # 2. Identifying which packages are used together
    # 3. Extracting common workflows
    # 4. Storing as usage_patterns in the database


if __name__ == "__main__":
    asyncio.run(process_full_repository())
    # Optionally also process notebooks
    # asyncio.run(process_notebooks_and_examples())