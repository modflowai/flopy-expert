#!/usr/bin/env python3
"""
Fix MFUSG source_code truncation by reprocessing with full source code.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import config
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fix_mfusg_source_code():
    """Update MFUSG modules with full source code"""
    
    # Get FloPy repository path
    flopy_repo = Path('/home/danilopezmella/flopy_expert/flopy')
    
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            # Get all MFUSG modules
            cur.execute("""
                SELECT id, relative_path, length(source_code) as current_length
                FROM flopy_modules 
                WHERE model_family = 'mfusg'
                ORDER BY relative_path
            """)
            
            mfusg_modules = cur.fetchall()
            logger.info(f"Found {len(mfusg_modules)} MFUSG modules to check")
            
            updated = 0
            for module_id, relative_path, current_length in mfusg_modules:
                file_path = flopy_repo / relative_path
                
                if not file_path.exists():
                    logger.warning(f"File not found: {relative_path}")
                    continue
                
                # Read full source code
                try:
                    full_source = file_path.read_text(encoding='utf-8')
                    full_length = len(full_source)
                    
                    if full_length > current_length:
                        # Update with full source code
                        cur.execute("""
                            UPDATE flopy_modules 
                            SET source_code = %s
                            WHERE id = %s
                        """, (full_source, module_id))
                        
                        updated += 1
                        logger.info(f"✅ Updated {relative_path}: {current_length} → {full_length} chars")
                    else:
                        logger.info(f"  Skipped {relative_path}: already has full source ({current_length} chars)")
                        
                except Exception as e:
                    logger.error(f"❌ Error reading {relative_path}: {e}")
            
            conn.commit()
            logger.info(f"\n🎉 Updated {updated} MFUSG modules with full source code")
            
            # Verify the fix
            cur.execute("""
                SELECT relative_path, length(source_code) as length
                FROM flopy_modules 
                WHERE model_family = 'mfusg'
                ORDER BY length(source_code) DESC
                LIMIT 5
            """)
            
            logger.info("\n📊 Top 5 MFUSG modules by source code length:")
            for path, length in cur.fetchall():
                logger.info(f"  {path}: {length:,} chars")


if __name__ == "__main__":
    fix_mfusg_source_code()