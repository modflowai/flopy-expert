import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_status():
    conn = await asyncpg.connect(os.getenv('NEON_CONNECTION_STRING'))
    
    # Check modules table
    module_count = await conn.fetchval("SELECT COUNT(*) FROM modules")
    print(f"Total modules in database: {module_count}")
    
    # Check recent modules
    recent = await conn.fetch("""
        SELECT relative_path, model_family, package_code, created_at 
        FROM modules 
        ORDER BY created_at DESC 
        LIMIT 10
    """)
    
    print("\nMost recent modules:")
    for row in recent:
        print(f"  - {row['relative_path']} | {row['model_family']} | {row['package_code']} | {row['created_at']}")
    
    # Check by model family
    families = await conn.fetch("""
        SELECT model_family, COUNT(*) as count 
        FROM modules 
        GROUP BY model_family 
        ORDER BY count DESC
    """)
    
    print("\nModules by family:")
    for row in families:
        print(f"  {row['model_family']}: {row['count']}")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_status())