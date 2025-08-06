#!/usr/bin/env python3
"""
Simple script to reprocess the single failed PyEmu module: pyemu/mc.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import config
import psycopg2
from src.pyemu_processing_pipeline import PyEMUProcessor


async def reprocess_pyemu_mc():
    """Reprocess the single failed PyEmu module"""
    
    target_module = 'pyemu/mc.py'
    
    print("🔄 REPROCESSING FAILED PYEMU MODULE")
    print("=" * 50)
    print(f"Target: {target_module}")
    print()
    
    # Initialize the processor
    processor = PyEMUProcessor(
        repo_path='/home/danilopezmella/flopy_expert/pyemu',
        neon_conn_string=config.NEON_CONNECTION_STRING,
        gemini_api_key=config.GEMINI_API_KEY,
        openai_api_key=config.OPENAI_API_KEY
    )
    
    # Delete the existing failed record
    print("🗑️  Deleting existing failed record...")
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM pyemu_modules 
                WHERE relative_path = %s
                RETURNING id, relative_path
            """, (target_module,))
            
            deleted = cur.fetchone()
            if deleted:
                print(f"  ✓ Deleted: {deleted[1]}")
                conn.commit()
            else:
                print("  No record found to delete")
    
    # Reprocess the module
    print(f"\n🚀 Reprocessing {target_module} with improved retry logic...")
    print("-" * 50)
    
    try:
        # Manually create the module info for mc.py
        from src.pyemu_docs_parser import PyEMUModule
        
        mc_module = PyEMUModule(
            module_path='pyemu.mc',
            category='core',
            description='Monte Carlo analysis',
            rst_file='mc.rst'
        )
        
        # Convert to file path
        file_path = Path('/home/danilopezmella/flopy_expert/pyemu/pyemu/mc.py')
        target_modules = [(file_path, mc_module)]
        
        # Process the single module
        completed, failed = await processor.process_batch(target_modules, batch_id=1, category='core')
        success = len(completed) > 0 and len(failed) == 0
        
        if success:
            print("✅ Successfully reprocessed!")
            
            # Verify the new embedding
            with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            LENGTH(embedding_text) as embed_len,
                            LENGTH(semantic_purpose) as purpose_len,
                            LEFT(semantic_purpose, 100) as purpose_start
                        FROM pyemu_modules 
                        WHERE relative_path = %s
                    """, (target_module,))
                    
                    result = cur.fetchone()
                    if result:
                        embed_len, purpose_len, purpose_start = result
                        print(f"\n📊 New embedding quality:")
                        print(f"  Embedding length: {embed_len} chars")
                        print(f"  Purpose length: {purpose_len} chars")
                        print(f"  Purpose start: {purpose_start}...")
                        
                        if embed_len > 1000 and purpose_len > 100:
                            print("\n🎉 Quality significantly improved!")
                        else:
                            print("\n⚠️  Still below ideal thresholds")
                    else:
                        print("\n❌ Module not found after processing")
        else:
            print("❌ Processing failed")
            
    except Exception as e:
        print(f"❌ Error during processing: {e}")


async def main():
    await reprocess_pyemu_mc()


if __name__ == "__main__":
    asyncio.run(main())