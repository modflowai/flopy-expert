#!/usr/bin/env python3
"""
Extract MF6 modules from flopy_modules table to CSV
Exports filename, embedding string, package code, and embedding vector for analysis
"""

import csv
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import psycopg2
import config

def extract_mf6_modules():
    """Extract all MF6 modules from flopy_modules table and save to CSV"""
    
    # Create docs directory if it doesn't exist
    docs_dir = Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    output_file = docs_dir / "mf6_modules_export.csv"
    
    with psycopg2.connect(config.NEON_CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            # Query for all MF6 modules
            cur.execute("""
                SELECT 
                    relative_path,
                    package_code,
                    embedding_text,
                    semantic_purpose
                FROM flopy_modules
                WHERE model_family = 'mf6'
                ORDER BY relative_path
            """)
            
            results = cur.fetchall()
            
            print(f"Found {len(results)} MF6 modules")
            
            # Write to CSV
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow([
                    'filename',
                    'package_code', 
                    'embedding_text',
                    'semantic_purpose'
                ])
                
                # Write data
                for row in results:
                    relative_path, package_code, embedding_text, semantic_purpose = row
                    
                    # Extract just the filename from the path
                    filename = Path(relative_path).name
                    
                    writer.writerow([
                        filename,
                        package_code or '',
                        embedding_text or '',
                        semantic_purpose or ''
                    ])
            
            print(f"✅ Exported {len(results)} MF6 modules to: {output_file}")
            print(f"📊 File size: {output_file.stat().st_size / 1024 / 1024:.1f} MB")
            
            # Show sample of what was exported
            print("\n📋 Sample of exported data:")
            print("Filename | Package | Semantic Purpose (first 80 chars)")
            print("-" * 80)
            
            for i, row in enumerate(results[:5]):
                filename = Path(row[0]).name
                package = row[1] or 'None'
                purpose_sample = (row[3] or 'No purpose')[:80].replace('\n', ' ')
                print(f"{filename:<25} | {package:<7} | {purpose_sample}...")
            
            if len(results) > 5:
                print(f"... and {len(results) - 5} more modules")

if __name__ == "__main__":
    extract_mf6_modules()