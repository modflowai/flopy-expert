#!/usr/bin/env python3
"""
Check the database tables to see what was processed
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import config

def check_tables():
    """Check all tables and show what was processed"""
    
    print("🔍 Checking Database Tables")
    print("=" * 50)
    
    try:
        with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                
                # Check modules table
                print("\n📊 MODULES TABLE:")
                cur.execute("""
                    SELECT 
                        relative_path,
                        package_code,
                        model_family,
                        LENGTH(semantic_purpose) as purpose_length,
                        array_length(user_scenarios, 1) as scenarios_count,
                        array_length(related_concepts, 1) as concepts_count,
                        array_length(typical_errors, 1) as errors_count,
                        LENGTH(embedding_text) as embedding_text_length,
                        processed_at
                    FROM modules 
                    ORDER BY processed_at DESC
                """)
                
                modules = cur.fetchall()
                print(f"Total modules: {len(modules)}")
                
                for module in modules:
                    print(f"\n  📁 {module['relative_path']}")
                    print(f"     Package: {module['package_code'] or 'None'}")
                    print(f"     Family: {module['model_family']}")
                    print(f"     Purpose: {module['purpose_length']} chars")
                    print(f"     Scenarios: {module['scenarios_count'] or 0}")
                    print(f"     Concepts: {module['concepts_count'] or 0}")
                    print(f"     Errors: {module['errors_count'] or 0}")
                    print(f"     Embedding text: {module['embedding_text_length']} chars")
                    print(f"     Processed: {module['processed_at']}")
                
                # Check packages table
                print(f"\n📦 PACKAGES TABLE:")
                cur.execute("SELECT COUNT(*) FROM packages")
                packages_count = cur.fetchone()['count']
                print(f"Total packages: {packages_count}")
                
                # Check workflows table  
                print(f"\n🔄 WORKFLOWS TABLE:")
                cur.execute("SELECT COUNT(*) FROM workflows")
                workflows_count = cur.fetchone()['count']
                print(f"Total workflows: {workflows_count}")
                
                # Check processing log
                print(f"\n📋 PROCESSING LOG:")
                cur.execute("SELECT COUNT(*) FROM processing_log")
                log_count = cur.fetchone()['count']
                print(f"Total log entries: {log_count}")
                
                # Show sample semantic analysis
                print(f"\n🧠 SAMPLE SEMANTIC ANALYSIS:")
                cur.execute("""
                    SELECT 
                        relative_path,
                        package_code,
                        semantic_purpose,
                        user_scenarios[1] as first_scenario,
                        related_concepts[1] as first_concept
                    FROM modules 
                    WHERE package_code IS NOT NULL
                    LIMIT 2
                """)
                
                samples = cur.fetchall()
                for sample in samples:
                    print(f"\n  📁 {sample['relative_path']} ({sample['package_code']})")
                    print(f"     Purpose: {sample['semantic_purpose'][:100]}...")
                    if sample['first_scenario']:
                        print(f"     Scenario: {sample['first_scenario'][:80]}...")
                    if sample['first_concept']:
                        print(f"     Concept: {sample['first_concept']}")
                
                # Test embedding search capability
                print(f"\n🔍 TESTING EMBEDDING SEARCH:")
                print("Searching for 'sparse matrix solver'...")
                
                cur.execute("""
                    SELECT 
                        relative_path,
                        package_code,
                        semantic_purpose,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM modules
                    ORDER BY embedding <=> %s::vector
                    LIMIT 3
                """, ("[0] * 1536", "[0] * 1536"))  # Placeholder - would need actual embedding
                
                print("(Note: Need actual embeddings for real similarity search)")
                
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    check_tables()