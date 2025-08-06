#!/usr/bin/env python3
"""
Manual test of vector similarity search to isolate the issue
"""
import asyncio
import psycopg2
from openai import AsyncOpenAI
import config

async def manual_test():
    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    
    # Get embedding
    response = await client.embeddings.create(
        model='text-embedding-3-small',
        input='sparse matrix solver'
    )
    query_embedding = response.data[0].embedding
    
    # First, test with stored SMS embedding
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            print("=== Test 1: Self-similarity with SMS ===")
            cur.execute("""
                SELECT package_code, 
                       1 - (embedding <=> (SELECT embedding FROM flopy_modules WHERE package_code = 'SMS')) as similarity
                FROM flopy_modules
                WHERE package_code = 'SMS'
            """)
            result = cur.fetchone()
            print(f"SMS self-similarity: {result[1]:.3f}")
            
            print("\n=== Test 2: Top 3 similar to SMS ===")
            cur.execute("""
                SELECT package_code, 
                       1 - (embedding <=> (SELECT embedding FROM flopy_modules WHERE package_code = 'SMS')) as similarity
                FROM flopy_modules
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> (SELECT embedding FROM flopy_modules WHERE package_code = 'SMS')
                LIMIT 3
            """)
            results = cur.fetchall()
            for pkg, sim in results:
                print(f"  {pkg}: {sim:.3f}")
            
            print("\n=== Test 3: Manual vector string (shorter) ===")
            # Create a much shorter test vector
            short_vec = '[' + ','.join(str(x) for x in query_embedding[:10]) + ']'
            print(f"Short vector: {short_vec}")
            
            # Won't work due to dimension mismatch, but let's see the error
            try:
                cur.execute(f"SELECT '{short_vec}'::vector")
                print("Short vector cast successful")
            except Exception as e:
                print(f"Short vector error (expected): {e}")
            
            print("\n=== Test 4: Full vector with file approach ===")
            # Write vector to temp file and read it
            temp_file = '/tmp/test_vector.txt'
            with open(temp_file, 'w') as f:
                f.write('[' + ','.join(map(str, query_embedding)) + ']')
            
            with open(temp_file, 'r') as f:
                file_vector = f.read().strip()
            
            print(f"File vector length: {len(file_vector)}")
            
            # Try direct substitution
            query_sql = f"""
                SELECT package_code, 
                       1 - (embedding <=> '{file_vector}'::vector) as similarity
                FROM flopy_modules
                WHERE package_code = 'SMS'
            """
            
            try:
                cur.execute(query_sql)
                result = cur.fetchone()
                print(f"File vector SMS similarity: {result[1]:.3f}")
                
                # If that works, try the full search
                print("\n=== Test 5: Full search with file vector ===")
                full_query = f"""
                    SELECT package_code, 
                           1 - (embedding <=> '{file_vector}'::vector) as similarity
                    FROM flopy_modules
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> '{file_vector}'::vector
                    LIMIT 5
                """
                cur.execute(full_query)
                results = cur.fetchall()
                print(f"Full search results: {len(results)}")
                for pkg, sim in results:
                    print(f"  {pkg}: {sim:.3f}")
                    if pkg == 'SMS':
                        print("    *** SMS FOUND! ***")
                        
            except Exception as e:
                print(f"File vector error: {e}")

asyncio.run(manual_test())