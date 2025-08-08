#!/usr/bin/env python3
"""
Add v00/v02 columns to pyemu_workflows table to enable ultra-discriminative embeddings
Similar to what we did for flopy_workflows
"""

import sys
sys.path.append('/home/danilopezmella/flopy_expert')
import psycopg2
import config
from datetime import datetime

def main():
    print("=" * 80)
    print("Adding v00/v02 Columns to PyEMU Workflows")
    print("=" * 80)
    print()
    
    conn = psycopg2.connect(config.NEON_CONNECTION_STRING)
    cur = conn.cursor()
    
    try:
        # Step 1: Add v02 columns only
        print("📝 Adding v02 columns for ultra-discriminative embeddings...")
        columns_to_add = [
            ('analysis_v02', 'JSONB'),
            ('emb_string_02', 'TEXT'),
            ('dspy_emb_02', 'vector(1536)')
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                cur.execute(f"""
                    ALTER TABLE pyemu_workflows 
                    ADD COLUMN IF NOT EXISTS {col_name} {col_type}
                """)
                conn.commit()
                print(f"  ✅ Added {col_name}")
            except psycopg2.Error as e:
                conn.rollback()
                if "already exists" in str(e):
                    print(f"  ℹ️ {col_name} already exists")
                else:
                    print(f"  ❌ Error adding {col_name}: {e}")
        
        # No need to copy or create v00 - we're only doing v02 for consistency
        
        # Step 2: Verify the update
        print("\n✅ Verification:")
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(embedding) as with_baseline_embeddings,
                COUNT(analysis_v02) as with_v02_analysis,
                COUNT(dspy_emb_02) as with_v02_embeddings
            FROM pyemu_workflows
        """)
        
        result = cur.fetchone()
        print(f"  Total workflows: {result[0]}")
        print(f"  With baseline embeddings: {result[1]}")
        print(f"  With v02 analysis: {result[2]} (ready for ultra-discriminative generation)")
        print(f"  With v02 embeddings: {result[3]} (ready for embedding creation)")
        
        print("\n🎯 Next Steps:")
        print("  1. Run generate_pyemu_analysis_v02.py to create ultra-discriminative analysis")
        print("  2. Generate v02 embeddings from the ultra-discriminative analysis")
        print("  3. Test v02 vs v00 performance on PyEMU workflows")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()