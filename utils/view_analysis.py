#!/usr/bin/env python3
"""
View the detailed semantic analysis for the processed modules
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import config

def view_analysis():
    """View the detailed semantic analysis"""
    
    print("🧠 Detailed Semantic Analysis")
    print("=" * 60)
    
    try:
        with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                
                cur.execute("""
                    SELECT 
                        relative_path,
                        package_code,
                        semantic_purpose,
                        user_scenarios,
                        related_concepts,
                        typical_errors,
                        embedding_text
                    FROM modules 
                    WHERE package_code IS NOT NULL
                    ORDER BY processed_at DESC
                    LIMIT 2
                """)
                
                modules = cur.fetchall()
                
                for i, module in enumerate(modules, 1):
                    print(f"\n{'='*60}")
                    print(f"MODULE {i}: {module['relative_path']}")
                    print(f"Package Code: {module['package_code']}")
                    print(f"{'='*60}")
                    
                    print(f"\n📝 PURPOSE:")
                    print(f"{module['semantic_purpose']}")
                    
                    if module['user_scenarios']:
                        print(f"\n👥 USER SCENARIOS:")
                        for j, scenario in enumerate(module['user_scenarios'], 1):
                            print(f"{j}. {scenario}")
                    
                    if module['related_concepts']:
                        print(f"\n🔗 RELATED CONCEPTS:")
                        for concept in module['related_concepts']:
                            print(f"• {concept}")
                    
                    if module['typical_errors']:
                        print(f"\n⚠️  TYPICAL ERRORS:")
                        for error in module['typical_errors']:
                            print(f"• {error}")
                    
                    print(f"\n📊 EMBEDDING TEXT SAMPLE:")
                    print(f"{module['embedding_text'][:200]}...")
                
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    view_analysis()