import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from create_flopy_knowledge_base import FloPyKnowledgeBuilder
import asyncpg
import time

load_dotenv()

async def continue_processing():
    """Continue processing from where we left off"""
    
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
    
    print(f"Total Python files in repository: {len(filtered_files)}")
    
    # Check what's already processed
    conn = await asyncpg.connect(NEON_CONN)
    processed_count = await conn.fetchval("SELECT COUNT(*) FROM modules")
    processed_files = await conn.fetch("SELECT file_path FROM modules")
    processed_paths = {row['file_path'] for row in processed_files}
    await conn.close()
    
    print(f"Already processed: {processed_count}")
    
    # Get unprocessed files
    unprocessed = [f for f in filtered_files if str(f) not in processed_paths]
    print(f"Files to process: {len(unprocessed)}")
    
    if not unprocessed:
        print("All files have been processed!")
        return
    
    # Create builder
    builder = FloPyKnowledgeBuilder(REPO_PATH, NEON_CONN, GEMINI_API_KEY, OPENAI_API_KEY)
    
    # Process in batches of 5 with retries
    batch_size = 5
    total_processed = 0
    total_errors = 0
    start_time = time.time()
    
    for batch_start in range(0, len(unprocessed), batch_size):
        batch_end = min(batch_start + batch_size, len(unprocessed))
        batch = unprocessed[batch_start:batch_end]
        
        print(f"\n=== Batch {batch_start//batch_size + 1} ({batch_start}-{batch_end} of {len(unprocessed)}) ===")
        
        # Extract module info for batch
        modules = []
        for file_path in batch:
            try:
                module_info = builder.extract_module_info(file_path)
                modules.append(module_info)
                print(f"✓ Extracted: {module_info.relative_path} [{module_info.model_family}] {module_info.package_code or ''}")
            except Exception as e:
                print(f"✗ Extract error {file_path.name}: {str(e)[:50]}")
                total_errors += 1
        
        if modules:
            # Analyze batch with Gemini
            try:
                print(f"\nAnalyzing {len(modules)} modules with Gemini...")
                gemini_results = await builder.analyze_modules_with_gemini(modules, batch_size=len(modules))
                print("✓ Gemini analysis complete")
            except Exception as e:
                print(f"✗ Gemini error: {str(e)[:100]}")
                # Create minimal results
                gemini_results = []
                for m in modules:
                    gemini_results.append({
                        'file_path': m.relative_path,
                        'semantic_purpose': m.module_docstring[:200] if m.module_docstring else '',
                        'user_scenarios': [],
                        'related_concepts': [],
                        'natural_language_queries': []
                    })
            
            # Store in database
            try:
                print("Storing in database...")
                await builder.store_in_database(modules, gemini_results)
                total_processed += len(modules)
                print(f"✓ Stored {len(modules)} modules")
            except Exception as e:
                print(f"✗ Database error: {str(e)[:100]}")
                total_errors += len(modules)
        
        # Progress update
        elapsed = time.time() - start_time
        rate = total_processed / elapsed if elapsed > 0 else 0
        remaining = len(unprocessed) - (batch_end)
        eta = remaining / rate if rate > 0 else 0
        
        print(f"\nProgress: {batch_end}/{len(unprocessed)} files")
        print(f"Processed: {total_processed} | Errors: {total_errors}")
        print(f"Rate: {rate:.1f} files/sec | ETA: {eta/60:.1f} minutes")
        
        # Rate limiting
        await asyncio.sleep(2)
        
        # Stop after 50 files for this run
        if batch_end >= 50:
            print(f"\n=== Stopping after {batch_end} files ===")
            print("Run again to continue processing")
            break
    
    # Final stats
    print(f"\n=== Processing Summary ===")
    print(f"Total processed: {total_processed}")
    print(f"Total errors: {total_errors}")
    print(f"Time taken: {(time.time() - start_time)/60:.1f} minutes")
    
    # Check new total
    conn = await asyncpg.connect(NEON_CONN)
    new_total = await conn.fetchval("SELECT COUNT(*) FROM modules")
    await conn.close()
    
    print(f"\nDatabase now contains: {new_total} modules")
    print(f"Remaining: {len(filtered_files) - new_total}")

if __name__ == "__main__":
    asyncio.run(continue_processing())