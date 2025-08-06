#!/usr/bin/env python3
"""
Quick check of what modules are actually used in a simple example.
"""

import psycopg2
import config
import re

# Connect to database
with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
    with conn.cursor() as cur:
        # Get the simple model example
        cur.execute("""
            SELECT source_code 
            FROM flopy_workflows 
            WHERE tutorial_file = 'Notebooks/mf6_simple_model_example.py'
        """)
        
        source_code = cur.fetchone()[0]
        
        # Extract all flopy usage patterns
        patterns = [
            r'import\s+(flopy(?:\.[\w.]+)?)',
            r'from\s+(flopy(?:\.[\w.]+)?)\s+import',
            r'(flopy\.[\w.]+\.[\w.]+)\('
        ]
        
        all_matches = set()
        for pattern in patterns:
            matches = re.findall(pattern, source_code)
            all_matches.update(matches)
        
        print("FloPy usage in mf6_simple_model_example.py:")
        for match in sorted(all_matches):
            print(f"  - {match}")
            
        # Now let's see what actual modules these map to
        print("\nMapping to actual modules:")
        
        # For each match, try to find corresponding modules
        for match in sorted(all_matches):
            # Convert to path format
            path = match.replace('.', '/') + '.py'
            
            cur.execute("""
                SELECT relative_path, package_code 
                FROM flopy_modules 
                WHERE relative_path = %s
            """, (path,))
            
            result = cur.fetchone()
            if result:
                print(f"  {match} -> {result[0]} (package: {result[1] or 'N/A'})")
