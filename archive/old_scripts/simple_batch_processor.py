import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from create_flopy_knowledge_base import FloPyKnowledgeBuilder
import asyncpg

load_dotenv()

async def process_next_batch(batch_size: int = 10):
    """Process next batch of unprocessed files"""
    
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
        and '.git' not in str(f)
    ]
    
    # Check what's already processed
    conn = await asyncpg.connect(NEON_CONN)
    processed_files = await conn.fetch("SELECT file_path FROM modules")
    processed_paths = {row['file_path'] for row in processed_files}
    
    # Get counts by category
    category_counts = await conn.fetch("""
        SELECT model_family, COUNT(*) as count 
        FROM modules 
        GROUP BY model_family 
        ORDER BY count DESC
    """)
    
    await conn.close()
    
    print("=== Current Status ===")
    print(f"Total repository files: {len(filtered_files)}")
    print(f"Already processed: {len(processed_paths)}")
    print(f"Remaining: {len(filtered_files) - len(processed_paths)}")
    
    print("\nProcessed by category:")
    for row in category_counts:
        print(f"  {row['model_family'] or 'core'}: {row['count']}")
    
    # Get next batch of unprocessed files
    unprocessed = [f for f in filtered_files if str(f) not in processed_paths][:batch_size]
    
    if not unprocessed:
        print("\nAll files processed!")
        return
    
    print(f"\n=== Processing Next {len(unprocessed)} Files ===")
    
    # Create builder
    builder = FloPyKnowledgeBuilder(REPO_PATH, NEON_CONN, GEMINI_API_KEY, OPENAI_API_KEY)
    
    success_count = 0
    
    for i, file_path in enumerate(unprocessed, 1):
        print(f"\n[{i}/{len(unprocessed)}] {file_path.relative_to(Path(REPO_PATH))}")
        
        try:
            # Extract
            module_info = builder.extract_module_info(file_path)
            print(f"  Family: {module_info.model_family}, Code: {module_info.package_code or 'N/A'}")
            
            # Analyze
            gemini_results = await builder.analyze_modules_with_gemini([module_info], batch_size=1)
            
            # Store
            await builder.store_in_database([module_info], gemini_results)
            
            success_count += 1
            print("  ✓ Success")
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)[:100]}")
        
        # Rate limit
        await asyncio.sleep(1)
    
    print(f"\n=== Batch Complete ===")
    print(f"Processed: {success_count}/{len(unprocessed)}")
    
    # Show updated total
    conn = await asyncpg.connect(NEON_CONN)
    new_total = await conn.fetchval("SELECT COUNT(*) FROM modules")
    await conn.close()
    
    print(f"\nTotal in database: {new_total}")
    print(f"Still to process: {len(filtered_files) - new_total}")

if __name__ == "__main__":
    import sys
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    asyncio.run(process_next_batch(size))