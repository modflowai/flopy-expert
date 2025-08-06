#!/usr/bin/env python3
"""
Improved module extraction for flopy_workflows.
This version does more precise matching based on actual imports in the source code.
"""

import re
import ast
import psycopg2
from psycopg2.extras import execute_values
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from typing import List, Set, Tuple, Dict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_flopy_usage(source_code: str) -> Dict[str, Set[str]]:
    """
    Extract FloPy usage patterns from source code.
    Returns a dict with:
    - direct_imports: modules imported directly (import flopy.x.y)
    - from_imports: modules imported via from (from flopy.x.y import z)
    - class_usage: classes used from flopy
    """
    usage = {
        'direct_imports': set(),
        'from_imports': set(),
        'class_usage': set()
    }
    
    # Pattern 1: Direct imports like "import flopy" or "import flopy.utils.binaryfile"
    direct_pattern = r'import\s+(flopy(?:\.[\w.]+)?)(?:\s+as\s+\w+)?'
    for match in re.finditer(direct_pattern, source_code):
        module_path = match.group(1)
        usage['direct_imports'].add(module_path)
    
    # Pattern 2: From imports like "from flopy.mf6 import MFSimulation"
    from_pattern = r'from\s+(flopy(?:\.[\w.]+)?)\s+import\s+([\w,\s]+)'
    for match in re.finditer(from_pattern, source_code):
        module_path = match.group(1)
        imports = match.group(2)
        usage['from_imports'].add(module_path)
        
        # Extract the specific classes/functions imported
        for item in imports.split(','):
            item = item.strip()
            if item and not item.startswith('*'):
                usage['class_usage'].add(item)
    
    # Pattern 3: Usage patterns like "flopy.mf6.ModflowGwf" or "flopy.utils.binaryfile.HeadFile"
    usage_pattern = r'flopy\.([\w.]+\.\w+)\('
    for match in re.finditer(usage_pattern, source_code):
        full_path = 'flopy.' + match.group(1)
        # This is likely a class instantiation
        parts = full_path.split('.')
        if len(parts) > 2:
            # Extract the module path (all but the last part which is the class)
            module_path = '.'.join(parts[:-1])
            class_name = parts[-1]
            usage['direct_imports'].add(module_path)
            usage['class_usage'].add(class_name)
    
    return usage


def map_usage_to_modules(conn, usage: Dict[str, Set[str]]) -> List[Tuple[str, str, float]]:
    """
    Map extracted usage patterns to actual modules in the database.
    Returns list of (module_id, relative_path, confidence) tuples.
    """
    matched_modules = []
    
    with conn.cursor() as cur:
        # 1. Match direct imports to module paths
        for imp in usage['direct_imports']:
            # Convert dot notation to path notation
            path_pattern = imp.replace('.', '/') + '.py'
            
            # Try exact match first
            cur.execute("""
                SELECT id, relative_path 
                FROM flopy_modules 
                WHERE relative_path = %s
            """, (path_pattern,))
            
            result = cur.fetchone()
            if result:
                matched_modules.append((result[0], result[1], 1.0))  # High confidence
            else:
                # Try prefix match for package imports
                cur.execute("""
                    SELECT id, relative_path 
                    FROM flopy_modules 
                    WHERE relative_path LIKE %s
                    ORDER BY relative_path
                    LIMIT 10
                """, (path_pattern.replace('.py', '') + '/%',))
                
                results = cur.fetchall()
                for r in results:
                    matched_modules.append((r[0], r[1], 0.8))  # Medium confidence
        
        # 2. Match from imports
        for imp in usage['from_imports']:
            path_pattern = imp.replace('.', '/') + '.py'
            
            cur.execute("""
                SELECT id, relative_path 
                FROM flopy_modules 
                WHERE relative_path = %s
                   OR relative_path LIKE %s
                LIMIT 5
            """, (path_pattern, path_pattern.replace('.py', '') + '/%'))
            
            results = cur.fetchall()
            for r in results:
                matched_modules.append((r[0], r[1], 0.9))  # High confidence
        
        # 3. Match class usage to modules containing those classes
        for class_name in usage['class_usage']:
            # Search for modules that might contain this class
            cur.execute("""
                SELECT id, relative_path
                FROM flopy_modules
                WHERE module_docstring LIKE %s
                   OR relative_path ILIKE %s
                   OR source_code LIKE %s
                LIMIT 5
            """, (
                f'%class {class_name}%',
                f'%{class_name.lower()}%',
                f'%class {class_name}%'
            ))
            
            results = cur.fetchall()
            for r in results:
                matched_modules.append((r[0], r[1], 0.7))  # Lower confidence
    
    # Deduplicate and keep highest confidence for each module
    module_confidence = {}
    for module_id, path, confidence in matched_modules:
        if module_id not in module_confidence or confidence > module_confidence[module_id][1]:
            module_confidence[module_id] = (path, confidence)
    
    # Return as list sorted by confidence
    return [(mid, path, conf) for mid, (path, conf) in module_confidence.items()]


