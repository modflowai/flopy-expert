import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def analyze_schema():
    conn = await asyncpg.connect(os.getenv('NEON_CONNECTION_STRING'))
    
    # Get all tables
    tables = await conn.fetch("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    
    print("=== DATABASE TABLES ===\n")
    
    for table in tables:
        table_name = table['table_name']
        print(f"\n📊 TABLE: {table_name}")
        print("-" * 50)
        
        # Get row count
        count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')
        print(f"Rows: {count}")
        
        # Get columns
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position
        """, table_name)
        
        print("\nColumns:")
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
            print(f"  - {col['column_name']}: {col['data_type']} {nullable}{default}")
        
        # Show sample data if table has rows
        if count > 0 and count < 10:
            print(f"\nSample data (all {count} rows):")
            rows = await conn.fetch(f'SELECT * FROM "{table_name}" LIMIT 5')
            for row in rows:
                print(f"  {dict(row)}")
        elif count > 0:
            print(f"\nSample data (first 3 rows):")
            rows = await conn.fetch(f'SELECT * FROM "{table_name}" LIMIT 3')
            for row in rows:
                # Show abbreviated version
                abbreviated = {}
                for key, value in dict(row).items():
                    if isinstance(value, str) and len(value) > 50:
                        abbreviated[key] = value[:50] + "..."
                    else:
                        abbreviated[key] = value
                print(f"  {abbreviated}")
    
    # Analyze relationships
    print("\n\n=== FOREIGN KEY RELATIONSHIPS ===")
    fks = await conn.fetch("""
        SELECT
            tc.table_name, 
            kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name 
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
        WHERE constraint_type = 'FOREIGN KEY'
    """)
    
    for fk in fks:
        print(f"{fk['table_name']}.{fk['column_name']} -> {fk['foreign_table_name']}.{fk['foreign_column_name']}")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(analyze_schema())