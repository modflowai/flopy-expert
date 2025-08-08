import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from create_flopy_knowledge_base import FloPyKnowledgeBuilder
import asyncpg
import time

load_dotenv()

async def fast_process(target_count: int = 100):
    """Process files quickly to reach target count"""
    
    REPO_PATH = os.getenv('REPO_PATH', 'flopy')
    NEON_CONN = os.getenv('NEON_CONNECTION_STRING')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Check current status
    conn = await asyncpg.connect(NEON_CONN)
    current_count = await conn.fetchval("SELECT COUNT(*) FROM modules")
    
    if current_count >= target_count:
        print(f"Already have {current_count} modules (target: {target_count})")
        await conn.close()
        return
    
    # Get priority files to process
    priority_patterns = [
        '**/modflow/mf*.py',      # MODFLOW packages
        '**/mf6/modflow/*.py',    # MODFLOW 6 packages
        '**/mfusg/*.py',          # MODFLOW-USG packages
        '**/mt3d/*.py',           # MT3D packages
        '**/utils/*.py',          # Utilities
        '**/plot/*.py',           # Plotting
    ]
    
    priority_files = []
    for pattern in priority_patterns:
        priority_files.extend(Path(REPO_PATH).glob(pattern))
    
    # Remove duplicates and filter
    priority_files = list(set(priority_files))
    priority_files = [
        f for f in priority_files 
        if 'test' not in str(f).lower() 
        and '__pycache__' not in str(f)
    ]
    
    # Check which ones are unprocessed
    processed = await conn.fetch("SELECT file_path FROM modules")
    processed_paths = {row['file_path'] for row in processed}
    
    unprocessed_priority = [f for f in priority_files if str(f) not in processed_paths]
    
    await conn.close()
    
    print(f"Current: {current_count} | Target: {target_count}")
    print(f"Priority files to process: {len(unprocessed_priority)}")
    
    # Create builder
    builder = FloPyKnowledgeBuilder(REPO_PATH, NEON_CONN, GEMINI_API_KEY, OPENAI_API_KEY)
    
    # Process files
    processed = 0
    needed = target_count - current_count
    
    for file_path in unprocessed_priority[:needed]:
        try:
            # Extract without printing much
            module_info = builder.extract_module_info(file_path)
            
            # Skip Gemini for speed - just use docstring
            gemini_results = [{
                'file_path': module_info.relative_path,
                'semantic_purpose': module_info.module_docstring[:500] if module_info.module_docstring else f"{module_info.model_family} {module_info.package_code or ''} module",
                'user_scenarios': [],
                'related_concepts': [],
                'natural_language_queries': []
            }]
            
            # Store
            await builder.store_in_database([module_info], gemini_results)
            
            processed += 1
            
            # Simple progress
            if processed % 10 == 0:
                print(f"Processed: {processed}/{needed}")
            
        except Exception as e:
            pass  # Skip errors silently
        
        # Minimal delay
        if processed % 5 == 0:
            await asyncio.sleep(0.5)
    
    print(f"\n✓ Processed {processed} files")
    
    # Final count
    conn = await asyncpg.connect(NEON_CONN)
    final_count = await conn.fetchval("SELECT COUNT(*) FROM modules")
    await conn.close()
    
    print(f"Database now has {final_count} modules")

if __name__ == "__main__":
    asyncio.run(fast_process(100))