def analyze_and_update():
    """Analyze workflows and update module usage with improved precision."""
    
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            # First, let's clear the existing data to start fresh
            logger.info("Clearing existing workflow-module relationships...")
            cur.execute("TRUNCATE TABLE workflow_module_usage")
            cur.execute("UPDATE flopy_workflows SET modules_used = '{}'")
            conn.commit()
            
            # Get all workflows
            cur.execute("""
                SELECT id, tutorial_file, source_code 
                FROM flopy_workflows 
                WHERE source_code IS NOT NULL
                ORDER BY tutorial_file
            """)
            
            workflows = cur.fetchall()
            total = len(workflows)
            logger.info(f"Found {total} workflows to analyze")
            
            # Process each workflow
            for idx, (workflow_id, tutorial_file, source_code) in enumerate(workflows, 1):
                if idx % 10 == 0:
                    logger.info(f"Processing workflow {idx}/{total}: {tutorial_file}")
                
                try:
                    # Extract usage patterns
                    usage = extract_flopy_usage(source_code)
                    
                    # Map to actual modules
                    matched_modules = map_usage_to_modules(conn, usage)
                    
                    if matched_modules:
                        # Only keep high confidence matches (>= 0.8)
                        high_confidence = [(mid, path, conf) for mid, path, conf in matched_modules if conf >= 0.8]
                        
                        if high_confidence:
                            # Insert relationships
                            usage_data = [
                                (workflow_id, module_id, 'import', confidence)
                                for module_id, _, confidence in high_confidence
                            ]
                            
                            execute_values(
                                cur,
                                """
                                INSERT INTO workflow_module_usage 
                                (workflow_id, module_id, import_type, confidence)
                                VALUES %s
                                ON CONFLICT (workflow_id, module_id) DO UPDATE
                                SET confidence = EXCLUDED.confidence,
                                    import_type = EXCLUDED.import_type
                                """,
                                usage_data,
                                template="(%s, %s, %s, %s)"
                            )
                            
                            # Update modules_used array
                            module_paths = [path for _, path, _ in high_confidence]
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
            
            logger.info("Analysis complete!")
            
            # Show statistics
            cur.execute("""
                SELECT COUNT(DISTINCT workflow_id) FROM workflow_module_usage WHERE confidence >= 0.8
            """)
            workflows_with_modules = cur.fetchone()[0]
            
            cur.execute("""
                SELECT COUNT(DISTINCT module_id) FROM workflow_module_usage WHERE confidence >= 0.8
            """)
            unique_modules = cur.fetchone()[0]
            
            cur.execute("""
                SELECT AVG(array_length(modules_used, 1)) 
                FROM flopy_workflows 
                WHERE modules_used != '{}'
            """)
            avg_modules = cur.fetchone()[0] or 0
            
            logger.info(f"\nStatistics:")
            logger.info(f"  Workflows with high-confidence modules: {workflows_with_modules}/{total}")
            logger.info(f"  Unique modules used: {unique_modules}")
            logger.info(f"  Average modules per workflow: {avg_modules:.1f}")
            
            # Show a sample
            logger.info("\nSample results:")
            cur.execute("""
                SELECT fw.tutorial_file, array_length(fw.modules_used, 1) as num_modules
                FROM flopy_workflows fw
                WHERE fw.modules_used != '{}'
                ORDER BY fw.tutorial_file
                LIMIT 5
            """)
            
            for row in cur.fetchall():
                logger.info(f"  {row[0]}: {row[1]} modules")


if __name__ == "__main__":
    analyze_and_update()
