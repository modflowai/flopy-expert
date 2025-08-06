import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from create_flopy_knowledge_base import FloPyKnowledgeBuilder
import asyncpg

load_dotenv()

async def process_batch(start_index: int = 0, batch_size: int = 20):
    """Process a batch of files starting from start_index"""
    
    REPO_PATH = os.getenv('REPO_PATH', 'flopy')
    NEON_CONN = os.getenv('NEON_CONNECTION_STRING')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Get all Python files
    all_files = sorted(list(Path(REPO_PATH).rglob("*.py")))
    
    # Filter
    filtered_files = [
        f for f in all_files 
        if 'test' not in str(f).lower() 
        and '__pycache__' not in str(f)
        and 'setup.py' not in str(f.name)
    ]
    
    # Check which are already processed
    conn = await asyncpg.connect(NEON_CONN)
    processed = await conn.fetch("SELECT file_path FROM modules")
    processed_paths = {row['file_path'] for row in processed}
    await conn.close()
    
    # Get unprocessed files
    unprocessed = [f for f in filtered_files if str(f) not in processed_paths]
    
    print(f"Total files: {len(filtered_files)}")
    print(f"Already processed: {len(processed_paths)}")
    print(f"To process: {len(unprocessed)}")
    
    if start_index >= len(unprocessed):
        print("All files processed!")
        return
    
    # Get batch
    batch_files = unprocessed[start_index:start_index + batch_size]
    print(f"\nProcessing batch: {start_index} to {start_index + len(batch_files)}")
    
    # Create builder
    builder = FloPyKnowledgeBuilder(REPO_PATH, NEON_CONN, GEMINI_API_KEY, OPENAI_API_KEY)
    
    # Process files
    for i, file_path in enumerate(batch_files):
        print(f"\n[{i+1}/{len(batch_files)}] {file_path.relative_to(Path(REPO_PATH))}")
        
        try:
            # Extract module info
            module_info = builder.extract_module_info(file_path)
            
            # Analyze with Gemini
            gemini_results = await builder.analyze_modules_with_gemini([module_info], batch_size=1)
            
            # Store in database
            await builder.store_in_database([module_info], gemini_results)
            
            print("  ✓ Success")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        # Rate limiting
        await asyncio.sleep(1)
    
    print(f"\nBatch complete! Next start index: {start_index + len(batch_files)}")

if __name__ == "__main__":
    import sys
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    asyncio.run(process_batch(start))