#!/usr/bin/env python3
"""
Add modules_used column to flopy_workflows table and create workflow-module relationships.

This script:
1. Adds a modules_used column to flopy_workflows table
2. Creates a workflow_module_usage table to track which modules are used in which workflows
3. Parses workflow source code to extract FloPy module imports
4. Updates the database with module usage information
"""

import re
import ast
import psycopg2
from psycopg2.extras import execute_values
import config
from typing import List, Set, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_flopy_imports(source_code: str) -> Set[str]:
    """
    Extract FloPy module imports from source code.
    Returns a set of relative paths like 'flopy/mf6/modflow/mfgwfwel.py'
    """
    flopy_modules = set()
    
    # Pattern to match various import styles
    # import flopy
    # from flopy import modflow
    # from flopy.mf6 import MFSimulation
    # from flopy.modflow import Modflow
    # import flopy.utils.binaryfile as bf
    
    import_patterns = [
        r'from\s+(flopy(?:\.[\w.]+)?)\s+import',  # from flopy.x.y import
        r'import\s+(flopy(?:\.[\w.]+)?)',         # import flopy.x.y
    ]
    
    for pattern in import_patterns:
        matches = re.findall(pattern, source_code)
        for match in matches:
            # Convert import path to potential module paths
            # e.g., 'flopy.mf6.modflow' -> 'flopy/mf6/modflow'
            module_path = match.replace('.', '/')
            flopy_modules.add(module_path)
    
    # Also extract specific class imports which might map to modules
    class_import_pattern = r'from\s+flopy(?:\.[\w.]+)?\s+import\s+([\w,\s]+)'
    class_matches = re.findall(class_import_pattern, source_code)
    for match in class_matches:
        # Clean up and split multiple imports
        classes = [c.strip() for c in match.split(',')]
        flopy_modules.update(classes)  # We'll match these against class names in modules
    
    return flopy_modules


def match_imports_to_modules(conn, imports: Set[str]) -> List[Tuple[str, str]]:
    """
    Match import paths and class names to actual module paths in flopy_modules table.
    Returns list of (module_id, relative_path) tuples.
    """
    matched_modules = []
    
    with conn.cursor() as cur:
        # For each import, try to find matching modules
        for imp in imports:
            # Direct path match (e.g., 'flopy/mf6/modflow' matches modules in that directory)
            cur.execute("""
                SELECT id, relative_path 
                FROM flopy_modules 
                WHERE relative_path LIKE %s
            """, (f"{imp}%.py",))
            
            results = cur.fetchall()
            matched_modules.extend(results)
            
            # Class name match - check if imp matches a class name in docstring
            if not results and not '/' in imp:  # Likely a class name
                cur.execute("""
                    SELECT id, relative_path
                    FROM flopy_modules
                    WHERE module_docstring ILIKE %s
                    OR relative_path ILIKE %s
                    LIMIT 5
                """, (f"%class {imp}%", f"%{imp.lower()}%"))
                
                class_results = cur.fetchall()
                matched_modules.extend(class_results)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_modules = []
    for module in matched_modules:
        if module[0] not in seen:
            seen.add(module[0])
            unique_modules.append(module)
    
    return unique_modules


def update_database():
    """Update database schema and populate module usage data."""
    
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            # 1. Add modules_used column if it doesn't exist
            logger.info("Adding modules_used column to flopy_workflows...")
            cur.execute("""
                ALTER TABLE flopy_workflows 
                ADD COLUMN IF NOT EXISTS modules_used TEXT[] DEFAULT '{}'
            """)
            
            # 2. Create workflow_module_usage table for detailed relationships
            logger.info("Creating workflow_module_usage table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS workflow_module_usage (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    workflow_id UUID NOT NULL REFERENCES flopy_workflows(id) ON DELETE CASCADE,
                    module_id UUID NOT NULL REFERENCES flopy_modules(id) ON DELETE CASCADE,
                    import_type TEXT,  -- 'direct', 'from_import', 'class_import'
                    confidence FLOAT DEFAULT 1.0,  -- Confidence score for the match
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(workflow_id, module_id)
                )
            """)
            
            # 3. Create indexes for performance
            logger.info("Creating indexes...")
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_workflow_module_workflow 
                ON workflow_module_usage(workflow_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_workflow_module_module 
                ON workflow_module_usage(module_id)
            """)
            
            conn.commit()
            
            # 4. Process each workflow
            logger.info("Processing workflows to extract module usage...")
            cur.execute("""
                SELECT id, tutorial_file, source_code 
                FROM flopy_workflows 
                WHERE source_code IS NOT NULL
            """)
            
            workflows = cur.fetchall()
            total = len(workflows)
            logger.info(f"Found {total} workflows to process")
            
            for idx, (workflow_id, tutorial_file, source_code) in enumerate(workflows, 1):
                if idx % 10 == 0:
                    logger.info(f"Processing workflow {idx}/{total}: {tutorial_file}")
                
                try:
                    # Extract imports from source code
                    imports = extract_flopy_imports(source_code)
                    
                    # Match imports to actual modules
                    matched_modules = match_imports_to_modules(conn, imports)
                    
                    if matched_modules:
                        # Insert into relationship table
                        usage_data = [
                            (workflow_id, module_id)
                            for module_id, _ in matched_modules
                        ]
                        
                        execute_values(
                            cur,
                            """
                            INSERT INTO workflow_module_usage (workflow_id, module_id)
                            VALUES %s
                            ON CONFLICT (workflow_id, module_id) DO NOTHING
                            """,
                            usage_data
                        )
                        
                        # Update modules_used array in workflows table
                        module_paths = [path for _, path in matched_modules]
                        cur.execute(
                            """
                            UPDATE flopy_workflows 
                            SET modules_used = %s
                            WHERE id = %s
                            """,
                            (module_paths, workflow_id)
                        )
                        
                        # Commit after each successful workflow
                        conn.commit()
                        
                except Exception as e:
                    logger.error(f"Error processing {tutorial_file}: {str(e)}")
                    # Rollback the failed transaction
                    conn.rollback()
                    continue
            
            conn.commit()
            logger.info("Module extraction complete!")
            
            # 5. Show statistics
            cur.execute("SELECT COUNT(DISTINCT workflow_id) FROM workflow_module_usage")
            workflows_with_modules = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(DISTINCT module_id) FROM workflow_module_usage")
            unique_modules_used = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM workflow_module_usage")
            total_relationships = cur.fetchone()[0]
            
            logger.info(f"\nStatistics:")
            logger.info(f"  Workflows with identified modules: {workflows_with_modules}/{total}")
            logger.info(f"  Unique modules used across workflows: {unique_modules_used}")
            logger.info(f"  Total workflow-module relationships: {total_relationships}")


if __name__ == "__main__":
    update_database()
