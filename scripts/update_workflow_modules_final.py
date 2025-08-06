#!/usr/bin/env python3
"""
Final version: Update workflow modules with precise extraction.
"""

import re
import psycopg2
from psycopg2.extras import execute_values
import config
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_flopy_patterns(source_code: str) -> set:
    """
    Extract all FloPy usage patterns from source code.
    """
    patterns = set()
    
    # Pattern 1: import flopy or import flopy.x.y
    for match in re.finditer(r'import\s+(flopy(?:\.[\w.]+)?)', source_code):
        patterns.add(match.group(1))
    
    # Pattern 2: from flopy.x.y import z
    for match in re.finditer(r'from\s+(flopy(?:\.[\w.]+)?)\s+import', source_code):
        patterns.add(match.group(1))
    
    # Pattern 3: flopy.x.y.ClassName(...) usage
    for match in re.finditer(r'(flopy\.[\w.]+)\(', source_code):
        patterns.add(match.group(1))
    
    return patterns


def map_patterns_to_modules(conn, patterns: set) -> list:
    """
    Map FloPy patterns to actual module files.
    Returns list of (module_id, relative_path, pattern) tuples.
    """
    matches = []
    
    with conn.cursor() as cur:
        for pattern in patterns:
            # Try different mapping strategies
            
            # 1. Direct file match (e.g., flopy.utils.binaryfile -> flopy/utils/binaryfile.py)
            file_path = pattern.replace('.', '/') + '.py'
            cur.execute(
                "SELECT id, relative_path FROM flopy_modules WHERE relative_path = %s",
                (file_path,)
            )
            result = cur.fetchone()
            if result:
                matches.append((result[0], result[1], pattern))
                continue
            
            # 2. For class usage patterns, try to find the module
            # e.g., flopy.mf6.modflow.mfgwfchd.ModflowGwfchd -> flopy/mf6/modflow/mfgwfchd.py
            if pattern.count('.') >= 3:
                # This might be a class reference, try without the last part
                parts = pattern.split('.')
                module_path = '/'.join(parts[:-1]) + '.py'
                cur.execute(
                    "SELECT id, relative_path FROM flopy_modules WHERE relative_path = %s",
                    (module_path,)
                )
                result = cur.fetchone()
                if result:
                    matches.append((result[0], result[1], pattern))
                    continue
            
            # 3. For high-level imports like flopy.mf6, find the __init__.py or main module
            if pattern in ['flopy', 'flopy.mf6', 'flopy.modflow', 'flopy.utils']:
                # These are package imports, find key modules in that package
                package_path = pattern.replace('.', '/') + '/'
                cur.execute(
                    """
                    SELECT id, relative_path 
                    FROM flopy_modules 
                    WHERE relative_path LIKE %s
                    AND (relative_path LIKE '%%__init__.py' 
                         OR relative_path LIKE '%%mf6.py'
                         OR relative_path LIKE '%%modflow.py')
                    LIMIT 1
                    """,
                    (package_path + '%',)
                )
                result = cur.fetchone()
                if result:
                    matches.append((result[0], result[1], pattern))
    
    return matches


def update_workflow_modules():
    """Update workflow module relationships with precise extraction."""
    
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            # Clear existing data
            logger.info("Clearing existing workflow-module relationships...")
            cur.execute("DELETE FROM workflow_module_usage")
            cur.execute("UPDATE flopy_workflows SET modules_used = '{}'")
            conn.commit()
            
            # Get all workflows
            cur.execute("""
                SELECT id, tutorial_file, source_code, title
                FROM flopy_workflows 
                WHERE source_code IS NOT NULL
                ORDER BY tutorial_file
            """)
            
            workflows = cur.fetchall()
            total = len(workflows)
            logger.info(f"Processing {total} workflows...")
            
            # Track statistics
            total_matches = 0
            workflows_with_modules = 0
            
            for idx, (workflow_id, tutorial_file, source_code, title) in enumerate(workflows, 1):
                if idx % 10 == 0:
                    logger.info(f"Progress: {idx}/{total}")
                
                try:
                    # Extract FloPy patterns
                    patterns = extract_flopy_patterns(source_code)
                    
                    if patterns:
                        # Map to actual modules
                        matches = map_patterns_to_modules(conn, patterns)
                        
                        if matches:
                            workflows_with_modules += 1
                            total_matches += len(matches)
                            
                            # Insert relationships
                            usage_data = [
                                (workflow_id, module_id)
                                for module_id, _, _ in matches
                            ]
                            
                            # Remove duplicates
                            usage_data = list(set(usage_data))
                            
                            execute_values(
                                cur,
                                """
                                INSERT INTO workflow_module_usage (workflow_id, module_id)
                                VALUES %s
                                ON CONFLICT (workflow_id, module_id) DO NOTHING
                                """,
                                usage_data
                            )
                            
                            # Update modules_used array with unique paths
                            module_paths = list(set(path for _, path, _ in matches))
                            cur.execute(
                                """
                                UPDATE flopy_workflows 
                                SET modules_used = %s
                                WHERE id = %s
                                """,
                                (module_paths, workflow_id)
                            )
                            
                            conn.commit()
                            
                except Exception as e:
                    logger.error(f"Error processing {tutorial_file}: {str(e)}")
                    conn.rollback()
                    continue
            
            logger.info(f"\nProcessing complete!")
            logger.info(f"Workflows with modules: {workflows_with_modules}/{total}")
            logger.info(f"Total module matches: {total_matches}")
            
            # Show sample results
            logger.info("\nSample results:")
            cur.execute("""
                SELECT fw.tutorial_file, fw.title, 
                       array_length(fw.modules_used, 1) as num_modules,
                       fw.modules_used[1:3] as sample_modules
                FROM flopy_workflows fw
                WHERE fw.modules_used != '{}'
                ORDER BY array_length(fw.modules_used, 1) DESC
                LIMIT 5
            """)
            
            for row in cur.fetchall():
                logger.info(f"\n{row[0]}:")
                logger.info(f"  Title: {row[1]}")
                logger.info(f"  Modules: {row[2]}")
                logger.info(f"  Sample: {row[3]}")


if __name__ == "__main__":
    update_workflow_modules()
